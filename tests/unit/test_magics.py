# Copyright (C) 2022-2025 by the nbvalx authors
#
# This file is part of nbvalx.
#
# SPDX-License-Identifier: BSD-3-Clause
"""Unit test for the functions behind the jupyter magics."""

import typing

import IPython
import pytest

import nbvalx.jupyter_magics


class MockMagicsManager:
    """A mock IPython magics manager."""

    def __init__(self) -> None:
        self.magics: dict[str, dict[str, typing.Callable[[typing.Any], typing.Any]]] = {
            "line": dict(),
            "cell": dict()
        }


class MockIPythonResult:
    """A mock IPython result."""

    def raise_error(self) -> None:
        """Never raise errors."""
        pass


class MockIPythonShell:
    """A mock IPython shell."""

    def __init__(self) -> None:
        self.magics_manager = MockMagicsManager()
        self.custom_exc_manager: dict[
            tuple[type[BaseException]], typing.Callable[[typing.Any], typing.Any]] = dict()
        self.cell = ""

    def register_magic_function(
        self, func: typing.Callable[[typing.Any], typing.Any], magic_kind: str, magic_name: str
    ) -> None:
        """Update magics manager."""
        self.magics_manager.magics[magic_kind][magic_name] = func

    def set_custom_exc(
        self, exc_tuple: tuple[type[BaseException]], handler: typing.Callable[[typing.Any], typing.Any]
    ) -> None:
        """Update custom exception handler manager."""
        self.custom_exc_manager[exc_tuple] = handler

    def run_cell(self, cell: str) -> MockIPythonResult:
        """Store the cell, rather than running it."""
        self.cell = cell
        return MockIPythonResult()


@pytest.fixture
def mock_ipython() -> object:
    """Return a mock IPython shell."""
    return MockIPythonShell()


@pytest.fixture
def mock_get_ipython() -> typing.Callable[[MockIPythonShell], None]:
    """Fixture that replaces IPython.get_ipython() function."""

    def mock_get_ipython_callable(mock_ipython: MockIPythonShell) -> None:
        """Callable that replaces IPython.get_ipython() function."""

        def _() -> MockIPythonShell:
            """Replace IPython.get_ipython() function."""
            return mock_ipython

        IPython.get_ipython = _  # type: ignore[attr-defined]

    return mock_get_ipython_callable


