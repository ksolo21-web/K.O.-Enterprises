"""M4 V10 private, read-only source-byte path and decoding controls."""
from __future__ import annotations
import hashlib
import os
from pathlib import Path, PurePosixPath
import stat

from PIL import Image
from .capture import MAX_PHOTO_BYTES, validate_image
from .serious_defect_benchmark import BenchmarkBlock


def private_root(value):
    root = Path(value).expanduser().absolute()
    if any(p.is_symlink() for p in (root, *root.parents)):
        raise BenchmarkBlock("Private evidence root cannot use symlinks")
    root = root.resolve(strict=True)
    if not root.is_dir() or any((p / ".git").exists() for p in (root, *root.parents)):
        raise BenchmarkBlock("Source evidence must remain outside Git")
    return root


def private_file(root, relative):
    if (not isinstance(relative, str) or not 1 <= len(relative) <= 240
            or "\\" in relative or "\x00" in relative or relative.startswith("/")):
        raise BenchmarkBlock("Unsafe private media locator")
    parts = relative.split("/")
    if (len(parts) > 8 or any(p in ("", ".", "..") for p in parts)
            or PurePosixPath(relative).as_posix() != relative):
        raise BenchmarkBlock("Noncanonical or traversal private media path")
    cursor = root
    for i, part in enumerate(parts):
        cursor = cursor / part
        try:
            info = cursor.lstat()
        except OSError as exc:
            raise BenchmarkBlock("Missing or unreadable source evidence") from exc
        if stat.S_ISLNK(info.st_mode):
            raise BenchmarkBlock("Symlinked source evidence prohibited")
        if i < len(parts) - 1 and not stat.S_ISDIR(info.st_mode):
            raise BenchmarkBlock("Media parent is not a directory")
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise BenchmarkBlock("Source must be a regular unlinked file")
    return cursor


def hash_file(path, limit):
    size = path.stat().st_size
    if not 1 <= size <= limit:
        raise BenchmarkBlock("Original bytes outside source size limit")
    digest = hashlib.sha256()
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(fd, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise BenchmarkBlock("Evidence changed into a non-file")
            total = 0
            while block := stream.read(1024 * 1024):
                total += len(block)
                if total > limit:
                    raise BenchmarkBlock("Source grew beyond size limit")
                digest.update(block)
    except OSError as exc:
        raise BenchmarkBlock("Original source unreadable") from exc
    if total != size:
        raise BenchmarkBlock("Source modified during hashing")
    return digest.hexdigest()


def validate_photo_pixels(path):
    try:
        details = validate_image(path)
        with Image.open(path) as image:
            if getattr(image, "n_frames", 1) != 1:
                raise BenchmarkBlock("Multi-frame image not supported")
            image.load()
        return details
    except BenchmarkBlock:
        raise
    except Exception as exc:
        raise BenchmarkBlock("Source image decoding failed") from exc


def check_photo_hash(path, expected):
    if hash_file(path, MAX_PHOTO_BYTES) != expected:
        raise BenchmarkBlock("Actual source-photo bytes differ from frozen V9 manifest")
