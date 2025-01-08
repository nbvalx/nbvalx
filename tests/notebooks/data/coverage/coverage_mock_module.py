# Copyright (C) 2022-2025 by the nbvalx authors
#
# This file is part of nbvalx.
#
# SPDX-License-Identifier: BSD-3-Clause
"""A mock module to test coverage integration."""

def my_sum(a: int, b: int) -> int:
    """Sum two numbers."""
    return a + b


def pragma_ignored() -> None:  # pragma: no cover
    """Ignored function that will be considered as covered even though it is untested."""
    pass
