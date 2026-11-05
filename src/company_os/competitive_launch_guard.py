"""Fail-closed competitive-engine precondition for all K.O. venture launches.

This verifies signed, time-limited health attestations.  It does NOT launch,
monitor, source-verify, or independently review the engine by itself.
Production must provision separate protected engine and critic signing keys,
a trusted monitor, private state, and authenticated human release authority.
No secret or customer data belongs in this public repository.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

COMPETITIVE_ENGINE_GATED_ACTIONS = frozenset(
    {
        "launch_business",
        "activate_business",
        "launch_venture",
        "launch_product",
        "activate_product",
        "start_revenue_operations",
        "deploy_authorized",
        "publish_authorized",
        "publish_regulated_claim",
    }
)
# Special engine-only bootstrap action is deliberately NOT in the above set.
# It is still owner-approval required and PAUSE_AUTONOMY blocks it.
COMPETITIVE_ENGINE_BOOTSTRAP_ACTION = "deploy_competitive_engine"

def requires_competitive_engine(action: str) -> bool:
    """Classify launch/publication intent without trusting caller side-effect flags."""
    normalized = action.strip().lower()
    if normalized == COMPETITIVE_ENGINE_BOOTSTRAP_ACTION:
        return False
    return (
        normalized in COMPETITIVE_ENGINE_GATED_ACTIONS
        or normalized.startswith(("launch_", "publish_", "go_live_", "start_revenue_", "deploy_"))
        or normalized in {"start_business", "open_business", "activate_venture"}
    )


REQUIRED_CRITIC_CHECKS = frozenset(
    {
        "source_accuracy",
        "claim_completeness",
        "contradictions",
        "recency",
        "client_fit",
        "compliance",
        "privacy",
        "professional_writing",
        "visual_pages",
        "links_and_citations",
        "numbers_and_tables",
        "scope_and_limits",
    }
)
REQUIRED_LIVE_CHECKS = frozenset(
    {
        "original_sources_verified",
        "competitor_comparisons_completed",
        "independent_critic_passed",
        "privacy_controls_ready",
        "release_controls_ready",
        "audit_chain_healthy",
        "monitor_probe_passed",
        "budget_controls_ready",
    }
)
MAX_HEALTH_AGE = timedelta(minutes=5)
MAX_HEALTH_VALIDITY = timedelta(minutes=10)
MAX_SOURCE_AGE = timedelta(hours=24)
MAX_REVIEW_AGE = timedelta(hours=1)
MAX_ATTESTATION_BYTES = 65_536


@dataclass(frozen=True, slots=True)
class EngineReadiness:
    ready: bool
    reasons: tuple[str, ...]
    checked_at: str
    engine_id: str | None = None
    cycle_id: str | None = None


def _utc_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or len(value) > 40:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None
    try:
        return dt.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        return None


def _no_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate key in readiness document")
        out[key] = value
    return out


def _canonical_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _trusted_key(name: str) -> bytes | None:
    value = os.environ.get(name, "")
    # Minimum 32 UTF-8 bytes; provider must use cryptographically random keys.
    if len(value.encode("utf-8")) < 32:
        return None
    return value.encode("utf-8")


def _valid_signature(secret: bytes, raw: bytes, supplied: Any) -> bool:
    if not isinstance(supplied, str) or len(supplied) != 64:
        return False
    expected = hmac.new(secret, raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, supplied)


def inspect_competitive_readiness(
    repo_root: str | os.PathLike[str] | None = None,
    *,
    now: datetime | None = None,
) -> EngineReadiness:
    """Check signed external monitor/critic records; never create readiness.

    The attestation is not a substitute for a real monitor or independent
    critic. A developer/agent must not generate production signatures merely
    to get a launch approved. This function performs zero network actions.
    """
    instant = (now or datetime.now(timezone.utc))
    if instant.tzinfo is None:
        raise ValueError("now must include an explicit timezone")
    instant = instant.astimezone(timezone.utc)
    checked_at = instant.isoformat()
    reasons: list[str] = []

    engine_key = _trusted_key("KO_COMPETITIVE_ENGINE_HEALTH_KEY")
    critic_key = _trusted_key("KO_COMPETITIVE_CRITIC_HEALTH_KEY")
    if not engine_key or not critic_key or engine_key == critic_key:
        return EngineReadiness(False, ("trusted_separate_signing_keys_unavailable",), checked_at)

    root = Path(repo_root).resolve() if repo_root is not None else Path.cwd().resolve()
    health_path_raw = os.environ.get("KO_COMPETITIVE_READINESS_PATH", "").strip()
    health_path = (
        Path(health_path_raw).expanduser()
        if health_path_raw
        else root / "state" / "competitive_engine" / "readiness.json"
    )
    try:
        # No directory creation, no recovery from missing health, no network fetch.
        if not health_path.is_file() or health_path.stat().st_size > MAX_ATTESTATION_BYTES:
            return EngineReadiness(False, ("health_record_unavailable_or_oversized",), checked_at)
        envelope = json.loads(
            health_path.read_text(encoding="utf-8"),
            object_pairs_hook=_no_duplicate_json_keys,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")),
        )
    except (OSError, UnicodeError, ValueError, TypeError):
        return EngineReadiness(False, ("health_record_invalid",), checked_at)

    if not isinstance(envelope, dict) or set(envelope) != {
        "payload", "engine_signature", "critic_signature"
    }:
        return EngineReadiness(False, ("health_record_schema_invalid",), checked_at)
    payload = envelope.get("payload")
    if not isinstance(payload, dict):
        return EngineReadiness(False, ("health_payload_invalid",), checked_at)
    try:
        signed = _canonical_bytes(payload)
    except (TypeError, ValueError, OverflowError):
        return EngineReadiness(False, ("health_payload_invalid",), checked_at)
    if not _valid_signature(engine_key, signed, envelope["engine_signature"]):
        reasons.append("engine_attestation_signature_invalid")
    if not _valid_signature(critic_key, signed, envelope["critic_signature"]):
        reasons.append("critic_attestation_signature_invalid")
    if reasons:
        return EngineReadiness(False, tuple(reasons), checked_at)

    def nonblank(field: str) -> bool:
        value = payload.get(field)
        return isinstance(value, str) and bool(value.strip()) and len(value) <= 160

    if payload.get("schema_version") != "1.0":
        reasons.append("unsupported_readiness_schema")
    if payload.get("environment") != "production" or payload.get("state") != "live_healthy":
        reasons.append("engine_not_live_in_production")
    for field in ("engine_id", "cycle_id", "revision", "producer_id", "reviewer_id"):
        if not nonblank(field):
            reasons.append("missing_" + field)
    if nonblank("producer_id") and nonblank("reviewer_id") and (
        payload["producer_id"] == payload["reviewer_id"]
    ):
        reasons.append("self_review_not_accepted")

    observed = _utc_timestamp(payload.get("observed_at"))
    expiry = _utc_timestamp(payload.get("expires_at"))
    source_checked = _utc_timestamp(payload.get("sources_verified_at"))
    critic_checked = _utc_timestamp(payload.get("critic_reviewed_at"))
    if observed is None or not (timedelta(seconds=-30) <= instant - observed <= MAX_HEALTH_AGE):
        reasons.append("heartbeat_missing_or_stale")
    if (expiry is None or observed is None or expiry <= instant or
            expiry > observed + MAX_HEALTH_VALIDITY):
        reasons.append("health_expired_or_overlong")
    if source_checked is None or not (
        timedelta(seconds=-30) <= instant - source_checked <= MAX_SOURCE_AGE
    ):
        reasons.append("source_verification_stale")
    if critic_checked is None or not (
        timedelta(seconds=-30) <= instant - critic_checked <= MAX_REVIEW_AGE
    ):
        reasons.append("independent_review_stale")

    checks = payload.get("live_checks")
    if not isinstance(checks, dict) or set(checks) != REQUIRED_LIVE_CHECKS or not all(
        checks[name] is True for name in REQUIRED_LIVE_CHECKS
    ):
        reasons.append("live_mandatory_checks_incomplete")
    critic_checks = payload.get("critic_checks")
    if not isinstance(critic_checks, dict) or set(critic_checks) != REQUIRED_CRITIC_CHECKS or not all(
        critic_checks[name] is True for name in REQUIRED_CRITIC_CHECKS
    ):
        reasons.append("critic_mandatory_checks_incomplete")
    score = payload.get("critic_score")
    if type(score) not in (int, float) or not 9.0 < score <= 10.0:
        reasons.append("critic_score_below_strict_threshold")
    if (type(payload.get("critical_findings_open")) is not int or
            payload["critical_findings_open"] != 0):
        reasons.append("open_or_unknown_critical_findings")
    if (type(payload.get("verified_primary_source_count")) is not int or
            payload["verified_primary_source_count"] < 1):
        reasons.append("no_verified_primary_source")
    if (type(payload.get("completed_comparison_count")) is not int or
            payload["completed_comparison_count"] < 1):
        reasons.append("no_completed_comparison")

    return EngineReadiness(
        ready=not reasons,
        reasons=tuple(reasons),
        checked_at=checked_at,
        engine_id=payload.get("engine_id") if nonblank("engine_id") else None,
        cycle_id=payload.get("cycle_id") if nonblank("cycle_id") else None,
    )
