"""Transparent Market Void and Entry-Wedge scoring."""

from __future__ import annotations

import ipaddress
from dataclasses import asdict, dataclass, fields
from datetime import date, datetime, timezone
from typing import Any, Iterable, Mapping
from urllib.parse import urlparse

from .errors import ValidationError


COMPONENT_WEIGHTS: dict[str, int] = {
    "need_severity": 20,
    "demand_acceleration": 10,
    "economic_commitment": 10,
    "supply_gap": 15,
    "incumbent_weakness": 10,
    "reachable_beachhead": 10,
    "sustainable_advantage": 10,
    "switching_feasibility": 5,
    "bootstrap_feasibility": 5,
    "recurring_revenue": 5,
}

PENALTY_WEIGHTS: dict[str, int] = {
    "legal_risk": 10,
    "platform_dependency": 8,
    "proprietary_data_dependency": 8,
    "security_exposure": 8,
    "support_burden": 6,
    "weak_buyer_reach": 8,
    "evidence_staleness": 7,
}

EVIDENCE_STRENGTH_WEIGHTS: dict[str, float] = {
    "weak": 0.35,
    "moderate": 0.70,
    "strong": 1.0,
}

# The documented scorecard permits a cheap validation experiment at 65.  Lower
# scores can remain in the research ledger but cannot be labeled advancement-ready.
ADVANCEMENT_THRESHOLD = 65.0
HARD_REJECTION_FLAGS = frozenset(
    {
        "meaningful_cash_before_validation",
        "regulated_or_risky_data",
        "mvp_too_large",
        "maintenance_incompatible",
        "unlawful_advantage",
    }
)


def _validate_unit_value(name: str, value: Any) -> float:
    if isinstance(value, bool):
        raise ValidationError(f"{name} must be a number between 0 and 1, not boolean")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{name} must be a number between 0 and 1") from exc
    if not 0.0 <= result <= 1.0:
        raise ValidationError(f"{name} must be between 0 and 1")
    return result


@dataclass(frozen=True, slots=True)
class MarketVoidInput:
    """Normalized scoring inputs; every numeric factor is in the 0..1 range."""

    need_severity: float = 0.0
    demand_acceleration: float = 0.0
    economic_commitment: float = 0.0
    supply_gap: float = 0.0
    incumbent_weakness: float = 0.0
    reachable_beachhead: float = 0.0
    sustainable_advantage: float = 0.0
    switching_feasibility: float = 0.0
    bootstrap_feasibility: float = 0.0
    recurring_revenue: float = 0.0
    low_competition: bool = False
    strong_demand_signal: bool = False
    independent_source_count: int = 0
    credible_problem_evidence: bool = True
    reachable_without_spam: bool = True
    meaningful_cash_before_validation: bool = False
    regulated_or_risky_data: bool = False
    mvp_too_large: bool = False
    maintenance_incompatible: bool = False
    unlawful_advantage: bool = False

    def __post_init__(self) -> None:
        for name in COMPONENT_WEIGHTS:
            object.__setattr__(self, name, _validate_unit_value(name, getattr(self, name)))
        if self.independent_source_count < 0:
            raise ValidationError("independent_source_count must be non-negative")

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> "MarketVoidInput":
        allowed = {field.name for field in fields(cls)}
        unknown = set(values) - allowed
        if unknown:
            raise ValidationError(
                "unknown market-void input(s): "
                + ", ".join(sorted(str(key) for key in unknown))
            )
        return cls(**dict(values))


@dataclass(frozen=True, slots=True)
class RiskPenalties:
    """Normalized risk penalty inputs; every factor is in the 0..1 range."""

    legal_risk: float = 0.0
    platform_dependency: float = 0.0
    proprietary_data_dependency: float = 0.0
    security_exposure: float = 0.0
    support_burden: float = 0.0
    weak_buyer_reach: float = 0.0
    evidence_staleness: float = 0.0

    def __post_init__(self) -> None:
        for name in PENALTY_WEIGHTS:
            object.__setattr__(self, name, _validate_unit_value(name, getattr(self, name)))

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> "RiskPenalties":
        allowed = {field.name for field in fields(cls)}
        unknown = set(values) - allowed
        if unknown:
            raise ValidationError(
                "unknown risk penalty input(s): "
                + ", ".join(sorted(str(key) for key in unknown))
            )
        return cls(**dict(values))


@dataclass(frozen=True, slots=True)
class MarketVoidScore:
    base_score: float
    penalty_score: float
    final_score: float
    component_points: Mapping[str, float]
    penalty_points: Mapping[str, float]
    eligible_for_advancement: bool
    rejection_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "base_score": round(self.base_score, 2),
            "penalty_score": round(self.penalty_score, 2),
            "final_score": round(self.final_score, 2),
            "component_points": {
                key: round(value, 2) for key, value in self.component_points.items()
            },
            "penalty_points": {
                key: round(value, 2) for key, value in self.penalty_points.items()
            },
            "eligible_for_advancement": self.eligible_for_advancement,
            "rejection_reasons": list(self.rejection_reasons),
            "warnings": list(self.warnings),
        }


