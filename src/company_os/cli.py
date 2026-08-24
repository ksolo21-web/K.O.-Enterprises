"""Command-line interface for the local company ledger."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Sequence

from .errors import CompanyOSError
from .policy import ApprovalClass
from .reporting import generate_ceo_report, write_ceo_report
from .scoring import COMPONENT_WEIGHTS, PENALTY_WEIGHTS, score_from_evidence
from .storage import CompanyStore, OPPORTUNITY_INITIAL_STATUSES, OPPORTUNITY_STATUSES


def _json_dump(value: Any) -> None:
    print(json.dumps(value, indent=2, sort_keys=True, default=str))


def _terminal_text(value: object) -> str:
    """Render untrusted ledger text without emitting terminal controls."""

    rendered: list[str] = []
    for character in str(value):
        if character in {"\n", "\t"} or character.isprintable():
            rendered.append(character)
        elif ord(character) <= 0xFF:
            rendered.append(f"\\x{ord(character):02x}")
        else:
            rendered.append(f"\\u{ord(character):04x}")
    return "".join(rendered)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="company-os",
        description="Evidence-led, human-governed operating ledger for K.O. Enterprises.",
    )
    parser.add_argument(
        "--db",
        default=os.environ.get(
            "COMPANY_OS_DB_PATH", os.environ.get("COMPANY_OS_DB", "state/company_os.db")
        ),
        help="SQLite database path (default: COMPANY_OS_DB_PATH or state/company_os.db)",
    )
    parser.add_argument(
        "--repo-root",
        default=os.environ.get("COMPANY_OS_REPO_ROOT", str(Path.cwd())),
        help="repository root used to check PAUSE_AUTONOMY",
    )
    parser.add_argument(
        "--actor",
        default=os.environ.get("COMPANY_OS_ACTOR", "company_os"),
        help="human-readable actor written to audit records",
    )
    parser.add_argument(
        "--report-dir",
        default=os.environ.get("COMPANY_OS_REPORT_DIR"),
        help="default directory for generated reports; without it, report prints to stdout",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("init", help="create or migrate the local database")

    status = commands.add_parser("status", help="show company ledger and pause status")
    status.add_argument("--json", action="store_true")

    opportunity = commands.add_parser("opportunity", help="manage market opportunities")
    opportunity_commands = opportunity.add_subparsers(dest="opportunity_command", required=True)
    opportunity_add = opportunity_commands.add_parser("add", help="add an opportunity")
    opportunity_add.add_argument("title")
    opportunity_add.add_argument("--slug")
    opportunity_add.add_argument("--description", default="")
    opportunity_add.add_argument("--buyer", default="")
    opportunity_add.add_argument("--budget-holder", default="")
    opportunity_add.add_argument("--why-now", default="")
    opportunity_add.add_argument("--cost-of-inaction", default="")
    opportunity_add.add_argument("--current-alternative", default="")
    opportunity_add.add_argument("--entry-wedge", default="")
    opportunity_add.add_argument("--distribution-path", default="")
    opportunity_add.add_argument(
        "--status", choices=sorted(OPPORTUNITY_INITIAL_STATUSES), default="candidate"
    )
    opportunity_add.add_argument("--json", action="store_true")

    opportunity_list = opportunity_commands.add_parser("list", help="list opportunities")
    opportunity_list.add_argument("--status", choices=sorted(OPPORTUNITY_STATUSES))
    opportunity_list.add_argument("--json", action="store_true")

    opportunity_show = opportunity_commands.add_parser("show", help="show one opportunity")
    opportunity_show.add_argument("opportunity")
    opportunity_show.add_argument("--json", action="store_true")

    opportunity_status = opportunity_commands.add_parser("set-status", help="change opportunity status")
    opportunity_status.add_argument("opportunity")
    opportunity_status.add_argument("status", choices=sorted(OPPORTUNITY_STATUSES))
    opportunity_status.add_argument("--json", action="store_true")

    evidence = commands.add_parser("evidence", help="manage timestamped evidence")
    evidence_commands = evidence.add_subparsers(dest="evidence_command", required=True)
    evidence_add = evidence_commands.add_parser("add", help="add sourced evidence")
    evidence_add.add_argument("opportunity")
    evidence_add.add_argument("--criterion", required=True)
    evidence_add.add_argument("--claim", required=True)
    evidence_add.add_argument("--source", required=True, dest="source_uri")
    evidence_add.add_argument("--source-type", default="public_web")
    evidence_add.add_argument("--strength", choices=["weak", "moderate", "strong"], default="moderate")
    evidence_add.add_argument("--rating", type=float, default=0.5)
    evidence_add.add_argument("--confidence", type=float, default=0.7)
    evidence_add.add_argument("--observed-at")
    evidence_add.add_argument(
        "--expires-at",
        required=True,
        help="ISO revalidation deadline; must be later than observed-at",
    )
    evidence_add.add_argument("--notes", default="")
    evidence_add.add_argument("--json", action="store_true")

    evidence_list = evidence_commands.add_parser("list", help="list evidence")
    evidence_list.add_argument("opportunity", nargs="?")
    evidence_list.add_argument("--include-expired", action="store_true")
    evidence_list.add_argument("--json", action="store_true")

    score = commands.add_parser("score", help="calculate and store a Market Void score")
    score.add_argument("opportunity")
    for component in COMPONENT_WEIGHTS:
        score.add_argument(f"--{component.replace('_', '-')}", type=float, dest=component)
    for penalty in PENALTY_WEIGHTS:
        score.add_argument(f"--{penalty.replace('_', '-')}", type=float, dest=penalty)
    score.add_argument("--low-competition", action="store_true")
    score.add_argument("--meaningful-cash-before-validation", action="store_true")
    score.add_argument("--regulated-or-risky-data", action="store_true")
    score.add_argument("--mvp-too-large", action="store_true")
    score.add_argument("--maintenance-incompatible", action="store_true")
    score.add_argument("--unlawful-advantage", action="store_true")
    score.add_argument("--json", action="store_true")

    approval = commands.add_parser("approval", help="manage explicit approvals")
    approval_commands = approval.add_subparsers(dest="approval_command", required=True)
    approval_request = approval_commands.add_parser("request", help="request approval")
    approval_request.add_argument("--action", required=True)
    approval_request.add_argument("--rationale", required=True)
    approval_request.add_argument("--risk", default="")
    approval_request.add_argument("--estimated-cost-cents", type=int, default=0)
    approval_request.add_argument("--reversibility", default="reversible")
    approval_request.add_argument(
        "--class",
        dest="approval_class",
        choices=[item.value for item in ApprovalClass],
    )
    approval_request.add_argument("--requested-by")
    approval_request.add_argument(
        "--expires-at",
        required=True,
        help="ISO timestamp after which the approval is unusable",
    )
    approval_request.add_argument("--json", action="store_true")

    approval_list = approval_commands.add_parser("list", help="list approvals")
    approval_list.add_argument(
        "--status", choices=["pending", "approved", "rejected", "expired", "cancelled"]
    )
    approval_list.add_argument("--json", action="store_true")

    approval_decide = approval_commands.add_parser("decide", help="approve or reject a request")
    approval_decide.add_argument("approval_id", type=int)
    approval_decide.add_argument("--decision", required=True, choices=["approved", "rejected"])
    approval_decide.add_argument("--decided-by", required=True)
    approval_decide.add_argument("--notes", default="")
    approval_decide.add_argument("--json", action="store_true")

    report = commands.add_parser("report", help="generate the Markdown CEO report")
    report.add_argument("--output")
    report.add_argument("--title", default="K.O. Enterprises CEO Report")

    return parser


def _print_status(state: dict[str, Any]) -> None:
    print(f"Company OS: {'PAUSED' if state['paused'] else 'ACTIVE'}")
    print(
        f"Database: {_terminal_text(state['database'])} "
        f"(schema v{state['schema_version']})"
    )
    print(
        f"Opportunities: {state['counts']['opportunities']} | "
        f"Evidence: {state['counts']['evidence']} ({state['stale_evidence']} stale) | "
        f"Experiments: {state['counts']['experiments']} | "
        f"Pending approvals: {state['pending_approvals']}"
    )
    for currency, financials in state["financials"].items():
        print(
            f"{currency} realized revenue={financials['actual_revenue_cents']}c "
            f"cleared={financials['cleared_revenue_cents']}c "
            f"refunds={financials['refunds_cents']}c "
            f"incurred costs={financials['incurred_costs_cents']}c "
            f"paid costs={financials['paid_costs_cents']}c "
            f"net cash contribution={financials['net_cash_contribution_cents']}c "
            f"projected={financials['projected_revenue_cents']}c"
        )


def _print_opportunities(rows: list[dict[str, Any]]) -> None:
    if not rows:
        print("No opportunities recorded.")
        return
    for row in rows:
        score = f"{row['latest_score']:.1f}" if row["latest_score"] is not None else "unscored"
        print(
            f"#{row['id']} {_terminal_text(row['slug'])} "
            f"[{_terminal_text(row['status'])}] score={score} — "
            f"{_terminal_text(row['title'])}"
        )


def _print_evidence(rows: list[dict[str, Any]]) -> None:
    if not rows:
        print("No evidence recorded.")
        return
    for row in rows:
        expiry = row["expires_at"] or "no expiry"
        print(
            f"#{row['id']} opportunity={row['opportunity_id']} "
            f"{_terminal_text(row['criterion'])} "
            f"rating={row['rating']:.2f} confidence={row['confidence']:.2f} "
            f"strength={row['strength']} expires={_terminal_text(expiry)}\n  "
            f"{_terminal_text(row['claim'])}\n  {_terminal_text(row['source_uri'])}"
        )


def _print_approvals(rows: list[dict[str, Any]]) -> None:
    if not rows:
        print("No approvals recorded.")
        return
    for row in rows:
        print(
            f"#{row['id']} [{row['status']}] {row['approval_class']} "
            f"cost_limit={row['estimated_cost_cents']}c — "
            f"{_terminal_text(row['action'])}"
        )


def _handle_command(args: argparse.Namespace, store: CompanyStore) -> int:
    if args.command == "init":
        result = store.initialize()
        print(
            f"Initialized {result['database']} at schema v{result['schema_version']} "
            f"(applied: {result['applied'] or 'none'})."
        )
        return 0

    if args.command == "status":
        state = store.status(repo_root=args.repo_root)
        _json_dump(state) if args.json else _print_status(state)
        return 0

    if args.command == "opportunity":
        if args.opportunity_command == "add":
            row = store.create_opportunity(
                args.title,
                slug=args.slug,
                description=args.description,
                buyer=args.buyer,
                budget_holder=args.budget_holder,
                why_now=args.why_now,
                cost_of_inaction=args.cost_of_inaction,
                current_alternative=args.current_alternative,
                entry_wedge=args.entry_wedge,
                distribution_path=args.distribution_path,
                status=args.status,
                actor=args.actor,
            )
            if args.json:
                _json_dump(row)
            else:
                print(f"Added opportunity #{row['id']} ({row['slug']}).")
            return 0
        if args.opportunity_command == "list":
            rows = store.list_opportunities(status=args.status)
            _json_dump(rows) if args.json else _print_opportunities(rows)
            return 0
        if args.opportunity_command == "show":
            row = store.get_opportunity(args.opportunity)
            if args.json:
                _json_dump(row)
            else:
                _print_opportunities([row])
                print(json.dumps(row, indent=2, sort_keys=True, default=str))
            return 0
        row = store.set_opportunity_status(args.opportunity, args.status, actor=args.actor)
        if args.json:
            _json_dump(row)
        else:
            print(f"Opportunity #{row['id']} is now {row['status']}.")
        return 0

    if args.command == "evidence":
        if args.evidence_command == "add":
            row = store.add_evidence(
                args.opportunity,
                criterion=args.criterion,
                claim=args.claim,
                source_uri=args.source_uri,
                source_type=args.source_type,
                strength=args.strength,
                rating=args.rating,
                confidence=args.confidence,
                observed_at=args.observed_at,
                expires_at=args.expires_at,
                notes=args.notes,
                actor=args.actor,
            )
            if args.json:
                _json_dump(row)
            else:
                print(f"Added evidence #{row['id']} to opportunity #{row['opportunity_id']}.")
            return 0
        rows = store.list_evidence(
            args.opportunity, include_expired=args.include_expired
        )
        _json_dump(rows) if args.json else _print_evidence(rows)
        return 0

    if args.command == "score":
        evidence = store.list_evidence(args.opportunity, include_expired=True)
        component_overrides = {
            name: getattr(args, name) for name in COMPONENT_WEIGHTS if getattr(args, name) is not None
        }
        penalty_overrides = {
            name: getattr(args, name) for name in PENALTY_WEIGHTS if getattr(args, name) is not None
        }
        hard_rejection_flags = {
            name: getattr(args, name)
            for name in (
                "meaningful_cash_before_validation",
                "regulated_or_risky_data",
                "mvp_too_large",
                "maintenance_incompatible",
                "unlawful_advantage",
            )
            if getattr(args, name)
        }
        score = score_from_evidence(
            evidence,
            overrides=component_overrides,
            penalty_overrides=penalty_overrides,
            hard_rejection_flags=hard_rejection_flags,
            low_competition=args.low_competition,
        )
        stored = store.save_score(
            args.opportunity,
            score,
            inputs={
                "evidence_ids": [row["id"] for row in evidence],
                "component_overrides": component_overrides,
                "penalty_overrides": penalty_overrides,
                "hard_rejection_flags": hard_rejection_flags,
                "low_competition": args.low_competition,
            },
            actor=args.actor,
        )
        if args.json:
            _json_dump(stored)
        else:
            print(
                f"Market Void score: {score.final_score:.2f}/100 "
                f"(base {score.base_score:.2f}, penalties {score.penalty_score:.2f})."
            )
            print(f"Eligible for advancement: {'yes' if score.eligible_for_advancement else 'no'}")
            for reason in score.rejection_reasons:
                print(f"REJECTION GATE: {reason}")
            for warning in score.warnings:
                print(f"WARNING: {warning}")
        return 0

    if args.command == "approval":
        if args.approval_command == "request":
            row = store.request_approval(
                action=args.action,
                rationale=args.rationale,
                risk=args.risk,
                estimated_cost_cents=args.estimated_cost_cents,
                reversibility=args.reversibility,
                approval_class=args.approval_class,
                requested_by=args.requested_by or args.actor,
                expires_at=args.expires_at,
            )
            if args.json:
                _json_dump(row)
            else:
                print(f"Created approval request #{row['id']} ({row['approval_class']}).")
            return 0
        if args.approval_command == "list":
            rows = store.list_approvals(status=args.status)
            _json_dump(rows) if args.json else _print_approvals(rows)
            return 0
        row = store.decide_approval(
            args.approval_id,
            decision=args.decision,
            decided_by=args.decided_by,
            notes=args.notes,
        )
        if args.json:
            _json_dump(row)
        else:
            print(f"Approval #{row['id']} is now {row['status']}.")
        return 0

    if args.command == "report":
        output_path = args.output
        if output_path is None and args.report_dir:
            output_path = str(Path(args.report_dir) / "ceo-report.md")
        if output_path:
            output = write_ceo_report(
                store, output_path, title=args.title, repo_root=args.repo_root
            )
            print(f"Wrote CEO report to {output.resolve()}")
        else:
            print(generate_ceo_report(store, title=args.title, repo_root=args.repo_root))
        return 0

    raise RuntimeError(f"unhandled command: {args.command}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    store = CompanyStore(args.db)
    try:
        return _handle_command(args, store)
    except CompanyOSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
