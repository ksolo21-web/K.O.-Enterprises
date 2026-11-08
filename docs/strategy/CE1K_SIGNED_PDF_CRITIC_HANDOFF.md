# CE-1K — Signed-staging issuer PDF → exact claim/page critic handoff

**Checkpoint:** 2026-11-08. **Status:** Offline internal integration; not customer, production or independent-critic approval.

## Connected existing systems

This change joins the **CE-1C3e** privately staged issuer HTML/PDF inventory, permit-bound source identity and root-governed **staging signatures** with the **CE-1I/J** attributed competitor dossier and the **CE-3A** independent-critic *work requirements*. It does not pretend that a signing key or automatic PDF text extraction authenticates a real issuer or constitutes critic visual review.

`inspect_issuer_pdf_handoff(root, dossier, issuer_id, package_id, source_document_ids, policy_envelope=..., trust_ledger=..., now=...)`:

1. Requires attributed **schema 1.1** competitive dossier and valid internal dossier evaluation; every dossier `issuer_original` source must map to an exact PDF document ID in one issuer inventory package. Never accepts HTML issuer listing as a PDF.
2. Requires a currently valid **strict signed staging** issuer package, rooted in the same private ledger, with matching listed PDFs, current staging signatures and no missing/revoked receipts. Superseded issuer listings, changed or missing attachments and stale observations block.
3. Re-reads every original PDF in the package, checks exact bytes and SHA-256 against issuer records, parses bounded text in existing constrained PDF worker, and records **all** PDF pages for a separate critic's visual inspection—including attachments not directly cited by the dossier.
4. Binds each dossier issuer claim's source to the PDF URL, original bytes digest, declared publisher/origin, observation time, capture kind, rights assertion and exact **single-page original excerpt**. Missing, altered, multiply occurring, or uncited issuer excerpts block.
5. Returns a deterministic SHA-256-bound **review worklist** with per-page extracted-text digests, page numbers, original capture receipt IDs, original PDF hashes, exact excerpt page and citing claim IDs. Records `visual_page_inspection_completed=false`, `independent_source_inspection_completed=false`, `original_issuer_authenticated=false` and `publication_authorized=false` throughout.

This output is a **handoff for external human/agent review**, not a fabricated review or a signed approval. Existing critic-verifier `source_inspections` and `page_inspections` currently cover dossier source digests and *output-report* pages; a separate renderer/critic will still need to inspect actual **input original PDF pages** and validate each citation/fact against the source evidence. A later integration must verify such independent work against this worklist without self-attestation or an untrusted signer.

## Acceptance and security posture

- [ ] Exact final PR-head Python 3.12 CI passes, including all 24 new synthetic real-PDF-bytes adversarial tests.
- [ ] Offline document-quality and repository release-surface audits pass, preserving explicit **production NO-GO**.
- [ ] Review actual PR diff, run internal critique and correct/retest defects.
- [ ] Merge exact verified head; check resulting main code, root pause and release-controller hard-lock.
- [ ] Do **not** accept CE-1/2/3/4/5 production readiness from a local PDF text/page task manifest.

Remaining non-substitutable requirements: **genuine permitted original issuer transport**, dynamic portal/addenda completeness, independent authorized signer/key custody, separate qualified reviewer with actual rendered page inspections and strict >9.0/10 review evidence, private protected always-on host, externally anchored tamper-resistant audit, all-ref release-path no-bypass proof (including [P0 #61](https://github.com/ksolo21-web/K.O.-Enterprises/issues/61)), and explicit CEO release authorization.

No live fetch, browser, secrets, payment, broker call, customer contact, scheduled service, release or deployment is added. `PAUSE_AUTONOMY` and `PRODUCTION_RELEASE_CONTROLLER_CERTIFIED=False` remain unchanged.

Related: [CE-1J](CE1J_PROVENANCE_BOUND_QUEUE.md), [#32](https://github.com/ksolo21-web/K.O.-Enterprises/issues/32), [#38](https://github.com/ksolo21-web/K.O.-Enterprises/issues/38).
