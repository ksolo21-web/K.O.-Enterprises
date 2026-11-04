"""V10 local private original-source media audit; not customer release."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from scripts.m4_safety_benchmark_cli import _private_json
from inspection_engine.m4_source_byte_custody import verify_private_source_bytes
from inspection_engine.serious_defect_benchmark import BenchmarkBlock


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Offline private original-byte/photo/video-frame audit only")
    parser.add_argument("--media-manifest", required=True, type=Path)
    parser.add_argument("--source-locators", required=True, type=Path)
    parser.add_argument("--private-root", required=True, type=Path)
    parser.add_argument("--externally-pinned-media-manifest-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        result = verify_private_source_bytes(
            _private_json(args.media_manifest), _private_json(args.source_locators),
            args.private_root,
            independent_media_manifest_pin_sha256=(
                args.externally_pinned_media_manifest_sha256))
    except (BenchmarkBlock, OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "ORIGINAL_MEDIA_BYTE_AUDIT_BLOCKED",
                          "reason": str(exc), "customer_release_allowed": False}))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
