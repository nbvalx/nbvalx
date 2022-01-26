# Copyright (C) 2022 by the nbvalx authors
#
# This file is part of nbvalx.
#
# SPDX-License-Identifier: BSD-3-Clause
"""
Utility functions to be used in pytest configuration file for notebooks tests.

nbvalx changes the default behavior of nbval in the following three ways:
    1) Users may start a ipyparallel Cluster and run notebooks tests in parallel
    2) New markers are introduced to mark cells as xfail
    3) Handle selective cell run using tags introduced in magics.py
    4) Print outputs to log file

See also: https://github.com/pytest-dev/pytest/blob/main/src/_pytest/hookspec.py for type hints.
"""

import collections
import contextlib
import copy
import fnmatch
import glob
import os
import re
import typing

try:
    import _pytest.config
    import _pytest.main
    import _pytest.nodes
    import _pytest.runner
    import nbformat
    import nbval.plugin
    import py
    import pytest
except ImportError:  # pragma: no cover
    addoption = None
    sessionstart = None
    collect_file = None
    runtest_setup = None
    runtest_makereport = None
    runtest_teardown = None
else:
    def addoption(parser: _pytest.main.Parser) -> None:
        """Add options to set the number of processes and tag actions."""
        # Number of processors
        parser.addoption("--np", action="store", type=int, default=1, help="Number of MPI processes to use")
        assert (
            not ("OMPI_COMM_WORLD_SIZE" in os.environ  # OpenMPI
                 or "MPI_LOCALNRANKS" in os.environ)), (  # MPICH
            "Please do not start pytest under mpirun. Use the --np pytest option.")
        # Action to carry out on notebooks
        parser.addoption(
            "--ipynb-action", type=str, default="collect-notebooks", help="Action on notebooks with tags")
        # Tag collapse
        parser.addoption("--tag-collapse", action="store_true", help="Collapse notebook to active tag")
        # Work directory
        parser.addoption(
            "--work-dir", type=str, default="", help="Work directory in which to run the tests")

    def sessionstart(session: _pytest.main.Session) -> None:
        """Parameterize jupyter notebooks based on available tags."""
        # Verify that nbval is not explicitly provided on the command line
        nbval = session.config.option.nbval
        assert not nbval, "--nbval is implicitly enabled, do not provide it on the command line"
        # Verify parallel options
        np = session.config.option.np
        assert np > 0
        # Verify action options
        ipynb_action = session.config.option.ipynb_action
        assert ipynb_action in ("create-notebooks", "collect-notebooks")
        # Verify tag options
        tag_collapse = session.config.option.tag_collapse
        assert tag_collapse in (True, False)
        # Verify work directory options
        if session.config.option.work_dir == "":
            session.config.option.work_dir = f".ipynb_pytest/np_{np}/collapse_{tag_collapse}"
        work_dir = session.config.option.work_dir
        assert not work_dir.startswith(os.sep), "Please use a relative path while specifying work directory"
        if np > 1 or ipynb_action != "create-notebooks":
            assert work_dir != ".", (
                "Please use a subdirectory as work directory to prevent losing the original notebooks")
        # Verify if keyword matching (-k option) is enabled, as it will be used to match tags
        keyword = session.config.option.keyword
        # List existing files
        files = list()
        dirs = set()
        for arg in session.config.args:
            dir_or_file, _ = _pytest.main.resolve_collection_argument(session.config.invocation_params.dir, arg)
            if os.path.isdir(dir_or_file):
                for dir_entry in _pytest.pathlib.visit(dir_or_file, session._recurse):
                    if dir_entry.is_file():
                        filepath = str(dir_entry.path)
                        if fnmatch.fnmatch(filepath, "**/*.ipynb"):
                            files.append(filepath)
                    dirs.add(str(dir_or_file))
            else:  # pragma: no cover
                assert fnmatch.fnmatch(dir_or_file, "**/*.ipynb")
                files.append(str(dir_or_file))
                dirs.add(os.path.dirname(dir_or_file))
        session.config.args = list(dirs)
        # Clean up possibly existing notebooks in work directory from a previous run
        if work_dir != ".":
            for dirpath in dirs:
                work_dirpath = os.path.join(dirpath, work_dir)
                if os.path.exists(work_dirpath):  # pragma: no cover
                    for dir_entry in _pytest.pathlib.visit(work_dirpath, session._recurse):
                        if dir_entry.is_file():
                            filepath = str(dir_entry.path)
                            if fnmatch.fnmatch(filepath, "**/*.ipynb"):
                                os.remove(filepath)
        # Process each notebook
        for filepath in files:
            # Read in notebook
            with open(filepath) as f:
                nb = nbformat.read(f, as_version=4)
            # Determine if the run_if extension is used
            run_if_loaded = False
            allowed_tags = []
            for cell in nb.cells:
                if cell.cell_type == "code":
                    if cell.source.startswith("%load_ext nbvalx"):
                        run_if_loaded = True
                        assert len(cell.source.splitlines()) == 1, (
                            "Use a standalone cell for %load_ext nbvalx")
                    elif cell.source.startswith("%register_run_if_allowed_tags"):
                        assert run_if_loaded
                        lines = cell.source.splitlines()
                        assert len(lines) == 1, (
                            "Use a standalone cell for %register_run_if_allowed_tags")
                        line = lines[0].replace("%register_run_if_allowed_tags ", "")
                        allowed_tags = [tag.strip() for tag in line.split(",")]
            # Create temporary copies for each tag to be processed
            nb_tags = dict()
            if run_if_loaded and len(allowed_tags) > 0:
                # Restrict tags to match keyword
                if keyword != "":  # pragma: no cover
                    if keyword in allowed_tags:
                        processed_tags = [keyword]
                    else:
                        processed_tags = []
                else:
                    processed_tags = allowed_tags
                # Process restricted tags
                for tag in processed_tags:
                    # Determine what will be the new notebook path
                    ipynb_path = os.path.join(
                        os.path.dirname(filepath), work_dir,
                        os.path.basename(filepath).replace(".ipynb", f"[{tag}].ipynb"))
                    # Replace tag and, if collapsing notebooks, strip cells with other tags
                    cells_tag = list()
                    for cell in nb.cells:
                        cell_tag = copy.deepcopy(cell)
                        if cell.cell_type == "code":
                            if (cell.source.startswith("%load_ext nbvalx")
                                    or cell.source.startswith("%register_run_if_allowed_tags")):
                                if not tag_collapse:
                                    cells_tag.append(cell_tag)
                            elif cell.source.startswith("%register_run_if_current_tag"):
                                assert len(cell.source.splitlines()) == 1, (
                                    "Use a standalone cell for %register_run_if_current_tag")
                                if not tag_collapse:
                                    cell_tag.source = f"%register_run_if_current_tag {tag}"
                                    cells_tag.append(cell_tag)
                            elif "%%run_if" in cell.source:
                                if tag_collapse:
                                    lines = cell.source.splitlines()
                                    magic_line_index = 0
                                    while not lines[magic_line_index].startswith("%%run_if"):
                                        magic_line_index += 1
                                    assert magic_line_index < len(lines)
                                    line = lines[magic_line_index].replace("%%run_if ", "")
                                    run_if_tags = [tag.strip() for tag in line.split(",")]
                                    if tag in run_if_tags:
                                        lines.remove(lines[magic_line_index])
                                        cell_tag.source = "\n".join(lines)
                                        cells_tag.append(cell_tag)
                                else:
                                    cells_tag.append(cell_tag)
                            else:
                                cells_tag.append(cell_tag)
                        else:
                            cells_tag.append(cell_tag)
                    # Attach cells to a copy of the notebook
                    nb_tag = copy.deepcopy(nb)
                    nb_tag.cells = cells_tag
                    # Store notebook in dictionary
                    nb_tags[ipynb_path] = nb_tag
            else:
                # Create a temporary copy only if no keyword is provided, as untagged
                # notebooks would not match any non null keyword
                if keyword == "":
                    # Determine what will be the new notebook path
                    ipynb_path = os.path.join(
                        os.path.dirname(filepath), work_dir, os.path.basename(filepath))
                    # Store notebook in dictionary
                    nb_tags[ipynb_path] = nb
            # Replace notebook name
            for (ipynb_path, nb_tag) in nb_tags.items():
                for cell in nb_tag.cells:
                    if cell.cell_type == "code":
                        if cell.source.startswith("__notebook_name__"):
                            assert len(cell.source.splitlines()) == 1, (
                                "Use a standalone cell for __notebook_name__")
                            notebook_name_tag = os.path.relpath(
                                ipynb_path, os.path.dirname(filepath))
                            cell.source = f'__notebook_name__ = "{notebook_name_tag}"'
            # Comment out xfail cells when only asked to create notebooks, so that the user
            # who requested them can run all cells
            if ipynb_action == "create-notebooks" and work_dir != ".":
                for cell in nb_tag.cells:
                    if cell.cell_type == "code":
                        if "# PYTEST_XFAIL" in cell.source:
                            lines = cell.source.splitlines()
                            xfail_line_index = 0
                            while not lines[xfail_line_index].startswith("# PYTEST_XFAIL"):
                                xfail_line_index += 1
                            assert xfail_line_index < len(lines)
                            xfail_code_index = xfail_line_index + 1
                            while lines[xfail_code_index].startswith("#"):
                                xfail_code_index += 1
                            assert xfail_code_index < len(lines)
                            quotes = "'''" if '"""' in cell.source else '"""'
                            lines.insert(xfail_code_index, quotes)
                            lines.append(quotes + "  # noqa: D")
                            cell.source = "\n".join(lines)
            # Add live stdout redirection to file when running notebooks through pytest
            # Such redirection is not added when only asked to create notebooks, as:
            # * the user who requested notebooks may not want redirection to take place
            # * the additional cell may interfere with flake8 checks
            if ipynb_action != "create-notebooks":
                for (ipynb_path, nb_tag) in nb_tags.items():
                    # Add the live_log magic to every existing cell
                    _add_cell_magic(nb_tag, "%%live_log")
                    # Add a cell on top to define the live_log magic
                    live_log_magic_code = f'''import contextlib

import IPython
import mpi4py
import mpi4py.MPI

import nbvalx.jupyter_magics

def live_log(line: str, cell: str = None) -> None:
    """Redirect notebook to log file."""
    with contextlib.redirect_stdout(open(live_log.__file__, "a", buffering=1)):
        print("---------------------------")
        print()
        print("Input:")
        print(cell.strip("\\n"))
        print()
        print("Output (stdout):")
        result = IPython.get_ipython().run_cell(cell)
        try:
            result.raise_error()
        except Exception as e:
            # The exception has already been printed to the terminal, there is
            # no need of printing it again
            raise nbvalx.jupyter_magics.SuppressTraceback(e)
        finally:
            print()

live_log.__file__ = "{ipynb_path[:-6] + ".log"}"  # noqa: E501
if mpi4py.MPI.COMM_WORLD.size > 1:
    live_log.__file__ += "-" + str(mpi4py.MPI.COMM_WORLD.rank)
open(live_log.__file__, "w").close()

IPython.get_ipython().register_magic_function(live_log, "cell")
IPython.get_ipython().set_custom_exc(
    (nbvalx.jupyter_magics.SuppressTraceback, ), nbvalx.jupyter_magics.suppress_traceback_handler)'''
                    live_log_magic_cell = nbformat.v4.new_code_cell(live_log_magic_code)
                    live_log_magic_cell.id = "live_log_magic"
                    nb_tag.cells.insert(0, live_log_magic_cell)
            # Add parallel support
            if np > 1:
                for (ipynb_path, nb_tag) in nb_tags.items():
                    # Add the px magic to every existing cell
                    _add_cell_magic(nb_tag, "%%px --no-stream" if ipynb_action != "create-notebooks" else "%%px")
                    # Add a cell on top to start a new ipyparallel cluster
                    cluster_start_code = f"""import ipyparallel as ipp

cluster = ipp.Cluster(engines="MPI", profile="mpi", n={np})
cluster.start_and_connect_sync()"""
                    cluster_start_cell = nbformat.v4.new_code_cell(cluster_start_code)
                    cluster_start_cell.id = "cluster_start"
                    nb_tag.cells.insert(0, cluster_start_cell)
                    # Add a cell at the end to stop the ipyparallel cluster
                    cluster_stop_code = """cluster.stop_cluster_sync()"""
                    cluster_stop_cell = nbformat.v4.new_code_cell(cluster_stop_code)
                    cluster_stop_cell.id = "cluster_stop"
                    nb_tag.cells.append(cluster_stop_cell)
            # Write modified notebooks to the work directory
            for (ipynb_path, nb_tag) in nb_tags.items():
                os.makedirs(os.path.dirname(ipynb_path), exist_ok=True)
                with open(ipynb_path, "w") as f:
                    nbformat.write(nb_tag, str(ipynb_path))
        # If the work directory is hidden, patch default norecursepatterns so that the files
        # we created will not get ignored
        if work_dir.startswith("."):
            norecursepatterns = session.config.getini("norecursedirs")
            assert ".*" in norecursepatterns
            norecursepatterns.remove(".*")

    def _add_cell_magic(nb: nbformat.NotebookNode, additional_cell_magic: str) -> None:
        """Add the cell magic to every cell of the notebook."""
        for cell in nb.cells:
            if cell.cell_type == "code":
                cell.source = additional_cell_magic + "\n" + cell.source

    class IPyNbCell(nbval.plugin.IPyNbCell):
        """Customize nbval IPyNbCell to write jupyter cell outputs to log file."""

        _MockExceptionInfo = collections.namedtuple("MockExceptionInfo", ["value"])

        def runtest(self) -> None:
            """
            Redirect jupyter outputs to log file after test execution is completed.

            In contrast to stdout, which is handled by the %%live_log magic, these outputs are not
            written live to the log file. However, we expect the delay to be minimal since jupyter outputs
            such as display_data or execute_result are typically shown when cell execution is completed.
            """
            try:
                super().runtest()
            except nbval.plugin.NbCellError as e:
                # Write the exception to log file
                self._write_to_log_file(
                    "Failure", self.repr_failure(IPyNbCell._MockExceptionInfo(value=e)))
                # Re-raise
                raise
            finally:
                # Write other jupyter outputs to log file
                self._write_to_log_file(
                    "Output (jupyter)", self._transform_jupyter_outputs_to_text(self.test_outputs))

        def _transform_jupyter_outputs_to_text(
                self, outputs: typing.Iterable[nbformat.NotebookNode]) -> typing.Iterable[nbformat.NotebookNode]:
            """Transform outputs that are not processed by the %%live_log magic to a text."""
            outputs = nbval.plugin.coalesce_streams(outputs)
            text_outputs = list()
            for out in outputs:
                if out["output_type"] == "stream":
                    text_outputs.append("[" + out["name"] + "] " + out["text"])
                elif out["output_type"] in ("display_data", "execute_result") and "text/plain" in out["data"]:
                    text_outputs.append("[" + out["output_type"] + "] " + out["data"]["text/plain"])
            if len(text_outputs) > 0:
                return ("\n" + "\n".join(text_outputs)).strip("\n")
            else:
                return ""

        def _write_to_log_file(self, section: str, content: str) -> None:
            """Write content to a section of the live log file."""
            if "%%live_log" in self.cell.source:
                for log_file in glob.glob(str(self.parent.fspath)[:-6] + ".log*"):
                    with contextlib.redirect_stdout(open(log_file, "a", buffering=1)):
                        print(section + ":")
                        print(self._strip_ansi(content))

        def _strip_ansi(self, content: str) -> None:
            """Strip colors while writing to file. See strip_ansi on PyPI."""
            return self._strip_ansi.pattern.sub("", content)

        _strip_ansi.pattern = re.compile(r"\x1B\[\d+(;\d+){0,2}m")

    class IPyNbFile(nbval.plugin.IPyNbFile):
        """Customize nbval IPyNbFile to use IPyNbCell defined in this module rather than nbval's one."""

        def collect(self) -> typing.Iterable[IPyNbCell]:
            """Strip nbval's IPyNbCell to the corresponding class defined in this module."""
            for cell in super().collect():
                yield IPyNbCell.from_parent(
                    cell.parent, name=cell.name, cell_num=cell.cell_num, cell=cell.cell, options=cell.options)

    def collect_file(path: py.path.local, parent: _pytest.nodes.Collector) -> IPyNbFile:
        """Collect IPython notebooks using the custom pytest nbval collector."""
        ipynb_action = parent.config.option.ipynb_action
        work_dir = parent.config.option.work_dir
        if path.fnmatch(f"{work_dir}/*.ipynb") and ipynb_action != "create-notebooks":
            return IPyNbFile.from_parent(parent, fspath=path)

    def runtest_setup(item: _pytest.nodes.Item) -> None:
        """Insert skips on cell failure."""
        # Do the normal setup
        item.setup()
        # If previous cells in a notebook failed skip the rest of the notebook
        if hasattr(item, "_force_skip"):
            if not hasattr(item.cell, "id") or item.cell.id not in ("cluster_stop", ):
                pytest.skip("A previous cell failed")

    def runtest_makereport(item: _pytest.nodes.Item, call: _pytest.runner.CallInfo[None]) -> None:
        """Determine whether the current cell failed or not."""
        if call.when == "call":
            if call.excinfo:
                source = item.cell.source
                lines = source.splitlines()
                while len(lines) > 1 and lines[0].startswith("%"):
                    lines = lines[1:]
                if len(lines) > 1 and lines[0].startswith("# PYTEST_XFAIL"):
                    xfail_line = lines[0]
                    xfail_comment = xfail_line.replace("# ", "")
                    xfail_marker, xfail_reason = xfail_comment.split(": ")
                    assert xfail_marker in (
                        "PYTEST_XFAIL", "PYTEST_XFAIL_IN_PARALLEL",
                        "PYTEST_XFAIL_AND_SKIP_NEXT", "PYTEST_XFAIL_IN_PARALLEL_AND_SKIP_NEXT")
                    if (xfail_marker in ("PYTEST_XFAIL", "PYTEST_XFAIL_AND_SKIP_NEXT")
                        or (xfail_marker in ("PYTEST_XFAIL_IN_PARALLEL", "PYTEST_XFAIL_IN_PARALLEL_AND_SKIP_NEXT")
                            and item.config.option.np > 1)):
                        # This failure was expected: report the reason of xfail.
                        original_repr_failure = item.repr_failure(call.excinfo)
                        call.excinfo._excinfo = (
                            call.excinfo._excinfo[0],
                            pytest.xfail.Exception(xfail_reason.capitalize() + "\n" + original_repr_failure),
                            call.excinfo._excinfo[2])
                    if xfail_marker in ("PYTEST_XFAIL_AND_SKIP_NEXT", "PYTEST_XFAIL_IN_PARALLEL_AND_SKIP_NEXT"):
                        # The failure, even though expected, forces the rest of the notebook to be skipped.
                        item._force_skip = True
                else:  # pragma: no cover
                    # An unexpected error forces the rest of the notebook to be skipped.
                    item._force_skip = True

    def runtest_teardown(item: _pytest.nodes.Item, nextitem: typing.Optional[_pytest.nodes.Item]) -> None:
        """Propagate cell failure."""
        # Do the normal teardown
        item.teardown()
        # Inform next cell of the notebook of failure of any previous cells
        if hasattr(item, "_force_skip"):
            if nextitem is not None and nextitem.name != "Cell 0":
                nextitem._force_skip = True
