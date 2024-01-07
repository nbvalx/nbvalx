# Copyright (C) 2022-2024 by the nbvalx authors
#
# This file is part of nbvalx.
#
# SPDX-License-Identifier: BSD-3-Clause
"""Unit test for the functions behind the jupyter magics."""

import typing

import IPython
import pytest

import nbvalx.jupyter_magics


class MockMagicsManager(object):
    """A mock IPython magics manager."""

    def __init__(self) -> None:
        self.magics: typing.Dict[str, typing.Dict[str, typing.Callable[[typing.Any], typing.Any]]] = {
            "line": dict(),
            "cell": dict()
        }


class MockIPythonResult(object):
    """A mock IPython result."""

    def raise_error(self) -> None:
        """Never raise errors."""
        pass


class MockIPythonShell(object):
    """A mock IPython shell."""

    def __init__(self) -> None:
        self.magics_manager = MockMagicsManager()
        self.custom_exc_manager: typing.Dict[
            typing.Tuple[typing.Type[BaseException]], typing.Callable[[typing.Any], typing.Any]] = dict()
        self.cell = ""

    def register_magic_function(
        self, func: typing.Callable[[typing.Any], typing.Any], magic_kind: str, magic_name: str
    ) -> None:
        """Update magics manager."""
        self.magics_manager.magics[magic_kind][magic_name] = func

    def set_custom_exc(
        self, exc_tuple: typing.Tuple[typing.Type[BaseException]], handler: typing.Callable[[typing.Any], typing.Any]
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
    nbvalx.jupyter_magics.unload_ipython_extension(mock_ipython)  # type: ignore[arg-type]


@pytest.mark.parametrize("tag_values", [[True, False], [1, 2], ["a", "b"]])
def test_register_run_if_allowed_tags_single(
    mock_ipython: MockIPythonShell, tag_values: typing.List[typing.Union[bool, int, str]]
) -> None:
    """Check registration of a single set of allowed tags."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)  # type: ignore[arg-type]
    nbvalx.jupyter_magics.IPythonExtension.register_run_if_allowed_tags("", f"tag: {', '.join(map(repr, tag_values))}")
    assert nbvalx.jupyter_magics.IPythonExtension.allowed_tags == {"tag": tag_values}
    nbvalx.jupyter_magics.unload_ipython_extension(mock_ipython)  # type: ignore[arg-type]


@pytest.mark.parametrize("tag1_values", [[True, False], [1, 2], ["a", "b"]])
@pytest.mark.parametrize("tag2_values", [[True, False], [3, 4], ["c", "d"]])
def test_register_run_if_allowed_tags_multiple(
    mock_ipython: MockIPythonShell, tag1_values: typing.List[typing.Union[bool, int, str]],
    tag2_values: typing.List[typing.Union[bool, int, str]]
) -> None:
    """Check registration of multiple sets allowed tags."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)  # type: ignore[arg-type]
    nbvalx.jupyter_magics.IPythonExtension.register_run_if_allowed_tags(
        "", f"tag1: {', '.join(map(repr, tag1_values))}\ntag2: {', '.join(map(repr, tag2_values))}")
    assert nbvalx.jupyter_magics.IPythonExtension.allowed_tags == {"tag1": tag1_values, "tag2": tag2_values}
    nbvalx.jupyter_magics.unload_ipython_extension(mock_ipython)  # type: ignore[arg-type]


@pytest.mark.parametrize("tag_values", [["a", "b"]])
def test_register_run_if_allowed_tags_without_quotes(
    mock_ipython: MockIPythonShell, tag_values: typing.List[str]
) -> None:
    """Check registration of allowed tags of type string not enclosed within quotes."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)  # type: ignore[arg-type]
    with pytest.raises(RuntimeError):
        nbvalx.jupyter_magics.IPythonExtension.register_run_if_allowed_tags(
            "", f"tag: {', '.join(map(str, tag_values))}")
    assert nbvalx.jupyter_magics.IPythonExtension.allowed_tags == {}
    nbvalx.jupyter_magics.unload_ipython_extension(mock_ipython)  # type: ignore[arg-type]


@pytest.mark.parametrize("tag_values", [[True, False], [1, 2], ["a", "b"]])
def test_register_run_if_current_tags_single(
    mock_ipython: MockIPythonShell, tag_values: typing.List[typing.Union[bool, int, str]]
) -> None:
    """Check registration of a single set of current tags."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)  # type: ignore[arg-type]
    nbvalx.jupyter_magics.IPythonExtension.register_run_if_allowed_tags("", f"tag: {', '.join(map(repr, tag_values))}")
    nbvalx.jupyter_magics.IPythonExtension.register_run_if_current_tags("", f"tag = {tag_values[0]!r}")
    assert nbvalx.jupyter_magics.IPythonExtension.current_tags == {"tag": tag_values[0]}
    nbvalx.jupyter_magics.unload_ipython_extension(mock_ipython)  # type: ignore[arg-type]


@pytest.mark.parametrize("tag1_values", [[True, False], [1, 2], ["a", "b"]])
@pytest.mark.parametrize("tag2_values", [[True, False], [3, 4], ["c", "d"]])
def test_register_run_if_current_tags_multiple(
    mock_ipython: MockIPythonShell, tag1_values: typing.List[typing.Union[bool, int, str]],
    tag2_values: typing.List[typing.Union[bool, int, str]]
) -> None:
    """Check registration of multiple sets of current tags."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)  # type: ignore[arg-type]
    nbvalx.jupyter_magics.IPythonExtension.register_run_if_allowed_tags(
        "", f"tag1: {', '.join(map(repr, tag1_values))}\ntag2: {', '.join(map(repr, tag2_values))}")
    nbvalx.jupyter_magics.IPythonExtension.register_run_if_current_tags(
        "", f"tag1 = {tag1_values[0]!r}\ntag2 = {tag2_values[0]!r}")
    assert nbvalx.jupyter_magics.IPythonExtension.current_tags == {"tag1": tag1_values[0], "tag2": tag2_values[0]}
    nbvalx.jupyter_magics.unload_ipython_extension(mock_ipython)  # type: ignore[arg-type]


@pytest.mark.parametrize("tag_values", [[True, False], [1, 2], ["a", "b"]])
def test_register_run_if_current_tags_without_allowed_tags(
    mock_ipython: MockIPythonShell, tag_values: typing.List[typing.Union[bool, int, str]]
) -> None:
    """Check registration of current tag raises when allowed tags have not been set."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)  # type: ignore[arg-type]
    with pytest.raises(AssertionError):
        nbvalx.jupyter_magics.IPythonExtension.register_run_if_current_tags("", f"tag = {tag_values[0]!r}")
    assert nbvalx.jupyter_magics.IPythonExtension.current_tags == {}
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
    tag_values: typing.List[typing.Union[bool, int, str]], tag_condition: str
) -> None:
    """Check running a cell with a condition formed by a single statement."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)  # type: ignore[arg-type]
    nbvalx.jupyter_magics.IPythonExtension.register_run_if_allowed_tags("", f"tag: {', '.join(map(repr, tag_values))}")
    nbvalx.jupyter_magics.IPythonExtension.register_run_if_current_tags("", f"tag = {tag_values[0]!r}")
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
    tag_values: typing.List[typing.Union[bool, int, str]], tag_condition: str
) -> None:
    """Check running a cell with a condition formed by a single statement and with line breaks."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)  # type: ignore[arg-type]
    nbvalx.jupyter_magics.IPythonExtension.register_run_if_allowed_tags("", f"tag: {', '.join(map(repr, tag_values))}")
    nbvalx.jupyter_magics.IPythonExtension.register_run_if_current_tags("", f"tag = {tag_values[0]!r}")
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
    tag_values: typing.List[typing.Union[bool, int, str]], tag_condition: str
) -> None:
    """Check running a cell with a condition formed by multiple statements."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)  # type: ignore[arg-type]
    nbvalx.jupyter_magics.IPythonExtension.register_run_if_allowed_tags("", f"tag: {', '.join(map(repr, tag_values))}")
    nbvalx.jupyter_magics.IPythonExtension.register_run_if_current_tags("", f"tag = {tag_values[0]!r}")
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
    tag_values: typing.List[typing.Union[bool, int, str]], tag_condition1: str, tag_condition2: str
) -> None:
    """Check running a cell with a condition formed by multiple statements and line breaks."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)  # type: ignore[arg-type]
    nbvalx.jupyter_magics.IPythonExtension.register_run_if_allowed_tags("", f"tag: {', '.join(map(repr, tag_values))}")
    nbvalx.jupyter_magics.IPythonExtension.register_run_if_current_tags("", f"tag = {tag_values[0]!r}")
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
    tag_values: typing.List[typing.Union[bool, int, str]], tag_condition: str
) -> None:
    """Check running a cell with a condition which evaluates to False."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)  # type: ignore[arg-type]
    nbvalx.jupyter_magics.IPythonExtension.register_run_if_allowed_tags("", f"tag: {', '.join(map(repr, tag_values))}")
    nbvalx.jupyter_magics.IPythonExtension.register_run_if_current_tags("", f"tag = {tag_values[0]!r}")
    mock_get_ipython(mock_ipython)
    nbvalx.jupyter_magics.IPythonExtension.run_if(tag_condition, "a = 1")
    assert mock_ipython.cell == ""
    nbvalx.jupyter_magics.unload_ipython_extension(mock_ipython)  # type: ignore[arg-type]


@pytest.mark.parametrize("tag_values", [[True, False], [1, 2], ["a", "b"]])
def test_unload_extension(
    mock_ipython: MockIPythonShell, tag_values: typing.List[typing.Union[bool, int, str]]
) -> None:
    """Check deletion of extension attributes."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)  # type: ignore[arg-type]
    nbvalx.jupyter_magics.IPythonExtension.register_run_if_allowed_tags("", f"tag: {', '.join(map(repr, tag_values))}")
    nbvalx.jupyter_magics.IPythonExtension.register_run_if_current_tags("", f"tag = {tag_values[0]!r}")
    nbvalx.jupyter_magics.unload_ipython_extension(mock_ipython)  # type: ignore[arg-type]
    assert nbvalx.jupyter_magics.IPythonExtension.loaded is False
    assert nbvalx.jupyter_magics.IPythonExtension.allowed_tags == {}
    assert nbvalx.jupyter_magics.IPythonExtension.current_tags == {}
