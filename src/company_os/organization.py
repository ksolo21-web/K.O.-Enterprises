"""Immutable organization blueprint and deterministic authority checks.

The blueprint describes digital operating roles; it does not claim that digital
workers are legal employees or that a database identity authenticates Kaleb.
Administrative command also never overrides an independent control decision.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

from .errors import ValidationError


_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
_SLUG_PATTERN = re.compile(r"^[a-z][a-z0-9-]*$")
_WORKER_TYPES = frozenset({"human", "digital"})
_WORKER_STATUSES = frozenset({"active", "paused", "disabled"})
_AUTHORITY_LEVELS = frozenset(
    {"owner", "company_executive", "department_executive", "specialist"}
)
_COMMAND_CAPABILITIES = frozenset(
    {"command:company", "command:department", "command:team"}
)


@dataclass(frozen=True, slots=True)
class DepartmentSpec:
    """Machine-readable department charter."""

    slug: str
    name: str
    mission: str
    parent_slug: str | None
    executive_role_key: str
    service_level_cycles: int
    wip_limit: int


@dataclass(frozen=True, slots=True)
class RoleSpec:
    """An immutable role, reporting line, and bounded operating mandate."""

    role_key: str
    department_slug: str
    title: str
    reports_to_role_key: str | None
    authority_level: str
    worker_type: str
    mandate: str
    capabilities: tuple[str, ...]
    kpis: tuple[str, ...]
    max_active_work: int
    independent_control: bool = False
    block_domains: tuple[str, ...] = ()
    escalation_role_key: str | None = None


@dataclass(frozen=True, slots=True)
class WorkerSpec:
    """A named occupant of one blueprint role.

    Except for Kaleb, every occupant is a digital worker role rather than a
    representation that a human employment relationship exists.
    """

    worker_key: str
    display_name: str
    role_key: str
    manager_worker_key: str | None
    worker_type: str
    status: str
    capacity_units: int
    quality_floor: float


DEPARTMENTS: tuple[DepartmentSpec, ...] = (
    DepartmentSpec(
        "executive-office",
        "Executive Office",
        "Translate owner direction into a bounded operating plan and concise executive exceptions.",
        None,
        "company_president",
        1,
        6,
    ),
    DepartmentSpec(
        "opportunity-intelligence",
        "Opportunity Intelligence",
        "Find current, specific buyer pain and preserve decision-grade evidence without inventing demand.",
        "executive-office",
        "opportunity_intelligence_lead",
        3,
        10,
    ),
    DepartmentSpec(
        "strategy-portfolio",
        "Strategy and Portfolio",
        "Allocate attention to the strongest evidence-adjusted opportunities and stop weak theses early.",
        "executive-office",
        "strategy_portfolio_chief",
        2,
        5,
    ),
    DepartmentSpec(
        "product-technology",
        "Product and Technology",
        "Deliver the smallest reliable user outcome justified by validation evidence.",
        "executive-office",
        "product_technology_chief",
        2,
        8,
    ),
    DepartmentSpec(
        "quality-reliability",
        "Quality and Reliability",
        "Independently verify release quality, accessibility, recovery, and operational readiness.",
        "executive-office",
        "qa_reliability_lead",
        1,
        4,
    ),
    DepartmentSpec(
        "marketing",
        "Marketing",
        "Generate permission-based qualified demand using accurate, supportable product education.",
        "executive-office",
        "revenue_chief",
        2,
        6,
    ),
    DepartmentSpec(
        "sales-partnerships",
        "Sales and Partnerships",
        "Convert qualified demand into truthful commitments without unsolicited bulk outreach.",
        "executive-office",
        "sales_partnerships_lead",
        1,
        5,
    ),
    DepartmentSpec(
        "customer-success",
        "Customer Success",
        "Maximize activation and retention while keeping customer-specific service bounded.",
        "executive-office",
        "customer_success_lead",
        1,
        8,
    ),
    DepartmentSpec(
        "finance",
        "Finance and Controller",
        "Maintain financial truth, enforce hard limits, and independently challenge unit economics.",
        "executive-office",
        "finance_controller",
        1,
        5,
    ),
    DepartmentSpec(
        "legal-risk-security",
        "Legal, Risk, Security, and Privacy",
        "Block unacceptable legal, IP, privacy, security, platform, and reputation exposure.",
        "executive-office",
        "risk_legal_chief",
        2,
        6,
    ),
    DepartmentSpec(
        "people-agent-operations",
        "People and Agent Operations",
        "Maintain a capable, efficient, policy-compliant digital workforce with clear role ownership.",
        "executive-office",
        "people_agent_ops_chief",
        2,
        5,
    ),
    DepartmentSpec(
        "business-operations-analytics",
        "Business Operations and Analytics",
        "Run the work system, measure outcomes, recover incidents, and minimize CEO operating time.",
        "executive-office",
        "operations_analytics_chief",
        1,
        10,
    ),
)


_OWNER_CAPABILITIES = (
    "command:company",
    "governance:set_direction",
    "governance:approve_reserved_action",
    "governance:authorize_budget",
    "governance:amend_constitution",
    "governance:appoint_president",
    "review:work",
)
_PRESIDENT_CAPABILITIES = (
    "command:company",
    "operations:execute_plan",
    "operations:allocate_capacity",
    "operations:resolve_priority",
    "people:appoint_digital_worker",
    "decision:approve_internal",
    "review:work",
    "escalate:owner_ceo",
)
_DEPARTMENT_EXECUTIVE_CAPABILITIES = (
    "command:department",
    "work:assign",
    "work:accept",
    "review:work",
    "escalate:company_president",
)


def _executive_capabilities(*domain_capabilities: str) -> tuple[str, ...]:
    return _DEPARTMENT_EXECUTIVE_CAPABILITIES + domain_capabilities


def _control_capabilities(
    *domains: str, additional: tuple[str, ...] = ()
) -> tuple[str, ...]:
    capabilities: list[str] = list(additional)
    for domain in domains:
        capabilities.extend((f"review:{domain}", f"block:{domain}"))
    return tuple(capabilities)


ROLES: tuple[RoleSpec, ...] = (
    RoleSpec(
        "owner_ceo",
        "executive-office",
        "Owner and Chief Executive Officer",
        None,
        "owner",
        "human",
        "Set corporate direction, risk limits, capital ceilings, and decide reserved high-impact matters.",
        _OWNER_CAPABILITIES,
        ("verified_net_cash_contribution", "revenue_per_ceo_hour", "critical_risk_exposure"),
        3,
    ),
    RoleSpec(
        "company_president",
        "executive-office",
        "Company President",
        "owner_ceo",
        "company_executive",
        "digital",
        "Own the approved operating plan, coordinate department executives, and escalate only true executive decisions.",
        _PRESIDENT_CAPABILITIES,
        ("objective_attainment", "autonomous_completion_rate", "ceo_minutes", "portfolio_cycle_time"),
        6,
    ),
    RoleSpec(
        "chief_of_staff",
        "executive-office",
        "Chief of Staff",
        "company_president",
        "specialist",
        "digital",
        "Maintain executive priorities, decision packets, action follow-through, and cross-department visibility.",
        ("executive:brief", "work:coordinate", "decision:packet", "escalate:company_president"),
        ("decision_packet_completeness", "executive_follow_through", "avoidable_ceo_interruptions"),
        3,
    ),
    RoleSpec(
        "opportunity_intelligence_lead",
        "opportunity-intelligence",
        "Opportunity Intelligence Lead",
        "company_president",
        "department_executive",
        "digital",
        "Direct lawful market sensing and deliver complete, current opportunity dossiers to Strategy.",
        _executive_capabilities("evidence:govern", "opportunity:qualify", "research:prioritize"),
        ("dossier_acceptance_rate", "evidence_freshness_rate", "research_cycle_time"),
        4,
    ),
    RoleSpec(
        "market_researcher",
        "opportunity-intelligence",
        "Market Evidence Researcher",
        "opportunity_intelligence_lead",
        "specialist",
        "digital",
        "Collect current lawful evidence about buyers, costly workarounds, purchase behavior, and reachable channels.",
        ("research:public_sources", "evidence:record", "opportunity:propose", "escalate:opportunity_intelligence_lead"),
        ("evidence_completeness_rate", "source_independence_rate", "accepted_claim_rate"),
        3,
    ),
    RoleSpec(
        "market_structure_analyst",
        "opportunity-intelligence",
        "Market Structure Analyst",
        "opportunity_intelligence_lead",
        "specialist",
        "digital",
        "Map competitors, concentration, pricing, switching friction, shortages, and reasons an apparent gap persists.",
        ("market:map_supply", "market:analyze_pricing", "market:analyze_switching", "evidence:record"),
        ("supply_map_completeness", "pricing_evidence_freshness", "false_void_detection_rate"),
        3,
    ),
    RoleSpec(
        "strategy_portfolio_chief",
        "strategy-portfolio",
        "Chief Strategy and Portfolio Officer",
        "company_president",
        "department_executive",
        "digital",
        "Enforce ordered opportunity gates and allocate capacity to the strongest evidence-adjusted thesis.",
        _executive_capabilities("portfolio:prioritize", "portfolio:allocate", "opportunity:gate"),
        ("stage_decision_latency", "portfolio_wip_compliance", "forecast_calibration", "kill_discipline"),
        4,
    ),
    RoleSpec(
        "validation_lead",
        "strategy-portfolio",
        "Market Validation Lead",
        "strategy_portfolio_chief",
        "specialist",
        "digital",
        "Design the fastest ethical experiment that can disprove or strengthen a commercial thesis.",
        ("experiment:design", "experiment:freeze_thresholds", "evidence:assess_behavior", "decision:recommend"),
        ("time_to_validation_test", "threshold_integrity", "experiment_decision_rate"),
        2,
    ),
    RoleSpec(
        "counter_thesis_analyst",
        "strategy-portfolio",
        "Independent Counter-Thesis Analyst",
        "strategy_portfolio_chief",
        "specialist",
        "digital",
        "Independently challenge demand, reachability, economics, competition, and false-positive risk before advancement.",
        _control_capabilities(
            "opportunity_advancement",
            "evidence_quality",
            additional=("analysis:counter_thesis", "escalate:company_president"),
        ),
        ("material_risk_discovery_rate", "challenge_resolution_rate", "false_positive_prevention"),
        2,
        True,
        ("opportunity_advancement", "evidence_quality"),
        "company_president",
    ),
    RoleSpec(
        "product_technology_chief",
        "product-technology",
        "Chief Product and Technology Officer",
        "company_president",
        "department_executive",
        "digital",
        "Convert validated demand into the smallest maintainable product and accountable technical plan.",
        _executive_capabilities("product:approve_brief", "technology:approve_architecture", "product:allocate_build"),
        ("validated_build_ratio", "product_cycle_time", "escaped_critical_defects", "shared_asset_reuse"),
        4,
    ),
    RoleSpec(
        "product_manager",
        "product-technology",
        "Product Manager",
        "product_technology_chief",
        "specialist",
        "digital",
        "Define the user outcome, smallest complete scope, acceptance criteria, and product kill gates.",
        ("product:define_outcome", "product:write_brief", "product:acceptance_criteria", "feedback:synthesize"),
        ("acceptance_criteria_pass_rate", "scope_change_rate", "time_to_first_value"),
        3,
    ),
    RoleSpec(
        "software_architect",
        "product-technology",
        "Software Architect",
        "product_technology_chief",
        "specialist",
        "digital",
        "Choose a small reliable architecture with explicit trust boundaries and reversible integration seams.",
        ("technology:design", "security:threat_model_draft", "architecture:review", "reliability:design"),
        ("architecture_rework_rate", "dependency_count", "recovery_design_coverage"),
        2,
    ),
    RoleSpec(
        "software_engineer",
        "product-technology",
        "Software Engineer",
        "product_technology_chief",
        "specialist",
        "digital",
        "Implement tested, documented product and company-system changes within approved scope.",
        ("software:implement", "software:test", "software:document", "software:remediate"),
        ("independent_acceptance_rate", "introduced_regression_rate", "delivery_cycle_time"),
        3,
    ),
    RoleSpec(
        "qa_reliability_lead",
        "quality-reliability",
        "Quality and Reliability Lead",
        "company_president",
        "department_executive",
        "digital",
        "Independently test quality, accessibility, recovery, and release readiness and block unsafe releases.",
        _executive_capabilities(
            *_control_capabilities(
                "quality", "release", "reliability", "accessibility",
                additional=("qa:test", "recovery:verify"),
            )
        ),
        ("escaped_critical_defects", "release_gate_coverage", "recovery_test_pass_rate", "review_latency"),
        4,
        True,
        ("quality", "release", "reliability", "accessibility"),
        "owner_ceo",
    ),
    RoleSpec(
        "revenue_chief",
        "marketing",
        "Chief Revenue and Marketing Officer",
        "company_president",
        "department_executive",
        "digital",
        "Own truthful permission-based demand generation and coordinate the revenue funnel within approved policies.",
        _executive_capabilities("marketing:plan", "revenue:funnel", "claims:submit_review"),
        ("qualified_conversion_rate", "activation_rate", "channel_cost", "claim_review_pass_rate"),
        4,
    ),
    RoleSpec(
        "growth_strategist",
        "marketing",
        "Growth Strategist",
        "revenue_chief",
        "specialist",
        "digital",
        "Design measurable, permission-based acquisition and product-led growth experiments.",
        ("marketing:design_experiment", "channel:analyze", "analytics:define_funnel", "claims:draft"),
        ("qualified_demand_rate", "channel_experiment_velocity", "conversion_lift"),
        3,
    ),
    RoleSpec(
        "content_operator",
        "marketing",
        "Content and Creative Operator",
        "revenue_chief",
        "specialist",
        "digital",
        "Create accurate original product education, demonstrations, documentation, and approved campaign assets.",
        ("content:create", "content:maintain", "claims:trace", "accessibility:content_check"),
        ("claims_traceability_rate", "content_acceptance_rate", "qualified_content_conversion"),
        3,
    ),
    RoleSpec(
        "sales_partnerships_lead",
        "sales-partnerships",
        "Sales and Partnerships Lead",
        "company_president",
        "department_executive",
        "digital",
        "Manage qualified inbound conversion and permission-based partnerships without unauthorized outreach.",
        _executive_capabilities("sales:qualify", "sales:manage_pipeline", "partnerships:evaluate", "customer:handoff"),
        ("qualified_to_commit_rate", "sales_cycle_time", "forecast_error", "unauthorized_outreach_count"),
        4,
    ),
    RoleSpec(
        "customer_success_lead",
        "customer-success",
        "Customer Success Lead",
        "company_president",
        "department_executive",
        "digital",
        "Own onboarding, support triage, retention signals, and structured product feedback with bounded service effort.",
        _executive_capabilities("customer:onboard", "support:triage", "retention:analyze", "feedback:handoff"),
        ("activation_rate", "time_to_first_value", "retention_rate", "support_minutes_per_customer"),
        5,
    ),
    RoleSpec(
        "finance_controller",
        "finance",
        "Chief Financial Officer and Controller",
        "company_president",
        "department_executive",
        "digital",
        "Maintain financial truth, enforce allocations, and block unsupported or out-of-limit financial action.",
        _executive_capabilities(
            *_control_capabilities(
                "finance", "budget", "unit_economics",
                additional=("finance:reconcile", "finance:close", "resource:reserve"),
            )
        ),
        ("actual_reference_coverage", "budget_breach_count", "close_timeliness", "forecast_variance"),
        4,
        True,
        ("finance", "budget", "unit_economics"),
        "owner_ceo",
    ),
    RoleSpec(
        "risk_legal_chief",
        "legal-risk-security",
        "Chief Legal and Risk Officer",
        "company_president",
        "department_executive",
        "digital",
        "Independently govern legal, IP, claims, regulatory, platform, and enterprise-risk gates.",
        _executive_capabilities(
            *_control_capabilities(
                "legal", "risk", "claims", "ip", "regulatory", "platform_policy",
                additional=("risk:register", "legal:triage"),
            )
        ),
        ("unresolved_critical_risks", "control_review_latency", "repeat_incident_rate", "claim_exception_count"),
        4,
        True,
        ("legal", "risk", "claims", "ip", "regulatory", "platform_policy"),
        "owner_ceo",
    ),
    RoleSpec(
        "legal_compliance_officer",
        "legal-risk-security",
        "Legal, Compliance, and IP Officer",
        "risk_legal_chief",
        "specialist",
        "digital",
        "Review licenses, terms, disclosures, claims, data use, and approval requirements without offering unlicensed advice.",
        _control_capabilities(
            "legal", "claims", "ip", "regulatory", "platform_policy",
            additional=("legal:research", "compliance:checklist"),
        ),
        ("review_completeness", "review_latency", "license_traceability", "overdue_finding_count"),
        3,
        True,
        ("legal", "claims", "ip", "regulatory", "platform_policy"),
        "risk_legal_chief",
    ),
    RoleSpec(
        "security_privacy_officer",
        "legal-risk-security",
        "Security and Privacy Officer",
        "risk_legal_chief",
        "specialist",
        "digital",
        "Review threat boundaries, secret handling, permissions, data minimization, retention, and incident exposure.",
        _control_capabilities(
            "security", "privacy", "data", "permissions",
            additional=("security:threat_model", "privacy:data_map", "incident:security_triage"),
        ),
        ("critical_security_findings", "data_minimization_coverage", "permission_exception_count", "remediation_latency"),
        3,
        True,
        ("security", "privacy", "data", "permissions"),
        "risk_legal_chief",
    ),
    RoleSpec(
        "people_agent_ops_chief",
        "people-agent-operations",
        "Chief People and Agent Operations Officer",
        "company_president",
        "department_executive",
        "digital",
        "Assign digital workers by demonstrated role fit and manage coaching, capacity, reassignment, and disablement.",
        _executive_capabilities("people:evaluate_digital_worker", "people:coach", "people:recommend_reassignment", "capacity:plan"),
        ("independent_acceptance_rate", "rework_rate", "policy_incident_rate", "capacity_utilization"),
        4,
    ),
    RoleSpec(
        "operations_analytics_chief",
        "business-operations-analytics",
        "Chief Operations and Analytics Officer",
        "company_president",
        "department_executive",
        "digital",
        "Operate the durable work loop, enforce service levels, maintain metric truth, and coordinate continuity.",
        _executive_capabilities("operations:dispatch", "operations:escalate_sla", "analytics:govern", "continuity:coordinate"),
        ("autonomous_completion_rate", "sla_adherence", "blocked_work_age", "recovery_time", "ceo_minutes"),
        5,
    ),
    RoleSpec(
        "data_analyst",
        "business-operations-analytics",
        "Data and Metrics Analyst",
        "operations_analytics_chief",
        "specialist",
        "digital",
        "Define metric contracts, validate observations, and separate actuals, estimates, forecasts, and assumptions.",
        ("analytics:define_metric", "analytics:validate_event", "analytics:report", "evidence:quality_check"),
        ("metric_definition_coverage", "event_validity_rate", "unknown_data_rate", "report_timeliness"),
        3,
    ),
    RoleSpec(
        "sre_operator",
        "business-operations-analytics",
        "Site Reliability and Continuity Operator",
        "operations_analytics_chief",
        "specialist",
        "digital",
        "Maintain health checks, idempotent recovery, backup verification, and incident runbooks within approved environments.",
        ("reliability:operate", "backup:verify", "incident:respond", "scheduler:health_check"),
        ("availability", "recovery_time", "backup_verification_rate", "repeat_incident_rate"),
        3,
    ),
    RoleSpec(
        "internal_auditor",
        "business-operations-analytics",
        "Independent Internal Auditor",
        "operations_analytics_chief",
        "specialist",
        "digital",
        "Independently audit policy compliance, evidence lineage, control effectiveness, and digital-worker performance.",
        _control_capabilities(
            "audit", "policy", "performance",
            additional=("audit:sample", "audit:trace", "escalate:owner_ceo"),
        ),
        ("audit_coverage", "material_finding_rate", "repeat_finding_rate", "remediation_verification_rate"),
        2,
        True,
        ("audit", "policy", "performance"),
        "owner_ceo",
    ),
)


def _worker_key_for_role(role_key: str) -> str:
    return "kaleb_ceo" if role_key == "owner_ceo" else role_key


def _worker_capacity(role: RoleSpec) -> int:
    return {
        "owner": 10,
        "company_executive": 100,
        "department_executive": 50,
        "specialist": 25,
    }[role.authority_level]


def _worker_quality_floor(role: RoleSpec) -> float:
    return {
        "owner": 1.0,
        "company_executive": 0.90,
        "department_executive": 0.88,
        "specialist": 0.85,
    }[role.authority_level]


_ROLE_SEED_BY_KEY = {role.role_key: role for role in ROLES}


WORKERS: tuple[WorkerSpec, ...] = tuple(
    WorkerSpec(
        worker_key=_worker_key_for_role(role.role_key),
        display_name="Kaleb" if role.role_key == "owner_ceo" else role.title,
        role_key=role.role_key,
        manager_worker_key=(
            _worker_key_for_role(role.reports_to_role_key)
            if role.reports_to_role_key is not None
            else None
        ),
        worker_type=role.worker_type,
        status="active",
        capacity_units=_worker_capacity(role),
        quality_floor=_worker_quality_floor(role),
    )
    for role in ROLES
)


_DEPARTMENT_BY_SLUG = {department.slug: department for department in DEPARTMENTS}
_ROLE_BY_KEY = dict(_ROLE_SEED_BY_KEY)
_WORKER_BY_KEY = {worker.worker_key: worker for worker in WORKERS}
_WORKER_BY_ROLE_KEY = {worker.role_key: worker for worker in WORKERS}


def department_by_slug(slug: str) -> DepartmentSpec:
    """Return a department by its stable persistence slug."""

    try:
        return _DEPARTMENT_BY_SLUG[slug]
    except KeyError as exc:
        raise KeyError(f"unknown department: {slug}") from exc


def role_by_key(role_key: str) -> RoleSpec:
    """Return a role by its stable persistence key."""

    try:
        return _ROLE_BY_KEY[role_key]
    except KeyError as exc:
        raise KeyError(f"unknown role: {role_key}") from exc


def worker_by_key(worker_key: str) -> WorkerSpec:
    """Return a worker by its stable persistence key."""

    try:
        return _WORKER_BY_KEY[worker_key]
    except KeyError as exc:
        raise KeyError(f"unknown worker: {worker_key}") from exc


def reporting_chain(role_key: str, *, include_self: bool = False) -> tuple[str, ...]:
    """Return direct manager through owner for ``role_key``.

    The tuple contains role keys ordered from the nearest manager to the root.
    Blueprint validation guarantees termination, but a defensive cycle check is
    retained so this helper fails closed if called against corrupted module data.
    """

    current = role_by_key(role_key)
    chain: list[str] = [current.role_key] if include_self else []
    seen = {current.role_key}
    while current.reports_to_role_key is not None:
        parent_key = current.reports_to_role_key
        if parent_key in seen:
            raise ValidationError(f"role reporting cycle detected at {parent_key}")
        seen.add(parent_key)
        chain.append(parent_key)
        current = role_by_key(parent_key)
    return tuple(chain)


def worker_reporting_chain(
    worker_key: str, *, include_self: bool = False
) -> tuple[str, ...]:
    """Return direct manager through Kaleb for a named worker."""

    current = worker_by_key(worker_key)
    chain: list[str] = [current.worker_key] if include_self else []
    seen = {current.worker_key}
    while current.manager_worker_key is not None:
        parent_key = current.manager_worker_key
        if parent_key in seen:
            raise ValidationError(f"worker reporting cycle detected at {parent_key}")
        seen.add(parent_key)
        chain.append(parent_key)
        current = worker_by_key(parent_key)
    return tuple(chain)


def can_command(commander_role_key: str, target_role_key: str) -> bool:
    """Return whether one role has administrative command over another.

    This answers assignment/reporting authority only.  It never authorizes an
    external action and never permits a manager to reverse an independent
    controller's block or manufacture the controller's review conclusion.
    """

    if commander_role_key == target_role_key:
        return False
    commander = role_by_key(commander_role_key)
    role_by_key(target_role_key)
    if not _COMMAND_CAPABILITIES.intersection(commander.capabilities):
        return False
    return commander_role_key in reporting_chain(target_role_key)


def can_block(role_key: str, domain: str) -> bool:
    """Return whether a role has an independent stop right for ``domain``."""

    role = role_by_key(role_key)
    normalized = domain.strip().lower()
    return (
        bool(normalized)
        and role.independent_control
        and normalized in role.block_domains
        and f"block:{normalized}" in role.capabilities
    )


def can_review(
    reviewer_role_key: str,
    author_role_key: str,
    domain: str = "work",
    *,
    independent: bool = False,
) -> bool:
    """Return whether ``reviewer_role_key`` may review the author's work."""

    if reviewer_role_key == author_role_key:
        return False
    reviewer = role_by_key(reviewer_role_key)
    role_by_key(author_role_key)
    normalized = domain.strip().lower()
    if not normalized:
        return False
    if normalized == "work":
        qualified = (
            "review:work" in reviewer.capabilities
            and can_command(reviewer_role_key, author_role_key)
        )
    else:
        qualified = f"review:{normalized}" in reviewer.capabilities
    if not qualified:
        return False
    if independent:
        return (
            reviewer.independent_control
            and normalized in reviewer.block_domains
            and reviewer.escalation_role_key is not None
        )
    return True


