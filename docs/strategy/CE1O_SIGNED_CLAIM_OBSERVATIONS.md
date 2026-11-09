# CE-1O — Signed page-by-page and claim-by-claim observation intake

**Checkpoint:** 2026-11-09. **Status:** engineering draft pending exact final-head CI; no genuine independent reviewer has run.

## Purpose

CE-1N provides a sealed, separately readable reviewer workroom containing all pages of the current issuer source PDFs, each image's controlled PDFium digest, and the complete attributed competitive dossier. Its byte verifier does **not** demand that the reviewer address all claims, their counterevidence, or every original page in a substantive written observation. CE-1O closes this *record-completeness* gap **without falsely claiming factual or independent-review completion**.

The new `src/company_os/competitive_critic_observations.py` provides:

- `build_pending_observation_worklist(room, expected_manifest_sha256=...)`: rechecks the real CE-1N sealed workroom, returns every issuer-original image digest/page and **every dossier claim** with its exact supporting/counter source IDs and located issuer-original excerpt-page PNG references. Every observation/claim disposition begins **unanswered**; the generator cannot silently fill in favorable findings.
- `inspect_signed_observation_receipt(room, manifest_sha, critic_policy_envelope, reviewer_signed_envelope, now=...)`: rechecks all sealed image bytes; loads the exact canonical room manifest using the out-of-band SHA; verifies a dedicated **domain-separated Ed25519 reviewer signature** against the **root-signed, current, revocable CE-3A governance policy**. Reviewer/key/venture scope must be registered and author/reviewer IDs must differ. All times must be short-lived and tied to the current reviewer key validity.
- Binds receipt to exact current private workroom SHA-256, attributed dossier SHA-256, CE-1K worklist SHA-256, issuer inventory ledger head, reviewer, author, venture and dossier ID. No tamperable permit to release is present.
- Enforces **one distinct, detailed, time-bounded visual observation per actual source PDF page** (`legible_reported`, `defect_reported` or `unassessable`; exact PNG digest and meaningful notes). A signed assertion is **not evidence that pixels were actually viewed**.
- Enforces **one detailed, time-bounded disposition per dossier claim**. Every claim's supporting source IDs and counter source IDs must match the dossier **exactly and in order**. Every issuer-original source cited in that claim, including counterevidence, requires its exact original PDF page and PNG digest. A claim with only nonissuer sources in the sealed packet cannot be marked `packet_excerpt_located`.
- Tracks `packet_excerpt_located`, `contradiction_reported`, and `unverified` dispositions and counts problems. `packet_excerpt_located` means **a reviewer claims to have located the cited passage in submitted pages**, not that the claim is corroborated, the original is authentic, or the issuer is trustworthy.
- Rejects unsigned, missing, forged, revoked, expired, self-signed, partially observed, page-swapped, citation-dropped, counterevidence-dropped or later altered records. A safe wrapper yields `BLOCK`; a structurally complete signed response **always yields `HOLD_SIGNED_PAGE_AND_CLAIM_OBSERVATIONS_NOT_INDEPENDENTLY_VERIFIED`** with all independence, factual-truth, independent approval, publication and production flags FALSE.

## Critic and security boundary

This component **does not fabricate or run a human/AI critic**. The tests generate synthetic reviewer keys and synthetic notes solely to verify the data path. The separately tested CE-1N Linux UID access boundary and this root-governed signature show **mechanical** record integrity and permissions, not an actually distinct qualified person, substantive visual/factual inspection, external original-source authentication or real independent challenges. Signing a completed template does **not** establish those facts.

In particular, nonissuer vendor/buyer/secondary claims require **other independently obtained evidence** beyond the current issuer PDF packet. Most of the fictional test dossier remains unverified, correctly. Real buyer interviews, competitor originals, factual contradiction resolution, copyright/rights, provenance, approved private operating host, reviewer credentials and externally anchored logs still require actual evidence. The existing separate CE-3A report review, twelve mandatory checks, threshold **strictly greater than 9.0**, and all release-channel guards remain independent additional gates. CE-1O cannot change any release guard or cause a business action.

This component makes no outbound network requests, stores no signing private keys, sends no customer communications, and does not authorize payment, broker operations or publication. Do **not** commit private review-room manifests, signed review responses or original source documents into public GitHub. Keep `PAUSE_AUTONOMY` and `PRODUCTION_RELEASE_CONTROLLER_CERTIFIED=False`.

## Engineering acceptance

- [ ] Full exact-head GitHub CI on Python 3.12 green, including **35 new signed observation tests**; no weakening of existing source/signature checks.
- [ ] Existing CE-1N real distinct-UID/Linux workroom isolation and capture/signer isolation green.
- [ ] Node comparison, document quality, release-surface NO-GO, source compile and no tracked test modifications all pass.
- [ ] Internal patch review (not independent critic), repair deficiencies, full retest and merge exact verified PR head. Re-read merged main and ensure root pause/false lock.
- [ ] Production acceptance still BLOCKED: genuinely independent qualified reviewer must actually inspect every PDF page and claim; record shortcomings, source truth and counterevidence, demonstrate separate custody and protected host, complete CE-3A report review and audit; P0 broker Actions owner-admin disable [#61](https://github.com/ksolo21-web/K.O.-Enterprises/issues/61) remains unexecuted and unverified.

**Next executable critical path:** expose this pending worklist to an authorized, separate reviewer through a protected inspection interface that displays the real exact PNG pages (and supports evidence/counterevidence attachments), require real page/claim observations and protected signed storage, then validate independent operations on an approved private host. Never automatically set all positive findings. See [CE-1N private reviewer workroom](CE1N_PRIVATE_REVIEW_ROOM.md), [Competitive #38](https://github.com/ksolo21-web/K.O.-Enterprises/issues/38) and [Market Intelligence #32](https://github.com/ksolo21-web/K.O.-Enterprises/issues/32).
