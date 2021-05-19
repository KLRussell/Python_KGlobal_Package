from pandas.core.dtypes.common import is_integer
from typing import List, Union
import types
import enum
import os

if os.name == 'nt':  # pragma: no cover
    import msvcrt

    LOCK_EX = 0x1  #: exclusive lock
    LOCK_SH = 0x2  #: shared lock
    LOCK_NB = 0x4  #: non-blocking
    LOCK_UN = msvcrt.LK_UNLCK  #: unlock
elif os.name == 'posix':  # pragma: no cover
    import fcntl

    LOCK_EX = fcntl.LOCK_EX  #: exclusive lock
    LOCK_SH = fcntl.LOCK_SH  #: shared lock
    LOCK_NB = fcntl.LOCK_NB  #: non-blocking
    LOCK_UN = fcntl.LOCK_UN  #: unlock
else:  # pragma: no cover
    raise RuntimeError('PortaLocker only defined for nt and posix platforms')


class LockFlags(enum.IntFlag):
    EXCLUSIVE = LOCK_EX  #: exclusive lock
    SHARED = LOCK_SH  #: shared lock
    NON_BLOCKING = LOCK_NB  #: non-blocking
    UNBLOCK = LOCK_UN  #: unlock


PythonScalar = Union[str, int, float, bool]
PandasScalar = Union["Period", "Timestamp", "Timedelta", "Interval"]
Scalar = Union[PythonScalar, PandasScalar]
DEFAULT_TIMEOUT = 5
DEFAULT_CHECK_INTERVAL = 0.25
DEFAULT_FAIL_WHEN_LOCKED = False
LOCK_METHOD = LockFlags.EXCLUSIVE | LockFlags.NON_BLOCKING


def get_version(module: types.ModuleType) -> str:
    version = getattr(module, "__version__", None)
    if version is None:
        # xlrd uses a capitalized attribute name
        version = getattr(module, "__VERSION__", None)

    if version is None:
        raise ImportError(f"Can't determine version for {module.__name__}")
    return version


def maybe_convert_usecols(usecols):
    if usecols is None:
        return usecols

    if is_integer(usecols):
        raise ValueError(
            "Passing an integer for `usecols` is no longer supported.  "
            "Please pass in a list of int from 0 to `usecols` inclusive instead."
        )

    if isinstance(usecols, str):
        return _range2cols(usecols)

    return usecols


def _range2cols(areas: str) -> List[int]:
    cols: List[int] = []

    for rng in areas.split(","):
        if ":" in rng:
            rngs = rng.split(":")
            cols.extend(range(_excel2num(rngs[0]), _excel2num(rngs[1]) + 1))
        else:
            cols.append(_excel2num(rng))

    return cols


def _excel2num(x: str) -> int:
    index = 0

    for c in x.upper().strip():
        cp = ord(c)

        if cp < ord("A") or cp > ord("Z"):
            raise ValueError(f"Invalid column name: {x}")

        index = index * 26 + cp - ord("A") + 1

    return index - 1