def calculate_market_void_score(
    inputs: MarketVoidInput | Mapping[str, Any],
    penalties: RiskPenalties | Mapping[str, Any] | None = None,
) -> MarketVoidScore:
    """Calculate the 100-point score and explicit risk deductions.

    The score is a prioritization signal.  ``eligible_for_advancement`` requires
    both a score at or above ``ADVANCEMENT_THRESHOLD`` and passage of the hard
    rejection and low-competition corroboration gates.
    """

    normalized = inputs if isinstance(inputs, MarketVoidInput) else MarketVoidInput.from_mapping(inputs)
    if penalties is None:
        normalized_penalties = RiskPenalties()
    elif isinstance(penalties, RiskPenalties):
        normalized_penalties = penalties
    else:
        normalized_penalties = RiskPenalties.from_mapping(penalties)

    component_points = {
        name: getattr(normalized, name) * weight for name, weight in COMPONENT_WEIGHTS.items()
    }
    penalty_points = {
        name: getattr(normalized_penalties, name) * weight
        for name, weight in PENALTY_WEIGHTS.items()
    }
    base_score = sum(component_points.values())
    penalty_score = sum(penalty_points.values())
    final_score = max(0.0, min(100.0, base_score - penalty_score))

    rejection_reasons: list[str] = []
    if not normalized.credible_problem_evidence:
        rejection_reasons.append("no credible evidence of a real problem")
    if not normalized.reachable_without_spam:
        rejection_reasons.append("no credible permission-based path to buyers")
    if normalized.meaningful_cash_before_validation:
        rejection_reasons.append("requires meaningful cash before validation")
    if normalized.regulated_or_risky_data:
        rejection_reasons.append("requires regulated activity or risky money/data handling")
    if normalized.mvp_too_large:
        rejection_reasons.append("MVP is too large for a bootstrap experiment")
    if normalized.maintenance_incompatible:
        rejection_reasons.append("maintenance burden conflicts with low-owner-time operation")
    if normalized.unlawful_advantage:
        rejection_reasons.append("the primary advantage depends on unlawful or prohibited conduct")

    warnings: list[str] = []
    if normalized.low_competition and not (
        normalized.strong_demand_signal and normalized.independent_source_count >= 2
    ):
        rejection_reasons.append(
            "low competition lacks a strong demand signal corroborated by two independent sources"
        )
    if final_score < ADVANCEMENT_THRESHOLD:
        rejection_reasons.append(
            f"score below {ADVANCEMENT_THRESHOLD:g} advancement threshold"
        )
    if normalized_penalties.evidence_staleness > 0:
        warnings.append("material evidence is stale and should be revalidated")
    if normalized_penalties.weak_buyer_reach >= 0.5:
        warnings.append("buyer reachability is weak")
    if penalty_score >= 20:
        warnings.append("risk deductions are material")

    return MarketVoidScore(
        base_score=base_score,
        penalty_score=penalty_score,
        final_score=final_score,
        component_points=component_points,
        penalty_points=penalty_points,
        eligible_for_advancement=not rejection_reasons,
        rejection_reasons=tuple(rejection_reasons),
        warnings=tuple(warnings),
    )


