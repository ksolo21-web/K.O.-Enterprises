"""Deterministic Markdown reporting for the CEO."""

from __future__ import annotations

import html
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path

from .corporate import CorporateOperations
from .errors import ValidationError
from .policy import ApprovalClass
from .storage import CompanyStore, normalize_owner_decision_packet


def format_money(cents: int, currency: str = "USD") -> str:
    sign = "-" if cents < 0 else ""
    absolute = abs(cents)
    return f"{sign}{currency} {absolute // 100:,}.{absolute % 100:02d}"


def _cell(value: object) -> str:
    # Ledger content may originate in untrusted research.  Escape raw HTML and
    # active Markdown before placing it into reports.
    escaped = html.escape(str(value or "—"), quote=True)
    escaped = escaped.replace("\\", "\\\\")
    for marker in ("`", "*", "_", "[", "]"):
        escaped = escaped.replace(marker, f"\\{marker}")
    return escaped.replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def generate_ceo_report(
    store: CompanyStore,
    *,
    title: str = "K.O. Enterprises CEO Report",
    repo_root: str | Path | None = None,
) -> str:
    """Generate a truth-separated portfolio report entirely from stored state."""

    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    state = store.status(repo_root=repo_root)
    opportunities = store.list_opportunities()
    experiments = store.list_experiments()
    pending_approvals = store.list_approvals(status="pending")
    ceo_approval_requests = [
        approval
        for approval in pending_approvals
        if approval["approval_class"] == ApprovalClass.CEO_APPROVAL_REQUIRED.value
    ]
    complete_approval_packets: list[tuple[dict[str, object], dict[str, str]]] = []
    approvals: list[dict[str, object]] = []
    for approval in ceo_approval_requests:
        try:
            packet, digest = normalize_owner_decision_packet(
                json.loads(str(approval.get("decision_packet_json") or "{}"))
            )
            if not secrets.compare_digest(str(approval.get("packet_digest") or ""), digest):
                raise ValueError("packet digest mismatch")
        except (TypeError, ValueError, json.JSONDecodeError, ValidationError):
            approvals.append(approval)
        else:
            complete_approval_packets.append((approval, packet))
    delegated_approvals = [
        approval
        for approval in pending_approvals
        if approval["approval_class"] != ApprovalClass.CEO_APPROVAL_REQUIRED.value
    ]
    risks = [risk for risk in store.list_risks() if risk["status"] != "closed"]
    decisions = store.list_decisions(limit=10)
    audit_valid, first_bad_audit_id = store.verify_audit_chain()
    operations = CorporateOperations(store)
    operations_state = operations.operations_summary()
    objectives = operations.list_objectives()
    owner_escalations = operations.list_escalations(
        owner_attention=True, status="routed"
    )
    critical_alerts = [
        item for item in owner_escalations if item["decision_class"] == "prohibited"
    ]
    owner_decision_escalations = [
        item for item in owner_escalations if item["decision_class"] != "prohibited"
    ]
    workforce = operations.performance_report()

    lines = [
        f"# {title}",
        "",
        f"Generated: {generated_at}",
        f"Operating state: **{'PAUSED' if state['paused'] else 'ACTIVE'}**",
        f"Audit chain: **{'valid' if audit_valid else f'INVALID at event {first_bad_audit_id}'}**",
        "",
        "## Executive operating view",
        "",
        f"- Active objectives: {operations_state['active_objectives']}",
        f"- Open work: {sum(operations_state['active_work_by_department'].values())}",
        f"- Open incidents: {operations_state['open_incidents']}",
        f"- Owner-attention escalations: {operations_state['owner_attention']}",
        f"- Pending delegated/policy approvals: {len(delegated_approvals)}",
        "",
        "| Objective | Owner | Key results | Priority | Status |",
        "|---|---|---:|---:|---|",
    ]
    if objectives:
        for objective in objectives:
            lines.append(
                f"| {_cell(objective['title'])} | {_cell(objective['owner_role_key'])} | "
                f"{objective['achieved_key_results']}/{objective['key_result_count']} | "
                f"{objective['priority']} | {_cell(objective['status'])} |"
            )
    else:
        lines.append("| No corporate objectives recorded | — | — | — | — |")

    lines.extend(
        [
            "",
            "### Work queue by state",
            "",
        ]
    )
    if operations_state["queue"]:
        lines.append(
            ", ".join(
                f"`{_cell(status)}`: {count}"
                for status, count in sorted(operations_state["queue"].items())
            )
        )
    else:
        lines.append("No work orders are recorded.")
    lines.extend(
        [
            "",
            "### Digital-workforce evidence",
            "",
            f"- Registered workers: {len(workforce)}",
            f"- Workers with sufficient performance sample: {sum(1 for item in workforce if item['performance_state'] != 'insufficient_sample')}",
            "- Performance remains `insufficient_sample` until at least five independently reviewed outcomes exist; activity alone is not success.",
            "",
            "## Financial truth",
            "",
            "All-time ledger totals are shown; recorded transaction-status assertions and projections are deliberately separated. The ledger checks that actual-status entries have unique source references, but it does not independently authenticate those references against a bank or processor.",
            "",
            "| Currency | Recorded realized revenue | Recorded cleared revenue | Recorded refunds | Recorded incurred costs | Recorded paid costs | Recorded net cash contribution | Projected revenue | Estimated/committed costs |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for currency, financials in state["financials"].items():
        lines.append(
            "| "
            + " | ".join(
                [
                    currency,
                    format_money(financials["actual_revenue_cents"], currency),
                    format_money(financials["cleared_revenue_cents"], currency),
                    format_money(financials["refunds_cents"], currency),
                    format_money(financials["incurred_costs_cents"], currency),
                    format_money(financials["paid_costs_cents"], currency),
                    format_money(financials["net_cash_contribution_cents"], currency),
                    format_money(financials["projected_revenue_cents"], currency),
                    format_money(financials["estimated_costs_cents"], currency),
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Opportunity portfolio",
            "",
            "| Rank | Opportunity | Status | Market Void score | Advancement-ready | Gates / evidence gaps | Buyer | Entry wedge |",
            "|---:|---|---|---:|---|---|---|---|",
        ]
    )
    if opportunities:
        for rank, opportunity in enumerate(opportunities, start=1):
            latest = store.latest_score(opportunity["id"])
            score = (
                f"{float(opportunity['latest_score']):.1f}"
                if opportunity["latest_score"] is not None
                else "unscored"
            )
            if latest is None:
                advancement = "unscored"
                gates = "No score or gate evaluation recorded"
            else:
                advancement = "yes" if latest["eligible_for_advancement"] else "no"
                reasons = latest["result"].get("rejection_reasons", [])
                gates = "; ".join(str(reason) for reason in reasons) or "No recorded rejection gate"
            lines.append(
                f"| {rank} | {_cell(opportunity['title'])} | {_cell(opportunity['status'])} | "
                f"{score} | {_cell(advancement)} | {_cell(gates)} | "
                f"{_cell(opportunity['buyer'])} | {_cell(opportunity['entry_wedge'])} |"
            )
    else:
        lines.append("| — | No opportunities recorded | — | — | — | — | — | — |")

    lines.extend(
        [
            "",
            "## Experiments",
            "",
            "| Experiment | Status | Hypothesis | Success metric | Kill metric | Planned cost |",
            "|---|---|---|---|---|---:|",
        ]
    )
    if experiments:
        for experiment in experiments:
            lines.append(
                f"| {_cell(experiment['name'])} | {_cell(experiment['status'])} | "
                f"{_cell(experiment['hypothesis'])} | {_cell(experiment['success_metric'])} | "
                f"{_cell(experiment['kill_metric'])} | "
                f"{format_money(experiment['planned_cost_cents'])} |"
            )
    else:
        lines.append("| No experiments recorded | — | — | — | — | USD 0.00 |")

    lines.extend(["", "## Critical alerts and containment", ""])
    if critical_alerts:
        lines.append(
            "These are non-approvable alerts. The operating chain must contain and remediate them; CEO acknowledgement never authorizes the prohibited action."
        )
        lines.append("")
        for escalation in critical_alerts:
            lines.append(
                f"- **Alert #{escalation['id']} - {_cell(escalation['title'])}:** "
                f"{_cell(escalation['context'])} Containment/default: "
                f"{_cell(escalation['safe_default'])}."
            )
    else:
        lines.append("No prohibited-action or critical-integrity alerts are routed to the CEO.")

    lines.extend(["", "## Held approval records awaiting packet completion", ""])
    if approvals:
        lines.append(
            "These records are held requests, not independently decidable CEO packets and not executable authority. The accountable executive must attach the complete owner packet before requesting a decision."
        )
        lines.append("")
        for approval in approvals:
            lines.append(
                f"- **Held request #{approval['id']} - {_cell(approval['action'])}:** "
                f"{_cell(approval['rationale'])} (maximum cost: "
                f"{format_money(approval['estimated_cost_cents'])}, risk: "
                f"{_cell(approval['risk'])}, reversibility: "
                f"{_cell(approval['reversibility'])}, expires: {_cell(approval['expires_at'])})"
            )
    else:
        lines.append("No incomplete CEO-class approval records are pending.")

    lines.extend(["", "## Owner decisions required", ""])
    if complete_approval_packets or owner_decision_escalations:
        lines.append(
            "These are complete owner-reserved decision packets, not executable authority; an authentic CEO decision must still be recorded before acting. Routine work is deliberately excluded."
        )
        lines.append("")
        for approval, packet in complete_approval_packets:
            lines.append(
                f"- **Approval #{approval['id']} - {_cell(approval['action'])}:** "
                f"{_cell(approval['rationale'])} (maximum cost: "
                f"{format_money(int(approval['estimated_cost_cents']))})."
            )
            for field, label in (
                ("exact_action", "Exact action"),
                ("why_now", "Why now"),
                ("source_evidence", "Source evidence"),
                ("resource_ceiling", "Resource ceiling"),
                ("accounts_data_public_surfaces", "Accounts/data/public surfaces"),
                ("control_findings", "Control findings"),
                ("reversibility", "Reversibility"),
                ("success_threshold", "Success threshold"),
                ("kill_threshold", "Kill threshold"),
                ("monitoring", "Monitoring"),
                ("expiry", "Expiry"),
                ("consequence_of_rejection_or_delay", "Reject/delay consequence"),
            ):
                lines.append(f"  - {label}: {_cell(packet[field])}")
        for escalation in owner_decision_escalations:
            try:
                packet = json.loads(escalation.get("decision_packet_json") or "{}")
            except (TypeError, ValueError, json.JSONDecodeError):
                packet = {}
            lines.append(
                f"- **Escalation #{escalation['id']} - {_cell(escalation['title'])}:** "
                f"{_cell(escalation['context'])} Recommended: {_cell(escalation['recommendation'])}. "
                f"Safe default: {_cell(escalation['safe_default'])}."
            )
            for field, label in (
                ("exact_action", "Exact action"),
                ("why_now", "Why now"),
                ("source_evidence", "Source evidence"),
                ("resource_ceiling", "Resource ceiling"),
                ("accounts_data_public_surfaces", "Accounts/data/public surfaces"),
                ("control_findings", "Control findings"),
                ("reversibility", "Reversibility"),
                ("success_threshold", "Success threshold"),
                ("kill_threshold", "Kill threshold"),
                ("monitoring", "Monitoring"),
                ("expiry", "Expiry"),
                ("consequence_of_rejection_or_delay", "Reject/delay consequence"),
            ):
                lines.append(f"  - {label}: {_cell(packet.get(field, 'MISSING'))}")
    else:
        lines.append("No complete owner decision packets are pending.")

    lines.extend(["", "## Open risks", ""])
    if risks:
        for risk in risks:
            lines.append(
                f"- **{_cell(risk['title'])}** — severity {risk['severity']}/25; "
                f"status `{risk['status']}`. {_cell(risk['mitigation'])}"
            )
    else:
        lines.append("No open risks are recorded. This means none are recorded, not that risk is absent.")

    lines.extend(["", "## Recent decisions", ""])
    if decisions:
        for decision in decisions:
            lines.append(
                f"- **{_cell(decision['title'])}:** {_cell(decision['decision'])} — "
                f"{_cell(decision['rationale'])}"
            )
    else:
        lines.append("No decisions have been recorded.")

    lines.extend(
        [
            "",
            "## Evidence health",
            "",
            f"- Evidence records: {state['counts']['evidence']}",
            f"- Stale evidence records: {state['stale_evidence']}",
            f"- Audit events: {state['counts']['audit_events']}",
            "",
            "## Next operating actions",
            "",
        ]
    )
    next_actions: list[str] = []
    if not complete_approval_packets and not owner_decision_escalations:
        next_actions.append(
            "CEO action: none. The Company President and named departments own all routine actions below."
        )
    if state["paused"]:
        next_actions.append(
            "Company President / Trust & Control: keep external and scheduled work stopped until an exact activation packet is approved and the corresponding bounded runtime is configured."
        )
    if complete_approval_packets or owner_decision_escalations:
        next_actions.append("Resolve the bundled owner-reserved packets; routine work should continue below the CEO.")
    if approvals:
        next_actions.append(
            "Company President: complete or withdraw held CEO-class approval requests before they reach the owner."
        )
    if critical_alerts:
        next_actions.append(
            "President / independent controls: maintain containment and remediate the critical alerts; do not seek approval for a prohibited action."
        )
    if not opportunities:
        next_actions.append(
            "Opportunity Intelligence: record a small set of source-backed market-void candidates."
        )
    elif state["counts"]["evidence"] == 0:
        next_actions.append(
            "Opportunity Intelligence: attach current, timestamped evidence to the highest-priority candidate before selecting it."
        )
    eligible_candidates: list[dict[str, object]] = []
    if opportunities:
        for opportunity in opportunities:
            latest = store.latest_score(opportunity["id"])
            if latest is not None and latest["eligible_for_advancement"]:
                eligible_candidates.append(opportunity)
        if opportunities[0]["latest_score"] is None:
            next_actions.append(
                "Score the top candidate after evidence is recorded; do not advance it on intuition alone."
            )
        elif not eligible_candidates:
            next_actions.append(
                "Resolve the recorded rejection gates or hold/reject the candidates; none is advancement-ready."
            )
        elif not any(experiment["status"] == "active" for experiment in experiments):
            next_actions.append(
                "Define one zero-spend validation experiment for the highest-ranked advancement-ready candidate with explicit success and kill metrics."
            )
    if state["stale_evidence"]:
        next_actions.append("Revalidate or retire stale evidence before the next portfolio decision.")
    if not next_actions:
        next_actions.append("Review the leading experiment's measured result and record an advance, hold, or kill decision.")
    lines.extend(f"{index}. {action}" for index, action in enumerate(next_actions, start=1))
    lines.extend(["", "_Generated from the local company ledger; missing records are never inferred._", ""])
    return "\n".join(lines)


def write_ceo_report(
    store: CompanyStore,
    output_path: str | Path,
    *,
    title: str = "K.O. Enterprises CEO Report",
    repo_root: str | Path | None = None,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(generate_ceo_report(store, title=title, repo_root=repo_root), encoding="utf-8")
    return path
