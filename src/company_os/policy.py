"""Executable pause and approval policy.

The policy is intentionally conservative.  It permits reversible, zero-spend
internal work while ensuring that spending, identity-bound actions, sensitive
data, contracts, permission expansion, and unapproved external actions stop for
authorization.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any, Mapping

from .errors import CompanyOSError, ValidationError


class ApprovalClass(StrEnum):
    AUTO_ALLOWED = "auto_allowed"
    POLICY_GATED = "policy_gated"
    CEO_APPROVAL_REQUIRED = "ceo_approval_required"


class PolicyViolation(CompanyOSError):
    """An action violates a non-overridable policy condition."""


class PauseActive(PolicyViolation):
    """An external or scheduled operation was stopped by the kill switch."""


class ApprovalRequired(PolicyViolation):
    """An action lacks the approval required by its policy class."""


AUTO_ALLOWED_ACTIONS = frozenset(
    {
        "read_repository",
        "write_code",
        "run_tests",
        "draft_content",
        "research_public_source",
        "update_score",
        "generate_report",
        "internal_analysis",
    }
)

POLICY_GATED_ACTIONS = frozenset(
    {
        "deploy_authorized",
        "publish_authorized",
        "send_transactional_message",
        "call_approved_api",
        "predefined_refund",
    }
)

CEO_REQUIRED_ACTIONS = frozenset(
    {
        "spend_money",
        "move_money",
        "open_financial_account",
        "accept_contract",
        "purchase_domain",
        "create_legal_entity",
        "publish_regulated_claim",
        "collect_sensitive_data",
        "change_billing_policy",
        "delete_revenue_asset",
        "expand_permissions",
        "speak_as_ceo",
    }
)

_TRUE_VALUES = frozenset({"1", "true", "yes", "on", "paused"})
_FALSE_VALUES = frozenset({"0", "false", "no", "off", "active", "unpaused"})


@dataclass(frozen=True, slots=True)
class ActionRequest:
    action: str
    actor: str = "company_os"
    estimated_cost_cents: int = 0
    external: bool = False
    scheduled: bool = False
    reversible: bool = True
    risk_level: str = "low"
    handles_sensitive_data: bool = False
    accepts_contract: bool = False
    expands_permissions: bool = False
    requested_class: ApprovalClass | str | None = None

    def __post_init__(self) -> None:
        if not self.action.strip():
            raise ValidationError("action must not be empty")
        if type(self.estimated_cost_cents) is not int:
            raise ValidationError("estimated_cost_cents must be an integer number of cents")
        if self.estimated_cost_cents < 0:
            raise ValidationError("estimated_cost_cents must be non-negative")
        if self.risk_level not in {"low", "medium", "high", "critical"}:
            raise ValidationError("risk_level must be low, medium, high, or critical")


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    allowed: bool
    approval_class: ApprovalClass
    reason: str
    approval_required: bool = False
    blocked_by_pause: bool = False
    approval_id: int | None = None


def is_paused(repo_root: str | os.PathLike[str] | None = None) -> bool:
    """Return whether the emergency pause is active.

    The environment flag is useful in hosted automation.  The repository file is
    deliberately simple so a human can stop external work without any tooling.
    """

    env_value = os.environ.get("COMPANY_OS_PAUSED", "").strip().lower()
    if env_value in _TRUE_VALUES:
        return True
    if env_value and env_value not in _FALSE_VALUES:
        # A misspelled safety setting must not silently disable the stop.
        return True
    root = Path(repo_root) if repo_root is not None else Path.cwd()
    return (root.resolve() / "PAUSE_AUTONOMY").is_file()


def classify_action(request: ActionRequest) -> ApprovalClass:
    """Classify an action using hard safety facts before its label."""

    if request.requested_class is not None:
        try:
            requested = ApprovalClass(request.requested_class)
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"unknown approval class: {request.requested_class}") from exc
    else:
        requested = None

    action = request.action.strip().lower()
    hard_ceo_gate = (
        request.estimated_cost_cents > 0
        or request.handles_sensitive_data
        or request.accepts_contract
        or request.expands_permissions
        or not request.reversible
        or request.risk_level in {"high", "critical"}
        or action in CEO_REQUIRED_ACTIONS
    )
    if hard_ceo_gate:
        baseline = ApprovalClass.CEO_APPROVAL_REQUIRED
    elif action in POLICY_GATED_ACTIONS:
        baseline = ApprovalClass.POLICY_GATED
    elif action in AUTO_ALLOWED_ACTIONS:
        # A known-safe action becomes policy-gated if it is scheduled or has an
        # external side effect.  Read-only network research should not set
        # ``external``; that flag denotes a side effect outside local state.
        baseline = (
            ApprovalClass.POLICY_GATED
            if request.external or request.scheduled
            else ApprovalClass.AUTO_ALLOWED
        )
    else:
        # An unknown external or scheduled operation is *more* concerning, not
        # a reason to inherit the less restrictive generic policy gate.
        baseline = ApprovalClass.CEO_APPROVAL_REQUIRED

    if requested is None:
        return baseline
    class_rank = {
        ApprovalClass.AUTO_ALLOWED: 0,
        ApprovalClass.POLICY_GATED: 1,
        ApprovalClass.CEO_APPROVAL_REQUIRED: 2,
    }
    # Callers may request stricter review but cannot relabel an action into a
    # less restrictive class.
    return max((baseline, requested), key=class_rank.__getitem__)


def _parse_expiry(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        normalized = str(value).replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except (TypeError, ValueError):
            return datetime.min.replace(tzinfo=timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def approval_matches(
    approval: Mapping[str, Any] | None,
    request: ActionRequest,
    required_class: ApprovalClass,
) -> tuple[bool, int | None]:
    if not approval or str(approval.get("status", "")).lower() != "approved":
        return False, None

    approved_action = str(approval.get("action", "")).strip().lower()
    if approved_action != request.action.strip().lower():
        return False, None

    try:
        approved_class = ApprovalClass(str(approval.get("approval_class", "")))
    except ValueError:
        return False, None
    class_rank = {
        ApprovalClass.AUTO_ALLOWED: 0,
        ApprovalClass.POLICY_GATED: 1,
        ApprovalClass.CEO_APPROVAL_REQUIRED: 2,
    }
    if class_rank[approved_class] < class_rank[required_class]:
        return False, None

    approved_cost = approval.get("estimated_cost_cents", 0)
    if type(approved_cost) is not int:
        return False, None
    if approved_cost < 0 or approved_cost > 9_223_372_036_854_775_807:
        return False, None
    if request.estimated_cost_cents > approved_cost:
        return False, None

    expiry = _parse_expiry(approval.get("expires_at"))
    # Consequential approvals are always time-bounded.  Legacy or malformed
    # records without an expiry fail closed.
    if expiry is None or expiry <= datetime.now(timezone.utc):
        return False, None
    approval_id = approval.get("id")
    if type(approval_id) is not int or approval_id <= 0:
        return False, None
    return True, approval_id


def evaluate_action(
    request: ActionRequest,
    approval: Mapping[str, Any] | None = None,
    repo_root: str | os.PathLike[str] | None = None,
) -> PolicyDecision:
    """Evaluate an action without carrying it out."""

    required_class = classify_action(request)
    # Do not let a caller bypass the emergency stop by omitting or falsifying
    # the side-effect flags.  Every non-auto action is gated by definition and
    # therefore remains stopped while the repository is paused.
    if is_paused(repo_root) and (
        request.external
        or request.scheduled
        or required_class is not ApprovalClass.AUTO_ALLOWED
    ):
        return PolicyDecision(
            allowed=False,
            approval_class=required_class,
            reason=(
                "PAUSE_AUTONOMY is active; external, scheduled, and otherwise "
                "gated operations are stopped"
            ),
            blocked_by_pause=True,
        )

    if required_class is ApprovalClass.AUTO_ALLOWED:
        return PolicyDecision(
            allowed=True,
            approval_class=required_class,
            reason="reversible, internal, zero-spend action is auto-allowed",
        )

    matched, approval_id = approval_matches(approval, request, required_class)
    if matched:
        return PolicyDecision(
            allowed=True,
            approval_class=required_class,
            reason="a matching unexpired approval covers this action and cost",
            approval_id=approval_id,
        )

    owner = "CEO" if required_class is ApprovalClass.CEO_APPROVAL_REQUIRED else "policy owner"
    return PolicyDecision(
        allowed=False,
        approval_class=required_class,
        reason=f"a matching approval from the {owner} is required",
        approval_required=True,
    )


def enforce_action(
    request: ActionRequest,
    approval: Mapping[str, Any] | None = None,
    repo_root: str | os.PathLike[str] | None = None,
) -> PolicyDecision:
    """Return an allowing decision or raise the precise policy exception."""

    decision = evaluate_action(request, approval=approval, repo_root=repo_root)
    if decision.allowed:
        return decision
    if decision.blocked_by_pause:
        raise PauseActive(decision.reason)
    if decision.approval_required:
        raise ApprovalRequired(decision.reason)
    raise PolicyViolation(decision.reason)
