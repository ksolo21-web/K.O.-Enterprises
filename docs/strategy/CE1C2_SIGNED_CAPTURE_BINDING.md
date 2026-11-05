# CE-1C2 — Signed capture receipts and issuer PDF inventory

**Checkpoint:** 2026-11-05  
**State:** Offline integrity validation only; original issuer authentication, independent critic and any K.O. launch are BLOCKED.  
**Source:** src/company_os/signed_capture_receipts.py, integrated with src/company_os/procurement_package.py  
**Tests:** tests/test_signed_capture_receipts.py

## Problem addressed

Previously CE-1C checked a locally assembled package whose PDF hashes and addenda count were operator statements. CE-1C2 binds each PDF to a separately signed capture receipt and also binds the declared document inventory to a saved issuer listing snapshot. That substantially reduces silent metadata alteration, omission of a listed PDF and accidental misassociation of source versions.

**Caution:** Signature verification establishes only that the configured capture private-key holder signed the metadata. It does NOT demonstrate that the signer honestly fetched the issuer's site, reviewed a full portal, or that no unlinked addenda exist. A genuine independent reviewer and complete original-source acquisition remain mandatory.

## Private input files and trust boundaries

The same private folder holds package.json and actual required PDFs, plus issuer-listing.html and capture_receipts.json. No customer files or issuer originals belong in public GitHub.

The receipt bundle contains a strict schema version 1.0, one signed listing envelope, and one signed per-document PDF envelope. Envelopes contain a payload and its base64 Ed25519 signature. The read-only verifier obtains KO_CAPTURE_RECEIPT_PUBLIC_KEY_B64 and KO_SOURCE_APPROVED_HOSTS from the approved protected environment; it contains no private signer.

Listing payload fields: schema_version, record_kind, capture_id, package_id, listing_url, listing_filename, listing_sha256, listing_observed_at, listing_reference, listed_items (document_id/source_url/kind/sequence), capture_actor and capture_method. Each PDF receipt binds capture_id, package_id, document_id, source_url, sha256, bytes_received, media_type, observed_at, capture_actor, capture_method, permit_id, tls_certificate_sha256 and pinned_ip.

Signed source transport metadata remains **an assertion from a capture service** pending actual protected service identity and source collection verification.

## Mandatory integrity checks

1. Exact signed Ed25519 receipts, trusted configured public key and HTTPS host registry.
2. Listing content hash and date, manifest package ID, issuer URL and source listing reference.
3. Equality of PDF anchor links extracted from the saved HTML, the signed issuer listing items and the complete package manifest, including addendum sequence/role.
4. Original local PDF byte hash/length equality with a signed per-PDF capture record and its source URL, timestamp, capture ID and claimed public-network TLS provenance.
5. No duplicate capture IDs, missing/extra PDF receipts, out-of-date captures, future timestamps, private IPs or unsupported acquisition claims.
6. All previous CE-1C original-PDF extraction, page-level quotations, change, deadline, mandatory event and inventory screening remain required.

### Invocation

- Default legacy offline review: python -m company_os.procurement_package /approved/private/package
- **Strict internal review:** python -m company_os.procurement_package /approved/private/package --require-capture-receipts

A missing signed sidecar is marked MISSING_SIGNED_ORIGINAL_CAPTURE in legacy mode and causes BLOCK in strict mode. Any present malformed/tampered sidecar BLOCKS regardless of mode. A structurally matching signed sidecar yields only HOLD_INDEPENDENT_ISSUER_AND_CLIENT_REVIEW with explicit publication_authorized=false.

## Unresolved high-priority gaps

- **Actual issuer integration absent.** CE-1B supports text/HTML read under governance but does not yet fetch PDF attachments; this signed receipt checker does not establish an honest external signer, actual website identity beyond configured claims, lawful retrieval, or authoritative complete portal/addenda discovery.
- **Dynamic issuer pages unsupported.** HTML PDF anchors can omit links hidden in JS, pagination, bid portals, related pages or updates after the snapshot. Anchor equality is a useful guard, not proof of exhaustive completeness.
- **No protected signer lifecycle.** A separately authenticated capture service, key custody, rotation/revocation, monotonic replay ledger, secured receipt storage and live integration still need to be built.
- **No genuine independent human or separate critic.** Visual original pages, bidder eligibility, mandatory attendance, semantic conclusions and buyer context are not verified by this code.
- **No release/hosting authority.** PAUSE_AUTONOMY remains active. PRODUCTION_RELEASE_CONTROLLER_CERTIFIED=False remains the global hard lock. GitHub Actions is not continuously running production infrastructure.

## Next critical-path engineering

CE-1C3: Build an approved, isolated source-capture worker with legal read-only PDF retrieval, trustworthy receipts from protected key custody, issuer listings and addenda change history. Then CE-1D: attach source-to-claim trace to genuine independent critic and company release controls. Keep Issues #32 and #38 open.

This increment is subject to internal test and critic review; it is not a valid production acceptance, external client report or grant of deployment authority.
