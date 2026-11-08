# CE-1J — Provenance-bound local competitive queue

**Checkpoint:** 2026-11-08. **Status:** Internal end-to-end integration, pending exact-head GitHub CI. **Not** live original-source acquisition, independent fact verification, or production approval.

## Why this is a larger integration

The CE-1F/CE-1I competitive evaluator previously accepted operator-supplied source URLs, original-byte hashes, excerpts and timestamps without requiring that those fields were recorded in the separately built CE-1A private source ledger. Similarly, CE-2A jobs processed JSON without rechecking whether a supporting capture had become stale, changed, or disappeared.

This change joins **source capture → source-ledger chain → exact source-to-snapshot manifest → durable queue → completion/release-review digest check** without granting publication or relying on network access.

## Behavior

- `competitive_source_binding.inspect_source_bindings(root, dossier, bindings, now)` takes a complete mapping of **each dossier source ID to one 64-character snapshot ID**. It verifies the CE-1A local chain and latest record for the source, rejects prior changed/superseded captures, checks <=7-day freshness and complete-document **operator assertion**, and checks exact URL, original byte digest, publisher, origin ID, observation time, normalized excerpt, source kind, acquisition type, and public-access basis. No missing, extra, aliased or duplicate snapshot mapping is accepted.
- `CompetitiveWorkQueue.submit(dossier, source_bindings=...)` is an **explicit internal-only** mode. It checks the mapping before enqueueing and atomically stores canonical binding JSON and its digest with the job, linked into the append-only *local* queue audit.
- Leased job completion rechecks the current source ledger and the binding digest. Missing/revised/expired or tampered evidence produces an internal `BLOCKED` job, **not** a legitimate held source analysis. `verified_snapshot(job_id)` also refresh-checks a bound job before returning its digests, avoiding a previously held result becoming silently reusable after source changes.
- Previously supported unbound synthetic/dry-run jobs remain available for internal simulation and **never** grant release authority. Attempting to downgrade a bound job to unbound (or silently upgrade an existing unbound job to bound) under the same job ID is refused.

## Non-substitutable limitations

- CE-1A accepts operator-provided HTML/text; recorded hashes and quoted excerpts are a **local snapshot assertion**, **not independently authenticated publisher transport** or verified buyer testimony. The binding does not independently adjudicate factual interpretations in dossier claims.
- This first bridge requires `operator_supplied` records with `public_access` basis and an explicitly asserted complete captured document. It **cannot** automatically claim signature trust or lawful access from a `local_staging_receipt` flag. Permitted licensed/connector-sourced material requires additional verified rights/identity wiring.
- This bridge does **not** integrate the signed PDF issuer inventory or cryptographic staging registry yet. Full original attachments, dynamic issuer portal content, source-page interpretation, independent critic, secure host and external audit remain required.
- Local SQLite and SHA chains are mutable by a privileged filesystem operator and are not an externally anchored evidence system. No private source bytes are added to GitHub.
- Existing legacy queue entrypoints can still accept clearly **internal-only** unbound fixtures, so **no** no-bypass production assertion may be made. The real CE-4 external delivery controller still requires universal enforcement at each actual execution surface.

## Acceptance checks

- [ ] Exact GitHub CI on this PR's final head: complete Python 3.12 safety/unit tests, Linux cross-UID, Node, release-surface inventory and offline document quality.
- [ ] 21 new targeted cases show matching private snapshots enter/complete to HOLD; missing, forged, duplicated or altered records fail; mid-queue revisions and post-HOLD changes block.
- [ ] Verified `main` merge with root `PAUSE_AUTONOMY` present, `PRODUCTION_RELEASE_CONTROLLER_CERTIFIED=False` unchanged.
- [ ] Classify review as **internal**; no separate authenticated factual critic ran. The source-binding bridge remains an unfinished CE-1/M1 increment even if its code tests pass.

**Allowed result:** internal `BLOCK` or `HOLD` only; `publication_authorized=false`. CE-1–CE-5 production milestones remain unaccepted; no customer send, launch, broker work, spending, new credentials or scheduled external operations.

Related: [CE-1I](CE1I_ORIGINAL_SOURCE_INDEPENDENCE.md), [#32](https://github.com/ksolo21-web/K.O.-Enterprises/issues/32), [#38](https://github.com/ksolo21-web/K.O.-Enterprises/issues/38), [P0 legacy-ref security #61](https://github.com/ksolo21-web/K.O.-Enterprises/issues/61).
