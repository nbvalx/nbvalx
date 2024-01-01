# Copyright (C) 2022-2024 by the nbvalx authors
#
# This file is part of nbvalx.
#
# SPDX-License-Identifier: BSD-3-Clause
"""nbvalx main module."""

# Import jupyter magics so that users can load them with %%load_ext nbvalx
from nbvalx.jupyter_magics import load_ipython_extension, unload_ipython_extension
