# Copyright (C) 2022-2025 by the nbvalx authors
#
# This file is part of nbvalx.
#
# SPDX-License-Identifier: BSD-3-Clause
"""Custom jupyter magics to selectively run cells using tags or add a parametrization."""

import types
import typing

import IPython
import simpleeval


class IPythonExtension:
    """Implementation and storage for IPython extension."""

    loaded = False
    allowed_tags: typing.ClassVar[
        dict[str, list[bool] | list[int] | list[str]]] = {}
    current_tags: typing.ClassVar[dict[str, bool | int | str]] = {}
    allowed_parameters: typing.ClassVar[
        dict[str, list[bool] | list[int] | list[str]]] = {}
    current_parameters: typing.ClassVar[dict[str, bool | int | str]] = {}

    class SuppressTracebackMockError(Exception):
        """Custom exception type used in run_if magic to suppress redundant traceback."""

        pass

    @classmethod
    def _split_magic_from_code(cls, line: str, cell: str) -> tuple[str, str]:
        """Split the input provided by IPython into a part related to the magic and a part containing the code."""
        line = line.strip()
        cell_lines = cell.splitlines()
        code_begins = 0
        while line.endswith("\\"):
            line = line.strip("\\") + " " + cell_lines[code_begins].strip()
            code_begins += 1
        magic = line
        code = "\n".join(cell_lines[code_begins:])
        return magic, code

    @classmethod
    def _convert_to_python_native_types(cls, value: str) -> bool | int | str:
        """Convert a string to a boolean or an integer, if possible."""
        if value == "True":
            return True
        elif value == "False":
            return False
        elif value.isdigit():
            return int(value)
        else:
            if value.startswith('"'):
                assert value.endswith('"')
                return value.strip('"')
            elif value.startswith("'"):
                assert value.endswith("'")
                return value.strip("'")
            else:
                raise RuntimeError(f"String {value} must be quoted either as \"{value}\" or '{value}'")

    @classmethod
    def _ipython_runner(cls, code: str) -> None:
        """Run a code through IPython."""
        result = IPython.get_ipython().run_cell(code)  # type: ignore[attr-defined, no-untyped-call]
        try:  # pragma: no cover
            result.raise_error()
        except Exception as e:  # pragma: no cover
            # The exception has already been printed to the terminal, there is
            # no need to print it again
            raise cls.SuppressTracebackMockError(e)

    @classmethod
    def _register_allowed_magic_entries(
        cls, line: str, cell: str,
        allowed_magic_entries_dict: dict[str, list[bool] | list[int] | list[str]],
        magic_name: str
    ) -> None:
        """Register allowed values of magic entries (internal implementation)."""
        magic, allowed_magic_entries = cls._split_magic_from_code(line, cell)
        assert magic == "", f"There should be no further text on the same line of %%{magic_name}"
        for allowed_magic_entry in allowed_magic_entries.splitlines():
            allowed_magic_entry_name, allowed_magic_entry_values_str = allowed_magic_entry.split(":")
            allowed_magic_entry_name = allowed_magic_entry_name.strip()
            allowed_magic_entry_values = [
                cls._convert_to_python_native_types(value.strip())
                for value in allowed_magic_entry_values_str.split(",")]
            assert all(isinstance(value, type(allowed_magic_entry_values[0])) for value in allowed_magic_entry_values)
            allowed_magic_entries_dict[allowed_magic_entry_name] = allowed_magic_entry_values  # type: ignore[assignment]

    @classmethod
    def _register_current_magic_entries(
        cls, line: str, cell: str,
        allowed_magic_entries_dict: dict[str, list[bool] | list[int] | list[str]],
        current_magic_entries_dict: dict[str, bool | int | str],
        magic_name: str,
        process_magic_entry: typing.Callable[[str, bool | int | str], None] | None
    ) -> None:
        """Register current value of magic entries (internal implementation)."""
        magic, current_magic_entries = cls._split_magic_from_code(line, cell)
        assert magic == "", f"There should be no further text on the same line of %%{magic_name}"
        for current_magic_entry in current_magic_entries.splitlines():
            current_magic_entry_name, current_magic_entry_value_str = current_magic_entry.split("=")
            current_magic_entry_name = current_magic_entry_name.strip()
            current_magic_entry_value_str = current_magic_entry_value_str.strip()
            current_magic_entry_value = cls._convert_to_python_native_types(current_magic_entry_value_str)
            assert current_magic_entry_name in allowed_magic_entries_dict
            assert current_magic_entry_value in allowed_magic_entries_dict[current_magic_entry_name]
            current_magic_entries_dict[current_magic_entry_name] = current_magic_entry_value
            if process_magic_entry is not None:
                process_magic_entry(current_magic_entry_name, current_magic_entry_value_str)

    @classmethod
    def register_allowed_run_if_tags(
        cls, line: str, cell: str, allowed_tags_dict: dict[str, list[bool] | list[int] | list[str]] | None = None
    ) -> None:
        """Register allowed tags."""
        if allowed_tags_dict is None:
            allowed_tags_dict = cls.allowed_tags
        cls._register_allowed_magic_entries(
            line, cell, allowed_tags_dict, "register_allowed_run_if_tags")

    @classmethod
    def register_current_run_if_tags(
        cls, line: str, cell: str, allowed_tags_dict: dict[str, list[bool] | list[int] | list[str]] | None = None,
        current_tags_dict: dict[str, bool | int | str] | None = None
    ) -> None:
        """Register current tags."""
        if allowed_tags_dict is None:
            allowed_tags_dict = cls.allowed_tags
        if current_tags_dict is None:
            current_tags_dict = cls.current_tags
        cls._register_current_magic_entries(
            line, cell, allowed_tags_dict, current_tags_dict, "register_current_run_if_tags", None)

    @classmethod
    def run_if(
        cls, line: str, cell: str, current_tags_dict: dict[str, bool | int | str] | None = None,
        runner: typing.Callable[[str], None] | None = None
    ) -> None:
        """Run cell if the condition provided in the magic argument evaluates to True."""
        if current_tags_dict is None:
            current_tags_dict = cls.current_tags
        if runner is None:
            runner = cls._ipython_runner
        magic, code = cls._split_magic_from_code(line, cell)
        if simpleeval.simple_eval(magic, names=current_tags_dict):
            runner(code)

    @classmethod
    def register_allowed_parameters(
        cls, line: str, cell: str, allowed_parameters_dict: dict[str, list[bool] | list[int] | list[str]] | None = None
    ) -> None:
        """Register allowed parameters."""
        if allowed_parameters_dict is None:
            allowed_parameters_dict = cls.allowed_parameters
        cls._register_allowed_magic_entries(
            line, cell, allowed_parameters_dict, "register_allowed_parameters")

    @classmethod
    def register_current_parameters(
        cls, line: str, cell: str, allowed_parameters_dict: dict[str, list[bool] | list[int] | list[str]] | None = None,
        current_parameters_dict: dict[str, bool | int | str] | None = None,
        runner: typing.Callable[[str], None] | None = None
    ) -> None:
        """Register current parameters."""
        if allowed_parameters_dict is None:
            allowed_parameters_dict = cls.allowed_parameters
        if current_parameters_dict is None:
            current_parameters_dict = cls.current_parameters
        if runner is None:
            runner = cls._ipython_runner
        cls._register_current_magic_entries(
            line, cell, allowed_parameters_dict, current_parameters_dict, "register_current_parameters",
            lambda name, value_str: runner(f"{name} = {value_str}"))

    @classmethod
    def suppress_traceback_handler(
        cls, ipython: IPython.core.interactiveshell.InteractiveShell, etype: type[BaseException],
        value: BaseException, tb: types.TracebackType, tb_offset: int | None = None
    ) -> None:  # pragma: no cover
        """Use a custom handler in load_ipython_extension to suppress redundant traceback."""
        pass


