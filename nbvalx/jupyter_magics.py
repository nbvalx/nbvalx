# Copyright (C) 2022-2024 by the nbvalx authors
#
# This file is part of nbvalx.
#
# SPDX-License-Identifier: BSD-3-Clause
"""Custom jupyter magics to selectively run cells using tags."""

import types
import typing

import IPython


class IPythonExtension(object):
    """Implementation and storage for IPython extension."""

    loaded = False
    allowed_tags: typing.ClassVar[typing.List[str]] = []
    current_tag = ""

    class SuppressTracebackMockError(Exception):
        """Custom exception type used in run_if magic to suppress redundant traceback."""

        pass

    @classmethod
    def _split_magic_from_code(cls, line: str, cell: str) -> typing.Tuple[str, str]:
        """Split the input provided by IPython into a part related to the magic and a part containing the code."""
        cell_lines = cell.splitlines()
        code_begins = 0
        while line.endswith("\\"):
            line = line.strip("\\") + cell_lines[code_begins].strip()
            code_begins += 1
        magic = line
        code = "\n".join(cell_lines[code_begins:])
        return magic, code

    @classmethod
    def register_run_if_allowed_tags(cls, line: str) -> None:
        """Register allowed tags."""
        IPythonExtension.allowed_tags = [tag.strip() for tag in line.split(",")]

    @classmethod
    def register_run_if_current_tag(cls, line: str) -> None:
        """Register current tag."""
        line = line.strip()
        assert line in IPythonExtension.allowed_tags
        IPythonExtension.current_tag = line

    @classmethod
    def run_if(cls, line: str, cell: str) -> None:
        """Run cell if the current tag is in the list provided by the magic argument."""
        magic, code = cls._split_magic_from_code(line, cell)
        allowed_tags = [tag.strip() for tag in magic.split(",")]
        if IPythonExtension.current_tag in allowed_tags:
            result = IPython.get_ipython().run_cell(code)  # type: ignore[attr-defined, no-untyped-call]
            try:  # pragma: no cover
                result.raise_error()
            except Exception as e:  # pragma: no cover
                # The exception has already been printed to the terminal, there is
                # no need to print it again
                raise cls.SuppressTracebackMockError(e)

    @classmethod
    def suppress_traceback_handler(
        cls, ipython: IPython.core.interactiveshell.InteractiveShell, etype: typing.Type[BaseException],
        value: BaseException, tb: types.TracebackType, tb_offset: typing.Optional[int] = None
    ) -> None:  # pragma: no cover
        """Use a custom handler in load_ipython_extension to suppress redundant traceback."""
        pass


def load_ipython_extension(
    ipython: IPython.core.interactiveshell.InteractiveShell
) -> None:
    """Register magics defined in this module when the extension loads."""
    ipython.register_magic_function(  # type: ignore[no-untyped-call]
        IPythonExtension.register_run_if_allowed_tags, "line", "register_run_if_allowed_tags")
    ipython.register_magic_function(  # type: ignore[no-untyped-call]
        IPythonExtension.register_run_if_current_tag, "line", "register_run_if_current_tag",)
    ipython.register_magic_function(  # type: ignore[no-untyped-call]
        IPythonExtension.run_if, "cell", "run_if")
    ipython.set_custom_exc(  # type: ignore[no-untyped-call]
        (IPythonExtension.SuppressTracebackMockError, ), IPythonExtension.suppress_traceback_handler)
    IPythonExtension.loaded = True
    IPythonExtension.allowed_tags = []
    IPythonExtension.current_tag = ""


def unload_ipython_extension(
    ipython: IPython.core.interactiveshell.InteractiveShell
) -> None:
    """Unregister the magics defined in this module when the extension unloads."""
    del ipython.magics_manager.magics["line"]["register_run_if_allowed_tags"]  # type: ignore[union-attr]
    del ipython.magics_manager.magics["line"]["register_run_if_current_tag"]  # type: ignore[union-attr]
    del ipython.magics_manager.magics["cell"]["run_if"]  # type: ignore[union-attr]
    IPythonExtension.loaded = False
    IPythonExtension.allowed_tags = []
    IPythonExtension.current_tag = ""
