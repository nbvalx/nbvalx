# Copyright (C) 2022-2024 by the nbvalx authors
#
# This file is part of nbvalx.
#
# SPDX-License-Identifier: BSD-3-Clause
"""Utility functions to be used in pytest configuration file for unit tests."""

import gc
import typing

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
