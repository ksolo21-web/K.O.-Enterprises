# CE-1A — Source Provenance and Change Ledger (Offline)

**State (2026-11-05):** First CE-1 engineering increment, **internal-only**, not CE-1 completion.  
**Implementation:** `src/company_os/source_provenance.py`  
**Tests:** `tests/test_source_provenance.py`  
**Upstream:** [Competitive Engine Launch Prerequisite](COMPETITIVE_ENGINE_LAUNCH_PREREQUISITE.md), [Quality System](../ventures/market-intelligence/QUALITY_SYSTEM.md)  
**Tracking:** [Issue #38](https://github.com/ksolo21-web/K.O.-Enterprises/issues/38) and [Issue #32](https://github.com/ksolo21-web/K.O.-Enterprises/issues/32).

## Actual capabilities implemented in CE-1A

1. **Exact-host HTTPS provenance policy.** Records only explicitly allowlisted origin hosts; rejects URL user-info, unapproved domains/subdomains, IP literals, local hostnames, nonstandard ports, fragments, suspicious credential-bearing query keys, and HTTP.
2. **Offline lawful snapshot ingestion.** Analyst or future independently approved connector supplies local UTF-8 text/HTML bytes. The module does **not** make network requests, follow redirects or bypass access controls. Full PDF parsing and live procurement-portal download are not yet implemented.
3. **Visible-text excerpt check.** Normalizes HTML/text, ignores script/style content, requires a bounded excerpt to occur exactly once in the actual supplied bytes and records its normalized character offset. This proves only consistency **within the supplied snapshot**, not original issuer authenticity or the truth of the interpretation.
4. **Provenance and change tracking.** Records a timestamp, source/doc/origin identity, publisher, exact HTTPS URL, acquisition method/reference, rights basis, content and excerpt SHA-256 digests and claimed document completeness. Timestamps cannot be silently backdated, and changing the same document's source identity requires explicit reconciliation.
5. **Append-only local SQLite event chain.** Records snapshots and separately registered claim interpretations with SHA-256 hash links, immutable SQLite triggers and integrity audit. An ordinary accidental edit is detectable. A privileged actor rewriting the entire chain could forge it; **there is no externally anchored audit record or cryptographic source authentication yet**.
6. **Claim-level review holds.** Claims bind to recorded quotation snippets, retain analyst reasoning and are always `HOLD_INDEPENDENT_REVIEW`. Records identify superseded sources, stale observations, incomplete snapshot assertions, conflicting values, company self-reports and repeated claims derived from one original source (not independent corroboration).
7. **Privacy boundary.** Does not save full copied source content; retains at most 240 characters of an operator-supplied excerpt per snapshot plus metadata in `state/competitive_engine/provenance.sqlite3`. State and SQLite files are Git-ignored, with restricted local POSIX file modes. **No personal, proprietary, copyrighted full-text or client source material in public GitHub.**
8. **Fail-closed internal CLI.** Captures approved local documents, views source/claim hold states, and audits chain integrity. No publish/send/outreach/auto-fetch mode.

## Example: operator-controlled LOCAL capture

Only after lawfully obtaining an original public HTML/text snapshot, use:

```bash
# The full UTF-8 HTML file must already exist in an authorized local location.
# This is NOT a command to download, scrape, impersonate or auto-publish.
python -m company_os.source_provenance --repo-root . capture \
  --document-id detroit-supply-schedule \
  --url https://detroitmi.gov/departments/office-chief-financial-officer/ocfo-divisions/office-contracting-and-procurement/detroit-supply-schedule-program \
  --allow-host detroitmi.gov \
  --publisher "City of Detroit" \
  --title "Detroit Supply Schedule Program" \
  --origin-id detroit-ocp \
  --source-kind issuer_primary \
  --acquisition-method operator_supplied \
  --acquisition-reference "internal-observation-record-2026-11-05" \
  --rights-basis public_access \
  --observed-at 2026-11-05T13:00:00+00:00 \
  --media-type text/html \
  --source-file /approved/private/snapshot.html \
  --evidence-excerpt "Janitorial/Custodial Services (Schedule 2) and Guard Services (Schedule 3) RFQQs are open only to Detroit-certified businesses."
```

The timestamp is illustrative; actual operation must use the **real observation time**, not reuse the example. `--complete-document` can be set only when the analyst truly reviewed the entire source; it remains an **unverified operator assertion**, not final publication authority. The URL is exact-publisher metadata; the module does not certify the host's server or anything outside the supplied bytes.

```bash
python -m company_os.source_provenance --repo-root . status
python -m company_os.source_provenance --repo-root . audit
python -m unittest discover -s tests -p 'test_source_provenance.py' -v
```

### Concrete original-source counterexample to an unqualified bid alert

An original **City of Detroit Supply Schedule Program** page examined on November 5, 2026 describes Schedule 2 janitorial and Schedule 3 guard services as limited to Detroit-certified businesses. It also lists a distinct current program RFQQ number. Reference:
https://detroitmi.gov/departments/office-chief-financial-officer/ocfo-divisions/office-contracting-and-procurement/detroit-supply-schedule-program

A separate older City of Detroit RFQQ page, published in 2023, displays an overall long-term close date and **2025 quarterly response deadlines**. Those historic dates must not be interpreted as current 2026 bid deadlines without examining the actual live portal and all addenda:
https://detroitmi.gov/news/detroit-supply-schedule-rfqq-1847953-2-janitorialcustodial-services

**Research treatment:** The first page supports a bounded *reported program restriction*, **not** a determination that a specific customer qualifies, that the portal is accepting a particular new submission, that its terms did not change, or that the complete bid package was examined. Record a partial snapshot / unknown client qualifications as `HOLD`. Tests include a short extract of the original webpage (not a false full capture). This is useful training data, **not a client report**.

## Security and correctness limitations (must not be silently reclassified)

- **No authenticated collection.** An operator may submit altered bytes or lie about source identity, rights or completeness. Future verified adapter must authenticate actual lawful retrieval, origin, TLS, redirect chain, IP/DNS constraints, publisher, availability and timing.
- **No automatic live watch.** Source change detection requires new operator-provided snapshots. GitHub Actions tests the code but does not run an unattended source-ingestion service.
- **No complete PDF/attachment review.** Procurement solicitations often require full PDFs, annexes, addenda, mandatory pre-bid events and eligibility review; a public HTML page is only a start.
- **No semantic truth engine.** Exact quotation proves occurrence in a local snapshot, not that an analyst's inference is correct; conflict detection compares explicitly structured values, and incomplete/missing opposing evidence may still exist.
- **No strong adversarial storage guarantees.** SQLite event hash links and triggers do not prevent a privileged database rewrite. Operational audit anchoring, signing, private backups and user authentication remain pending.
- **No independent reviewer execution.** No produced result may be labeled independently reviewed; a future truly separate reviewer must inspect actual source material and record a digest-bound evaluation.
- **No release:** `PAUSE_AUTONOMY` remains present, and `PRODUCTION_RELEASE_CONTROLLER_CERTIFIED=False` prevents any K.O. business launch. Source capture does not count as fulfilling CE-1, CE-3, CE-4 or CE-5.

## Next executable engineering tasks

1. **CE-1B — Verified protected fetch adapter:** allow only issuer-approved HTTPS targets; enforce terms/rate/size bounds, DNS rebinding/SSRF protection, zero redirects unless each target reverified, TLS verification, content-type validation and a preserved authenticated retrieval trail. Do not attempt this as a live background job until the company explicitly authorizes its environment and access.
2. **CE-1C — Full document and addendum processing:** lawful PDF extraction, content-level provenance, linkage from notice to every attachment and revision, expiration and mandatory-event checks.
3. **CE-1D — Critic/evidence bridge:** reconcile claim records with the existing document-quality packs and market-intelligence competitor battlecard, require actually inspected original sources, independently challenge analyst reasoning and compare conflicting editions.
4. **M2/CE-2 — Persistent secure worker execution:** operational queue, idempotency, bounded concurrency, retry/cost tracking and secure private state; no false claim that GitHub CI is permanent hosting.

### Quality checkpoint

For this increment, do not mark full CE-1 complete until real authorized source authenticity, complete procurement package tests, opposing-evidence review, an independent reviewer, and reproducible production evidence exist. Keep Issues #32 and #38 open. Customer delivery and business launches remain blocked.

**Review type:** Internal source-code and CI review only. No genuine independent critic available on this internal implementation.
