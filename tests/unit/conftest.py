# Copyright (C) 2022-2025 by the nbvalx authors
#
# This file is part of nbvalx.
#
# SPDX-License-Identifier: BSD-3-Clause
"""pytest configuration file for unit tests."""

import nbvalx.pytest_hooks_unit_tests

pytest_runtest_setup = nbvalx.pytest_hooks_unit_tests.runtest_setup
pytest_runtest_teardown = nbvalx.pytest_hooks_unit_tests.runtest_teardown
