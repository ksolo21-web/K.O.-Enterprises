"""CE-1F: offline evidence-bounded competitor comparison and counterevidence.

This evaluator performs no browsing, customer contact, signing, payments,
production monitoring, publication or release. Every source/competitor/buyer
claim is OPERATOR-SUPPLIED; apparent corroboration is NOT independently
authenticated. All complete internal results are HOLD, never certified facts.

The check is useful because it rejects mismatched market comparators,
unsupported weaknesses, missing counterexamples, invented paid demand, stale
sources, contradictions and financially unsupported advantage claims.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .source_provenance import EvidenceError, validate_source_url

MAX_DOSSIER_BYTES = 250_000
MAX_SOURCES = 80
MAX_CLAIMS = 120
MAX_ALTERNATIVES = 12
MAX_ADVANTAGES = 3
_ID = re.compile(r"^[a-z][a-z0-9_-]{2,79}$")
_SHA = re.compile(r"^[a-f0-9]{64}$")
_SOURCE_KEYS = frozenset({
    "id", "publisher", "origin_id", "url", "observed_at", "sha256",
    "kind", "grade", "rights_basis", "excerpt", "capture_type",
})
_SOURCE_KEYS_V11 = _SOURCE_KEYS | frozenset({"applies_to_alternative_id"})
_CLAIM_KEYS = frozenset({
    "id", "text", "source_ids", "counter_source_ids",
    "classification", "materiality", "fact_key", "observed_value", "limitations",
})
_CLAIM_KEYS_V11 = _CLAIM_KEYS | frozenset({"applies_to_alternative_id"})
_ALTERNATIVE_KEYS = frozenset({
    "id", "name", "offering_tier", "buyer_segment", "geography",
    "strength_claim_ids", "weakness_claim_ids",
})
_ADVANTAGE_KEYS = frozenset({
    "id", "buyer_outcome", "compared_alternative_ids", "support_claim_ids",
    "contrary_claim_ids", "expected_price_cents", "estimated_delivery_cost_cents",
    "buyer_payment_state", "buyer_payment_evidence_ids", "switching_friction",
})
_ROOT_KEYS = frozenset({
    "schema_version", "dossier_id", "venture_id", "author_id", "prepared_at",
    "buyer_segment", "buyer_problem", "geography", "sources", "claims",
    "alternatives", "advantages", "limitations",
})
_ALLOWED_GRADES = frozenset({"A", "B", "C", "D"})
_SOURCE_KINDS = frozenset({"issuer_original", "vendor_original", "buyer_firsthand", "secondary"})
_MATERIALITY = frozenset({"standard", "critical", "deadline", "safety", "financial"})
_CLASSIFICATIONS = frozenset({"strength", "weakness", "buyer_value", "contrary", "cost"})
_PAYMENT_STATES = frozenset({"untested", "stated_interest", "paid_pilot_reported"})
_GRADE_ORDER = {"A": 4, "B": 3, "C": 2, "D": 1}


def canonical(obj: Any) -> bytes:
    try:
        blob = json.dumps(
            obj, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, OverflowError) as exc:
        raise EvidenceError("competitive dossier is not canonical JSON") from exc
    if len(blob) > MAX_DOSSIER_BYTES:
        raise EvidenceError("competitive dossier exceeds reviewed size limit")
    return blob


def _id(v: Any, name: str) -> str:
    if not isinstance(v, str) or not _ID.fullmatch(v):
        raise EvidenceError("invalid " + name)
    return v


def _description(v: Any, name: str, *, maximum: int = 500) -> str:
    if (not isinstance(v, str) or not v.strip() or len(v) > maximum
            or any(ord(c) < 32 or ord(c) == 127 for c in v)):
        raise EvidenceError("missing/unsafe " + name)
    return v


def _date(v: Any, name: str) -> datetime:
    if not isinstance(v, str) or len(v) > 48:
        raise EvidenceError("invalid " + name)
    try:
        result = datetime.fromisoformat(v.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceError("invalid " + name) from exc
    if result.tzinfo is None:
        raise EvidenceError("timezone required for " + name)
    return result.astimezone(timezone.utc)


def _ids(values: Any, name: str, *, minimum: int = 0, maximum: int = 30) -> list[str]:
    if (not isinstance(values, list) or not minimum <= len(values) <= maximum
            or any(not isinstance(x, str) or not _ID.fullmatch(x) for x in values)
            or len(values) != len(set(values))):
        raise EvidenceError("duplicate, missing or invalid " + name)
    return values


def _map(items: Any, fields: frozenset[str], name: str, cap: int) -> dict[str, dict[str, Any]]:
    if not isinstance(items, list) or not 1 <= len(items) <= cap:
        raise EvidenceError("missing or excessive " + name)
    output: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict) or set(item) != fields:
            raise EvidenceError("invalid " + name + " record fields")
        ident = _id(item["id"], name + " id")
        if ident in output:
            raise EvidenceError("duplicate " + name + " identifier")
        output[ident] = item
    return output


def _hosts() -> tuple[str, ...]:
    raw = __import__("os").environ.get("KO_SOURCE_APPROVED_HOSTS", "")
    hosts = tuple(x.strip() for x in raw.split(","))
    if (not raw or len(raw) > 2048 or not 1 <= len(hosts) <= 32
            or len(set(hosts)) != len(hosts)
            or any(not host or host != host.lower() for host in hosts)):
        raise EvidenceError("approved source-host registry unavailable or invalid")
    return hosts


def assess_competitive_dossier(
    dossier: Any, *, now: datetime | None = None,
) -> dict[str, Any]:
    """Validate an internally compiled dossier; never return release authority.

    BLOCK means structurally defective / unsupported required assertions.
    HOLD means internally coherent but sources and paid-value claims still
    require a genuinely independent original-record and buyer review.
    """
    moment = now if now is not None else datetime.now(timezone.utc)
    if moment.tzinfo is None:
        return _blocked("assessment clock must include timezone")
    moment = moment.astimezone(timezone.utc)
    try:
        return _assess(dossier, moment)
    except (EvidenceError, KeyError, TypeError, ValueError, OverflowError) as exc:
        return _blocked(str(exc))


def _blocked(reason: str) -> dict[str, Any]:
    return {
        "status": "BLOCK", "publication_authorized": False,
        "original_sources_independently_authenticated": False,
        "independent_critic_approved": False, "issues": [reason[:240]],
    }


def _assess(dossier: Any, moment: datetime) -> dict[str, Any]:
    if not isinstance(dossier, dict) or set(dossier) != _ROOT_KEYS:
        raise EvidenceError("competitive dossier required fields missing or unexpected")
    digest = hashlib.sha256(canonical(dossier)).hexdigest()
    if dossier["schema_version"] not in ("1.0", "1.1"):
        raise EvidenceError("competitive dossier schema unsupported")
    attributed = dossier["schema_version"] == "1.1"
    for k in ("dossier_id", "venture_id", "author_id"):
        _id(dossier[k], k)
    for k in ("buyer_segment", "buyer_problem", "geography", "limitations"):
        _description(dossier[k], k)
    prepared = _date(dossier["prepared_at"], "prepared_at")
    if not timedelta(minutes=-2) <= moment - prepared <= timedelta(days=1):
        raise EvidenceError("competitive dossier time is future or stale")
    sources = _map(dossier["sources"], _SOURCE_KEYS_V11 if attributed else _SOURCE_KEYS,
                   "source", MAX_SOURCES)
    claims = _map(dossier["claims"], _CLAIM_KEYS_V11 if attributed else _CLAIM_KEYS,
                  "claim", MAX_CLAIMS)
    alternatives = _map(dossier["alternatives"], _ALTERNATIVE_KEYS,
                        "alternative", MAX_ALTERNATIVES)
    advantages = _map(dossier["advantages"], _ADVANTAGE_KEYS,
                      "advantage", MAX_ADVANTAGES)
    if len(alternatives) < 3:
        raise EvidenceError("fewer than three comparable alternatives")
    hosts = _hosts()

    source_meta: dict[str, dict[str, Any]] = {}
    for sid, src in sources.items():
        _description(src["publisher"], "publisher")
        origin = _id(src["origin_id"], "original source origin")
        if src["kind"] not in _SOURCE_KINDS or src["grade"] not in _ALLOWED_GRADES:
            raise EvidenceError("unsupported evidence kind or grade")
        if src["capture_type"] not in ("operator_supplied", "local_staging_receipt"):
            raise EvidenceError("source falsely claims authenticated transport")
        if src["rights_basis"] not in ("public_access", "owner_authorized", "quoted_excerpt"):
            raise EvidenceError("source retrieval rights not established")
        if not isinstance(src["sha256"], str) or not _SHA.fullmatch(src["sha256"]):
            raise EvidenceError("source original byte digest invalid")
        url = src["url"]
        if not isinstance(url, str) or validate_source_url(url, hosts) != url:
            raise EvidenceError("source URL is not an exact approved HTTPS original")
        excerpt = _description(src["excerpt"], "source excerpt", maximum=1200)
        if len(excerpt.split()) < 3:
            raise EvidenceError("source excerpt too short to contextualize")
        observed = _date(src["observed_at"], "source observed_at")
        age = moment - observed
        if not timedelta(minutes=-2) <= age <= timedelta(days=30):
            raise EvidenceError("source is future or older than thirty days")
        subject = None
        if attributed:
            subject = src["applies_to_alternative_id"]
            if subject is not None:
                _id(subject, "source comparator subject")
                if subject not in alternatives:
                    raise EvidenceError("source refers to missing comparator subject")
        source_meta[sid] = {
            "subject": subject,
            "origin": origin, "grade": src["grade"], "age": age,
            "observed": observed, "kind": src["kind"], "url": url,
        }

    issues: list[str] = []
    if not attributed:
        # Historical v1.0 packs lack exact comparator/source subject binding.
        # Do not silently treat their three competitor rows as validated.
        issues.append("legacy_comparator_attribution_unverified")
    evidence_origins: set[str] = set()
    contradiction_groups: dict[str, set[str]] = {}
    for cid, claim in claims.items():
        _description(claim["text"], "claim")
        _description(claim["limitations"], "claim scope", maximum=400)
        linked = _ids(claim["source_ids"], "claim sources", minimum=1)
        contrary = _ids(claim["counter_source_ids"], "counterevidence", maximum=30)
        if set(linked) & set(contrary):
            raise EvidenceError("same source cannot count as both support and counterevidence")
        if not set(linked + contrary) <= set(sources):
            raise EvidenceError("claim citation references unknown source")
        if claim["classification"] not in _CLASSIFICATIONS or claim["materiality"] not in _MATERIALITY:
            raise EvidenceError("claim classification or materiality not permitted")
        if attributed:
            subject = claim["applies_to_alternative_id"]
            if subject is not None:
                _id(subject, "claim comparator subject")
                if subject not in alternatives:
                    raise EvidenceError("claim refers to missing comparator subject")
            if claim["classification"] in ("strength", "weakness"):
                if subject is None:
                    raise EvidenceError("competitor claim must name one comparator")
                if any(source_meta[sid]["subject"] != subject for sid in linked + contrary):
                    raise EvidenceError("competitor claim source attribution disagrees")
                if (claim["classification"] == "strength" and not any(
                    source_meta[sid]["kind"] == "vendor_original" for sid in linked
                )):
                    raise EvidenceError("competitor strength lacks vendor-original evidence")
        key = _id(claim["fact_key"], "claim comparable fact key")
        value = _description(claim["observed_value"], "comparable observed value", maximum=160)
        contradiction_groups.setdefault(key, set()).add(value.casefold().strip())
        if claim["materiality"] in {"deadline", "safety", "financial", "critical"}:
            if not any(source_meta[sid]["kind"] in {
                "issuer_original", "vendor_original", "buyer_firsthand"
            } for sid in linked):
                raise EvidenceError("material claim missing a stated original/firsthand source")
            if any(source_meta[sid]["age"] > timedelta(days=1) for sid in linked):
                issues.append("material_claim_source_older_than_one_day:" + cid)
        if claim["classification"] == "weakness":
            independent_origins = {source_meta[sid]["origin"] for sid in linked}
            if len(independent_origins) < 2:
                issues.append("weakness_lacks_independent_corrob:" + cid)
            if not contrary:
                issues.append("weakness_missing_counterevidence:" + cid)
            if any(source_meta[sid]["grade"] == "D" for sid in linked):
                issues.append("hypothesis_used_to_assert_competitor_weakness:" + cid)
        if claim["classification"] != "contrary" and any(
            source_meta[sid]["grade"] == "D" for sid in linked
        ):
            issues.append("unverified_hypothesis_support:" + cid)
        for sid in linked:
            evidence_origins.add(source_meta[sid]["origin"])
    for key, values in contradiction_groups.items():
        if len(values) > 1:
            issues.append("contradictory_unreconciled_values:" + key)

    alternative_names: set[str] = set()
    all_strengths: set[str] = set()
    all_weaknesses: set[str] = set()
    for aid, competitor in alternatives.items():
        for key in ("name", "offering_tier", "buyer_segment", "geography"):
            _description(competitor[key], key)
        normalized_name = competitor["name"].casefold().strip()
        if normalized_name in alternative_names:
            raise EvidenceError("duplicate competitor or alternative")
        alternative_names.add(normalized_name)
        if (competitor["buyer_segment"] != dossier["buyer_segment"]
                or competitor["geography"] != dossier["geography"]):
            issues.append("noncomparable_competitor_scope:" + aid)
        strengths = _ids(competitor["strength_claim_ids"], "strength claims", minimum=1)
        weaknesses = _ids(competitor["weakness_claim_ids"], "weakness claims")
        if not set(strengths + weaknesses) <= set(claims):
            raise EvidenceError("competitor comparison references unknown claim")
        if any(claims[x]["classification"] != "strength" for x in strengths):
            raise EvidenceError("incumbent strength must cite a strength claim")
        if any(claims[x]["classification"] != "weakness" for x in weaknesses):
            raise EvidenceError("competitor weakness must cite a weakness claim")
        if attributed and any(
            claims[x]["applies_to_alternative_id"] != aid for x in strengths + weaknesses
        ):
            raise EvidenceError("competitor cited another comparator's claim")
        all_strengths.update(strengths)
        all_weaknesses.update(weaknesses)

    any_paid_signal = False
    for vid, advantage in advantages.items():
        _description(advantage["buyer_outcome"], "buyer-valued outcome")
        _description(advantage["switching_friction"], "switching friction")
        comparators = _ids(advantage["compared_alternative_ids"],
                           "advantage comparators", minimum=1)
        if not set(comparators) <= set(alternatives):
            raise EvidenceError("proposed advantage cites unknown competitor")
        support = _ids(advantage["support_claim_ids"], "advantage supporting claims", minimum=1)
        contrary = _ids(advantage["contrary_claim_ids"], "advantage contrary claims")
        buyer_sources = _ids(
            advantage["buyer_payment_evidence_ids"], "buyer/payment evidence",
        )
        if not set(support + contrary) <= set(claims) or not set(buyer_sources) <= set(sources):
            raise EvidenceError("advantage evidence points to unknown claim or source")
        for field in ("expected_price_cents", "estimated_delivery_cost_cents"):
            if type(advantage[field]) is not int or not 0 <= advantage[field] <= 10_000_000:
                raise EvidenceError("advantage monetary inputs require bounded integer cents")
        if advantage["estimated_delivery_cost_cents"] > advantage["expected_price_cents"]:
            issues.append("negative_contribution_margin_hypothesis:" + vid)
        if advantage["buyer_payment_state"] not in _PAYMENT_STATES:
            raise EvidenceError("buyer payment state unsupported")
        if advantage["buyer_payment_state"] == "paid_pilot_reported":
            if not buyer_sources or not any(
                source_meta[x]["kind"] == "buyer_firsthand" for x in buyer_sources
            ):
                issues.append("reported_paid_pilot_without_firsthand_evidence:" + vid)
            else:
                any_paid_signal = True
        if not contrary:
            issues.append("advantage_missing_disconfirming_test:" + vid)
    if not all_strengths:
        issues.append("missing_incumbent_strengths")
    if not all_weaknesses:
        issues.append("missing_weakness_investigation")
    if not any_paid_signal:
        issues.append("no_paid_pilot_independently_authenticated")

    return {
        "status": ("BLOCK" if any(
            issue.startswith(("contradictory_unreconciled", "noncomparable_competitor",
                              "negative_contribution_margin", "weakness_lacks_independent",
                              "weakness_missing_counterevidence",
                              "hypothesis_used_to_assert", "unverified_hypothesis_support"))
            for issue in issues
        ) else "HOLD_INDEPENDENT_SOURCE_BUYER_AND_CRITIC_REVIEW"),
        "dossier_sha256": digest,
        "venture_id": dossier["venture_id"],
        "dossier_id": dossier["dossier_id"],
        "source_count": len(sources),
        "claim_count": len(claims),
        "alternatives_compared": len(alternatives),
        "advantage_hypotheses": len(advantages),
        "distinct_operator_reported_origins": len(evidence_origins),
        "issues": sorted(set(issues)),
        "original_sources_independently_authenticated": False,
        "paid_demand_independently_verified": False,
        "independent_critic_approved": False,
        "publication_authorized": False,
        "limits": [
            "Operator assertions and synthetic fixtures do not establish original-source truth",
            "Competing source origins can be controlled by the same publisher; provenance must be reviewed",
            "Weakness evidence, buyer demand and prices require independent real-world review",
            "A held dossier is not approval to launch, quote, solicit or publish",
        ],
    }


def evaluate_file(
    path: Path | str, *, now: datetime | None = None,
) -> dict[str, Any]:
    candidate = Path(path)
    try:
        if candidate.is_symlink() or not candidate.is_file():
            return _blocked("dossier file missing or symbolic link")
        if not 32 <= candidate.stat().st_size <= MAX_DOSSIER_BYTES:
            return _blocked("dossier file exceeds size policy")
        def unique(pairs):
            result = {}
            for k, v in pairs:
                if k in result:
                    raise EvidenceError("duplicate dossier JSON field")
                result[k] = v
            return result
        content = json.loads(
            candidate.read_text(encoding="utf-8"), object_pairs_hook=unique,
            parse_constant=lambda _: (_ for _ in ()).throw(
                EvidenceError("nonfinite dossier number")),
        )
        return assess_competitive_dossier(content, now=now)
    except (OSError, UnicodeError, ValueError, EvidenceError, OverflowError) as exc:
        return _blocked(str(exc))


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="K.O. offline competitor evidence check")
    parser.add_argument("dossier", help="local private/synthetic JSON input")
    args = parser.parse_args()
    report = evaluate_file(args.dossier)
    print(json.dumps(report, sort_keys=True))
    return 2 if report["status"] == "BLOCK" else 1  # HOLD is NOT release permission


if __name__ == "__main__":
    raise SystemExit(main())
