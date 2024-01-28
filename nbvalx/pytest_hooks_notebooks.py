# Copyright (C) 2022-2024 by the nbvalx authors
#
# This file is part of nbvalx.
#
# SPDX-License-Identifier: BSD-3-Clause
"""Utility functions to be used in pytest configuration file for notebooks tests."""

import collections
import copy
import fnmatch
import glob
import itertools
import os
import pathlib
import re
import shutil
import textwrap
import typing

import _pytest.main
import nbformat
import nbval.plugin
import pytest

import nbvalx.jupyter_magics


def addoption(parser: pytest.Parser, pluginmanager: pytest.PytestPluginManager) -> None:
    """Add options to set the number of processes and tag actions."""
    # Number of processors
    parser.addoption("--np", type=int, default=1, help="Number of MPI processes to use")
    # Coverage source
    parser.addoption("--coverage-source", type=str, default="", help="The value to be passed to coverage --source")
    parser.addoption(
        "--coverage-run-allow", action="store_true", help=(
            "Allow to start pytest under coverage. This should never be done, except while determining the coverage "
            "of nbvalx notebooks hooks themselves."))
    # Action to carry out on notebooks
    parser.addoption("--ipynb-action", type=str, default="collect-notebooks", help="Action on notebooks with tags")
    # Tag collapse
    parser.addoption("--tag-collapse", action="store_true", help="Collapse notebook to current tags")
    # Work directory
    parser.addoption("--work-dir", type=str, default="", help="Work directory in which to run the tests")
    parser.addoption(
        "--link-data-in-work-dir", action="append", type=str, default=[], help=(
            "Glob patterns of data files that need to be copied to the work directory. The option can be passed "
            "multiple times in case multiple patterns are desired, and they will be joined with an or condition."))


