# Copyright (C) 2022-2024 by the nbvalx authors
#
# This file is part of nbvalx.
#
# SPDX-License-Identifier: BSD-3-Clause
"""Parallel-safe context managers to create temporary files and directories."""

import tempfile
import types
import typing

import mpi4py.MPI


class TempFileContextManagerStub(typing.ContextManager[str]):
    """Stub for tempfile context managers."""

    def __init__(
        self, *args: typing.Any, **kwargs: typing.Any  # noqa: ANN401
    ) -> None:  # pragma: no cover
        ...

    @property
    def name(self) -> str:  # type: ignore[empty-body] # pragma: no cover
        """Return the path of the temporary object."""
        ...


class ParallelSafeContextManagerStub(typing.ContextManager[str]):
    """Stub for parallel safe tempfile context managers."""

    def __init__(
        self, comm: mpi4py.MPI.Intracomm, *args: typing.Any, **kwargs: typing.Any  # noqa: ANN401
    ) -> None:  # pragma: no cover
        ...

    @property
    def name(self) -> str:  # type: ignore[empty-body] # pragma: no cover
        """Return the path of the temporary object."""
        ...


def ParallelSafeWrapper(  # noqa: N802
    TempFileContextManager: typing.Type[TempFileContextManagerStub]  # noqa: N803
) -> typing.Type[ParallelSafeContextManagerStub]:
    """Implement a decorator to wrap a parallel-safe version of tempfile context managers."""

    class _(ParallelSafeContextManagerStub):  # noqa: N801
        """A context manager that wraps a parallel-safe version of tempfile context managers."""

        def __init__(
            self, comm: mpi4py.MPI.Intracomm, *args: typing.Any, **kwargs: typing.Any  # noqa: ANN401
        ) -> None:
            self._comm = comm
            self._args = args
            self._kwargs = kwargs
            self._temp_obj: typing.Optional[TempFileContextManagerStub] = None

        @property
        def name(self) -> str:
            """Return the path of the temporary object."""
            name = None
            if self._comm.rank == 0:
                assert self._temp_obj is not None
                name = self._temp_obj.name
            return self._comm.bcast(name, root=0)  # type: ignore[no-any-return]

        def __enter__(self) -> str:
            """Enter the context on rank zero and broadcast the result to the other ranks."""
            self._comm.Barrier()
            if self._comm.rank == 0:
                self._temp_obj = TempFileContextManager(*self._args, **self._kwargs)
                self._temp_obj.__enter__()
            self._comm.Barrier()
            return self.name

        def __exit__(
            self, exception_type: typing.Optional[typing.Type[BaseException]],
            exception_value: typing.Optional[BaseException],
            traceback: typing.Optional[types.TracebackType]
        ) -> None:
            """Exit the context on rank zero."""
            self._comm.Barrier()
            if self._comm.rank == 0:
                assert self._temp_obj is not None
                self._temp_obj.__exit__(exception_type, exception_value, traceback)
                del self._temp_obj
            self._comm.Barrier()

    return _


TemporaryFile = ParallelSafeWrapper(tempfile.NamedTemporaryFile)  # type: ignore[arg-type]
TemporaryDirectory = ParallelSafeWrapper(tempfile.TemporaryDirectory)  # type: ignore[arg-type]
