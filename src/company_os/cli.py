"""Command-line interface for the local company ledger."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Sequence

from .autonomy import AutonomousCompany
from .corporate import CorporateOperations, DecisionClass
from .errors import CompanyOSError, ValidationError
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


def _parse_json_object(value: str, *, name: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{name} must be valid JSON: {exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise ValidationError(f"{name} must be a JSON object")
    return parsed


def _parse_json_object_list(value: str, *, name: str) -> list[dict[str, Any]]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"{name} must be valid JSON: {exc.msg}") from exc
    if not isinstance(parsed, list) or not all(isinstance(item, dict) for item in parsed):
        raise ValidationError(f"{name} must be a JSON array of objects")
    return parsed


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
    approval_request.add_argument(
        "--decision-packet-json",
        default="{}",
        help="complete owner packet JSON required before CEO-class approval",
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

    corporation = commands.add_parser(
        "corporation", help="bootstrap and inspect the executable corporation"
    )
    corporation_commands = corporation.add_subparsers(
        dest="corporation_command", required=True
    )
    corporation_bootstrap = corporation_commands.add_parser(
        "bootstrap", help="install the version-controlled organization blueprint"
    )
    corporation_bootstrap.add_argument("--json", action="store_true")
    corporation_status = corporation_commands.add_parser(
        "status", help="show organization and operations status"
    )
    corporation_status.add_argument("--json", action="store_true")

    org = commands.add_parser("org", help="inspect the reporting hierarchy")
    org_commands = org.add_subparsers(dest="org_command", required=True)
    org_show = org_commands.add_parser("show", help="show departments, roles, and workers")
    org_show.add_argument("--json", action="store_true")

    objective = commands.add_parser("objective", help="manage commanded objectives")
    objective_commands = objective.add_subparsers(dest="objective_command", required=True)
    objective_add = objective_commands.add_parser("add", help="issue an objective down the chain")
    objective_add.add_argument("--key", required=True, dest="objective_key")
    objective_add.add_argument("--title", required=True)
    objective_add.add_argument("--description", default="")
    objective_add.add_argument("--owner-role", required=True, dest="owner_role_key")
    objective_add.add_argument("--commanded-by", default="company_president")
    objective_add.add_argument("--priority", type=int, default=50)
    objective_add.add_argument("--starts-at")
    objective_add.add_argument("--due-at")
    objective_add.add_argument("--json", action="store_true")
    objective_list = objective_commands.add_parser("list", help="list objectives")
    objective_list.add_argument(
        "--status", choices=["draft", "active", "at_risk", "achieved", "cancelled"]
    )
    objective_list.add_argument("--json", action="store_true")
    objective_show = objective_commands.add_parser(
        "show", help="show one objective and its measurable key results"
    )
    objective_show.add_argument("objective")
    objective_show.add_argument("--json", action="store_true")
    objective_status = objective_commands.add_parser(
        "status", help="change an objective after an authorized evidence review"
    )
    objective_status.add_argument("objective")
    objective_status.add_argument(
        "--status", required=True, choices=["active", "at_risk", "achieved", "cancelled"]
    )
    objective_status.add_argument("--rationale", required=True)
    objective_status.add_argument("--actor", default="company_president")
    objective_status.add_argument("--json", action="store_true")
    key_result_add = objective_commands.add_parser(
        "key-result-add", help="add a measurable result to an objective"
    )
    key_result_add.add_argument("objective")
    key_result_add.add_argument("--key", required=True, dest="result_key")
    key_result_add.add_argument("--description", required=True)
    key_result_add.add_argument("--metric", required=True, dest="metric_name")
    key_result_add.add_argument("--baseline", required=True, type=float)
    key_result_add.add_argument("--target", required=True, type=float)
    key_result_add.add_argument("--unit", required=True)
    key_result_add.add_argument("--actor", default="company_president")
    key_result_add.add_argument("--json", action="store_true")
    key_result_update = objective_commands.add_parser(
        "key-result-update", help="record evidence-backed key-result progress"
    )
    key_result_update.add_argument("key_result_id", type=int)
    key_result_update.add_argument("--value", required=True, type=float)
    key_result_update.add_argument("--evidence", required=True)
    key_result_update.add_argument(
        "--status", choices=["active", "at_risk", "achieved", "cancelled"]
    )
    key_result_update.add_argument("--actor", default="company_president")
    key_result_update.add_argument("--json", action="store_true")

    work = commands.add_parser("work", help="manage the durable departmental work queue")
    work_commands = work.add_subparsers(dest="work_command", required=True)
    work_add = work_commands.add_parser("add", help="issue a work order")
    work_add.add_argument("--key", required=True, dest="work_key")
    work_add.add_argument("--commanded-by", default="company_president")
    work_add.add_argument("--assigned-role", required=True)
    work_add.add_argument("--assigned-worker")
    work_add.add_argument("--reviewer-role", required=True)
    work_add.add_argument("--task-type", required=True)
    work_add.add_argument("--title", required=True)
    work_add.add_argument("--description", required=True)
    work_add.add_argument("--acceptance-criteria", required=True)
    work_add.add_argument(
        "--decision-class",
        choices=[item.value for item in DecisionClass],
        default=DecisionClass.WORK_EXECUTION.value,
    )
    work_add.add_argument("--priority", type=int, default=50)
    work_add.add_argument("--risk-level", choices=["low", "medium", "high", "critical"], default="low")
    work_add.add_argument("--external-effect", action="store_true")
    work_add.add_argument("--estimated-cost-cents", type=int, default=0)
    work_add.add_argument("--objective-id", type=int, required=True)
    work_add.add_argument("--opportunity-id", type=int)
    work_add.add_argument("--cycle-id", type=int)
    work_add.add_argument("--dependency", type=int, action="append", default=[])
    work_add.add_argument("--max-attempts", type=int, default=3)
    work_add.add_argument("--input-json", default="{}")
    work_add.add_argument("--json", action="store_true")
    work_list = work_commands.add_parser("list", help="list queued and completed work")
    work_list.add_argument("--status")
    work_list.add_argument("--department")
    work_list.add_argument("--cycle-id", type=int)
    work_list.add_argument("--limit", type=int, default=100)
    work_list.add_argument("--json", action="store_true")
    work_show = work_commands.add_parser("show", help="show one work order")
    work_show.add_argument("work")
    work_show.add_argument("--json", action="store_true")
    work_authorize = work_commands.add_parser(
        "authorize", help="bind an exact CEO approval to held internal work"
    )
    work_authorize.add_argument("work")
    work_authorize.add_argument("--approval-id", required=True, type=int)
    work_authorize.add_argument("--actor", default="company_president")
    work_authorize.add_argument("--json", action="store_true")
    work_claim = work_commands.add_parser("claim", help="atomically lease the next eligible task")
    work_claim.add_argument("--worker", required=True)
    work_claim.add_argument("--lease-seconds", type=int, default=900)
    work_claim.add_argument("--json", action="store_true")
    work_start = work_commands.add_parser("start", help="start leased work")
    work_start.add_argument("work")
    work_start.add_argument("--worker", required=True)
    work_start.add_argument("--lease-token", required=True)
    work_start.add_argument("--lease-epoch", required=True, type=int)
    work_start.add_argument("--json", action="store_true")
    work_submit = work_commands.add_parser("submit", help="submit work for independent review")
    work_submit.add_argument("work")
    work_submit.add_argument("--worker", required=True)
    work_submit.add_argument("--lease-token", required=True)
    work_submit.add_argument("--lease-epoch", required=True, type=int)
    work_submit.add_argument("--result-json", required=True)
    work_submit.add_argument("--json", action="store_true")
    work_review = work_commands.add_parser("review", help="accept or reject submitted work")
    work_review.add_argument("work")
    work_review.add_argument("--reviewer", required=True)
    work_review.add_argument("--decision", required=True, choices=["accept", "reject"])
    work_review.add_argument("--notes", required=True)
    work_review.add_argument("--quality-score", type=float)
    work_review.add_argument("--json", action="store_true")

    cycle = commands.add_parser("cycle", help="run one bounded autonomous operating cycle")
    cycle_commands = cycle.add_subparsers(dest="cycle_command", required=True)
    cycle_run = cycle_commands.add_parser("run", help="plan and execute one safe internal cycle")
    cycle_run.add_argument(
        "--mode", choices=["simulation", "internal", "shadow", "external"], default="internal"
    )
    cycle_run.add_argument("--triggered-by", default="company_president")
    cycle_run.add_argument("--scheduled", action="store_true")
    cycle_run.add_argument("--max-work-items", type=int, default=20)
    cycle_run.add_argument(
        "--approval-id",
        type=int,
        help="matching unexpired approval required for a scheduled cycle",
    )
    cycle_run.add_argument("--json", action="store_true")
    cycle_dispatch = cycle_commands.add_parser("dispatch", help="show ready work grouped by department")
    cycle_dispatch.add_argument("--cycle-id", type=int)
    cycle_dispatch.add_argument("--json", action="store_true")

    escalation = commands.add_parser("escalation", help="inspect executive exceptions")
    escalation_commands = escalation.add_subparsers(dest="escalation_command", required=True)
    escalation_add = escalation_commands.add_parser(
        "add", help="route a management exception or complete owner packet"
    )
    escalation_add.add_argument("--raised-by", required=True)
    escalation_add.add_argument("--routed-to", required=True)
    escalation_add.add_argument(
        "--decision-class",
        required=True,
        choices=[
            item.value
            for item in DecisionClass
            if item is not DecisionClass.WORK_EXECUTION
        ],
    )
    escalation_add.add_argument("--reason-code", required=True)
    escalation_add.add_argument("--title", required=True)
    escalation_add.add_argument("--context", required=True)
    escalation_add.add_argument("--recommendation", required=True)
    escalation_add.add_argument("--safe-default", required=True)
    escalation_add.add_argument("--work-id", type=int)
    escalation_add.add_argument("--options-json", default="[]")
    escalation_add.add_argument("--owner-packet-json", default="{}")
    escalation_add.add_argument("--due-at")
    escalation_add.add_argument("--json", action="store_true")
    escalation_list = escalation_commands.add_parser("list", help="list routed escalations")
    escalation_list.add_argument("--owner-only", action="store_true")
    escalation_list.add_argument("--status")
    escalation_list.add_argument("--json", action="store_true")
    escalation_resolve = escalation_commands.add_parser(
        "resolve", help="close an escalation through its routed decision role"
    )
    escalation_resolve.add_argument("escalation_id", type=int)
    escalation_resolve.add_argument("--actor", required=True)
    escalation_resolve.add_argument(
        "--decision", required=True, choices=["resolved", "dismissed"]
    )
    escalation_resolve.add_argument("--resolution", required=True)
    escalation_resolve.add_argument("--json", action="store_true")

    performance = commands.add_parser("performance", help="inspect digital-worker outcomes")
    performance_commands = performance.add_subparsers(dest="performance_command", required=True)
    performance_report = performance_commands.add_parser(
        "report", help="derive provisional workforce throughput inputs"
    )
    performance_report.add_argument("--json", action="store_true")

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
    print(
        f"Corporation: {state['counts']['departments']} departments | "
        f"{state['counts']['workers']} workers | "
        f"{state['counts']['objectives']} objectives | "
        f"{state['counts']['work_items']} work items | "
        f"{state['counts']['incidents']} incidents"
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
            f"[{_terminal_text(row['status'])}] score={score} - "
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
            f"cost_limit={row['estimated_cost_cents']}c - "
            f"{_terminal_text(row['action'])}"
        )


def _handle_command(args: argparse.Namespace, store: CompanyStore) -> int:
    operations = CorporateOperations(store)

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
                decision_packet=_parse_json_object(
                    args.decision_packet_json, name="decision_packet_json"
                ),
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

    if args.command == "corporation":
        if args.corporation_command == "bootstrap":
            result = operations.bootstrap_organization(actor=args.actor)
            if args.json:
                _json_dump(result)
            else:
                print(
                    "Bootstrapped executable corporation: "
                    f"{result['departments']} departments, {result['roles']} roles, "
                    f"{result['workers']} workers."
                )
            return 0
        organization = operations.organization_snapshot()
        result = {
            "organization": {
                "departments": len(organization["departments"]),
                "roles": len(organization["roles"]),
                "workers": len(organization["workers"]),
            },
            "operations": operations.operations_summary(),
            "paused": store.status(repo_root=args.repo_root)["paused"],
        }
        if args.json:
            _json_dump(result)
        else:
            print(
                f"Corporation: {result['organization']['departments']} departments | "
                f"{result['organization']['roles']} roles | "
                f"{result['organization']['workers']} workers | "
                f"external autonomy={'PAUSED' if result['paused'] else 'ACTIVE'}"
            )
            print(
                f"Active objectives: {result['operations']['active_objectives']} | "
                f"Owner-attention items: {result['operations']['owner_attention']} | "
                f"Open incidents: {result['operations']['open_incidents']}"
            )
        return 0

    if args.command == "org":
        snapshot = operations.organization_snapshot()
        if args.json:
            _json_dump(snapshot)
        else:
            workers_by_role = {row["role_key"]: row for row in snapshot["workers"]}
            children: dict[str | None, list[dict[str, Any]]] = {}
            for role in snapshot["roles"]:
                children.setdefault(role["reports_to_role_key"], []).append(role)
            print("K.O. Enterprises reporting hierarchy")

            def print_branch(parent: str | None, depth: int) -> None:
                for role in sorted(
                    children.get(parent, []), key=lambda row: str(row["role_key"])
                ):
                    worker = workers_by_role.get(role["role_key"])
                    occupant = worker["display_name"] if worker else "unfilled"
                    control = (
                        " [INDEPENDENT CONTROL / STOP RIGHT]"
                        if role["independent_control"]
                        else ""
                    )
                    print(
                        f"{'  ' * depth}- {role['role_key']}: "
                        f"{_terminal_text(role['title'])} - "
                        f"{_terminal_text(occupant)}{control}"
                    )
                    print_branch(role["role_key"], depth + 1)

            print_branch(None, 0)
        return 0

    if args.command == "objective":
        if args.objective_command == "add":
            row = operations.create_objective(
                objective_key=args.objective_key,
                title=args.title,
                description=args.description,
                owner_role_key=args.owner_role_key,
                commanded_by_worker=args.commanded_by,
                priority=args.priority,
                starts_at=args.starts_at,
                due_at=args.due_at,
            )
            if args.json:
                _json_dump(row)
            else:
                print(f"Issued objective #{row['id']} ({row['objective_key']}).")
            return 0
        if args.objective_command == "status":
            row = operations.set_objective_status(
                args.objective,
                status=args.status,
                rationale=args.rationale,
                actor_worker=args.actor,
            )
            _json_dump(row) if args.json else print(
                f"Objective #{row['id']} is now {row['status']}."
            )
            return 0
        if args.objective_command == "show":
            row = operations.get_objective(args.objective)
            _json_dump(row) if args.json else print(
                json.dumps(row, indent=2, sort_keys=True, default=str)
            )
            return 0
        if args.objective_command == "key-result-add":
            row = operations.create_key_result(
                args.objective,
                result_key=args.result_key,
                description=args.description,
                metric_name=args.metric_name,
                baseline=args.baseline,
                target=args.target,
                unit=args.unit,
                actor_worker=args.actor,
            )
            _json_dump(row) if args.json else print(
                f"Added key result #{row['id']} to objective #{row['objective_id']}."
            )
            return 0
        if args.objective_command == "key-result-update":
            row = operations.update_key_result(
                args.key_result_id,
                current_value=args.value,
                evidence_reference=args.evidence,
                actor_worker=args.actor,
                status=args.status,
            )
            _json_dump(row) if args.json else print(
                f"Key result #{row['id']} is {row['status']} at {row['current_value']} {row['unit']}."
            )
            return 0
        rows = operations.list_objectives(status=args.status)
        if args.json:
            _json_dump(rows)
        elif not rows:
            print("No objectives recorded.")
        else:
            for row in rows:
                print(
                    f"#{row['id']} [{row['status']}] priority={row['priority']} "
                    f"owner={row['owner_role_key']} - {_terminal_text(row['title'])}"
                )
        return 0

    if args.command == "work":
        if args.work_command == "add":
            row = operations.create_work(
                work_key=args.work_key,
                commanded_by_worker=args.commanded_by,
                assigned_role_key=args.assigned_role,
                assigned_worker_key=args.assigned_worker,
                reviewer_role_key=args.reviewer_role,
                task_type=args.task_type,
                title=args.title,
                description=args.description,
                acceptance_criteria=args.acceptance_criteria,
                decision_class=args.decision_class,
                priority=args.priority,
                risk_level=args.risk_level,
                external_effect=args.external_effect,
                estimated_cost_cents=args.estimated_cost_cents,
                objective_id=args.objective_id,
                opportunity_id=args.opportunity_id,
                cycle_id=args.cycle_id,
                dependencies=tuple(args.dependency),
                input_data=_parse_json_object(args.input_json, name="input_json"),
                max_attempts=args.max_attempts,
            )
            if args.json:
                _json_dump(row)
            else:
                print(
                    f"Issued work #{row['id']} [{row['status']}] to "
                    f"{row['assigned_role_key']}."
                )
            return 0
        if args.work_command == "list":
            rows = operations.list_work(
                status=args.status,
                department=args.department,
                cycle_id=args.cycle_id,
                limit=args.limit,
            )
            if args.json:
                _json_dump(rows)
            elif not rows:
                print("No work items recorded.")
            else:
                for row in rows:
                    print(
                        f"#{row['id']} [{row['status']}] p{row['priority']} "
                        f"{row['assigned_role_key']} - {_terminal_text(row['title'])}"
                    )
            return 0
        if args.work_command == "show":
            row = operations.get_work(args.work)
            _json_dump(row) if args.json else print(
                json.dumps(row, indent=2, sort_keys=True, default=str)
            )
            return 0
        if args.work_command == "authorize":
            row = operations.authorize_internal_work(
                args.work,
                approval_id=args.approval_id,
                actor_worker=args.actor,
            )
            _json_dump(row) if args.json else print(
                f"Authorized internal work #{row['id']} into {row['status']}."
            )
            return 0
        if args.work_command == "claim":
            row = operations.claim_work(
                worker_key=args.worker, lease_seconds=args.lease_seconds
            )
            if args.json:
                _json_dump(row)
            elif row is None:
                print("No eligible work is ready for this worker.")
            else:
                print(
                    f"Leased work #{row['id']} epoch={row['lease_epoch']} "
                    f"until {row['lease_expires_at']}."
                )
            return 0
        if args.work_command == "start":
            row = operations.start_work(
                args.work,
                worker_key=args.worker,
                lease_token=args.lease_token,
                lease_epoch=args.lease_epoch,
            )
            _json_dump(row) if args.json else print(f"Started work #{row['id']}.")
            return 0
        if args.work_command == "submit":
            row = operations.submit_work(
                args.work,
                worker_key=args.worker,
                lease_token=args.lease_token,
                lease_epoch=args.lease_epoch,
                result=_parse_json_object(args.result_json, name="result_json"),
            )
            _json_dump(row) if args.json else print(
                f"Submitted work #{row['id']} for {row['reviewer_role_key']} review."
            )
            return 0
        row = operations.review_work(
            args.work,
            reviewer_worker_key=args.reviewer,
            decision=args.decision,
            notes=args.notes,
            quality_score=args.quality_score,
        )
        _json_dump(row) if args.json else print(
            f"Review recorded; work #{row['id']} is {row['status']}."
        )
        return 0

    if args.command == "cycle":
        company = AutonomousCompany(operations, repo_root=args.repo_root)
        if args.cycle_command == "run":
            result = company.run_cycle(
                triggered_by_worker=args.triggered_by,
                mode=args.mode,
                scheduled=args.scheduled,
                max_work_items=args.max_work_items,
                approval_id=args.approval_id,
            )
            if args.json:
                _json_dump(result)
            else:
                summary = result["summary"]
                print(
                    f"Cycle #{result['cycle']['id']} is {result['cycle']['status']}: "
                    f"planned={summary['planned_work_items']} "
                    f"ready={summary['dispatchable_work_items']} "
                    f"owner_attention={summary['owner_attention_items']} "
                    f"external_effects={summary['external_effects_executed']}."
                )
            return 0
        manifest = company.dispatch_manifest(cycle_id=args.cycle_id)
        if args.json:
            _json_dump(manifest)
        else:
            print(f"Dispatchable work: {manifest['dispatchable_count']}")
            for department, rows in manifest["departments"].items():
                print(f"{department}:")
                for row in rows:
                    print(
                        f"  #{row['work_id']} {row['codex_agent']} p{row['priority']} - "
                        f"{_terminal_text(row['title'])}"
                    )
        return 0

    if args.command == "escalation":
        if args.escalation_command == "add":
            row = operations.create_escalation(
                raised_by_worker=args.raised_by,
                routed_to_role_key=args.routed_to,
                decision_class=args.decision_class,
                reason_code=args.reason_code,
                title=args.title,
                context=args.context,
                recommendation=args.recommendation,
                safe_default=args.safe_default,
                work_id=args.work_id,
                options=_parse_json_object_list(
                    args.options_json, name="options_json"
                ),
                owner_packet=_parse_json_object(
                    args.owner_packet_json, name="owner_packet_json"
                ),
                due_at=args.due_at,
            )
            _json_dump(row) if args.json else print(
                f"Escalation #{row['id']} routed to {row['routed_to_role_key']}."
            )
            return 0
        if args.escalation_command == "resolve":
            row = operations.resolve_escalation(
                args.escalation_id,
                actor_worker=args.actor,
                decision=args.decision,
                resolution=args.resolution,
            )
            _json_dump(row) if args.json else print(
                f"Escalation #{row['id']} is {row['status']}."
            )
            return 0
        rows = operations.list_escalations(
            owner_attention=True if args.owner_only else None,
            status=args.status,
        )
        if args.json:
            _json_dump(rows)
        elif not rows:
            print("No matching escalations.")
        else:
            for row in rows:
                print(
                    f"#{row['id']} [{row['decision_class']}] -> {row['routed_to_role_key']} "
                    f"- {_terminal_text(row['title'])}"
                )
        return 0

    if args.command == "performance":
        rows = operations.performance_report()
        if args.json:
            _json_dump(rows)
        else:
            for row in rows:
                print(
                    f"{row['worker_key']} [{row['performance_state']}] "
                    f"sample={row['sample_size']} accepted={row['accepted_work']} "
                    f"failed={row['failed_work']} rejected={row['rejected_reviews']}"
                )
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
