"""Offline, operator-invoked M4 human-review packet, UI and signature CLI.

Do not commit a generated worksheet, response, private signing key, customer
media or source inspection report. All outputs are internal; no release action.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from inspection_engine.core import DataError
from inspection_engine.m4_pipeline import _get_case, _atomic_json, _load_json
from inspection_engine.m4_human_review import (
    prepare_review_request, sign_review, verify_reviews, _get_packet, _digest, ROLES
)
from inspection_engine.m4_review_ui import build_review_worksheet


def template(workspace: Path, role: str) -> dict:
    work, state, _, _ = _get_case(workspace)
    packet = _get_packet(work, state)
    response = {
        "request_digest": _digest(packet),
        "reviewer_id": "",
        "role": role,
        "note": "",
        "items": [{
            "section": x["section"], "id": x["id"],
            "decision": "", "note": ""
        } for x in packet["items"]],
        "media": [{
            "id": x["id"], "decision": "", "note": ""
        } for x in packet["media"]],
        "systems": [{
            "system": x, "decision": "", "note": ""
        } for x in packet["systems"]],
    }
    output = work / ("review_" + role + "_UNSIGNED_template.json")
    if output.exists():
        if _load_json(output) != response:
            raise DataError("Existing unsigned review template changed")
        return {"status": "REUSED", "template": str(output),
                "customer_release_allowed": False}
    _atomic_json(output, response)
    return {"status": "CREATED", "template": str(output),
            "customer_release_allowed": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Private M4 review tools; never authorizes customer release")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("prepare", "worksheet", "template", "sign", "verify"):
        p = sub.add_parser(command)
        p.add_argument("--workspace", type=Path, required=True)
        if command in ("prepare", "sign", "verify"):
            p.add_argument("--trust-file", type=Path, required=True)
        if command == "template":
            p.add_argument("--role", required=True, choices=ROLES)
        if command == "sign":
            p.add_argument("--review-json", type=Path, required=True)
            p.add_argument("--private-key", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare_review_request(args.workspace, args.trust_file)
        elif args.command == "worksheet":
            result = build_review_worksheet(args.workspace)
        elif args.command == "template":
            result = template(args.workspace, args.role)
        elif args.command == "sign":
            decisions = json.loads(args.review_json.read_text(encoding="utf-8"))
            result = sign_review(args.workspace, args.trust_file, args.private_key, decisions)
        else:
            result = verify_reviews(args.workspace, args.trust_file)
    except (DataError, ValueError, OSError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc),
                          "customer_release_allowed": False}, indent=2))
        return 2
    print(json.dumps({"status": "INTERNAL_ONLY", "result": result,
                      "customer_release_allowed": False}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
