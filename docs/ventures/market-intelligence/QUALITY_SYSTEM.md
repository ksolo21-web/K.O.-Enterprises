# K.O. Enterprises — Evidence & Document Critic System v1

**State:** internal preflight prototype. No customer publication, automatic sending, external scraping, paid API calls, or credential access enabled. The root `PAUSE_AUTONOMY` file remains in force. All current customer and revenue claims remain unverified unless independently evidenced.

## Business scope

This common quality gate covers the **K.O. Market Intelligence** and **Contractor Operations Desk** business lines. It is intentionally *additive* to the company OS, `CORPORATE_CONSTITUTION.md`, and `CEO_APPROVAL_POLICY.md`. Passing this gate never overrides company governance, customer approval, or legal and security review.

### Defensible selling proposition

K.O. aims to sell **client-specific, decision-grade, traceable intelligence**, not recycled articles, unreviewed AI summaries, or page counts. A well-grounded no-go finding can be more valuable than a long list of inappropriate opportunities. This positioning is a hypothesis until paid clients and outcomes validate it.

Differentiators to test: (1) every material fact mapped to inspectable evidence, (2) original issuer/source reviews with counterevidence and date checks, (3) client's real eligibility and opportunity fit, (4) separate review and change-sensitive approval, (5) explicit limitations and conditional options, (6) premium editorial/visual standards, (7) correction log after publication.

## Four-stage production chain

1. **Analyst / builder** — state client question and limits, gather permitted public/or client-authorized records, record research date, cite original records, distinguish facts/inference/unknowns. For sourced statements capture short supporting excerpts with hashes and location/reference; a hash only verifies the excerpt did not change, *not* that the issuer actually said it. Never copy entire copyrighted resources into public GitHub.
2. **Structured evidence gate** — run `python -m company_os.document_quality /secure/path/to/pack`. The gate validates source records, dates, excerpt fingerprints, source access, claim mapping, counterevidence attestations, opportunity eligibility, document hashes, PDF framing, dangerous text patterns, and critic digest. It blocks incomplete cases. All important assertions must be registered as claims; an independent reviewer must separately check for *unregistered* claims and inaccurate interpretations.
3. **Independent critic** — a genuinely distinct qualified reviewer (human or separately executed review worker) checks the complete original sources, calculations, client assumptions, contradictions, accuracy, grammar, formatting, rendered PDF pages, links, safety/compliance, and residual risks. Reviewer must score **strictly above 9.0/10 with all twelve named checks passing**. The reviewer signs an attestation for the exact manifest payload digest. A revised pack invalidates that digest. **This module cannot authenticate a self-asserted reviewer ID, verify URLs online, detect every unsupported claim, or establish professional/legal competence.** An authenticated reviewer identity and evidence of real original-record inspection are mandatory outside this code for live client use; no pretended separate critic.
4. **Release authority** — separate authenticated company authority, approved client scope, security controls, final date check, and a supported sending channel. This gate returns `PASS_REVIEWED_NOT_AUTHORIZED`, **never** `PUBLISHED` or `APPROVED_TO_SEND`. `publication_authorization` must remain `false` in the manifest. `PAUSE_AUTONOMY` still blocks all external operations; no CI workflow should bypass it.

## Manifest format

Each pack directory includes a `manifest.json` plus its deliverables. Required essentials:

- `schema_version: "1.0"`; `business_line: "market_intelligence"` or `"contractor_operations"`; `output_type: "test_fixture" | "public_demo" | "client_delivery"`; `classification: "public_demo" | "client_confidential"`.
- `pack_id`, `title`, `author`, `scope`, `limitations`, `prepared_at` (ISO date), `publication_authorization: false`.
- `sources[]`: `id`, `title`, `publisher`, `type` (primary/secondary/client_provided), `url` (HTTPS except client-provided), `file_reference` for private documents, `record_reference`, `evidence_excerpt` (short and lawful), `excerpt_sha256`, `verification_method`, `checked_at`, `access: complete`, `verification: verified`.
- `claims[]`: `id`, `text`, `kind` (fact/analysis/recommendation), `risk` (standard/critical/deadline), `status`, `source_ids`, `verified_at`, `counterevidence_checked`, `evidence_reasoning`, `limitations`. High-impact and deadline claims require a primary source. Deadline claim verification expires after one day; other claims/sources have longer windows.
- `opportunities[]` (when applicable): original `source_id`, `complete_documents_checked`, `addenda_checked`, explicit `fit: hold | no_go | qualified`, `mandatory_events[]` with met/missed status; qualified bids also need dated deadline and confirmed, evidenced client eligibility. **Missed mandatory events require `no_go` unless the issuer supplies and independently verifies an exception.** Do not force an unsupported qualification.
- `deliverables[]` with `path` and exact `sha256`. At least one Markdown evidence annex with every registered claim as a single annotated line containing exact claim text, `[C-001]` and `[S-001]` source markers. Client-delivery packs also require a PDF. PDF magic/trailer is an integrity preflight, not actual page-layout inspection.
- `review`: `reviewer_id` distinct from author, `decision: approve`, `quality_score > 9.0`, `reviewed_digest`, `reviewed_at`, `checks` (every required gate true), `notes`, `review_context`, `visual_evidence`. All assertions remain subject to authentication and human/independent scrutiny.

