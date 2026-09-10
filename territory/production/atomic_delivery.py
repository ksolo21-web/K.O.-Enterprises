"""Atomic, no-clobber installation of a verified result directory.

Linux uses renameat2(RENAME_NOREPLACE), not a check followed by rename.
Windows os.rename already refuses an existing destination. Other runtimes and
unsupported Linux filesystems fail closed; there is no copy/delete fallback.
Parent directories must remain in the owner's trusted local workspace. This
primitive covers process interruption, not a complete power-loss durability claim.
"""
from __future__ import annotations
import ctypes
import errno
import os
from pathlib import Path
import stat
import sys


def _linux_rename(source: bytes, destination: bytes) -> None:
    try:
        rename = ctypes.CDLL(None, use_errno=True).renameat2
    except (AttributeError, OSError) as error:
        raise OSError(errno.ENOTSUP, 'Atomic no-replace rename is unavailable') from error
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int,
                       ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    # AT_FDCWD = -100; RENAME_NOREPLACE = 1. Never remove this flag on failure.
    if rename(-100, source, -100, destination, 1) != 0:
        code = ctypes.get_errno()
        raise OSError(code, 'Atomic result installation refused')


def install_directory(source: Path, destination: Path) -> None:
    """Move a staged directory once, leaving any existing destination intact."""
    source, destination = Path(source), Path(destination)
    encoded_source, encoded_destination = os.fsencode(source), os.fsencode(destination)
    if b'\0' in encoded_source or b'\0' in encoded_destination:
        raise ValueError('NUL is not a valid filesystem path character')
    if not stat.S_ISDIR(source.lstat().st_mode):
        raise OSError(errno.EINVAL, 'Staging path must be a real directory')
    if sys.platform.startswith('linux'):
        _linux_rename(encoded_source, encoded_destination)
    elif sys.platform == 'win32':
        os.rename(source, destination)
    else:
        raise OSError(errno.ENOTSUP, 'No verified atomic no-replace primitive on this platform')
