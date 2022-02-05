# Copyright (C) 2022 by the nbvalx authors
#
# This file is part of nbvalx.
#
# SPDX-License-Identifier: BSD-3-Clause
"""
Utility functions to be used in pytest configuration file for unit tests.

Such functions are mainly responsible to call garbage collection and put a MPI barrier after each test.

See also: https://github.com/pytest-dev/pytest/blob/main/src/_pytest/hookspec.py for type hints.
"""

import gc
import typing

import mpi4py
import mpi4py.MPI
import pytest


def runtest_setup(item: pytest.Item) -> None:
    """Disable garbage collection before running tests."""
    # Disable garbage collection
    gc.disable()


def runtest_teardown(item: pytest.Item, nextitem: typing.Optional[pytest.Item]) -> None:
    """Force garbage collection and put a MPI barrier after running tests."""
    # Re-enable garbage collection
    gc.enable()
    # Run garbage gollection
    del item
    gc.collect()
    # Add a MPI barrier in parallel
    mpi4py.MPI.COMM_WORLD.Barrier()