Run `python -m company_os.document_quality PACK_DIR --json --public-repo` for **public synthetic or sanitized demos only**. For local encrypted or controlled private client storage, omit `--public-repo` but maintain the rest of the company privacy policy. Public GitHub must never contain customer data or internal proprietary research packages. For batch workloads, use `python -m company_os.document_quality_batch PACK_ROOT --workers 4` (JSON output is default); up to 16 bounded local threads. If `--as-of` is supplied for a synthetic test, it fixes the test clock; real delivery should use the current UTC date.

### Required review checks

`source_accuracy`, `claim_completeness`, `contradictions`, `recency`, `client_fit`, `compliance`, `privacy`, `professional_writing`, `visual_pages`, `links_and_citations`, `numbers_and_tables`, `scope_and_limits`.

A reviewer must check complete *rendered* PDFs at ordinary and closeup size, including cover, tables, charts, page numbering, typography, hyperlinks and appendix, then document actual evidence. The gate cannot make visual quality claims just because the PDF has a valid trailer. No 9.0 average can override a failed mandatory check. Revise, invalidate approval, retest.

## Liability-conscious client writing

- Separate **observed facts**, **interpretations**, **scenarios**, **options**, and **unknowns**. Use precise evidence, dates, applicability, and conditional language: “One option to consider…”, “The available records suggest…”, “This may merit further verification…”.
- Do not pretend hedging words make incorrect information safe. Avoid guarantees, false certainty, advice outside competence, prescriptive legal/tax/financial claims, fabricated insider knowledge, and “we verified” statements without records.
- The client controls all operational decisions; regulated matters and material contractual exposure require appropriate licensed advice. Qualifying findings must still be accurate and useful.
- Pre-send correction workflow: flag, hold, investigate original source, fix/correct, re-review exact digest, authenticate permission, issue documented replacement with version/time. Notify affected clients only after authorized review, not automatically through CI.

## CI and volume model

The repository's existing CI remains unchanged. A new dedicated `document-quality.yml` checks Python 3.12 and runs offline adversarial tests plus a deliberately blocked synthetic draft. Multi-pack validation is stateless and can be distributed to independent jobs with unique **private** artifacts in an approved runner environment later, but Github Actions is ephemeral and not a customer database or autonomous AI research host. Parallelism is subject to GitHub plan limits, quotas, cost and privacy obligations. No cron schedule or remote URL-fetching is added while `PAUSE_AUTONOMY` is present.

## Minimum launch blockers (unresolved)

- Approved and authenticated independent critic identity and a review audit trail; reviewer attestation alone is forgeable.
- Secure **private** customer data store and artifact retention; current repository is public.
- Source collection pipeline with rate limits, legal access controls, validated URL reachability, primary record snapshots where allowed, contradiction search and authentic provenance.
- Real PDF rendering and page-by-page visual inspection evidence (not just signature checks), correction logs, and safe customer export.
- Approved customer intake, actual client qualifications and permission to use their data; legal review of contracts/disclaimers; consent and compliant outreach identity.
- Separate, authenticated release process and valid authority while `PAUSE_AUTONOMY` remains on; no autonomous email.

## Tested scope

Synthetic tests exercise successful static preflight, tampering, outdated claims, unverified primary sources, missing/mismatched critics, reviewer score 9.0, missing visuals checklist, missed mandatory walkthrough, unknown client eligibility, public/private boundary and multi-pack batch isolation. **Fictional fixtures are never evidence of real market claims**. The tests do not demonstrate real-world source correctness or readiness to serve clients.