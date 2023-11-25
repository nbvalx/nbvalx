# Copyright (C) 2022-2023 by the nbvalx authors
#
# This file is part of nbvalx.
#
# SPDX-License-Identifier: BSD-3-Clause
"""Custom jupyter magics to selectively run cells using tags."""

import types
import typing

import IPython


class IPythonExtensionStatus(object):
    """Storage for extension status."""

    loaded = False
    allowed_tags: typing.ClassVar[typing.List[str]] = []
    current_tag = ""


def register_run_if_allowed_tags(line: str) -> None:
    """Register allowed tags."""
    IPythonExtensionStatus.allowed_tags = [tag.strip() for tag in line.split(",")]


def register_run_if_current_tag(line: str) -> None:
    """Register current tag."""
    line = line.strip()
    assert line in IPythonExtensionStatus.allowed_tags
    IPythonExtensionStatus.current_tag = line


def run_if(line: str, cell: str) -> None:
    """Run cell if the current tag is in the list provided by the magic argument."""
    cell_lines = cell.splitlines()
    code_begins = 0
    while line.endswith("\\"):
        line = line.strip("\\") + cell_lines[code_begins].strip()
        code_begins += 1
    allowed_tags = [tag.strip() for tag in line.split(",")]
    cell = "\n".join(cell_lines[code_begins:])
    if IPythonExtensionStatus.current_tag in allowed_tags:
        result = IPython.get_ipython().run_cell(cell)  # type: ignore[attr-defined, no-untyped-call]
        try:  # pragma: no cover
            result.raise_error()
        except Exception as e:  # pragma: no cover
            # The exception has already been printed to the terminal, there is
            # no need of printing it again
            raise SuppressTracebackMockError(e)


class SuppressTracebackMockError(Exception):
    """Custom exception type used in run_if magic to suppress redundant traceback."""

    pass


def suppress_traceback_handler(
    ipython: IPython.core.interactiveshell.InteractiveShell, etype: typing.Type[BaseException],
    value: BaseException, tb: types.TracebackType, tb_offset: typing.Optional[int] = None
) -> None:  # pragma: no cover
    """Use a custom handler in load_ipython_extension to suppress redundant traceback."""
    pass


def load_ipython_extension(
    ipython: IPython.core.interactiveshell.InteractiveShell
) -> None:
    """Register magics defined in this module when the extension loads."""
    ipython.register_magic_function(register_run_if_allowed_tags, "line")  # type: ignore[no-untyped-call]
    ipython.register_magic_function(register_run_if_current_tag, "line")  # type: ignore[no-untyped-call]
    ipython.register_magic_function(run_if, "cell")  # type: ignore[no-untyped-call]
    ipython.set_custom_exc((SuppressTracebackMockError, ), suppress_traceback_handler)  # type: ignore[no-untyped-call]
    IPythonExtensionStatus.loaded = True
    IPythonExtensionStatus.allowed_tags = []
    IPythonExtensionStatus.current_tag = ""


def unload_ipython_extension(
    ipython: IPython.core.interactiveshell.InteractiveShell
) -> None:
    """Unregister the magics defined in this module when the extension unloads."""
    del ipython.magics_manager.magics["line"]["register_run_if_allowed_tags"]  # type: ignore[union-attr]
    del ipython.magics_manager.magics["line"]["register_run_if_current_tag"]  # type: ignore[union-attr]
    del ipython.magics_manager.magics["cell"]["run_if"]  # type: ignore[union-attr]
    IPythonExtensionStatus.loaded = False
    IPythonExtensionStatus.allowed_tags = []
    IPythonExtensionStatus.current_tag = ""
