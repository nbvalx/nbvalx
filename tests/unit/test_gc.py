# Copyright (C) 2022-2024 by the nbvalx authors
#
# This file is part of nbvalx.
#
# SPDX-License-Identifier: BSD-3-Clause
"""Unit test to check that garbage collection is disabled."""

import gc


def test_gc_is_disabled() -> None:
    """Unit test to check that garbage collection is disabled."""
    assert not gc.isenabled()
