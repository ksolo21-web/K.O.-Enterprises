"""Opt-in local M4 private draft builder; no external calls or approvals."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from inspection_engine.core import DataError
from inspection_engine.m4_assembly import assemble_private_draft


def main() -> int:
    parser = argparse.ArgumentParser(description="Source-bound PRIVATE Option 2 draft; never customer release")
    parser.add_argument("project", type=Path, help="Existing validated inspection JSON file")
    parser.add_argument("--out-dir", required=True, type=Path, help="Private draft output directory")
    parser.add_argument("--q02-json", type=Path, help="Optional saved Q02 record")
    parser.add_argument("--q03-json", type=Path, help="Optional matched Q03 record")
    args = parser.parse_args()
    try:
        q02 = json.loads(args.q02_json.read_text(encoding="utf-8")) if args.q02_json else None
        q03 = json.loads(args.q03_json.read_text(encoding="utf-8")) if args.q03_json else None
        result = assemble_private_draft(args.project, args.out_dir, q02=q02, q03=q03)
    except (DataError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc),
                          "customer_release_allowed": False}, indent=2))
        return 2
    print(json.dumps({"status": "PRIVATE_DRAFT_CREATED", **result}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
