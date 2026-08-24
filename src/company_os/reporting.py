"""Deterministic Markdown reporting for the CEO."""

from __future__ import annotations

import html
from datetime import datetime, timezone
from pathlib import Path

from .storage import CompanyStore


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
    approvals = store.list_approvals(status="pending")
    risks = [risk for risk in store.list_risks() if risk["status"] != "closed"]
    decisions = store.list_decisions(limit=10)
    audit_valid, first_bad_audit_id = store.verify_audit_chain()

    lines = [
        f"# {title}",
        "",
        f"Generated: {generated_at}",
        f"Operating state: **{'PAUSED' if state['paused'] else 'ACTIVE'}**",
        f"Audit chain: **{'valid' if audit_valid else f'INVALID at event {first_bad_audit_id}'}**",
        "",
        "## Financial truth",
        "",
        "All-time ledger totals are shown; recorded transaction-status assertions and projections are deliberately separated. Phase 0 checks that actual-status entries have unique source references, but it does not independently authenticate those references against a bank or processor.",
        "",
        "| Currency | Recorded realized revenue | Recorded cleared revenue | Recorded refunds | Recorded incurred costs | Recorded paid costs | Recorded net cash contribution | Projected revenue | Estimated/committed costs |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
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

    lines.extend(["", "## Approvals required", ""])
    if approvals:
        lines.append(
            "These are unauthenticated ledger summaries, not executable authority; review the complete approval packet and authentic CEO decision before acting."
        )
        lines.append("")
        for approval in approvals:
            lines.append(
                f"- **#{approval['id']} — {_cell(approval['action'])}:** "
                f"{_cell(approval['rationale'])} "
                f"(class: `{_cell(approval['approval_class'])}`, maximum cost: "
                f"{format_money(approval['estimated_cost_cents'])}, risk: "
                f"{_cell(approval['risk'])}, reversibility: "
                f"{_cell(approval['reversibility'])}, expires: "
                f"{_cell(approval['expires_at'])})"
            )
    else:
        lines.append("No approvals are pending.")

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
    if state["paused"]:
        next_actions.append("Keep all external and scheduled work stopped until the CEO removes the pause intentionally.")
    if approvals:
        next_actions.append("Resolve pending approval packets before attempting their gated actions.")
    if not opportunities:
        next_actions.append("Record a small set of source-backed market-void candidates.")
    elif state["counts"]["evidence"] == 0:
        next_actions.append("Attach current, timestamped evidence to the highest-priority candidate before selecting it.")
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