def sessionstart(session: pytest.Session) -> None:
    """Parameterize jupyter notebooks based on available tags."""
    # Verify that nbval is not explicitly provided on the command line
    nbval = session.config.option.nbval
    assert not nbval, "--nbval is implicitly enabled, do not provide it on the command line"
    # Verify that nbval_lax is not explicitly provided on the command line
    nbval_lax = session.config.option.nbval_lax
    assert not nbval_lax, "--nbval-lax is implicitly enabled, do not provide it on the command line"
    # Verify parallel options
    np = session.config.option.np
    assert np > 0
    assert (
        not ("OMPI_COMM_WORLD_SIZE" in os.environ  # OpenMPI
             or "MPI_LOCALNRANKS" in os.environ)), (  # MPICH
        "Please do not start pytest under mpirun. Use the --np pytest option.")
    # Verify if coverage is requested
    coverage_source = session.config.option.coverage_source
    if not session.config.option.coverage_run_allow:  # pragma: no cover
        assert "COVERAGE_RUN" not in os.environ, (
            "Please do not start pytest under coverage. Use the --coverage-source pytest option.")
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
    link_data_in_work_dir = session.config.option.link_data_in_work_dir
    assert not work_dir.startswith(os.sep), "Please use a relative path while specifying work directory"
    if np > 1 or ipynb_action != "create-notebooks":
        assert work_dir != ".", (
            "Please use a subdirectory as work directory to prevent losing the original notebooks")
    # Verify if keyword matching (-k option) is enabled, as it will be used to match tags
    keyword = session.config.option.keyword
    # pathlib.PurePath.full_match is only available in python 3.13+. In the meantime,
    # implement the comparison using fnmatch
    def full_match(path: pathlib.Path, pattern: str) -> bool:
        """Backport of pathlib.PurePath.full_match."""
        return fnmatch.fnmatch(str(path), pattern)
    # List existing files
    files = list()
    dirs = set()
    for arg in session.config.args:
        dir_or_file, _ = _pytest.main.resolve_collection_argument(session.config.invocation_params.dir, arg)
        if dir_or_file.is_dir():
            dir_or_file_candidates = [dir_entry for dir_entry in dir_or_file.rglob("*")]
        else:  # pragma: no cover
            assert full_match(dir_or_file, "**/*.ipynb")
            dir_or_file_candidates = [dir_or_file]
        for dir_entry in dir_or_file_candidates:
            if dir_entry.is_file():
                if (
                    full_match(dir_entry, "**/*.ipynb")
                        and
                    not full_match(dir_entry, f"**/{work_dir}/*.ipynb")
                        and
                    not any(full_match(dir_entry, f"**/{parent}/*.ipynb") for parent in pathlib.Path(work_dir).parents)
                ):
                    files.append(dir_entry)
                    dirs.add(dir_entry.parent)
    session.config.args = [str(dir_) for dir_ in dirs]
    # Clean up possibly existing links and notebooks in work directory from a previous run
    if work_dir != ".":
        cleanup_patterns = [*link_data_in_work_dir, "**/*.ipynb"]
        for dir_ in dirs:
            for dir_entry in dir_.rglob("*"):
                if (
                    any(full_match(dir_entry, cleanup_pattern) for cleanup_pattern in cleanup_patterns)
                        and
                    work_dir in str(dir_entry)
                ):
                    if dir_entry.is_symlink() or dir_entry.is_file():
                        dir_entry.unlink()
                    elif dir_entry.is_dir():  # pragma: no cover
                        shutil.rmtree(dir_entry, ignore_errors=True)
                    if dir_entry in files:  # pragma: no cover
                        files.remove(dir_entry)
    # Link data in the work directory
    if work_dir != "." and len(link_data_in_work_dir) > 0:
        for file_ in files:
            for source_path in file_.parent.rglob("*"):
                if (
                    any(full_match(source_path, pattern) for pattern in link_data_in_work_dir)
                        and
                    work_dir not in str(source_path)
                ):
                    destination_path = file_.parent / work_dir / source_path.relative_to(file_.parent)
                    if not destination_path.exists():
                        destination_path.parent.mkdir(parents=True, exist_ok=True)
                        destination_path.symlink_to(source_path)
    # Process each notebook
    for file_ in files:
        # Read in notebook
        with open(file_) as f:
            nb = nbformat.read(f, as_version=4)  # type: ignore[no-untyped-call]
        # Determine if the run_if extension is used
        run_if_loaded = False
        allowed_tags: typing.Dict[str, typing.Union[typing.List[bool], typing.List[int], typing.List[str]]] = {}
        for cell in nb.cells:
            if cell.cell_type == "code":
                if cell.source.startswith("%load_ext nbvalx"):
                    run_if_loaded = True
                    assert len(cell.source.splitlines()) == 1, "Use a standalone cell for %load_ext nbvalx"
                elif cell.source.startswith("%%register_run_if_allowed_tags"):
                    assert run_if_loaded
                    lines = cell.source.splitlines()
                    assert lines[0] == "%%register_run_if_allowed_tags"
                    nbvalx.jupyter_magics.IPythonExtension.register_run_if_allowed_tags(
                        "", "\n".join(lines[1:]), allowed_tags)
                elif cell.source.startswith("__notebook_basename__"):
                    lines = cell.source.splitlines()
                    assert len(lines) == 2, (
                        f"Use a standalone cell for __notebook_basename__ and __notebook_dirname__ in {file_}")
                    assert lines[0].startswith("__notebook_basename__"), (
                        f"__notebook_basename__ must be on the first line of the cell in {file_}")
                    assert lines[1].startswith("__notebook_dirname__"), (
                        f"__notebook_dirname__ must be on the second line of the cell in {file_}")

                    _, hardcoded_notebook_name = lines[0].split("=")
                    hardcoded_notebook_name = hardcoded_notebook_name.strip()
                    assert hardcoded_notebook_name[0] in ('"', "'")
                    assert hardcoded_notebook_name[-1] in ('"', "'")
                    hardcoded_notebook_name = hardcoded_notebook_name[1:-1]
                    assert hardcoded_notebook_name == file_.name, (
                        f"Wrong attribute __notebook_basename__ for {file_}")

                    _, hardcoded_notebook_path = lines[1].split("=")
                    hardcoded_notebook_path = hardcoded_notebook_path.strip()
                    assert hardcoded_notebook_path in ('""', "''")
        # Determine all possible tag combinations
        allowed_tags_names = list(allowed_tags.keys())
        if len(allowed_tags_names) > 0:
            allowed_tags_values_product = list(itertools.product(*allowed_tags.values()))
            allowed_tags_dict_product = [
                {name: value for (name, value) in zip(allowed_tags_names, values)}
                for values in allowed_tags_values_product]
            allowed_tags_keyword = [
                ",".join(f"{name}={value}" for (name, value) in zip(allowed_tags_names, values))
                for values in allowed_tags_values_product]
        else:
            allowed_tags_values_product = []
            allowed_tags_dict_product = []
            allowed_tags_keyword = []
        assert len(allowed_tags_values_product) == len(allowed_tags_keyword)
        # Create temporary copies for each tag to be processed
        nb_tags = dict()
        if run_if_loaded and len(allowed_tags_keyword) > 0:
            # Process restricted tags
            for (tag_values, tag_dict, tag_keyword) in zip(
                allowed_tags_values_product, allowed_tags_dict_product, allowed_tags_keyword
            ):
                # Restrict tags to match keyword
                if keyword != "":  # pragma: no cover
                    if keyword not in allowed_tags_keyword:
                        continue
                # Determine what will be the new notebook path
                nb_tag_path = file_.parent / work_dir / file_.name.replace(".ipynb", f"[{tag_keyword}].ipynb")
                # Replace tag and, if collapsing notebooks, strip cells with other tags
                cells_tag = list()
                for cell in nb.cells:
                    cell_tag = copy.deepcopy(cell)

                    def store_and_append(source: str) -> None:
                        """Store source in the cell and append it to the notebook."""
                        cell_tag.source = source
                        cells_tag.append(cell_tag)

                    if cell.cell_type == "code":
                        if (cell.source.startswith("%load_ext nbvalx")
                                or cell.source.startswith("%%register_run_if_allowed_tags")):
                            if not tag_collapse:
                                cells_tag.append(cell_tag)
                        elif cell.source.startswith("%%register_run_if_current_tags"):
                            if not tag_collapse:
                                lines = ["%%register_run_if_current_tags"]
                                for (tag_name, tag_value) in zip(allowed_tags_names, tag_values):
                                    lines.append(f"{tag_name} = {tag_value!r}")
                                store_and_append("\n".join(lines))
                        elif "%%run_if" in cell.source:
                            if tag_collapse:
                                lines = cell.source.splitlines()
                                magic_line_index_begin = 0
                                while not lines[magic_line_index_begin].startswith("%%run_if"):
                                    magic_line_index_begin += 1
                                assert magic_line_index_begin < len(lines)
                                line = lines[magic_line_index_begin]
                                magic_line_index_end = magic_line_index_begin + 1
                                while line.endswith("\\"):
                                    line = line.strip("\\") + lines[magic_line_index_end].strip()
                                    magic_line_index_end += 1
                                assert magic_line_index_end < len(lines)
                                magic = line.replace("%%run_if", "")
                                for magic_line_index in range(
                                        magic_line_index_end - 1, magic_line_index_begin - 1, - 1):
                                    lines.remove(lines[magic_line_index])
                                code = "\n".join(lines)
                                nbvalx.jupyter_magics.IPythonExtension.run_if(magic, code, tag_dict, store_and_append)
                            else:
                                cells_tag.append(cell_tag)
                        else:
                            cells_tag.append(cell_tag)
                    elif cell.cell_type == "markdown":
                        if "<!-- keep_if" in cell.source:
                            if tag_collapse:
                                lines = cell.source.splitlines()
                                comment_line_index_begin = 0
                                while not lines[comment_line_index_begin].startswith("<!--"):
                                    comment_line_index_begin += 1
                                assert comment_line_index_begin < len(lines)
                                line = lines[comment_line_index_begin]
                                comment_line_index_end = comment_line_index_begin + 1
                                while not line.endswith("-->"):
                                    line = line + lines[comment_line_index_end].strip()
                                    comment_line_index_end += 1
                                assert comment_line_index_end <= len(lines)
                                comment = line.replace("<!-- keep_if", "").replace("-->", "")
                                for comment_line_index in range(
                                        comment_line_index_end - 1, comment_line_index_begin - 1, - 1):
                                    lines.remove(lines[comment_line_index])
                                text = "\n".join(lines)
                                nbvalx.jupyter_magics.IPythonExtension.run_if(comment, text, tag_dict, store_and_append)
                            else:
                                cells_tag.append(cell_tag)
                        else:
                            cells_tag.append(cell_tag)
                    else:  # pragma: no cover
                        cells_tag.append(cell_tag)
                # Attach cells to a copy of the notebook
                nb_tag = copy.deepcopy(nb)
                nb_tag.cells = cells_tag
                # Store notebook in dictionary
                nb_tags[nb_tag_path] = nb_tag
        else:
            # Create a temporary copy only if no keyword is provided, as untagged
            # notebooks would not match any non null keyword
            if keyword == "":
                # Determine what will be the new notebook path
                nb_tag_path = file_.parent / work_dir / file_.name
                # Store notebook in dictionary
                nb_tags[nb_tag_path] = nb
        # Replace notebook name
        for (nb_tag_path, nb_tag) in nb_tags.items():
            for cell in nb_tag.cells:
                if cell.cell_type == "code":
                    if cell.source.startswith("__notebook_basename__"):
                        def wrap_if_long_line(key: str, value: str) -> str:
                            """Wrap text if line is too long."""
                            if len(value) < 60:
                                return f'__notebook_{key}__ = "{value}"'
                            else:
                                wrapped_value = textwrap.wrap(value, 60)
                                return "\n".join([
                                    f"__notebook_{key}__ = (",
                                    *[f'    "{wrapped_value_part}"' for wrapped_value_part in wrapped_value],
                                    ")"
                                ])

                        cell.source = "\n".join([
                            wrap_if_long_line("basename", str(nb_tag_path.name)),
                            wrap_if_long_line("dirname", str(nb_tag_path.parent))
                        ])
        # Comment out xfail cells when only asked to create notebooks, so that the user
        # who requested them can run all cells
        if ipynb_action == "create-notebooks" and work_dir != ".":
            xfail_and_skip_next = False
            for cell in nb_tag.cells:
                if cell.cell_type == "code":
                    lines = cell.source.splitlines()
                    quotes = "'''" if '"""' in cell.source else '"""'
                    if xfail_and_skip_next:
                        lines.insert(0, quotes + "Skip cell due to a previously xfailed cell.\n")
                        lines.append(quotes)
                    elif "# PYTEST_XFAIL" in cell.source:
                        xfail_line_index = 0
                        while not lines[xfail_line_index].startswith("# PYTEST_XFAIL"):
                            xfail_line_index += 1
                        assert xfail_line_index < len(lines)
                        if "_AND_SKIP_NEXT" in lines[xfail_line_index]:
                            xfail_and_skip_next = True
                        xfail_code_index = xfail_line_index + 1
                        while lines[xfail_code_index].startswith("#"):
                            xfail_code_index += 1
                        assert xfail_code_index < len(lines)
                        lines.insert(xfail_code_index, quotes + "Expect this cell to fail.\n")
                        lines.append(quotes)
                    cell.source = "\n".join(lines)
        # If requested, add coverage testing when running notebooks through pytest
        # Coverage is not added when only asked to create notebooks because:
        # * the user who requested notebook creation may not want coverage testing to take place
        # * the additional cell may interfere with linting
        if coverage_source != "" and ipynb_action != "create-notebooks":
            for (nb_tag_path, nb_tag) in nb_tags.items():
                # Add a cell on top to start coverage collection
                coverage_start_code = f"""import coverage

cov = coverage.Coverage(
    data_file="{os.path.join(os.getcwd(), os.environ.get("COVERAGE_FILE", ".coverage"))}",
    data_suffix={np > 1}, source=["{coverage_source}"]
)
cov.load()
cov.start()
"""
                coverage_start_cell = nbformat.v4.new_code_cell(coverage_start_code)  # type: ignore[no-untyped-call]
                coverage_start_cell.id = "coverage_start"
                nb_tag.cells.insert(0, coverage_start_cell)
                # Add a cell at the end to stop coverage collection
                coverage_stop_code = """cov.stop()
cov.save()
"""
                coverage_stop_cell = nbformat.v4.new_code_cell(coverage_stop_code)  # type: ignore[no-untyped-call]
                coverage_stop_cell.id = "coverage_stop"
                nb_tag.cells.append(coverage_stop_cell)
        # Add live stdout redirection to file when running notebooks through pytest
        # Such redirection is not added when only asked to create notebooks because:
        # * the user who requested notebook creation may not want redirection to take place
        # * the additional cell may interfere with linting
        if ipynb_action != "create-notebooks":
            for (nb_tag_path, nb_tag) in nb_tags.items():
                # Add the live_log magic to every existing cell
                _add_cell_magic(nb_tag, "%%live_log")
                # Add a cell on top to define the live_log magic
                live_log_magic_code = f'''import sys
import types
import typing

import IPython

import nbvalx.jupyter_magics

live_log_suffix = ".log"
try:
    import mpi4py.MPI
except ImportError:
    pass
else:
    if mpi4py.MPI.COMM_WORLD.size > 1:
        live_log_suffix += "-" + str(mpi4py.MPI.COMM_WORLD.rank)


class LiveLogStream(typing.IO):
    """A stream that redirects to both sys.stdout and file."""

    def __init__(self, log_file: typing.IO) -> None:
        self._targets = [sys.stdout, log_file]

    def write(self, string: typing.AnyStr) -> None:
        """Write string to all targets."""
        for target in self._targets:
            target.write(string)


class LiveLogRedirection:
    """A context manager that wraps LiveLogStream to redirect to both sys.stdout and file."""

    def __init__(self, log_file: typing.IO, cell: typing.Optional[str] = None) -> None:
        self._log_file = log_file
        self._cell = cell
        self._old_stdout = None
        self._new_stdout = None

    def __enter__(self) -> None:
        """Replace sys.stdout with a LiveLogStream."""
        # Setup the live log stream
        self._new_stdout = LiveLogStream(self._log_file)
        # Print helper content to the live log stream
        print("===========================", file=self._log_file)
        print(file=self._log_file)
        print("Input:", file=self._log_file)
        if self._cell is not None:
            print(self._cell.strip("\\n"), file=self._log_file)
        else:
            print("empty", file=self._log_file)
        print(file=self._log_file)
        print("Output (stdout):", file=self._log_file)
        # Override standard stdout
        self._old_stdout = sys.stdout
        sys.stdout = self._new_stdout

    def __exit__(
        self, exception_type: typing.Optional[typing.Type[BaseException]],
        exception_value: typing.Optional[BaseException],
        traceback: typing.Optional[types.TracebackType]
    ) -> None:
        """Restore sys.stdout to its original value."""
        # Print a final blank line to live log stream
        print(file=self._log_file)
        # Clean up the live log stream
        self._new_stdout = None
        # Restore standard stdout
        sys.stdout = self._old_stdout
        self._old_stdout = None


def live_log(line: str, cell: typing.Optional[str] = None) -> None:
    """Redirect notebook to log file."""
    with LiveLogRedirection(live_log.__file__, cell):
        result = IPython.get_ipython().run_cell(cell)
        try:
            result.raise_error()
        except Exception as e:
            # The exception has already been printed to the terminal, there is
            # no need to print it again
            raise nbvalx.jupyter_magics.IPythonExtension.SuppressTracebackMockError(e)


live_log_filename = "{str(nb_tag_path)[:-6]}" + live_log_suffix  # noqa: E501
del live_log_suffix
open(live_log_filename, "w").close()
live_log.__file__ = open(live_log_filename, "a", buffering=1)
del live_log_filename

IPython.get_ipython().register_magic_function(live_log, "cell")
IPython.get_ipython().set_custom_exc(
    (nbvalx.jupyter_magics.IPythonExtension.SuppressTracebackMockError, ),
    nbvalx.jupyter_magics.IPythonExtension.suppress_traceback_handler)'''
                live_log_magic_cell = nbformat.v4.new_code_cell(live_log_magic_code)  # type: ignore[no-untyped-call]
                live_log_magic_cell.id = "live_log_magic"
                nb_tag.cells.insert(0, live_log_magic_cell)
        # Add parallel support
        if np > 1:
            for (nb_tag_path, nb_tag) in nb_tags.items():
                # Add the px magic to every existing cell
                _add_cell_magic(nb_tag, "%%px --no-stream" if ipynb_action != "create-notebooks" else "%%px")
                # Add a cell on top to start a new ipyparallel cluster
                cluster_start_code = f"""import ipyparallel as ipp

cluster = ipp.Cluster(engines="MPI", profile="mpi", n={np})
cluster.start_and_connect_sync()"""
                cluster_start_cell = nbformat.v4.new_code_cell(cluster_start_code)  # type: ignore[no-untyped-call]
                cluster_start_cell.id = "cluster_start"
                nb_tag.cells.insert(0, cluster_start_cell)
                # Add a cell at the end to stop the ipyparallel cluster
                cluster_stop_code = """cluster.stop_cluster_sync()"""
                cluster_stop_cell = nbformat.v4.new_code_cell(cluster_stop_code)  # type: ignore[no-untyped-call]
                cluster_stop_cell.id = "cluster_stop"
                nb_tag.cells.append(cluster_stop_cell)
        # Write modified notebooks to the work directory
        for (nb_tag_path, nb_tag) in nb_tags.items():
            nb_tag_path.parent.mkdir(parents=True, exist_ok=True)
            with open(nb_tag_path, "w") as f:
                nbformat.write(nb_tag, f)  # type: ignore[no-untyped-call]
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