def separation_of_duties_satisfied(
    requester_role_key: str, reviewer_role_key: str, domain: str
) -> bool:
    """Require a distinct, functionally independent controller for a domain."""

    return can_review(
        reviewer_role_key,
        requester_role_key,
        domain,
        independent=True,
    )


def escalation_route(role_key: str) -> tuple[str, ...]:
    """Return the explicit control escalation path, then its reporting path."""

    role = role_by_key(role_key)
    next_key = role.escalation_role_key or role.reports_to_role_key
    if next_key is None:
        return ()
    route = [next_key]
    seen = {role_key, next_key}
    current = role_by_key(next_key)
    while current.reports_to_role_key is not None:
        candidate = current.escalation_role_key or current.reports_to_role_key
        if candidate in seen:
            raise ValidationError(f"role escalation cycle detected at {candidate}")
        seen.add(candidate)
        route.append(candidate)
        current = role_by_key(candidate)
    return tuple(route)


def _validate_unique(values: Sequence[str], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValidationError(f"duplicate {label} key")


def validate_blueprint(
    departments: Sequence[DepartmentSpec] = DEPARTMENTS,
    roles: Sequence[RoleSpec] = ROLES,
    workers: Sequence[WorkerSpec] = WORKERS,
) -> bool:
    """Validate hierarchy, persistence keys, controls, and worker assignments.

    The function returns ``True`` for convenient startup assertions and raises
    :class:`ValidationError` with the first deterministic defect otherwise.
    """

    if not departments or not roles or not workers:
        raise ValidationError("organization blueprint sections must not be empty")

    department_keys = [item.slug for item in departments]
    role_keys = [item.role_key for item in roles]
    worker_keys = [item.worker_key for item in workers]
    _validate_unique(department_keys, "department")
    _validate_unique(role_keys, "role")
    _validate_unique(worker_keys, "worker")

    department_map = {item.slug: item for item in departments}
    role_map = {item.role_key: item for item in roles}
    worker_map = {item.worker_key: item for item in workers}
    worker_by_role = {item.role_key: item for item in workers}
    if len(worker_by_role) != len(workers):
        raise ValidationError("each role may have only one blueprint worker")

    for department in departments:
        if not _SLUG_PATTERN.fullmatch(department.slug):
            raise ValidationError(f"invalid department slug: {department.slug}")
        if not department.name.strip() or not department.mission.strip():
            raise ValidationError(f"department {department.slug} needs a name and mission")
        if department.service_level_cycles < 1 or department.wip_limit < 1:
            raise ValidationError(
                f"department {department.slug} needs positive service level and WIP limit"
            )
        if department.parent_slug is not None and department.parent_slug not in department_map:
            raise ValidationError(
                f"department {department.slug} has unknown parent {department.parent_slug}"
            )
        executive = role_map.get(department.executive_role_key)
        if executive is None or executive.department_slug != department.slug:
            raise ValidationError(
                f"department {department.slug} has an invalid executive role"
            )

        seen_departments = {department.slug}
        parent_slug = department.parent_slug
        while parent_slug is not None:
            if parent_slug in seen_departments:
                raise ValidationError(
                    f"department reporting cycle detected at {parent_slug}"
                )
            seen_departments.add(parent_slug)
            parent_slug = department_map[parent_slug].parent_slug

    roots = [role for role in roles if role.reports_to_role_key is None]
    if len(roots) != 1 or roots[0].role_key != "owner_ceo":
        raise ValidationError("owner_ceo must be the single root role")
    if role_map.get("company_president") is None or (
        role_map["company_president"].reports_to_role_key != "owner_ceo"
    ):
        raise ValidationError("company_president must report to owner_ceo")

    for role in roles:
        if not _KEY_PATTERN.fullmatch(role.role_key):
            raise ValidationError(f"invalid role key: {role.role_key}")
        if role.department_slug not in department_map:
            raise ValidationError(
                f"role {role.role_key} has unknown department {role.department_slug}"
            )
        if role.authority_level not in _AUTHORITY_LEVELS:
            raise ValidationError(
                f"role {role.role_key} has invalid authority level {role.authority_level}"
            )
        if role.worker_type not in _WORKER_TYPES:
            raise ValidationError(
                f"role {role.role_key} has invalid worker type {role.worker_type}"
            )
        if not role.title.strip() or not role.mandate.strip():
            raise ValidationError(f"role {role.role_key} needs a title and mandate")
        if (
            not isinstance(role.capabilities, tuple)
            or not role.capabilities
            or len(role.capabilities) != len(set(role.capabilities))
        ):
            raise ValidationError(
                f"role {role.role_key} needs unique immutable capabilities"
            )
        if (
            not isinstance(role.kpis, tuple)
            or not role.kpis
            or len(role.kpis) != len(set(role.kpis))
        ):
            raise ValidationError(f"role {role.role_key} needs unique immutable KPIs")
        if role.max_active_work < 1:
            raise ValidationError(f"role {role.role_key} needs a positive WIP limit")
        if role.reports_to_role_key is not None and role.reports_to_role_key not in role_map:
            raise ValidationError(
                f"role {role.role_key} has unknown manager {role.reports_to_role_key}"
            )

        seen_roles = {role.role_key}
        manager_key = role.reports_to_role_key
        while manager_key is not None:
            if manager_key in seen_roles:
                raise ValidationError(f"role reporting cycle detected at {manager_key}")
            seen_roles.add(manager_key)
            manager_key = role_map[manager_key].reports_to_role_key

        if role.independent_control:
            if not role.block_domains or role.escalation_role_key is None:
                raise ValidationError(
                    f"independent control role {role.role_key} needs block domains and escalation"
                )
            if role.escalation_role_key not in role_map or role.escalation_role_key == role.role_key:
                raise ValidationError(
                    f"independent control role {role.role_key} has invalid escalation"
                )
            for domain in role.block_domains:
                if (
                    f"review:{domain}" not in role.capabilities
                    or f"block:{domain}" not in role.capabilities
                ):
                    raise ValidationError(
                        f"independent control role {role.role_key} lacks review/block capability for {domain}"
                    )
        elif role.block_domains:
            raise ValidationError(
                f"non-control role {role.role_key} cannot declare block domains"
            )

    expected_executive_reports = {
        department.executive_role_key
        for department in departments
        if department.slug != "executive-office"
    }
    for role_key in expected_executive_reports:
        role = role_map[role_key]
        if role.reports_to_role_key != "company_president":
            raise ValidationError(
                f"department executive {role_key} must report to company_president"
            )
        if role.authority_level != "department_executive":
            raise ValidationError(
                f"department executive {role_key} has invalid authority level"
            )

    if set(worker_by_role) != set(role_map):
        raise ValidationError("every role must have exactly one blueprint worker")
    root_workers = [worker for worker in workers if worker.manager_worker_key is None]
    if len(root_workers) != 1 or root_workers[0].worker_key != "kaleb_ceo":
        raise ValidationError("kaleb_ceo must be the single root worker")

    for worker in workers:
        if not _KEY_PATTERN.fullmatch(worker.worker_key):
            raise ValidationError(f"invalid worker key: {worker.worker_key}")
        role = role_map.get(worker.role_key)
        if role is None:
            raise ValidationError(
                f"worker {worker.worker_key} has unknown role {worker.role_key}"
            )
        if not worker.display_name.strip():
            raise ValidationError(f"worker {worker.worker_key} needs a display name")
        if worker.worker_type != role.worker_type:
            raise ValidationError(
                f"worker {worker.worker_key} type does not match role {role.role_key}"
            )
        if worker.status not in _WORKER_STATUSES:
            raise ValidationError(
                f"worker {worker.worker_key} has invalid status {worker.status}"
            )
        if worker.capacity_units < 1:
            raise ValidationError(f"worker {worker.worker_key} needs positive capacity")
        if not 0.0 <= worker.quality_floor <= 1.0:
            raise ValidationError(
                f"worker {worker.worker_key} quality floor must be in 0..1"
            )
        expected_manager = (
            _worker_key_for_role(role.reports_to_role_key)
            if role.reports_to_role_key is not None
            else None
        )
        if worker.manager_worker_key != expected_manager:
            raise ValidationError(
                f"worker {worker.worker_key} manager does not match role hierarchy"
            )
        if worker.manager_worker_key is not None and worker.manager_worker_key not in worker_map:
            raise ValidationError(
                f"worker {worker.worker_key} has unknown manager {worker.manager_worker_key}"
            )

    covered_control_domains = {
        domain
        for role in roles
        if role.independent_control
        for domain in role.block_domains
    }
    required_control_domains = {
        "opportunity_advancement",
        "finance",
        "budget",
        "legal",
        "risk",
        "security",
        "privacy",
        "quality",
        "release",
        "audit",
    }
    missing_controls = sorted(required_control_domains - covered_control_domains)
    if missing_controls:
        raise ValidationError(
            "organization lacks independent control coverage for: "
            + ", ".join(missing_controls)
        )

    return True


# A malformed built-in roster is a programming error and should fail at import,
# before it can be persisted or used to route work.
validate_blueprint()


__all__ = [
    "DEPARTMENTS",
    "ROLES",
    "WORKERS",
    "DepartmentSpec",
    "RoleSpec",
    "WorkerSpec",
    "can_block",
    "can_command",
    "can_review",
    "department_by_slug",
    "escalation_route",
    "reporting_chain",
    "role_by_key",
    "separation_of_duties_satisfied",
    "validate_blueprint",
    "worker_by_key",
    "worker_reporting_chain",
]
