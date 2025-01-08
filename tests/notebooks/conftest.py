# Copyright (C) 2022-2025 by the nbvalx authors
#
# This file is part of nbvalx.
#
# SPDX-License-Identifier: BSD-3-Clause
"""pytest configuration file for notebooks tests."""

import pytest

import nbvalx.pytest_hooks_notebooks

pytest_addoption = nbvalx.pytest_hooks_notebooks.addoption
pytest_collect_file = nbvalx.pytest_hooks_notebooks.collect_file


def pytest_sessionstart(session: pytest.Session) -> None:
    """Automatically add **/coverage_mock_module.py as data to be linked in the work directory."""
    # Add mesh files as data to be linked
    link_data_in_work_dir = session.config.option.link_data_in_work_dir
    if len(link_data_in_work_dir) == 0:
        link_data_in_work_dir.append("**/coverage_mock_module.py")
    else:
        assert len(link_data_in_work_dir) == 1
        assert link_data_in_work_dir[0] == "**/coverage_mock_module.py"
    # Start session as in notebooks hooks
    nbvalx.pytest_hooks_notebooks.sessionstart(session)
