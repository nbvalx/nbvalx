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

try:
    import _pytest.config
    import _pytest.main
    import _pytest.nodes
except ImportError:  # pragma: no cover
    runtest_setup = None
    runtest_teardown = None
else:
    def runtest_setup(item: _pytest.nodes.Item) -> None:
        """Disable garbage collection before running tests."""
        # Disable garbage collection
        gc.disable()

    def runtest_teardown(item: _pytest.nodes.Item, nextitem: typing.Optional[_pytest.nodes.Item]) -> None:
        """Force garbage collection and put a MPI barrier after running tests."""
        # Re-enable garbage collection
        gc.enable()
        # Run garbage gollection
        del item
        gc.collect()
        # Add a MPI barrier in parallel
        mpi4py.MPI.COMM_WORLD.Barrier()
