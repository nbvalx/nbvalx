# Copyright (C) 2022-2024 by the nbvalx authors
#
# This file is part of nbvalx.
#
# SPDX-License-Identifier: BSD-3-Clause
"""Custom jupyter magics to selectively run cells using tags."""

import types
import typing

import IPython
import simpleeval


class IPythonExtension:
    """Implementation and storage for IPython extension."""

    loaded = False
    allowed_tags: typing.ClassVar[
        typing.Dict[str, typing.Union[typing.List[bool], typing.List[int], typing.List[str]]]] = {}
    current_tags: typing.ClassVar[typing.Dict[str, typing.Union[bool, int, str]]] = {}

    class SuppressTracebackMockError(Exception):
        """Custom exception type used in run_if magic to suppress redundant traceback."""

        pass

    @classmethod
    def _split_magic_from_code(cls, line: str, cell: str) -> typing.Tuple[str, str]:
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
    def _convert_to_tags_value_types(cls, value: str) -> typing.Union[bool, int, str]:
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
    def register_run_if_allowed_tags(
        cls, line: str, cell: str, allowed_tags_dict: typing.Optional[
            typing.Dict[str, typing.Union[typing.List[bool], typing.List[int], typing.List[str]]]] = None
    ) -> None:
        """Register allowed tags."""
        if allowed_tags_dict is None:
            allowed_tags_dict = cls.allowed_tags
        magic, allowed_tags = cls._split_magic_from_code(line, cell)
        assert magic == "", "There should be no further text on the same line of %%register_run_if_allowed_tags"
        for allowed_tag in allowed_tags.splitlines():
            allowed_tag_name, allowed_tag_values_str = allowed_tag.split(":")
            allowed_tag_name = allowed_tag_name.strip()
            allowed_tag_values = [
                cls._convert_to_tags_value_types(value.strip()) for value in allowed_tag_values_str.split(",")]
            assert all(isinstance(value, type(allowed_tag_values[0])) for value in allowed_tag_values)
            assert allowed_tag_name not in allowed_tags_dict
            allowed_tags_dict[allowed_tag_name] = allowed_tag_values  # type: ignore[assignment]

    @classmethod
    def register_run_if_current_tags(
        cls, line: str, cell: str, allowed_tags_dict: typing.Optional[
            typing.Dict[str, typing.Union[typing.List[bool], typing.List[int], typing.List[str]]]] = None,
        current_tags_dict: typing.Optional[typing.Dict[str, typing.Union[bool, int, str]]] = None
    ) -> None:
        """Register current tags."""
        if allowed_tags_dict is None:
            allowed_tags_dict = cls.allowed_tags
        if current_tags_dict is None:
            current_tags_dict = cls.current_tags
        magic, current_tags = cls._split_magic_from_code(line, cell)
        assert magic == "", "There should be no further text on the same line of %%register_run_if_current_tags"
        for current_tag in current_tags.splitlines():
            current_tag_name, current_tag_value_str = current_tag.split("=")
            current_tag_name = current_tag_name.strip()
            current_tag_value = cls._convert_to_tags_value_types(current_tag_value_str.strip())
            assert current_tag_name in allowed_tags_dict
            assert current_tag_value in allowed_tags_dict[current_tag_name]
            assert current_tag_name not in current_tags_dict
            current_tags_dict[current_tag_name] = current_tag_value

    @classmethod
    def run_if(
        cls, line: str, cell: str, current_tags_dict: typing.Optional[
            typing.Dict[str, typing.Union[bool, int, str]]] = None,
        runner: typing.Optional[typing.Callable[[str], None]] = None
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
        IPythonExtension.register_run_if_allowed_tags, "cell", "register_run_if_allowed_tags")
    ipython.register_magic_function(  # type: ignore[no-untyped-call]
        IPythonExtension.register_run_if_current_tags, "cell", "register_run_if_current_tags",)
    ipython.register_magic_function(  # type: ignore[no-untyped-call]
        IPythonExtension.run_if, "cell", "run_if")
    ipython.set_custom_exc(  # type: ignore[no-untyped-call]
        (IPythonExtension.SuppressTracebackMockError, ), IPythonExtension.suppress_traceback_handler)
    IPythonExtension.loaded = True
    IPythonExtension.allowed_tags = {}
    IPythonExtension.current_tags = {}


def unload_ipython_extension(
    ipython: IPython.core.interactiveshell.InteractiveShell
) -> None:
    """Unregister the magics defined in this module when the extension unloads."""
    del ipython.magics_manager.magics["cell"]["register_run_if_allowed_tags"]  # type: ignore[union-attr]
    del ipython.magics_manager.magics["cell"]["register_run_if_current_tags"]  # type: ignore[union-attr]
    del ipython.magics_manager.magics["cell"]["run_if"]  # type: ignore[union-attr]
    IPythonExtension.loaded = False
    IPythonExtension.allowed_tags = {}
    IPythonExtension.current_tags = {}
