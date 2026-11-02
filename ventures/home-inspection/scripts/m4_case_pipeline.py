"""M4 private case operator CLI; explicit single-stage invocation only.

Inference stages require --authorize-local-inference, an already-installed local
Ollama model, and human operator invocation. No downloads or cloud fallback.
This CLI does not approve findings, sign reports, or deliver to customers.
"""
from __future__ import annotations

import argparse
import json

from inspection_engine.core import DataError
from inspection_engine.vision import ollama_local
from inspection_engine.critic import CRITIC_SCHEMA, CRITIC_SYSTEM_PROMPT
from inspection_engine.adjudication import ollama_reasoner
from inspection_engine.m4_pipeline import (
    prepare_case, status_case, run_specialists, run_q02,
    run_q03, render_private_case,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="M4 internal draft runner: not customer release")
    commands = parser.add_subparsers(dest="stage", required=True)
    p = commands.add_parser("prepare", help="Bind source and selected photos, without model calls")
    p.add_argument("project")
    p.add_argument("--workspace", required=True)
    p.add_argument("--media-ids", nargs="+", default=None)

    p = commands.add_parser("status", help="Validate staged receipts and show current state")
    p.add_argument("--workspace", required=True)

    p = commands.add_parser("render", help="Create private Option 2 draft after saved Q03")
    p.add_argument("--workspace", required=True)

    for stage in ("specialists", "q02", "q03"):
        p = commands.add_parser(stage, help="Opt-in local Ollama " + stage + " stage")
        p.add_argument("--workspace", required=True)
        p.add_argument("--model", required=True,
                       help="Already-installed localhost Ollama model name")
        p.add_argument("--authorize-local-inference", action="store_true",
                       help="Confirm explicit operator approval for this one local-model stage")

    args = parser.parse_args(argv)
    try:
        if args.stage == "prepare":
            result = prepare_case(args.project, args.workspace, media_ids=args.media_ids)
        elif args.stage == "status":
            result = status_case(args.workspace)
        elif args.stage == "render":
            result = render_private_case(args.workspace)
        else:
            if not args.authorize_local_inference:
                raise DataError("Model stage requires explicit --authorize-local-inference")
            model = args.model
            identity = "local-ollama:" + model
            if args.stage == "specialists":
                result = run_specialists(
                    args.workspace,
                    lambda image, prompt, *, schema: ollama_local(
                        image, prompt, model, schema=schema),
                    provider_id=identity, provider_accepts_schema=True,
                )
            elif args.stage == "q02":
                result = run_q02(
                    args.workspace,
                    lambda image, prompt: ollama_local(
                        image, prompt, model, schema=CRITIC_SCHEMA,
                        system_prompt=CRITIC_SYSTEM_PROMPT),
                    provider_id=identity,
                )
            else:
                result = run_q03(
                    args.workspace,
                    lambda prompt, schema: ollama_reasoner(prompt, schema, model),
                    provider_id=identity,
                )
    except (DataError, ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({
            "status": "BLOCKED", "reason": str(exc),
            "inspect_in_flight_marker_before_retry": True,
            "customer_release_allowed": False,
        }, indent=2))
        return 2
    print(json.dumps({"status": "INTERNAL_ONLY", "result": result,
                      "customer_release_allowed": False}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
