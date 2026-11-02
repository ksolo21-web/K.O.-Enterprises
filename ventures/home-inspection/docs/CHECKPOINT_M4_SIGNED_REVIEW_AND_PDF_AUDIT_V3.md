# M4 checkpoint V3 — offline signed human review and page-by-page PDF evidence

**Branch:** `home-inspection-development` in `ksolo21-web/K.O.-Enterprises`. **Scope:** Engineering-only implementation, synthetic tests. No real inspection, inspector credential verification, licensed professional approval or customer release was performed. Preserve all previous M1–M4 safeguards and source fixtures.

## Added in V3

1. `inspection_engine/m4_human_review.py`: private review request bound to source SHA256, all stage-receipt SHA256 values, private Option 2 PDF SHA256, report audit hash, explicit Q03 holds, registered reviewer public-key registry and all recorded observations, findings, equipment, limitations, media, and 13 system coverage checks.
2. The qualified-inspector declaration and independent quality-review declaration must be **separately signed using different trusted Ed25519 private keys**. The public keys, reviewer IDs and roles are pre-registered. Changes to PDF/source, signer identity, registration, response, checklist coverage, or signatures fail verification. Explanations are mandatory for held/correction decisions. Neither reviewer can use a declared M2 model provider ID.
3. `inspection_engine/m4_review_ui.py`: local-only static HTML review worksheet, embedded source-bound photo thumbnails, explicit individual decisions on every source/media/system record, all selections initially blank, export to unsigned JSON. Strict local-only CSP, no external scripts/requests, no auto signing.
4. `scripts/m4_review_cli.py`: `prepare`, `worksheet`, `template`, `sign`, `verify`. Signing requires an externally generated private Ed25519 PEM key kept outside Git and private case workspace, owner-only file access, and the exact existing trusted-key registry. Signing never edits the original case or authorizes report release.
5. `inspection_engine/report.py`: all standalone source photos now receive dedicated private Option 2 gallery views; selected video frames retain their separate provenance gallery. Every media record and native crop also remains in the unabridged technical register. Standard Option 2 non-M4 rendering is unchanged.
6. `inspection_engine/m4_pdf_audit.py`: every actual PDF page is rendered locally with PDFium and retained as private PNG with page SHA256, dimensions, raster variation, full source register check and a private contact sheet. Automated raster checks are NOT human visual acceptance.

## Private operator sequence

All generated case files, trusts, keys and worksheets must remain **outside all public and private Git checkout directories**; real customer media and credentials must never be committed to this repository.

After the existing M4 `scripts.m4_case_pipeline` stages are completed, use:

```bash
# First configure two registered Ed25519 public keys, with roles
# qualified_inspector and independent_quality_reviewer, in a private trust registry.
python -m scripts.m4_review_cli prepare --workspace /private/m4-run --trust-file /private/trusted_signers.json
python -m scripts.m4_review_cli worksheet --workspace /private/m4-run
# Open the generated local human_review_worksheet_PRIVATE.html in a browser.
# Inspect original media and report independently from thumbnail-only previews.
# Each reviewer exports a separate, manually completed unsigned JSON response.
python -m scripts.m4_review_cli sign --workspace /private/m4-run --trust-file /private/trusted_signers.json --review-json /private/inspector_UNS.json --private-key /private/inspector_ed25519.pem
python -m scripts.m4_review_cli sign --workspace /private/m4-run --trust-file /private/trusted_signers.json --review-json /private/qa_UNS.json --private-key /private/qa_ed25519.pem
python -m scripts.m4_review_cli verify --workspace /private/m4-run --trust-file /private/trusted_signers.json
```

Optional CLI `template --role qualified_inspector` creates a blank unsigned checklist for manual completion.

For the local PDF visual audit:
```bash
python -c "from inspection_engine.m4_pdf_audit import audit_private_pdf; print(audit_private_pdf('/private/m4-run'))"
```
Inspect **all** generated `page_raster_audit/page_NNNN.png` images and `all_pages_contact_sheet.png` before claiming visual acceptance. Images and the worksheet can contain private personal/address/photo data.

The sample trusted-key registry format is:

```json
{"schema_version":1,"reviewers":[
  {"reviewer_id":"EXAMPLE-INSPECTOR","role":"qualified_inspector","public_key_hex":"<64 lowercase hex characters>","active":true},
  {"reviewer_id":"EXAMPLE-SECOND-REVIEWER","role":"independent_quality_reviewer","public_key_hex":"<different 64 lowercase hex characters>","active":true}
]}
```

**Authentication boundary:** Ed25519 verifies registered-key possession and record integrity. It cannot verify licensure, proof of professional independence, employment, identity proofing, credential revocation, whether someone actually inspected source images, or physical inspection competence. Those controls require additional operational and service design. The browser worksheet is not an authenticated application. No `customer_release_allowed=True` execution path exists in V3.

## Acceptance and pending gaps

- [x] Durable signed review request bound to pipeline source, evidence, original photo/video, Q02/Q03 decisions and exact private PDF.
- [x] Distinct registered keys, complete item/media/system decisions, identity mismatch rejection, signed-record tamper detection and no-release state.
- [x] Offline private worksheet export with no preselected decisions.
- [x] Private paginated gallery for all standalone photos, separate video still gallery, full record registry.
- [x] Local page-by-page PDFium renderer, image hashes, blank-page checks, contact sheet output and no false manual acceptance.
- [ ] Latest-commit full CI must pass. Previous V2 baseline: 872/872 tests green at `941bcd84efb4`. New V3 suite must be evaluated on its own SHA.
- [ ] **Human visual PDF inspection** of actual rendered pages, including long/complex cases, every page, margin defects, readable sizes, cover, image cropping and captions. An automated contact sheet alone is not sufficient.
- [ ] Browser end-to-end interaction test on Android, mobile/tablet, desktop, offline and accessibility; HTML source/unit tests alone are not browser acceptance.
- [ ] Secure independently authenticated identity/real credential verification, regulated professional standards, privacy/security external audit and protected customer sharing.
- [ ] Real-world serious-defect sensitivity and false-positive benchmark professionally labeled, held out and permissioned.
- [ ] Independent critic agent review not performed; engineering internal review and CI tests only.

**Release posture: NOT APPROVED — internal synthetic engineering only.** Even when two registered signatures validate, report holds or signed key possession can never be converted into a customer-facing release authorization here.