def _parse_datetime(value: Any) -> datetime | None:
    if value in {None, ""}:
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime.combine(value, datetime.min.time())
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return datetime.min.replace(tzinfo=timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _is_expired(value: Any, now: datetime) -> bool:
    parsed = _parse_datetime(value)
    # Missing or malformed revalidation dates cannot make evidence evergreen.
    return parsed is None or parsed <= now


def _source_identity(value: Any) -> str:
    """Return a conservative site identity for corroboration counting.

    The standard library has no public-suffix database, so collapse DNS names
    to their final two labels.  This can undercount some independent sites on a
    shared multi-label suffix, which is safer than treating sibling subdomains
    controlled by one publisher as independent corroboration.
    """

    source = str(value or "").strip()
    if not source:
        return ""
    parsed = urlparse(source)
    if parsed.scheme.lower() in {"http", "https"} and parsed.hostname:
        hostname = parsed.hostname.lower().rstrip(".")
        if hostname.startswith("www."):
            hostname = hostname[4:]
        try:
            ipaddress.ip_address(hostname)
        except ValueError:
            labels = [label for label in hostname.split(".") if label]
            return ".".join(labels[-2:]) if len(labels) > 2 else hostname
        return hostname
    return source.casefold()


def score_from_evidence(
    evidence_rows: Iterable[Mapping[str, Any]],
    *,
    overrides: Mapping[str, float] | None = None,
    penalty_overrides: Mapping[str, float] | None = None,
    hard_rejection_flags: Mapping[str, bool] | None = None,
    low_competition: bool = False,
    now: datetime | None = None,
) -> MarketVoidScore:
    """Aggregate timestamped evidence into a score.

    Multiple sources are combined as a confidence- and strength-weighted mean.
    Expired evidence does not contribute positive points and creates a staleness
    penalty.  Explicit overrides remain visible in the stored score payload.
    """

    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    rows = list(evidence_rows)
    active_rows = [row for row in rows if not _is_expired(row.get("expires_at"), current_time)]

    components: dict[str, float] = {}
    for criterion in COMPONENT_WEIGHTS:
        matching = [row for row in active_rows if row.get("criterion") == criterion]
        numerator = 0.0
        denominator = 0.0
        for row in matching:
            strength = EVIDENCE_STRENGTH_WEIGHTS.get(str(row.get("strength", "weak")), 0.0)
            confidence = _validate_unit_value("confidence", row.get("confidence", 0.0))
            rating = _validate_unit_value("rating", row.get("rating", 0.0))
            evidence_weight = strength * confidence
            numerator += rating * evidence_weight
            denominator += evidence_weight
        components[criterion] = numerator / denominator if denominator else 0.0

    for key, value in (overrides or {}).items():
        if key not in COMPONENT_WEIGHTS:
            raise ValidationError(f"unknown score component override: {key}")
        components[key] = _validate_unit_value(key, value)

    risks: dict[str, float] = {}
    for penalty in PENALTY_WEIGHTS:
        criterion = f"risk_{penalty}"
        matching = [row for row in active_rows if row.get("criterion") == criterion]
        if matching:
            # Risks fail conservatively: use the strongest supported rating.
            risks[penalty] = max(
                _validate_unit_value("rating", row.get("rating", 0.0))
                * _validate_unit_value("confidence", row.get("confidence", 0.0))
                for row in matching
            )
        else:
            risks[penalty] = 0.0
    if rows:
        risks["evidence_staleness"] = max(
            risks["evidence_staleness"], (len(rows) - len(active_rows)) / len(rows)
        )
    for key, value in (penalty_overrides or {}).items():
        if key not in PENALTY_WEIGHTS:
            raise ValidationError(f"unknown penalty override: {key}")
        risks[key] = _validate_unit_value(key, value)

    normalized_hard_flags: dict[str, bool] = {}
    for key, value in (hard_rejection_flags or {}).items():
        if key not in HARD_REJECTION_FLAGS:
            raise ValidationError(f"unknown hard rejection flag: {key}")
        if type(value) is not bool:
            raise ValidationError(f"hard rejection flag {key} must be boolean")
        normalized_hard_flags[key] = value

    corroborating_rows = [
        row
        for row in active_rows
        if row.get("criterion") in COMPONENT_WEIGHTS
        and EVIDENCE_STRENGTH_WEIGHTS.get(str(row.get("strength", "weak")), 0.0) > 0
        and _validate_unit_value("confidence", row.get("confidence", 0.0)) >= 0.5
        and _validate_unit_value("rating", row.get("rating", 0.0)) >= 0.3
    ]
    source_count = len(
        {
            identity
            for row in corroborating_rows
            if (identity := _source_identity(row.get("source_uri")))
        }
    )
    strong_demand_signal = any(
        row.get("criterion") in {"need_severity", "economic_commitment"}
        and row.get("strength") == "strong"
        and _validate_unit_value("rating", row.get("rating", 0.0)) >= 0.5
        and _validate_unit_value("confidence", row.get("confidence", 0.0)) >= 0.7
        for row in active_rows
    )
    credible_problem_evidence = any(
        row.get("criterion") in {"need_severity", "economic_commitment"}
        and EVIDENCE_STRENGTH_WEIGHTS.get(str(row.get("strength", "weak")), 0.0) > 0
        and _validate_unit_value("rating", row.get("rating", 0.0)) >= 0.3
        and _validate_unit_value("confidence", row.get("confidence", 0.0)) >= 0.5
        for row in active_rows
    )
    reachable_without_spam = any(
        row.get("criterion") == "reachable_beachhead"
        and EVIDENCE_STRENGTH_WEIGHTS.get(str(row.get("strength", "weak")), 0.0) > 0
        and _validate_unit_value("rating", row.get("rating", 0.0)) >= 0.3
        and _validate_unit_value("confidence", row.get("confidence", 0.0)) >= 0.5
        for row in active_rows
    )

    return calculate_market_void_score(
        MarketVoidInput(
            **components,
            **normalized_hard_flags,
            low_competition=low_competition,
            strong_demand_signal=strong_demand_signal,
            independent_source_count=source_count,
            credible_problem_evidence=credible_problem_evidence,
            reachable_without_spam=reachable_without_spam,
        ),
        RiskPenalties(**risks),
    )


def score_inputs_as_dict(inputs: MarketVoidInput, penalties: RiskPenalties) -> dict[str, Any]:
    """Return JSON-safe inputs for audit and persistence."""

    return {"components": asdict(inputs), "penalties": asdict(penalties)}
