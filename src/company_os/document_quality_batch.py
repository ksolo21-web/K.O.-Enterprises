"""Bounded, offline parallel document preflight for safe GitHub CI use.

No network calls, notifications, approvals or publication are performed.
"""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

from .document_quality import _date, audit_pack


def check_many(root: Path, *, workers: int = 4, as_of: date | None = None,
               public_repo: bool = False) -> dict:
    if not root.is_dir():
        return {"status": "BLOCK", "total": 0, "passed": 0,
                "results": [{"pack": str(root), "status": "BLOCK", "errors": ["BATCH_ROOT: not a directory"]}]}
    packs = sorted(p.parent for p in root.glob("*/manifest.json") if p.parent.is_dir())
    if not packs:
        return {"status": "BLOCK", "total": 0, "passed": 0,
                "results": [{"pack": str(root), "status": "BLOCK", "errors": ["BATCH_EMPTY: no direct child packs"]}]}
    with ThreadPoolExecutor(max_workers=max(1, min(int(workers), 16))) as pool:
        results = list(pool.map(lambda p: audit_pack(p, as_of, public_repo=public_repo), packs))
    items = [{"pack": p.name, **result} for p, result in zip(packs, results)]
    passed = sum(item["status"] == "PASS_REVIEWED_NOT_AUTHORIZED" for item in items)
    return {"status": "PASS_REVIEWED_NOT_AUTHORIZED" if passed == len(packs) else "BLOCK",
            "total": len(packs), "passed": passed, "results": items}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate bounded batches of independent document packs")
    parser.add_argument("root", type=Path)
    parser.add_argument("--workers", type=int, choices=range(1, 17), default=4)
    parser.add_argument("--as-of")
    parser.add_argument("--public-repo", action="store_true")
    args = parser.parse_args()
    as_of = _date(args.as_of) if args.as_of else None
    if args.as_of and as_of is None:
        parser.error("--as-of must be ISO YYYY-MM-DD")
    result = check_many(args.root, workers=args.workers, as_of=as_of,
                        public_repo=args.public_repo)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS_REVIEWED_NOT_AUTHORIZED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