class IPyNbCell(nbval.plugin.IPyNbCell):  # type: ignore[misc,no-any-unimported]
    """Customize nbval IPyNbCell to write jupyter cell outputs to log file."""

    _MockExceptionInfo = collections.namedtuple("_MockExceptionInfo", ["value"])

    def runtest(self) -> None:
        """
        Redirect jupyter outputs to log file and determine if exceptions were expected or not.

        In contrast to stdout, which is handled by the %%live_log magic, these outputs are not
        written live to the log file, but only after test execution is completed. However, we expect
        the delay to be minimal since jupyter outputs such as display_data or execute_result are
        typically shown when cell execution is completed.
        """
        try:
            if (
                self.parent._force_skip
                    and
                (not hasattr(self.cell, "id") or self.cell.id not in ("cluster_stop", ))
            ):
                # If previous cells in a notebook failed skip the rest of the notebook
                raise pytest.skip.Exception(msg="A previous cell failed", pytrace=False)
            else:
                # Run the cell
                super().runtest()
        except nbval.plugin.NbCellError as e:
            # Write the exception to log file
            if e.inner_traceback:
                self._write_to_log_file("Traceback", e.inner_traceback)
            # Determine if exception was expected or not
            lines = self.cell.source.splitlines()
            while len(lines) > 1 and lines[0].startswith("%"):
                lines = lines[1:]
            if len(lines) > 1 and lines[0].startswith("# PYTEST_XFAIL"):
                xfail_line = lines[0]
                xfail_comment = xfail_line.replace("# ", "")
                xfail_marker, xfail_reason = xfail_comment.split(": ")
                assert xfail_marker in (
                    "PYTEST_XFAIL", "PYTEST_XFAIL_IN_PARALLEL",
                    "PYTEST_XFAIL_AND_SKIP_NEXT", "PYTEST_XFAIL_IN_PARALLEL_AND_SKIP_NEXT")
                if xfail_marker in ("PYTEST_XFAIL_AND_SKIP_NEXT", "PYTEST_XFAIL_IN_PARALLEL_AND_SKIP_NEXT"):
                    # The failure, even though expected, forces the rest of the notebook to be skipped.
                    self.parent._force_skip = True
                if (xfail_marker in ("PYTEST_XFAIL", "PYTEST_XFAIL_AND_SKIP_NEXT")
                    or (xfail_marker in ("PYTEST_XFAIL_IN_PARALLEL", "PYTEST_XFAIL_IN_PARALLEL_AND_SKIP_NEXT")
                        and self.config.option.np > 1)):
                    # This failure was expected: report the reason of xfail.
                    original_repr_failure = self.repr_failure(IPyNbCell._MockExceptionInfo(value=e))
                    raise pytest.xfail.Exception(
                        msg=xfail_reason.capitalize() + "\n" + original_repr_failure, pytrace=False)
            else:  # pragma: no cover
                # An unexpected error forces the rest of the notebook to be skipped.
                self.parent._force_skip = True
                # Re-raise exception
                raise
        finally:
            # Store outputs
            if self.test_outputs is None:
                self.cell.outputs = []
            else:
                self.cell.outputs = self.test_outputs
            # Write other jupyter outputs to log file
            self._write_to_log_file("Output (jupyter)", self._transform_jupyter_outputs_to_text(self.cell.outputs))
            # Write cell name and id to log file
            self._write_to_log_file("Cell name", self.name)
            if hasattr(self.cell, "id"):
                self._write_to_log_file("Cell ID", self.cell.id)
            else:
                self._write_to_log_file("Cell ID", "not available")

    def _transform_jupyter_outputs_to_text(
            self, outputs: typing.Iterable[nbformat.NotebookNode]) -> str:
        """Transform outputs that are not processed by the %%live_log magic to a text."""
        outputs = nbval.plugin.coalesce_streams(outputs)
        text_outputs = list()
        for out in outputs:
            if out["output_type"] == "stream":
                if out["name"] != "stdout":  # it was already printed by %%live_log
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
                with open(log_file, "a", buffering=1) as log_file_handler:
                    print(section + ":", file=log_file_handler)
                    content = self._strip_ansi(content)
                    if content != "":
                        print(content, file=log_file_handler)
                    print(file=log_file_handler)

    def _strip_ansi(self, content: str) -> str:
        """Strip colors while writing to file. See strip_ansi on PyPI."""
        return self._strip_ansi_pattern.sub("", content)

    _strip_ansi_pattern = re.compile(r"\x1B\[\d+(;\d+){0,3}m")