def test_load_extension(mock_ipython: MockIPythonShell) -> None:
    """Check initialization of extension attributes."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)  # type: ignore[arg-type]
    assert nbvalx.jupyter_magics.IPythonExtension.loaded is True
    assert nbvalx.jupyter_magics.IPythonExtension.allowed_tags == {}
    assert nbvalx.jupyter_magics.IPythonExtension.current_tags == {}
    assert nbvalx.jupyter_magics.IPythonExtension.allowed_parameters == {}
    assert nbvalx.jupyter_magics.IPythonExtension.current_parameters == {}
    nbvalx.jupyter_magics.unload_ipython_extension(mock_ipython)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "register_allowed_magic_entries_function_name,allowed_magic_entries_dict_name",
    [("register_allowed_run_if_tags", "allowed_tags"), ("register_allowed_parameters", "allowed_parameters")]
)
@pytest.mark.parametrize("magic_entry_values", [[True, False], [1, 2], ["a", "b"]])
def test_register_allowed_magic_entries_single(
    mock_ipython: MockIPythonShell, register_allowed_magic_entries_function_name: str,
    allowed_magic_entries_dict_name: str, magic_entry_values: list[bool | int | str]
) -> None:
    """Check registration of a single set of allowed magic entries."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)  # type: ignore[arg-type]
    getattr(nbvalx.jupyter_magics.IPythonExtension, register_allowed_magic_entries_function_name)(
        "", f"magic_entry: {', '.join(map(repr, magic_entry_values))}")
    assert getattr(nbvalx.jupyter_magics.IPythonExtension, allowed_magic_entries_dict_name) == {
        "magic_entry": magic_entry_values}
    nbvalx.jupyter_magics.unload_ipython_extension(mock_ipython)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "register_allowed_magic_entries_function_name,allowed_magic_entries_dict_name",
    [("register_allowed_run_if_tags", "allowed_tags"), ("register_allowed_parameters", "allowed_parameters")]
)
@pytest.mark.parametrize("magic_entry_1_values", [[True, False], [1, 2], ["a", "b"]])
@pytest.mark.parametrize("magic_entry_2_values", [[True, False], [3, 4], ["c", "d"]])
def test_register_allowed_magic_entries_multiple(
    mock_ipython: MockIPythonShell, register_allowed_magic_entries_function_name: str,
    allowed_magic_entries_dict_name: str, magic_entry_1_values: list[bool | int | str],
    magic_entry_2_values: list[bool | int | str]
) -> None:
    """Check registration of multiple sets allowed magic entries."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)  # type: ignore[arg-type]
    getattr(nbvalx.jupyter_magics.IPythonExtension, register_allowed_magic_entries_function_name)(
        "",
        f"magic_entry_1: {', '.join(map(repr, magic_entry_1_values))}\n"
        f"magic_entry_2: {', '.join(map(repr, magic_entry_2_values))}"
    )
    assert getattr(nbvalx.jupyter_magics.IPythonExtension, allowed_magic_entries_dict_name) == {
        "magic_entry_1": magic_entry_1_values, "magic_entry_2": magic_entry_2_values}
    nbvalx.jupyter_magics.unload_ipython_extension(mock_ipython)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "register_allowed_magic_entries_function_name,allowed_magic_entries_dict_name",
    [("register_allowed_run_if_tags", "allowed_tags"), ("register_allowed_parameters", "allowed_parameters")]
)
@pytest.mark.parametrize("magic_entry_values", [["a", "b"]])
def test_register_allowed_magic_entries_without_quotes(
    mock_ipython: MockIPythonShell, register_allowed_magic_entries_function_name: str,
    allowed_magic_entries_dict_name: str, magic_entry_values: list[str]
) -> None:
    """Check registration of allowed magic entries of type string not enclosed within quotes."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)  # type: ignore[arg-type]
    with pytest.raises(RuntimeError):
        getattr(nbvalx.jupyter_magics.IPythonExtension, register_allowed_magic_entries_function_name)(
            "", f"magic_entry: {', '.join(map(str, magic_entry_values))}")
    assert getattr(nbvalx.jupyter_magics.IPythonExtension, allowed_magic_entries_dict_name) == {}
    nbvalx.jupyter_magics.unload_ipython_extension(mock_ipython)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "register_allowed_magic_entries_function_name,register_current_magic_entries_function_name,"
    "current_magic_entries_dict_name",
    [
        ("register_allowed_run_if_tags", "register_current_run_if_tags", "current_tags"),
        ("register_allowed_parameters", "register_current_parameters", "current_parameters")
    ]
)
@pytest.mark.parametrize("magic_entry_values", [[True, False], [1, 2], ["a", "b"]])
def test_register_current_magic_entries_single(
    mock_ipython: MockIPythonShell, mock_get_ipython: typing.Callable[[MockIPythonShell], None],
    register_allowed_magic_entries_function_name: str, register_current_magic_entries_function_name: str,
    current_magic_entries_dict_name: str, magic_entry_values: list[bool | int | str]
) -> None:
    """Check registration of a single set of current magic entries."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)  # type: ignore[arg-type]
    getattr(nbvalx.jupyter_magics.IPythonExtension, register_allowed_magic_entries_function_name)(
        "", f"magic_entry: {', '.join(map(repr, magic_entry_values))}")
    if register_current_magic_entries_function_name == "register_current_parameters":
        mock_get_ipython(mock_ipython)
        assert mock_ipython.cell == ""
    getattr(nbvalx.jupyter_magics.IPythonExtension, register_current_magic_entries_function_name)(
        "", f"magic_entry = {magic_entry_values[0]!r}")
    assert getattr(nbvalx.jupyter_magics.IPythonExtension, current_magic_entries_dict_name) == {
        "magic_entry": magic_entry_values[0]}
    if register_current_magic_entries_function_name == "register_current_parameters":
        assert mock_ipython.cell == f"magic_entry = {magic_entry_values[0]!r}"
    nbvalx.jupyter_magics.unload_ipython_extension(mock_ipython)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "register_allowed_magic_entries_function_name,register_current_magic_entries_function_name,"
    "current_magic_entries_dict_name",
    [
        ("register_allowed_run_if_tags", "register_current_run_if_tags", "current_tags"),
        ("register_allowed_parameters", "register_current_parameters", "current_parameters")
    ]
)
@pytest.mark.parametrize("magic_entry_1_values", [[True, False], [1, 2], ["a", "b"]])
@pytest.mark.parametrize("magic_entry_2_values", [[True, False], [3, 4], ["c", "d"]])
def test_register_current_magic_entries_multiple(
    mock_ipython: MockIPythonShell, mock_get_ipython: typing.Callable[[MockIPythonShell], None],
    register_allowed_magic_entries_function_name: str, register_current_magic_entries_function_name: str,
    current_magic_entries_dict_name: str, magic_entry_1_values: list[bool | int | str],
    magic_entry_2_values: list[bool | int | str]
) -> None:
    """Check registration of multiple sets of current magic entries."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)  # type: ignore[arg-type]
    getattr(nbvalx.jupyter_magics.IPythonExtension, register_allowed_magic_entries_function_name)(
        "",
        f"magic_entry_1: {', '.join(map(repr, magic_entry_1_values))}\n"
        f"magic_entry_2: {', '.join(map(repr, magic_entry_2_values))}"
    )
    if register_current_magic_entries_function_name == "register_current_parameters":
        mock_get_ipython(mock_ipython)
        assert mock_ipython.cell == ""
    getattr(nbvalx.jupyter_magics.IPythonExtension, register_current_magic_entries_function_name)(
        "",
        f"magic_entry_1 = {magic_entry_1_values[0]!r}\n"
        f"magic_entry_2 = {magic_entry_2_values[0]!r}"
    )
    assert getattr(nbvalx.jupyter_magics.IPythonExtension, current_magic_entries_dict_name) == {
        "magic_entry_1": magic_entry_1_values[0], "magic_entry_2": magic_entry_2_values[0]}
    if register_current_magic_entries_function_name == "register_current_parameters":
        assert mock_ipython.cell == f"magic_entry_2 = {magic_entry_2_values[0]!r}"
    nbvalx.jupyter_magics.unload_ipython_extension(mock_ipython)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "register_current_magic_entries_function_name,allowed_magic_entries_dict_name",
    [
        ("register_current_run_if_tags", "allowed_tags"),
        ("register_current_parameters", "allowed_parameters")
    ]
)
@pytest.mark.parametrize("magic_entry_values", [[True, False], [1, 2], ["a", "b"]])
def test_register_current_magic_entries_without_allowed(
    mock_ipython: MockIPythonShell, register_current_magic_entries_function_name: str,
    allowed_magic_entries_dict_name: str, magic_entry_values: list[bool | int | str]
) -> None:
    """Check registration of current magic entries raises when allowed values have not been set."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)  # type: ignore[arg-type]
    with pytest.raises(AssertionError):
        getattr(nbvalx.jupyter_magics.IPythonExtension, register_current_magic_entries_function_name)(
            "", f"magic_entry = {magic_entry_values[0]!r}")
    assert getattr(nbvalx.jupyter_magics.IPythonExtension, allowed_magic_entries_dict_name) == {}
    nbvalx.jupyter_magics.unload_ipython_extension(mock_ipython)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "tag_values,tag_condition", [
        ([True, False], "tag is True"),
        ([1, 2], "tag**2 == 1"),
        (["a", "b"], "tag + '!' == 'a!'")
    ]
)
def test_run_if_single_condition(
    mock_ipython: MockIPythonShell, mock_get_ipython: typing.Callable[[MockIPythonShell], None],
    tag_values: list[bool | int | str], tag_condition: str
) -> None:
    """Check running a cell with a condition formed by a single statement."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)  # type: ignore[arg-type]
    nbvalx.jupyter_magics.IPythonExtension.register_allowed_run_if_tags("", f"tag: {', '.join(map(repr, tag_values))}")
    nbvalx.jupyter_magics.IPythonExtension.register_current_run_if_tags("", f"tag = {tag_values[0]!r}")
    mock_get_ipython(mock_ipython)
    nbvalx.jupyter_magics.IPythonExtension.run_if(tag_condition, "a = 1")
    assert mock_ipython.cell == "a = 1"
    nbvalx.jupyter_magics.unload_ipython_extension(mock_ipython)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "tag_values,tag_condition", [
        ([True, False], "tag is True"),
        ([1, 2], "tag**2 == 1"),
        (["a", "b"], "tag + '!' == 'a!'")
    ]
)
def test_run_if_single_condition_with_line_breaks(
    mock_ipython: MockIPythonShell, mock_get_ipython: typing.Callable[[MockIPythonShell], None],
    tag_values: list[bool | int | str], tag_condition: str
) -> None:
    """Check running a cell with a condition formed by a single statement and with line breaks."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)  # type: ignore[arg-type]
    nbvalx.jupyter_magics.IPythonExtension.register_allowed_run_if_tags("", f"tag: {', '.join(map(repr, tag_values))}")
    nbvalx.jupyter_magics.IPythonExtension.register_current_run_if_tags("", f"tag = {tag_values[0]!r}")
    mock_get_ipython(mock_ipython)
    nbvalx.jupyter_magics.IPythonExtension.run_if(" \\", f"  {tag_condition}\na = 1")
    assert mock_ipython.cell == "a = 1"
    nbvalx.jupyter_magics.unload_ipython_extension(mock_ipython)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "tag_values,tag_condition", [
        ([True, False], "tag is True or tag is False"),
        ([1, 2], "tag**2 == 1 or tag**3 == 1 and tag > -1"),
        (["a", "b"], "tag + '!' == 'a!' and tag != 'b'")
    ]
)
def test_run_if_multiple_conditions(
    mock_ipython: MockIPythonShell, mock_get_ipython: typing.Callable[[MockIPythonShell], None],
    tag_values: list[bool | int | str], tag_condition: str
) -> None:
    """Check running a cell with a condition formed by multiple statements."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)  # type: ignore[arg-type]
    nbvalx.jupyter_magics.IPythonExtension.register_allowed_run_if_tags("", f"tag: {', '.join(map(repr, tag_values))}")
    nbvalx.jupyter_magics.IPythonExtension.register_current_run_if_tags("", f"tag = {tag_values[0]!r}")
    mock_get_ipython(mock_ipython)
    nbvalx.jupyter_magics.IPythonExtension.run_if(tag_condition, "a = 1")
    assert mock_ipython.cell == "a = 1"
    nbvalx.jupyter_magics.unload_ipython_extension(mock_ipython)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "tag_values,tag_condition1,tag_condition2", [
        ([True, False], "tag is True or", "tag is False"),
        ([1, 2], "tag**2 == 1 or", "tag**3 == 1 and tag > -1"),
        (["a", "b"], "tag + '!' == 'a!' and", "tag != 'b'")
    ]
)
def test_run_if_multiple_conditions_with_line_breaks(
    mock_ipython: MockIPythonShell, mock_get_ipython: typing.Callable[[MockIPythonShell], None],
    tag_values: list[bool | int | str], tag_condition1: str, tag_condition2: str
) -> None:
    """Check running a cell with a condition formed by multiple statements and line breaks."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)  # type: ignore[arg-type]
    nbvalx.jupyter_magics.IPythonExtension.register_allowed_run_if_tags("", f"tag: {', '.join(map(repr, tag_values))}")
    nbvalx.jupyter_magics.IPythonExtension.register_current_run_if_tags("", f"tag = {tag_values[0]!r}")
    mock_get_ipython(mock_ipython)
    nbvalx.jupyter_magics.IPythonExtension.run_if(f"{tag_condition1}\\", f"  {tag_condition2}\na = 1")
    assert mock_ipython.cell == "a = 1"
    nbvalx.jupyter_magics.unload_ipython_extension(mock_ipython)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "tag_values,tag_condition", [
        ([True, False], "tag is False"),
        ([1, 2], "tag**2 == 10"),
        (["a", "b"], "tag + '!' == 'a?'")
    ]
)
def test_run_if_single_condition_false(
    mock_ipython: MockIPythonShell, mock_get_ipython: typing.Callable[[MockIPythonShell], None],
    tag_values: list[bool | int | str], tag_condition: str
) -> None:
    """Check running a cell with a condition which evaluates to False."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)  # type: ignore[arg-type]
    nbvalx.jupyter_magics.IPythonExtension.register_allowed_run_if_tags("", f"tag: {', '.join(map(repr, tag_values))}")
    nbvalx.jupyter_magics.IPythonExtension.register_current_run_if_tags("", f"tag = {tag_values[0]!r}")
    mock_get_ipython(mock_ipython)
    nbvalx.jupyter_magics.IPythonExtension.run_if(tag_condition, "a = 1")
    assert mock_ipython.cell == ""
    nbvalx.jupyter_magics.unload_ipython_extension(mock_ipython)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "register_allowed_magic_entries_function_name,register_current_magic_entries_function_name,"
    "allowed_magic_entries_dict_name,current_magic_entries_dict_name",
    [
        ("register_allowed_run_if_tags", "register_current_run_if_tags", "allowed_tags", "current_tags"),
        ("register_allowed_parameters", "register_current_parameters", "allowed_parameters", "current_parameters")
    ]
)
@pytest.mark.parametrize("magic_entry_values", [[True, False], [1, 2], ["a", "b"]])
def test_unload_extension(
    mock_ipython: MockIPythonShell, register_allowed_magic_entries_function_name: str,
    register_current_magic_entries_function_name: str, allowed_magic_entries_dict_name: str,
    current_magic_entries_dict_name: str, magic_entry_values: list[bool | int | str]
) -> None:
    """Check deletion of extension attributes."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)  # type: ignore[arg-type]
    getattr(nbvalx.jupyter_magics.IPythonExtension, register_allowed_magic_entries_function_name)(
        "", f"magic_entry: {', '.join(map(repr, magic_entry_values))}")
    getattr(nbvalx.jupyter_magics.IPythonExtension, register_current_magic_entries_function_name)(
        "", f"magic_entry = {magic_entry_values[0]!r}")
    nbvalx.jupyter_magics.unload_ipython_extension(mock_ipython)  # type: ignore[arg-type]
    assert nbvalx.jupyter_magics.IPythonExtension.loaded is False
    assert getattr(nbvalx.jupyter_magics.IPythonExtension, allowed_magic_entries_dict_name) == {}
    assert getattr(nbvalx.jupyter_magics.IPythonExtension, current_magic_entries_dict_name) == {}
