# Copyright (C) 2022 by the nbvalx authors
#
# This file is part of nbvalx.
#
# SPDX-License-Identifier: BSD-3-Clause
"""Unit test for the functions behind the jupyter magics."""

import typing

import pytest

import nbvalx.jupyter_magics


class MockMagicsManager(object):
    """A mock IPython magics manager."""

    def __init__(self) -> None:
        self.magics = {
            "line": dict(),
            "cell": dict()
        }


class MockIPythonShell(object):
    """A mock IPython shell."""

    def __init__(self) -> None:
        self.magics_manager = MockMagicsManager()
        self.custom_exc_manager = dict()

    def register_magic_function(self, func: typing.Callable, magic_kind: str) -> None:
        """Update magics manager."""
        self.magics_manager.magics[magic_kind][func.__name__] = func

    def set_custom_exc(self, exc_tuple: typing.Tuple[typing.Type[BaseException]], handler: typing.Callable) -> None:
        """Update custom exception handler manager."""
        self.custom_exc_manager[exc_tuple] = handler


@pytest.fixture
def mock_ipython() -> object:
    """Return a mock IPython shell."""
    return MockIPythonShell()


def test_load_extension(mock_ipython: MockIPythonShell) -> None:
    """Check initialization of extension attributes."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)
    assert nbvalx.jupyter_magics.load_ipython_extension.loaded is True
    assert nbvalx.jupyter_magics.load_ipython_extension.allowed_tags == []
    assert nbvalx.jupyter_magics.load_ipython_extension.current_tag is None
    nbvalx.jupyter_magics.unload_ipython_extension(mock_ipython)


def test_register_run_if_allowed_tags(mock_ipython: MockIPythonShell) -> None:
    """Check registration of allowed tags."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)
    nbvalx.jupyter_magics.register_run_if_allowed_tags("tag1, tag2")
    assert nbvalx.jupyter_magics.load_ipython_extension.allowed_tags == ["tag1", "tag2"]
    nbvalx.jupyter_magics.unload_ipython_extension(mock_ipython)


def test_register_run_if_current_tag(mock_ipython: MockIPythonShell) -> None:
    """Check registration of current tag."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)
    nbvalx.jupyter_magics.register_run_if_allowed_tags("tag1, tag2")
    nbvalx.jupyter_magics.register_run_if_current_tag("tag1")
    assert nbvalx.jupyter_magics.load_ipython_extension.current_tag == "tag1"
    nbvalx.jupyter_magics.unload_ipython_extension(mock_ipython)


def test_register_run_if_current_tag_without_allowed_tags(mock_ipython: MockIPythonShell) -> None:
    """Check registration of current tag raises when allowed tags have not been set."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)
    with pytest.raises(AssertionError):
        nbvalx.jupyter_magics.register_run_if_current_tag("tag1")
    assert nbvalx.jupyter_magics.load_ipython_extension.current_tag is None
    nbvalx.jupyter_magics.unload_ipython_extension(mock_ipython)


def test_run_if_single_tag(mock_ipython: MockIPythonShell) -> None:
    """Check running a cell with a single tag."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)
    nbvalx.jupyter_magics.register_run_if_allowed_tags("tag1, tag2")
    nbvalx.jupyter_magics.register_run_if_current_tag("tag1")
    with pytest.raises(AttributeError) as excinfo:
        # raises because we are outside of ipython, and IPython.get_ipython() returns None
        nbvalx.jupyter_magics.run_if("tag1", "a = 1")
    assert str(excinfo.value) == "'NoneType' object has no attribute 'run_cell'"
    nbvalx.jupyter_magics.unload_ipython_extension(mock_ipython)


def test_run_if_multiple_tag(mock_ipython: MockIPythonShell) -> None:
    """Check running a cell with multiple tag."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)
    nbvalx.jupyter_magics.register_run_if_allowed_tags("tag1, tag2")
    nbvalx.jupyter_magics.register_run_if_current_tag("tag1")
    with pytest.raises(AttributeError) as excinfo:
        # raises because we are outside of ipython, and IPython.get_ipython() returns None
        nbvalx.jupyter_magics.run_if("tag1, tag2", "a = 1")
    assert str(excinfo.value) == "'NoneType' object has no attribute 'run_cell'"
    nbvalx.jupyter_magics.unload_ipython_extension(mock_ipython)


def test_run_if_inactive_tag(mock_ipython: MockIPythonShell) -> None:
    """Check running a cell with an inactive tag."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)
    nbvalx.jupyter_magics.register_run_if_allowed_tags("tag1, tag2")
    nbvalx.jupyter_magics.register_run_if_current_tag("tag1")
    nbvalx.jupyter_magics.run_if("tag2", "a = 1")
    # the cell does not get executed, otherwise it would have raised an AttributeError
    nbvalx.jupyter_magics.unload_ipython_extension(mock_ipython)


def test_unload_extension(mock_ipython: MockIPythonShell) -> None:
    """Check deletion of extension attributes."""
    nbvalx.jupyter_magics.load_ipython_extension(mock_ipython)
    nbvalx.jupyter_magics.unload_ipython_extension(mock_ipython)
    assert nbvalx.jupyter_magics.load_ipython_extension.loaded is False
    assert not hasattr(nbvalx.jupyter_magics.load_ipython_extension, "allowed_tags")
    assert not hasattr(nbvalx.jupyter_magics.load_ipython_extension, "current_tag")
