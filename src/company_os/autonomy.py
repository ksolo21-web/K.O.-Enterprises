"""Bounded autonomous operating-cycle planner for K.O. Enterprises.

The engine performs deterministic, zero-spend internal coordination.  It can
create objectives and work, recover safe internal state, execute integrity
checks, and prepare department dispatches.  It cannot invoke model providers,
contact customers, publish, deploy, move money, or remove the emergency pause.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .corporate import CorporateOperations, DecisionClass
from .errors import ConflictError
from .policy import ActionRequest, enforce_action


ROLE_TO_CODEX_AGENT: dict[str, str] = {
    "company_president": "president",
    "chief_of_staff": "president",
    "strategy_portfolio_chief": "portfolio_lead",
    "opportunity_intelligence_lead": "opportunity_intelligence",
    "market_researcher": "opportunity_intelligence",
    "market_structure_analyst": "opportunity_intelligence",
    "validation_lead": "validation_red_team",
    "counter_thesis_analyst": "validation_red_team",
    "product_technology_chief": "product_engineer",
    "product_manager": "product_engineer",
    "software_architect": "product_engineer",
    "software_engineer": "product_engineer",
    "qa_reliability_lead": "quality_reliability",
    "revenue_chief": "commercial_operator",
    "growth_strategist": "commercial_operator",
    "content_operator": "commercial_operator",
    "sales_partnerships_lead": "commercial_operator",
    "customer_success_lead": "commercial_operator",
    "finance_controller": "finance_controller",
    "risk_legal_chief": "trust_officer",
    "legal_compliance_officer": "trust_officer",
    "security_privacy_officer": "trust_officer",
    "people_agent_ops_chief": "internal_auditor",
    "operations_analytics_chief": "president",
    "data_analyst": "internal_auditor",
    "sre_operator": "quality_reliability",
    "internal_auditor": "internal_auditor",
}


class AutonomousCompany:
    """Create and reconcile one finite company operating cycle."""

    def __init__(self, operations: CorporateOperations, *, repo_root: str) -> None:
        self.operations = operations
        self.repo_root = repo_root

    def _ensure_objectives(self) -> dict[str, dict[str, Any]]:
        desired = (
            {
                "objective_key": "company.validate-first-demand",
                "title": "Validate one urgent, reachable, lawful customer problem",
                "description": (
                    "Build current evidence, falsify weak theses quickly, and present only "
                    "a decision-grade validation recommendation."
                ),
                "owner_role_key": "strategy_portfolio_chief",
                "priority": 95,
                "key_results": (
                    {
                        "result_key": "decision-grade-validation",
                        "description": "Produce one independently reviewed validation recommendation backed by current evidence.",
                        "metric_name": "accepted_validation_recommendations",
                        "baseline": 0,
                        "target": 1,
                        "unit": "recommendations",
                    },
                ),
            },
            {
                "objective_key": "company.zero-constitutional-breaches",
                "title": "Operate with zero constitutional or evidence-integrity breaches",
                "description": (
                    "Keep all activity truthful, auditable, within delegated authority, "
                    "and externally paused until exact authorization exists."
                ),
                "owner_role_key": "risk_legal_chief",
                "priority": 100,
                "key_results": (
                    {
                        "result_key": "verified-control-posture",
                        "description": "Complete one independently accepted operating-ledger and audit-chain integrity check.",
                        "metric_name": "verified_integrity_cycles",
                        "baseline": 0,
                        "target": 1,
                        "unit": "cycles",
                    },
                ),
            },
            {
                "objective_key": "company.owner-leverage",
                "title": "Reduce routine owner involvement to executive exceptions",
                "description": (
                    "Resolve ordinary work through the chain of command and bundle only "
                    "owner-reserved decisions into concise packets."
                ),
                "owner_role_key": "chief_of_staff",
                "priority": 90,
                "key_results": (
                    {
                        "result_key": "routine-owner-interventions",
                        "description": "Complete one operating cycle without asking the owner to perform routine work.",
                        "metric_name": "cycles_without_routine_owner_intervention",
                        "baseline": 0,
                        "target": 1,
                        "unit": "cycles",
                    },
                ),
            },
        )
        objectives: dict[str, dict[str, Any]] = {}
        existing = self.operations.list_objectives()
        for definition in desired:
            base_key = definition["objective_key"]
            lineage = [
                row
                for row in existing
                if row["objective_key"] == base_key
                or row["objective_key"].startswith(f"{base_key}.v")
            ]
            active = [row for row in lineage if row["status"] in {"active", "at_risk"}]
            if active:
                objective = max(active, key=lambda row: int(row["id"]))
            else:
                latest = max(lineage, key=lambda row: int(row["id"])) if lineage else None
                if latest is not None and latest["status"] == "cancelled":
                    raise ConflictError(
                        f"standing objective {base_key} is cancelled; an explicit new mandate is required"
                    )
                versions = [1]
                for row in lineage:
                    suffix = row["objective_key"].removeprefix(f"{base_key}.v")
                    if suffix.isdigit():
                        versions.append(int(suffix))
                objective_key = base_key if not lineage else f"{base_key}.v{max(versions) + 1}"
                objective = self.operations.create_objective(
                    objective_key=objective_key,
                    title=definition["title"],
                    description=definition["description"],
                    owner_role_key=definition["owner_role_key"],
                    priority=definition["priority"],
                    commanded_by_worker="company_president",
                )
                existing.append(objective)
            objective_detail = self.operations.get_objective(objective["id"])
            existing_results = {
                result["result_key"] for result in objective_detail["key_results"]
            }
            for result in definition["key_results"]:
                if result["result_key"] not in existing_results:
                    self.operations.create_key_result(
                        objective["id"],
                        **result,
                        actor_worker="company_president",
                    )
            objectives[base_key] = self.operations.get_objective(objective["id"])
        return objectives

    def _record_key_result_evidence(
        self,
        objective: Mapping[str, Any],
        *,
        result_key: str,
        current_value: float,
        evidence_reference: str,
    ) -> None:
        detail = self.operations.get_objective(int(objective["id"]))
        result = next(
            (
                item
                for item in detail["key_results"]
                if item["result_key"] == result_key
                and item["status"] in {"active", "at_risk"}
            ),
            None,
        )
        if result is not None:
            self.operations.update_key_result(
                int(result["id"]),
                current_value=current_value,
                evidence_reference=evidence_reference,
                actor_worker="company_president",
            )

    @staticmethod
    def _work_spec(
        *,
        work_key: str,
        role: str,
        reviewer: str,
        task_type: str,
        title: str,
        description: str,
        acceptance: str,
        priority: int,
        objective_id: int,
        cycle_id: int,
        opportunity_id: int | None = None,
        dependencies: Sequence[int] = (),
        input_data: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "work_key": work_key,
            "commanded_by_worker": "company_president",
            "assigned_role_key": role,
            "reviewer_role_key": reviewer,
            "task_type": task_type,
            "title": title,
            "description": description,
            "acceptance_criteria": acceptance,
            "decision_class": DecisionClass.WORK_EXECUTION,
            "priority": priority,
            "risk_level": "low",
            "external_effect": False,
            "estimated_cost_cents": 0,
            "objective_id": objective_id,
            "cycle_id": cycle_id,
            "opportunity_id": opportunity_id,
            "dependencies": dependencies,
            "input_data": input_data,
        }

    def _plan_discovery_work(
        self, cycle_id: int, objective_id: int, period_key: str, *, limit: int
    ) -> list[dict[str, Any]]:
        created: list[dict[str, Any]] = []

        if limit <= 0:
            return created

        market = self.operations.create_work(
            **self._work_spec(
                work_key=f"{period_key}.market-signals",
                role="market_researcher",
                reviewer="opportunity_intelligence_lead",
                task_type="market_signal_scan",
                title="Find evidence-backed urgent buyer problems",
                description=(
                    "Search lawful current public sources for recurring, costly, specific "
                    "workarounds. Record sources, observation dates, buyer, budget holder, "
                    "cost of inaction, reachability, and evidence expiry."
                ),
                acceptance=(
                    "At least three specific candidate dossiers; every material claim has "
                    "source URI, observation date, evidence type, confidence, and expiry; "
                    "no generic idea-list entries or fabricated demand."
                ),
                priority=90,
                objective_id=objective_id,
                cycle_id=cycle_id,
            )
        )
        created.append(market)
        if len(created) >= limit:
            return created
        structure = self.operations.create_work(
            **self._work_spec(
                work_key=f"{period_key}.market-structure",
                role="market_structure_analyst",
                reviewer="opportunity_intelligence_lead",
                task_type="market_structure_scan",
                title="Map high-need, weak-supply market structures",
                description=(
                    "Independently map incumbent concentration, pricing, lock-in, switching "
                    "friction, neglected segments, substitutes, and why a gap may persist."
                ),
                acceptance=(
                    "A sourced supply map that distinguishes genuine unmet demand from a "
                    "market with no viable demand and names lawful entry wedges."
                ),
                priority=88,
                objective_id=objective_id,
                cycle_id=cycle_id,
            )
        )
        created.append(structure)
        if len(created) >= limit:
            return created
        shortlist = self.operations.create_work(
            **self._work_spec(
                work_key=f"{period_key}.candidate-shortlist",
                role="opportunity_intelligence_lead",
                reviewer="company_president",
                task_type="opportunity_shortlist",
                title="Reconcile signals into the smallest credible shortlist",
                description=(
                    "Compare the independent demand and market-structure work. Create or "
                    "update only candidates supported by current traceable evidence."
                ),
                acceptance=(
                    "No more than three shortlisted candidates; each includes user, buyer, "
                    "workaround, urgency, reachable channel, smallest wedge, counter-signals, "
                    "kill criteria, and explicit unknowns."
                ),
                priority=85,
                objective_id=objective_id,
                cycle_id=cycle_id,
                dependencies=(market["id"], structure["id"]),
            )
        )
        created.append(shortlist)
        if len(created) >= limit:
            return created
        counter = self.operations.create_work(
            **self._work_spec(
                work_key=f"{period_key}.independent-falsification",
                role="counter_thesis_analyst",
                reviewer="strategy_portfolio_chief",
                task_type="counter_thesis",
                title="Try to disprove the shortlisted opportunity theses",
                description=(
                    "Independently identify false urgency, unreachable buyers, weak economics, "
                    "crowded supply, regulatory risk, incumbent response, and maintenance traps."
                ),
                acceptance=(
                    "A falsifiable counter-thesis for each candidate with disconfirming evidence, "
                    "unknowns, cheapest decisive test, and stop recommendation where warranted."
                ),
                priority=83,
                objective_id=objective_id,
                cycle_id=cycle_id,
                dependencies=(shortlist["id"],),
            )
        )
        created.append(counter)
        if len(created) >= limit:
            return created
        finance = self.operations.create_work(
            **self._work_spec(
                work_key=f"{period_key}.finance-feasibility",
                role="finance_controller",
                reviewer="internal_auditor",
                task_type="finance_feasibility",
                title="Evaluate zero-cash feasibility and unit-economics assumptions",
                description=(
                    "Review the shortlist without moving money. Separate actuals, assumptions, "
                    "estimates, and forecasts; identify any future owner-reserved cash decision."
                ),
                acceptance=(
                    "Per-candidate cost envelope, pricing hypothesis, break-even drivers, downside, "
                    "and explicit statement that no financial figure is externally verified unless sourced."
                ),
                priority=80,
                objective_id=objective_id,
                cycle_id=cycle_id,
                dependencies=(shortlist["id"],),
            )
        )
        created.append(finance)
        if len(created) >= limit:
            return created
        legal = self.operations.create_work(
            **self._work_spec(
                work_key=f"{period_key}.legal-risk-screen",
                role="legal_compliance_officer",
                reviewer="risk_legal_chief",
                task_type="legal_risk_screen",
                title="Screen candidate categories and evidence collection boundaries",
                description=(
                    "Identify terms, privacy, IP, claims, data, licensing, regulated-category, "
                    "and reputation risks. This is an internal control checklist, not legal advice."
                ),
                acceptance=(
                    "Pass/revise/block recommendation per candidate, exact unresolved questions, "
                    "safest internal next action, and any matter requiring qualified review."
                ),
                priority=82,
                objective_id=objective_id,
                cycle_id=cycle_id,
                dependencies=(shortlist["id"],),
            )
        )
        created.append(legal)
        if len(created) >= limit:
            return created
        memo = self.operations.create_work(
            **self._work_spec(
                work_key=f"{period_key}.executive-opportunity-memo",
                role="strategy_portfolio_chief",
                reviewer="company_president",
                task_type="portfolio_recommendation",
                title="Prepare the company-level opportunity recommendation",
                description=(
                    "Synthesize accepted evidence, counter-thesis, finance, and risk work into a "
                    "ranked portfolio decision. Prefer the cheapest test that can disprove demand."
                ),
                acceptance=(
                    "One recommended internal next step, alternatives, evidence quality, resource "
                    "allocation, success/kill thresholds, residual risks, and owner ask only if reserved."
                ),
                priority=78,
                objective_id=objective_id,
                cycle_id=cycle_id,
                dependencies=(counter["id"], finance["id"], legal["id"]),
            )
        )
        created.append(memo)
        return created

    def _plan_opportunity_work(
        self,
        cycle_id: int,
        objective_id: int,
        period_key: str,
        opportunities: Sequence[Mapping[str, Any]],
        *,
        limit: int,
    ) -> list[dict[str, Any]]:
        created: list[dict[str, Any]] = []
        for opportunity in opportunities[:3]:
            if len(created) >= limit:
                break
            opportunity_id = int(opportunity["id"])
            prefix = f"{period_key}.opportunity-{opportunity_id}"
            dossier = self.operations.create_work(
                **self._work_spec(
                    work_key=f"{prefix}.evidence-refresh",
                    role="market_researcher",
                    reviewer="opportunity_intelligence_lead",
                    task_type="evidence_refresh",
                    title=f"Refresh evidence for {opportunity['title']}",
                    description=(
                        "Revalidate the buyer problem, budget holder, workaround, urgency, "
                        "cost of inaction, reachable channel, and competing alternatives."
                    ),
                    acceptance=(
                        "All claims are current and traceable; contrary evidence and missing "
                        "information are explicit; stale evidence is not treated as support."
                    ),
                    priority=90,
                    objective_id=objective_id,
                    cycle_id=cycle_id,
                    opportunity_id=opportunity_id,
                    input_data={"opportunity": dict(opportunity)},
                )
            )
            created.append(dossier)
            # A complete review lane needs the counter-thesis, control screen,
            # and validation-plan tasks together.  If this cycle's bounded
            # capacity cannot hold that lane, leave the dossier as the useful
            # independent unit and continue next cycle.
            if limit - len(created) < 3:
                continue
            counter = self.operations.create_work(
                **self._work_spec(
                    work_key=f"{prefix}.counter-thesis",
                    role="counter_thesis_analyst",
                    reviewer="strategy_portfolio_chief",
                    task_type="counter_thesis",
                    title=f"Falsify the thesis for {opportunity['title']}",
                    description="Find the strongest evidence that the opportunity should be rejected or held.",
                    acceptance=(
                        "Independent counter-thesis, failure modes, decisive evidence gaps, "
                        "and cheapest ethical test with frozen success and kill thresholds."
                    ),
                    priority=88,
                    objective_id=objective_id,
                    cycle_id=cycle_id,
                    opportunity_id=opportunity_id,
                    dependencies=(dossier["id"],),
                )
            )
            created.append(counter)
            risk = self.operations.create_work(
                **self._work_spec(
                    work_key=f"{prefix}.control-screen",
                    role="legal_compliance_officer",
                    reviewer="risk_legal_chief",
                    task_type="opportunity_control_screen",
                    title=f"Control screen for {opportunity['title']}",
                    description="Screen legal, privacy, security, IP, claims, and regulated-category exposure.",
                    acceptance="Pass/revise/block result, evidence, expiry, and precise remediation path.",
                    priority=86,
                    objective_id=objective_id,
                    cycle_id=cycle_id,
                    opportunity_id=opportunity_id,
                    dependencies=(dossier["id"],),
                )
            )
            created.append(risk)
            validation = self.operations.create_work(
                **self._work_spec(
                    work_key=f"{prefix}.validation-plan",
                    role="validation_lead",
                    reviewer="strategy_portfolio_chief",
                    task_type="validation_plan",
                    title=f"Design the smallest decisive test for {opportunity['title']}",
                    description=(
                        "Design a reversible, ethical, zero-cash internal or draft validation plan. "
                        "Do not contact users or publish without a separate exact approval."
                    ),
                    acceptance=(
                        "Frozen hypothesis, audience, method, success threshold, kill threshold, "
                        "timebox, measurement plan, risks, and exact gated action if later needed."
                    ),
                    priority=82,
                    objective_id=objective_id,
                    cycle_id=cycle_id,
                    opportunity_id=opportunity_id,
                    dependencies=(counter["id"], risk["id"]),
                )
            )
            created.append(validation)
        return created

    def _execute_integrity_check(
        self, *, cycle_id: int, objective_id: int, cycle_key: str
    ) -> dict[str, Any]:
        work = self.operations.create_work(
            **self._work_spec(
                work_key=f"{cycle_key}.integrity-check",
                role="sre_operator",
                reviewer="internal_auditor",
                task_type="system_integrity_check",
                title="Verify company-state integrity and audit continuity",
                description="Run SQLite quick-check and verify the tamper-evident audit chain.",
                acceptance="SQLite returns ok and the audit hash chain verifies completely.",
                priority=100,
                objective_id=objective_id,
                cycle_id=cycle_id,
            )
        )
        if work["status"] == "succeeded":
            return work
        claimed = self.operations.claim_work(worker_key="sre_operator", lease_seconds=300)
        if claimed is None or claimed["id"] != work["id"]:
            return work
        started = self.operations.start_work(
            claimed["id"],
            worker_key="sre_operator",
            lease_token=claimed["lease_token"],
            lease_epoch=claimed["lease_epoch"],
        )
        with self.operations.store._connection() as connection:
            sqlite_result = connection.execute("PRAGMA quick_check").fetchone()[0]
        audit_valid, invalid_event = self.operations.store.verify_audit_chain()
        result = {
            "sqlite_quick_check": sqlite_result,
            "audit_chain_valid": audit_valid,
            "first_invalid_audit_event": invalid_event,
        }
        submitted = self.operations.submit_work(
            started["id"],
            worker_key="sre_operator",
            lease_token=started["lease_token"],
            lease_epoch=started["lease_epoch"],
            result=result,
        )
        return self.operations.review_work(
            submitted["id"],
            reviewer_worker_key="internal_auditor",
            decision="accept" if sqlite_result == "ok" and audit_valid else "reject",
            notes="Deterministic integrity gate",
            quality_score=1.0 if sqlite_result == "ok" and audit_valid else 0.0,
        )

    def dispatch_manifest(self, *, cycle_id: int | None = None) -> dict[str, Any]:
        work = self.operations.list_work(cycle_id=cycle_id, limit=1000)
        dispatchable = [item for item in work if item["status"] == "ready"]
        departments: dict[str, list[dict[str, Any]]] = {}
        for item in dispatchable:
            departments.setdefault(item["department_slug"], []).append(
                {
                    "work_id": item["id"],
                    "work_key": item["work_key"],
                    "codex_agent": ROLE_TO_CODEX_AGENT.get(
                        item["assigned_role_key"], item["assigned_role_key"]
                    ),
                    "assigned_role": item["assigned_role_key"],
                    "reviewer_role": item["reviewer_role_key"],
                    "priority": item["priority"],
                    "title": item["title"],
                    "description": item["description"],
                    "acceptance_criteria": item["acceptance_criteria"],
                    "instruction": (
                        "Claim this exact work item through the company OS, stay inside its "
                        "scope and repository policy, return evidence and artifacts, then submit "
                        "for the named independent reviewer. Do not perform external side effects."
                    ),
                }
            )
        return {
            "cycle_id": cycle_id,
            "dispatchable_count": len(dispatchable),
            "departments": departments,
            "owner_attention": self.operations.list_escalations(
                owner_attention=True, status="routed"
            ),
        }

    def run_cycle(
        self,
        *,
        triggered_by_worker: str = "company_president",
        mode: str = "internal",
        scheduled: bool = False,
        max_work_items: int = 20,
        approval_id: int | None = None,
    ) -> dict[str, Any]:
        return self._run_cycle(
            triggered_by_worker=triggered_by_worker,
            mode=mode,
            scheduled=scheduled,
            max_work_items=max_work_items,
            approval_id=approval_id,
        )

    def _run_cycle(
        self,
        *,
        triggered_by_worker: str,
        mode: str,
        scheduled: bool,
        max_work_items: int,
        approval_id: int | None,
    ) -> dict[str, Any]:
        approval = (
            self.operations.store.get_approval(approval_id)
            if approval_id is not None
            else None
        )
        enforce_action(
            ActionRequest(
                action="internal_analysis",
                actor=triggered_by_worker,
                scheduled=scheduled,
                external=mode == "external",
                reversible=True,
            ),
            approval=approval,
            repo_root=self.repo_root,
        )
        self.operations.bootstrap_organization(actor=triggered_by_worker)
        if not self.operations.command_authorized(
            triggered_by_worker, "chief_of_staff"
        ):
            raise ConflictError(
                "only the owner or Company President may trigger the corporate operating cycle"
            )
        stale_cycles_recovered = self.operations.recover_stale_cycles(
            actor_worker="sre_operator"
        )
        now = datetime.now(timezone.utc)
        cycle_key = (
            f"cycle-{now.strftime('%Y%m%dT%H%M%SZ')}-{secrets.token_hex(3)}"
        )
        cycle = self.operations.create_cycle(
            cycle_key=cycle_key,
            mode=mode,
            triggered_by_worker=triggered_by_worker,
            scheduled=scheduled,
            max_work_items=max_work_items,
            plan={"planner": "deterministic-v1", "external_effects_allowed": False},
        )
        try:
            objectives = self._ensure_objectives()
            return self._continue_started_cycle(
                cycle=cycle,
                objectives=objectives,
                cycle_key=cycle_key,
                now=now,
                max_work_items=max_work_items,
                triggered_by_worker=triggered_by_worker,
                stale_cycles_recovered=stale_cycles_recovered,
            )
        except Exception:
            try:
                self.operations.finish_cycle(
                    int(cycle["id"]),
                    status="failed",
                    summary={
                        "external_effects_executed": 0,
                        "aborted_by_unhandled_error": True,
                    },
                    actor_worker=triggered_by_worker,
                )
            except Exception:
                # Preserve the original failure. A later recovery cycle and
                # audit will still expose any cycle that could not be fenced.
                pass
            raise

    def _continue_started_cycle(
        self,
        *,
        cycle: Mapping[str, Any],
        objectives: Mapping[str, Mapping[str, Any]],
        cycle_key: str,
        now: datetime,
        max_work_items: int,
        triggered_by_worker: str,
        stale_cycles_recovered: int,
    ) -> dict[str, Any]:

        recovered = self.operations.recover_expired_leases(actor_worker="sre_operator")
        released_before = self.operations.release_ready_work(actor_worker="company_president")
        reconciled_cycles = self.operations.reconcile_cycles(
            actor_worker="company_president"
        )
        integrity = self._execute_integrity_check(
            cycle_id=cycle["id"],
            objective_id=objectives["company.zero-constitutional-breaches"]["id"],
            cycle_key=cycle_key,
        )
        if integrity["status"] != "succeeded":
            self.operations.open_incident(
                incident_key=f"{cycle_key}.audit-integrity",
                severity="sev0",
                title="Company audit integrity gate failed",
                description=(
                    "The deterministic integrity task did not pass; planning and dispatch "
                    "were halted before departmental work was issued."
                ),
                affected_scope="company operating ledger and work dispatch",
                owner_role_key="internal_auditor",
                opened_by_worker="sre_operator",
                containment="All new planning and dispatch for this cycle stopped.",
            )
            self.operations.create_escalation(
                raised_by_worker="internal_auditor",
                routed_to_role_key="owner_ceo",
                decision_class=DecisionClass.PROHIBITED,
                reason_code="audit_integrity_failure",
                title="Audit integrity failure requires owner awareness",
                context=(
                    "The company ledger's audit chain did not verify during the mandatory "
                    "pre-dispatch integrity gate."
                ),
                recommendation="Keep operations contained and restore from verified evidence.",
                safe_default="Do not plan, dispatch, schedule, or execute further work.",
                work_id=integrity["id"],
            )
            summary = {
                "recovered_leases": recovered,
                "recovered_stale_cycles": stale_cycles_recovered,
                "reconciled_cycles": reconciled_cycles,
                "released_work": released_before,
                "integrity_check_status": integrity["status"],
                "planned_work_items": 0,
                "reconciled_portfolio_work_items": 0,
                "dispatchable_work_items": 0,
                "owner_attention_items": 1,
                "external_effects_executed": 0,
                "halted_by_integrity_gate": True,
            }
            final_cycle = self.operations.finish_cycle(
                cycle["id"],
                status="failed",
                summary=summary,
                actor_worker=triggered_by_worker,
            )
            return {
                "cycle": final_cycle,
                "summary": summary,
                "dispatch": {
                    "cycle_id": cycle["id"],
                    "dispatchable_count": 0,
                    "departments": {},
                    "owner_attention": self.operations.list_escalations(
                        owner_attention=True, status="routed"
                    ),
                },
                "operations": self.operations.operations_summary(),
            }

        self._record_key_result_evidence(
            objectives["company.zero-constitutional-breaches"],
            result_key="verified-control-posture",
            current_value=1,
            evidence_reference=f"work:{integrity['id']}:accepted-integrity-check",
        )
        opportunities = self.operations.store.list_opportunities()
        validation_objective = objectives["company.validate-first-demand"]
        period_key = (
            f"{now.strftime('%G-W%V')}.company-discovery."
            f"{validation_objective['objective_key']}"
        )
        if opportunities:
            planned = self._plan_opportunity_work(
                cycle["id"],
                validation_objective["id"],
                period_key,
                opportunities,
                limit=max(0, max_work_items - 1),
            )
        else:
            planned = self._plan_discovery_work(
                cycle["id"],
                validation_objective["id"],
                period_key,
                limit=max(0, max_work_items - 1),
            )
        released_after = self.operations.release_ready_work(actor_worker="company_president")
        # Reconcile the complete durable backlog, including accepted work from
        # an earlier cycle that unlocked a downstream task today.
        manifest = self.dispatch_manifest(cycle_id=None)
        if not manifest["owner_attention"]:
            self._record_key_result_evidence(
                objectives["company.owner-leverage"],
                result_key="routine-owner-interventions",
                current_value=1,
                evidence_reference=f"cycle:{cycle['id']}:zero-routine-owner-attention",
            )
        new_planned = sum(1 for item in planned if item["cycle_id"] == cycle["id"])
        summary = {
            "recovered_leases": recovered,
            "recovered_stale_cycles": stale_cycles_recovered,
            "reconciled_cycles": reconciled_cycles,
            "released_work": released_before + released_after,
            "integrity_check_status": integrity["status"],
            "planned_work_items": new_planned,
            "reconciled_portfolio_work_items": len(planned),
            "dispatchable_work_items": manifest["dispatchable_count"],
            "owner_attention_items": len(manifest["owner_attention"]),
            "external_effects_executed": 0,
        }
        status = "awaiting_workers" if any(
            item["status"] not in {"succeeded", "failed", "dead_letter", "cancelled"}
            for item in self.operations.list_work(cycle_id=cycle["id"], limit=1000)
        ) else "completed"
        final_cycle = self.operations.finish_cycle(
            cycle["id"],
            status=status,
            summary=summary,
            actor_worker=triggered_by_worker,
        )
        return {
            "cycle": final_cycle,
            "summary": summary,
            "dispatch": manifest,
            "operations": self.operations.operations_summary(),
        }


__all__ = ["AutonomousCompany", "ROLE_TO_CODEX_AGENT"]
