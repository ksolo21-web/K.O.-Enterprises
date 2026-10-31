"""Verify pinned upstream Ollama Linux package without executing downloaded code.

Release metadata verified against ollama/ollama GitHub release v0.40.13 on
2026-10-30. Changing this pin requires reviewing upstream release metadata.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

OLLAMA_RELEASE = 'v0.40.13'
OLLAMA_ASSET = 'ollama-linux-amd64.tar.zst'
OLLAMA_SHA256 = 'c9490e0f520be21271d969e6703f012268b1d39f8b70dd58854e5bfef7a75bb6'
OLLAMA_SIZE_BYTES = 1525346571
OLLAMA_ASSET_URL = (
    'https://github.com/ollama/ollama/releases/download/'
    + OLLAMA_RELEASE + '/' + OLLAMA_ASSET
)
UPSTREAM_METADATA = 'https://api.github.com/repos/ollama/ollama/releases/tags/' + OLLAMA_RELEASE

class VerificationError(ValueError):
    pass


def verify_archive(path: Path) -> dict:
    """Fail closed on absent, symlinked, wrong-size or checksum-mismatched archive."""
    if path.is_symlink() or not path.is_file():
        raise VerificationError('Archive must be a regular existing file, not a symlink')
    if path.stat().st_size != OLLAMA_SIZE_BYTES:
        raise VerificationError('Ollama release archive size mismatch')
    sha=hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            sha.update(block)
    if sha.hexdigest() != OLLAMA_SHA256:
        raise VerificationError('Ollama release archive SHA-256 mismatch')
    return {'status':'VERIFIED', 'release':OLLAMA_RELEASE, 'asset':OLLAMA_ASSET,
            'asset_size_bytes':OLLAMA_SIZE_BYTES, 'asset_sha256':OLLAMA_SHA256}


def main(argv=None):
    parser=argparse.ArgumentParser(description='Verify pinned Ollama release archive before extraction')
    parser.add_argument('archive',type=Path)
    args=parser.parse_args(argv)
    try:
        result=verify_archive(args.archive)
    except (VerificationError,OSError) as error:
        print('BLOCKED: '+str(error),file=sys.stderr)
        return 2
    print('VERIFIED: '+result['release']+' '+result['asset_sha256'])
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
