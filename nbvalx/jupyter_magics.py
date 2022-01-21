# Copyright (C) 2022 by the nbvalx authors
#
# This file is part of nbvalx.
#
# SPDX-License-Identifier: BSD-3-Clause
"""Custom jupyter magics to selectively run cells using tags."""

import IPython


def register_run_if_allowed_tags(line: str) -> None:
    """Register allowed tags."""
    load_ipython_extension.allowed_tags = [tag.strip() for tag in line.split(",")]


def register_run_if_current_tag(line: str) -> None:
    """Register current tag."""
    assert line in load_ipython_extension.allowed_tags
    load_ipython_extension.current_tag = line


def run_if(line: str, cell: str = None) -> None:
    """Run cell if the current tag is in the list provided by the magic argument."""
    allowed_tags = [tag.strip() for tag in line.split(",")]
    if load_ipython_extension.current_tag in allowed_tags:
        IPython.get_ipython().run_cell(cell)


def load_ipython_extension(ipython: IPython.core.interactiveshell.InteractiveShell) -> None:
    """Register magics defined in this module when the extension loads."""
    ipython.register_magic_function(register_run_if_allowed_tags, "line")
    ipython.register_magic_function(register_run_if_current_tag, "line")
    ipython.register_magic_function(run_if, "cell")
    load_ipython_extension.loaded = True
    load_ipython_extension.allowed_tags = []
    load_ipython_extension.current_tag = None


load_ipython_extension.loaded = False


def unload_ipython_extension(ipython: IPython.core.interactiveshell.InteractiveShell) -> None:
    """Unregister the magics defined in this module when the extension unloads."""
    del ipython.magics_manager.magics["line"]["register_run_if_allowed_tags"]
    del ipython.magics_manager.magics["line"]["register_run_if_current_tag"]
    del ipython.magics_manager.magics["cell"]["run_if"]
    load_ipython_extension.loaded = False
    del load_ipython_extension.allowed_tags
    del load_ipython_extension.current_tag
