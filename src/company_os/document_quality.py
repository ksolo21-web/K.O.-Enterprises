"""Deterministic, fail-closed screening; never authorizes publishing."""
import argparse
import json
import re
from datetime import date
from urllib.parse import urlsplit
from pathlib import Path

REVIEW_CHECKS = ("facts", "source_match", "freshness", "contradictions",
                 "client_fit", "legal", "privacy", "tone", "rendered_pages")
SECTIONS = ("summary", "scope", "method", "findings", "countercase",
            "limitations")
PLACEHOLDER = re.compile(r"\b(lorem ipsum|tbd|todo|as an ai language model|guaranteed results)\b|\[(insert|placeholder)[^\]]*\]", re.I)
DIRECTIVE = re.compile(r"^\s*(you (must|should|need to|have to)|we guarantee|(?:buy|sign|hire|fire|invest|submit|stop|avoid)\b)", re.I)
SECRET = re.compile(r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----")


def day(value):
    try:
        return date.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None


def domain(url):
    try:
        p = urlsplit(url)
        return p.hostname.lower() if p.scheme == "https" and p.hostname else ""
    except (ValueError, TypeError):
        return ""


def evaluate(pack, *, today=None):
    today = today or date.today()
    failures = []

    def fail(code, where):
        failures.append({"code": code, "where": where})

    if not isinstance(pack, dict):
        return {"status": "HOLD", "can_publish": False,
                "failures": [{"code": "SCHEMA", "where": "$"}]}

    if pack.get("business_unit") not in ("market_intelligence", "contractor_operations"):
        fail("BUSINESS_UNIT", "business_unit")
    if pack.get("data_class") != "public":
        fail("PRIVATE_DATA", "data_class")
    if not isinstance(pack.get("pack_id"), str) or not pack["pack_id"].strip():
        fail("PACK_ID", "pack_id")
    author = pack.get("author_id")
    if not isinstance(author, str) or not author.strip():
        fail("AUTHOR", "author_id")
    report_day = day(pack.get("as_of"))
    if not report_day or report_day > today or (today - report_day).days > 7:
        fail("STALE_REPORT", "as_of")
    client = pack.get("client_context")
    if not isinstance(client, dict) or any(
        not isinstance(client.get(k), str) or len(client[k].strip()) < 5
        for k in ("sector", "region", "constraints")
    ):
        fail("CLIENT_CONTEXT", "client_context")

    doc = pack.get("document")
    doc = doc if isinstance(doc, dict) else {}
    for key in SECTIONS:
        if not isinstance(doc.get(key), str) or len(doc[key].strip()) < 25:
            fail("DOCUMENT_SECTION", "document." + key)
    if PLACEHOLDER.search(json.dumps({"document": doc, "options": pack.get("options", [])})):
        fail("BOILERPLATE", "document")
    if SECRET.search(json.dumps(pack)):
        fail("POSSIBLE_SECRET", "$")

    sources = pack.get("sources")
    if not isinstance(sources, list) or not sources:
        fail("MISSING_SOURCES", "sources")
        sources = []
    known = {}
    for idx, source in enumerate(sources):
        loc = "sources[" + str(idx) + "]"
        if not isinstance(source, dict):
            fail("BAD_SOURCE", loc)
            continue
        sid = source.get("id")
        if not isinstance(sid, str) or not sid or sid in known:
            fail("SOURCE_ID", loc)
            continue
        known[sid] = source
        if not domain(source.get("url")):
            fail("SOURCE_URL", loc)
        if source.get("kind") not in ("issuer", "original", "first_party", "secondary"):
            fail("SOURCE_KIND", loc)
        if len(str(source.get("publisher", "")).strip()) < 3 or len(str(source.get("excerpt", "")).strip()) < 20:
            fail("SOURCE_TRACE", loc)
        seen = day(source.get("observed_on"))
        if not seen or (report_day and seen > report_day):
            fail("SOURCE_DATE", loc)

    claims = pack.get("claims")
    if not isinstance(claims, list) or not claims:
        fail("MISSING_CLAIMS", "claims")
        claims = []
    claim_ids = set()
    for idx, claim in enumerate(claims):
        loc = "claims[" + str(idx) + "]"
        if not isinstance(claim, dict):
            fail("BAD_CLAIM", loc)
            continue
        cid = claim.get("id")
        if not isinstance(cid, str) or not cid or cid in claim_ids:
            fail("CLAIM_ID", loc)
            continue
        claim_ids.add(cid)
        if len(str(claim.get("text", "")).strip()) < 20:
            fail("CLAIM_TEXT", loc)
        if claim.get("importance") not in ("context", "material", "critical"):
            fail("CLAIM_IMPORTANCE", loc)
        if claim.get("fact_checked") is not True or claim.get("counter_evidence") != "resolved":
            fail("CLAIM_UNCHECKED", loc)
        refs = claim.get("source_ids")
        if not isinstance(refs, list) or not refs:
            refs = []
            fail("MISSING_CITATION", loc)
        cited = []
        for sid in refs:
            if not isinstance(sid, str) or sid not in known:
                fail("BROKEN_CITATION", loc)
            else:
                cited.append(known[sid])
        if claim.get("importance") == "critical":
            if len({domain(x.get("url")) for x in cited} - {""}) < 2:
                fail("CRITICAL_CORROBORATION", loc)
            if not any(x.get("kind") in ("issuer", "original") for x in cited):
                fail("PRIMARY_EVIDENCE", loc)
        if claim.get("topic") == "procurement":
            if not any(x.get("kind") == "issuer" for x in cited):
                fail("OFFICIAL_ISSUER", loc)
        for source in cited:
            seen = day(source.get("observed_on"))
            if not seen or not report_day:
                continue
            age = (report_day - seen).days
            if claim.get("topic") == "procurement" and age > 1:
                fail("STALE_PROCUREMENT", loc)
            elif claim.get("topic") != "procurement" and age > 90:
                fail("STALE_EVIDENCE", loc)

    options = pack.get("options")
    if not isinstance(options, list) or not options:
        fail("NO_OPTIONS", "options")
        options = []
    for idx, option in enumerate(options):
        loc = "options[" + str(idx) + "]"
        if not isinstance(option, dict):
            fail("BAD_OPTION", loc)
            continue
        words = option.get("text")
        if not isinstance(words, str) or len(words.strip()) < 25:
            fail("OPTION_TEXT", loc)
        elif DIRECTIVE.search(words):
            fail("PRESCRIPTIVE_LANGUAGE", loc)
        if len(str(option.get("tradeoff", "")).strip()) < 20:
            fail("OPTION_TRADEOFF", loc)
        refs = option.get("claim_ids")
        if not isinstance(refs, list) or not refs or any(x not in claim_ids for x in refs):
            fail("UNSUPPORTED_OPTION", loc)

    review = pack.get("critic")
    review = review if isinstance(review, dict) else {}
    reviewer = review.get("reviewer_id")
    if not isinstance(reviewer, str) or not reviewer or reviewer == author:
        fail("REVIEWER_NOT_INDEPENDENT", "critic.reviewer_id")
    checked = day(review.get("reviewed_on"))
    if not checked or (report_day and checked < report_day) or checked > today:
        fail("REVIEW_DATE", "critic.reviewed_on")
    checks = review.get("checks")
    if not isinstance(checks, dict) or not all(checks.get(k) is True for k in REVIEW_CHECKS):
        fail("CRITIC_INCOMPLETE", "critic.checks")
    score = review.get("score")
    if isinstance(score, bool) or not isinstance(score, (int, float)) or not (9.0 < score <= 10):
        fail("REVIEW_SCORE", "critic.score")
    if len(str(review.get("evidence_ref", "")).strip()) < 8:
        fail("NO_REVIEW_EVIDENCE", "critic.evidence_ref")

    return {
        "status": "HOLD" if failures else "READY_FOR_OWNER_APPROVAL",
        "can_publish": False,
        "failures": failures,
        "warning": "Declared sources and reviewer identities have NOT been authenticated; a human must check original evidence and approve actual delivery.",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("pack", type=Path)
    p.add_argument("--today", help="ISO date override for replay/testing only")
    a = p.parse_args()
    if a.today and not day(a.today):
        p.error("Invalid ISO date")
    try:
        pack = json.loads(a.pack.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "HOLD", "can_publish": False, "error": str(exc)}))
        return 2
    result = evaluate(pack, today=day(a.today) if a.today else None)
    print(json.dumps(result, indent=2))
    return 2 if result["status"] == "HOLD" else 0


if __name__ == "__main__":
    raise SystemExit(main())
