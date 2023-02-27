# Copyright (C) 2022-2023 by the nbvalx authors
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

    def register_magic_function(self, func: typing.Callable[[typing.Any], typing.Any], magic_kind: str) -> None:
        """Update magics manager."""
        self.magics_manager.magics[magic_kind][func.__name__] = func

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
    assert nbvalx.jupyter_magics.IPythonExtensionStatus.loaded is True
    assert nbvalx.jupyter_magics.IPythonExtensionStatus.allowed_tags == []
    assert nbvalx.jupyter_magics.IPythonExtensionStatus.current_tag == ""
    nbvalx.jupyter_magics.unload_ipython_extension(mock_ipython)  # type: ignore[arg-type]


def test_register_run_if_allowed_tags(mock_ipython: MockIPythonShell) -> None:
    """Check registration of allowed tags."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)  # type: ignore[arg-type]
    nbvalx.jupyter_magics.register_run_if_allowed_tags("tag1, tag2")
    assert nbvalx.jupyter_magics.IPythonExtensionStatus.allowed_tags == ["tag1", "tag2"]
    nbvalx.jupyter_magics.unload_ipython_extension(mock_ipython)  # type: ignore[arg-type]


def test_register_run_if_current_tag(mock_ipython: MockIPythonShell) -> None:
    """Check registration of current tag."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)  # type: ignore[arg-type]
    nbvalx.jupyter_magics.register_run_if_allowed_tags("tag1, tag2")
    nbvalx.jupyter_magics.register_run_if_current_tag("tag1")
    assert nbvalx.jupyter_magics.IPythonExtensionStatus.current_tag == "tag1"
    nbvalx.jupyter_magics.unload_ipython_extension(mock_ipython)  # type: ignore[arg-type]


def test_register_run_if_current_tag_without_allowed_tags(mock_ipython: MockIPythonShell) -> None:
    """Check registration of current tag raises when allowed tags have not been set."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)  # type: ignore[arg-type]
    with pytest.raises(AssertionError):
        nbvalx.jupyter_magics.register_run_if_current_tag("tag1")
    assert nbvalx.jupyter_magics.IPythonExtensionStatus.current_tag == ""
    nbvalx.jupyter_magics.unload_ipython_extension(mock_ipython)  # type: ignore[arg-type]


def test_run_if_single_tag(
    mock_ipython: MockIPythonShell, mock_get_ipython: typing.Callable[[MockIPythonShell], None]
) -> None:
    """Check running a cell with a single tag."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)  # type: ignore[arg-type]
    nbvalx.jupyter_magics.register_run_if_allowed_tags("tag1, tag2")
    nbvalx.jupyter_magics.register_run_if_current_tag("tag1")
    mock_get_ipython(mock_ipython)
    nbvalx.jupyter_magics.run_if("tag1", "a = 1")
    assert mock_ipython.cell == "a = 1"
    nbvalx.jupyter_magics.unload_ipython_extension(mock_ipython)  # type: ignore[arg-type]


def test_run_if_single_tag_with_line_breaks(
    mock_ipython: MockIPythonShell, mock_get_ipython: typing.Callable[[MockIPythonShell], None]
) -> None:
    """Check running a cell with a single tag and with line breaks."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)  # type: ignore[arg-type]
    nbvalx.jupyter_magics.register_run_if_allowed_tags("tag1, tag2")
    nbvalx.jupyter_magics.register_run_if_current_tag("tag1")
    mock_get_ipython(mock_ipython)
    nbvalx.jupyter_magics.run_if(" \\", "  tag1\na = 1")
    assert mock_ipython.cell == "a = 1"
    nbvalx.jupyter_magics.unload_ipython_extension(mock_ipython)  # type: ignore[arg-type]


def test_run_if_multiple_tag(
    mock_ipython: MockIPythonShell, mock_get_ipython: typing.Callable[[MockIPythonShell], None]
) -> None:
    """Check running a cell with multiple tag."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)  # type: ignore[arg-type]
    nbvalx.jupyter_magics.register_run_if_allowed_tags("tag1, tag2")
    nbvalx.jupyter_magics.register_run_if_current_tag("tag1")
    mock_get_ipython(mock_ipython)
    nbvalx.jupyter_magics.run_if("tag1, tag2", "a = 1")
    assert mock_ipython.cell == "a = 1"
    nbvalx.jupyter_magics.unload_ipython_extension(mock_ipython)  # type: ignore[arg-type]


def test_run_if_multiple_tag_with_line_breaks(
    mock_ipython: MockIPythonShell, mock_get_ipython: typing.Callable[[MockIPythonShell], None]
) -> None:
    """Check running a cell with multiple tag and line breaks."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)  # type: ignore[arg-type]
    nbvalx.jupyter_magics.register_run_if_allowed_tags("tag1, tag2")
    nbvalx.jupyter_magics.register_run_if_current_tag("tag1")
    mock_get_ipython(mock_ipython)
    nbvalx.jupyter_magics.run_if("tag1, \\", "  tag2\na = 1")
    assert mock_ipython.cell == "a = 1"
    nbvalx.jupyter_magics.unload_ipython_extension(mock_ipython)  # type: ignore[arg-type]


def test_run_if_inactive_tag(
    mock_ipython: MockIPythonShell, mock_get_ipython: typing.Callable[[MockIPythonShell], None]
) -> None:
    """Check running a cell with an inactive tag."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)  # type: ignore[arg-type]
    nbvalx.jupyter_magics.register_run_if_allowed_tags("tag1, tag2")
    nbvalx.jupyter_magics.register_run_if_current_tag("tag1")
    mock_get_ipython(mock_ipython)
    nbvalx.jupyter_magics.run_if("tag2", "a = 1")
    assert mock_ipython.cell == ""
    nbvalx.jupyter_magics.unload_ipython_extension(mock_ipython)  # type: ignore[arg-type]


def test_unload_extension(mock_ipython: MockIPythonShell) -> None:
    """Check deletion of extension attributes."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)  # type: ignore[arg-type]
    nbvalx.jupyter_magics.unload_ipython_extension(mock_ipython)  # type: ignore[arg-type]
    assert nbvalx.jupyter_magics.IPythonExtensionStatus.loaded is False
    assert nbvalx.jupyter_magics.IPythonExtensionStatus.allowed_tags == []
    assert nbvalx.jupyter_magics.IPythonExtensionStatus.current_tag == ""
