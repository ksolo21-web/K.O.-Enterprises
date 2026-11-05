# CE-1B — Protected HTTPS Source Retrieval (reviewed code, not a live service)

**Build date:** 2026-11-05  
**Component:** `src/company_os/approved_source_fetch.py`  
**Adversarial tests:** `tests/test_approved_source_fetch.py`  
**Requires:** [CE-1A private provenance ledger](CE1_SOURCE_PROVENANCE.md) and company `policy.enforce_action`  
**Governance:** [Mandatory Competitive Engine Launch Prerequisite](COMPETITIVE_ENGINE_LAUNCH_PREREQUISITE.md)  
**Status:** INTERNAL IMPLEMENTATION ONLY. Genuine live retrieval, issuer authenticity, independent critic and CE-1 milestone approval **NOT VERIFIED**.

## What CE-1B implements

The single-document `fetch_and_capture` operation:

1. Calls the existing company `enforce_action(ActionRequest(action="call_approved_api", external=True))` **before network access**. `PAUSE_AUTONOMY` or missing approval blocks DNS and HTTP. This action is separately governed; a user asking to "continue" is not an external-access authorization.
2. Validates a time-limited **signed, exact-target source permit** (source URL, publisher attribution, origin, rights assertion, source kind, budget, source-permit ID, issuer identity label). The verifier accepts only **Ed25519 schema v2.0** signatures using `KO_SOURCE_PERMIT_PUBLIC_KEY_B64` (base64-encoded 32-byte trusted public key); only a separately governed issuer may retain the private signer. The verifier no longer uses a shared HMAC signing secret. No signing private key belongs in GitHub or the research worker. Permits expire in at most seven days and never expand to a related domain or changed URL. Public-key verification prevents a reader with only the public key from minting a valid permit, but authenticated signer operations, key custody, revocation and a real separate critic still require a protected deployment.
3. Applies CE-1A canonical HTTPS URL and hostname validation; performs one DNS resolution, checks *every* returned IP for public/global routability, then pins a raw socket to the selected numeric IP with original-host TLS SNI and hostname/certificate verification. TLS version >=1.2; normal system trust store. No proxies or alternate transport.
4. Issues one GET and refuses all redirect statuses. A redirect requires separate review and a fresh permit for the exact new URL; there is no automatic redirect following or link crawling.
5. Accepts only explicit UTF-8/ASCII `text/plain` or `text/html`, no compression/ambiguous transfer encoding, with tight `Content-Length` checks, an explicit source-permit body limit **up to 512 KB**, and bounded `read(limit+1)`. PDF, binary files, JavaScript-only pages and annexes require future dedicated review and CE-1C.
6. Rechecks the permit after the HTTPS response, verifies that the bounded excerpt appears in the actual response, stores the digest, TLS peer certificate fingerprint, selected IP and programmatic retrieval provenance using CE-1A's private SQLite event history. Full fetched source bytes are **not** committed to public GitHub.
7. Returns `CaptureReceipt(review_status="HOLD_INDEPENDENT_REVIEW", publication_authorized=False)`. It **never** upgrades a fact, source credibility or business readiness merely because TLS succeeded.

### Intended integration (not authorized to execute under emergency pause)

```python
from pathlib import Path
from company_os.approved_source_fetch import fetch_and_capture
from company_os.source_provenance import SourceLedger

# permit = signed private source-governance record for EXACT target URL;
# approval = matching, current company-OS explicit external-action approval.
# Neither is supplied by this repository or approved by this example.
with SourceLedger(Path(".")) as ledger:
    receipt = fetch_and_capture(
        ledger=ledger,
        permit=permit,
        approval=approval,
        document_id="approved-document-id",
        evidence_excerpt="Exact 16-240 character quotation from the original page.",
        repo_root=Path("."),
    )
    # receipt proves bounded transport/source capture; all decisions remain HOLD.
```

**Do not put credentials, private client data, full copyrighted records, permit-signing secrets or unapproved automated workers in a public repository.**


**Additional tested control:** `KO_SOURCE_APPROVED_HOSTS` must enumerate trusted exact hostnames separately from the signed URL permit. The DNS filter also excludes multicast and reserved addresses. Test results do not prove a live authorized issuer fetch.

## Verified vs unverified (critical distinction)

**Offline tested:** refusal of absent approval and active pause *before DNS*, exact URL and permit-signature validation, expiration and size checks, mixed public/private DNS rejection, IP pinning, host TLS SNI with certificate checks, redirect and bad-content rejection, header ambiguity controls, private ledger integration and held review state. Network responses and certificates in these tests are **synthetic mocks**. Source content correctness is not proven.

**Not yet tested or built:** live source TLS retrieval on an approved host; separate real source signing identity; verified compliance with each site's use conditions and robots policies; DNS lookup deadlines, true network reliability, connection pooling, per-domain rate limits and auditing; signed source-policy revocation; retained exact authorized page snapshots for a genuine critic; HTTP dates or external certified time; automatic monitoring; complete PDFs/attachments/addenda; independent original-source review and semantic evidence accuracy; private encrypted storage; production health and release controller.

**Important security boundaries:** The signed policy is **not** sufficient by itself: runtime company approval still applies, and the private signing key must remain outside the fetch worker on protected separate governance infrastructure; signing authorization, rotation and revocation still need production verification. The certificate fingerprint records *which* TLS peer we spoke to but not whether its statements are accurate, current, applicable to the client or independently corroborated. An exact-host signed policy only defines a proposed lawful scope; terms and legal access must be established outside software. Other applications bypassing the company OS remain a separate CE-4 blocker.

## Independent review and release policy

- Every fetched source is kept on `HOLD_INDEPENDENT_REVIEW`.
- Original URLs, issuer documents, procurement addenda, customer-specific eligibility, contradictory claims and source freshness require separate analysis. No false "verified" stamp.
- Always retain `PAUSE_AUTONOMY` and `PRODUCTION_RELEASE_CONTROLLER_CERTIFIED=False`.
- A genuine independent critic must challenge both the source and interpretation, including live TLS/transport behavior, before CE-1 production acceptance.
- Keep GitHub Issues #32 and #38 open: passing offline tests does **not** complete CE-1 or approve any venture launch.

## Next executable engineering actions

1. **CE-1B2:** Independent signing authority and exact-URL permit registry with revocation and protected audit, plus bounded per-issuer rate limits, actual authorized live-fetch evidence, safe DNS deadlines and real TLS integration tests on an approved host.
2. **CE-1C:** Legal PDF/attachment/addendum capture and related-record completeness with corrected deadlines, mandatory events, independent-source comparisons and issuer package verification.
3. **CE-1D:** Tie claim/digest lineage into full competitor battlecards and independent critic audits; flagged unsupported weaknesses must never appear as factual accusations.
4. **CE-2/3:** Supervised private hosting, durable workers, authenticated separate reviewer, health probes and incident controls. No automatic schedules while the pause is active.

### Reusable checkpoint

On resumption, read this document and `CE1_SOURCE_PROVENANCE.md`, inspect relevant merged PR and CI evidence, verify source modules on `main`, examine Issues #32/#38, and continue at the earliest unaccepted critical-path item without deleting previous implementation. This checkpoint is **not** itself a QA approval.