def load_ipython_extension(
    ipython: IPython.core.interactiveshell.InteractiveShell
) -> None:
    """Register magics defined in this module when the extension loads."""
    ipython.register_magic_function(
        IPythonExtension.register_allowed_run_if_tags,  # type: ignore[arg-type]
        "cell", "register_allowed_run_if_tags")
    ipython.register_magic_function(
        IPythonExtension.register_current_run_if_tags,  # type: ignore[arg-type]
        "cell", "register_current_run_if_tags")
    ipython.register_magic_function(IPythonExtension.run_if, "cell", "run_if")  # type: ignore[arg-type]
    ipython.register_magic_function(
        IPythonExtension.register_allowed_parameters,  # type: ignore[arg-type]
        "cell", "register_allowed_parameters")
    ipython.register_magic_function(
        IPythonExtension.register_current_parameters,  # type: ignore[arg-type]
        "cell", "register_current_parameters")
    ipython.set_custom_exc(  # type: ignore[no-untyped-call]
        (IPythonExtension.SuppressTracebackMockError, ), IPythonExtension.suppress_traceback_handler)
    IPythonExtension.loaded = True
    IPythonExtension.allowed_tags = {}
    IPythonExtension.current_tags = {}
    IPythonExtension.allowed_parameters = {}
    IPythonExtension.current_parameters = {}


def unload_ipython_extension(
    ipython: IPython.core.interactiveshell.InteractiveShell
) -> None:
    """Unregister the magics defined in this module when the extension unloads."""
    del ipython.magics_manager.magics["cell"]["register_allowed_run_if_tags"]
    del ipython.magics_manager.magics["cell"]["register_current_run_if_tags"]
    del ipython.magics_manager.magics["cell"]["register_allowed_parameters"]
    del ipython.magics_manager.magics["cell"]["register_current_parameters"]
    del ipython.magics_manager.magics["cell"]["run_if"]
    IPythonExtension.loaded = False
    IPythonExtension.allowed_tags = {}
    IPythonExtension.current_tags = {}
    IPythonExtension.allowed_parameters = {}
    IPythonExtension.current_parameters = {}