class IPyNbFile(nbval.plugin.IPyNbFile):  # type: ignore[misc,no-any-unimported]
    """Customize nbval IPyNbFile to use IPyNbCell defined in this module rather than nbval's one."""

    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:  # noqa: ANN401
        """Customize parent initialization by disabling output comparison."""
        super().__init__(*args, **kwargs)
        self.compare_outputs = False
        self._force_skip = False

    def collect(self) -> typing.Iterable[IPyNbCell]:
        """Strip nbval's IPyNbCell to the corresponding class defined in this module."""
        for cell in super().collect():
            yield IPyNbCell.from_parent(
                cell.parent, name=cell.name, cell_num=cell.cell_num, cell=cell.cell, options=cell.options)

    def teardown(self) -> None:
        """Save outputs in a log notebook."""
        # Save outputs in a log notebook
        with open(str(self.fspath)[:-6] + ".log.ipynb", "w") as f:
            nbformat.write(self.nb, f)  # type: ignore[no-untyped-call]
        # Do the normal teardown
        super().teardown()


def collect_file(file_path: pathlib.Path, parent: pytest.Collector) -> typing.Optional[IPyNbFile]:
    """Collect IPython notebooks using the custom pytest nbval collector."""
    ipynb_action = parent.config.option.ipynb_action
    work_dir = parent.config.option.work_dir
    if file_path.match(f"{work_dir}/*.ipynb") and ipynb_action != "create-notebooks":
        return IPyNbFile.from_parent(parent, path=file_path)  # type: ignore[no-any-return]
    else:
        return None
