# Copyright (C) 2022 by the nbvalx authors
#
# This file is part of nbvalx.
#
# SPDX-License-Identifier: BSD-3-Clause
"""Unit test for the nbvalx.tempfile module."""

import os
import typing

import mpi4py.MPI
import pytest

import nbvalx.tempfile


@pytest.mark.parametrize("TemporaryPath", [nbvalx.tempfile.TemporaryFile, nbvalx.tempfile.TemporaryDirectory])
def test_tempfile_name(TemporaryPath: typing.Type[nbvalx.tempfile.ParallelSafeContextManagerStub]) -> None:
    """Unit test to check that all ranks see a path of the same name."""
    comm = mpi4py.MPI.COMM_WORLD
    tmp_path = TemporaryPath(comm)
    tmp_path.__enter__()
    name_0 = None
    if comm.rank == 0:
        name_0 = tmp_path._temp_obj.name  # type: ignore[attr-defined]
    name_0 = comm.bcast(name_0, root=0)
    assert tmp_path.name == name_0
    tmp_path.__exit__(None, None, None)


@pytest.mark.parametrize("TemporaryPath", [nbvalx.tempfile.TemporaryFile, nbvalx.tempfile.TemporaryDirectory])
def test_tempfile_context_manager(TemporaryPath: typing.Type[nbvalx.tempfile.ParallelSafeContextManagerStub]) -> None:
    """Unit test to check that context manager returns a string with the path."""
    comm = mpi4py.MPI.COMM_WORLD
    with TemporaryPath(comm) as tmp_path:
        assert isinstance(tmp_path, str)
        assert tmp_path.startswith(os.sep)


@pytest.mark.parametrize("TemporaryPath", [nbvalx.tempfile.TemporaryFile, nbvalx.tempfile.TemporaryDirectory])
def test_tempfile_cleanup_on_success(
    TemporaryPath: typing.Type[nbvalx.tempfile.ParallelSafeContextManagerStub]
) -> None:
    """Unit test to check that temporary path gets cleaned up after successful execution."""
    comm = mpi4py.MPI.COMM_WORLD
    with TemporaryPath(comm) as tmp_path:
        assert os.path.exists(tmp_path)
    assert not os.path.exists(tmp_path)


@pytest.mark.parametrize("TemporaryPath", [nbvalx.tempfile.TemporaryFile, nbvalx.tempfile.TemporaryDirectory])
def test_tempfile_cleanup_on_error(TemporaryPath: typing.Type[nbvalx.tempfile.ParallelSafeContextManagerStub]) -> None:
    """Unit test to check that temporary path get cleaned up after an error too."""
    comm = mpi4py.MPI.COMM_WORLD
    with pytest.raises(RuntimeError):
        with TemporaryPath(comm) as tmp_path:
            assert os.path.exists(tmp_path)
            raise RuntimeError()
    assert not os.path.exists(tmp_path)
