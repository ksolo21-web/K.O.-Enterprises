# CE-1N — Private sealed reviewer workroom and real Linux UID isolation

**Checkpoint:** 2026-11-09. **Status:** Offline internal engineering, pending final GitHub tests. **No actual independent critic or production launch authority.**

## Purpose and dependency chain

CE-1K validates current signed-staged original issuer PDF bytes, URL, claimed origin, cited excerpt, and complete listed attachments. CE-1M reproducibly renders every original PDF page and binds PNG hashes into the source worklist. CE-1L verifies a signed reviewer claim and exact original PNG hashes **but has never proven the reviewer was actually separate**.

CE-1N makes the missing operational boundary tangible:

1. `stage_critic_room(...)` re-runs **current CE-1K** signed issuer inventory validation. It rejects revoked receipts, superseded sources and changed original bytes; requires all exact controlled original PDF-page PNGs and an exact attributed dossier with all claims/contrary sources. It writes one private sealed packet with every current issuer PDF page and the **full internal dossier/claim context**. This material may be confidential: **never commit or publish real packets**.
2. The packet manifest binds the canonical dossier SHA-256, current issuer inventory chain head, CE-1K source-page worklist SHA-256, all original PDF page image hashes and sizes, and exact source-to-claim citations. There is a 120-page/64-MiB limit per packet and no silent truncation; larger packages require a future reviewed chunked protocol.
3. Files are created exclusively, are owner-read-only `0400`, and room/page directories are `0500`. The workroom cannot overwrite a prior room ID. The **operating-system provisioner** must transfer access to a separate reviewer group by retaining provisioner ownership and assigning directory `0550` and file `0440`, never allowing the capture UID or reviewer to own/modify reviewer evidence.
4. `inspect_sealed_critic_room(..., expected_manifest_sha256=...)` is a **read-only verifier** for the reviewer process. It checks canonical manifest bytes against a supplied out-of-band digest, dossier/worklist hash chain, exact page list, filename safety *before path access*, no hidden/extra page files, no symlinks, no writable packet data, and original PDFium PNG hash/size/dimensions. It never reads capture directories, signing keys, broker secrets, or private source material outside the sealed workroom.
5. `tests/cross_uid_critic_room_ci.py` runs **real numeric Linux UID/GID** isolation on disposable GitHub-hosted CI using a root test provisioner, a distinct capture UID, signer UID, reviewer UID and unrelated UID. Its subprocess checks must demonstrate: dedicated reviewer can verify the complete exact two-document synthetic PDF-page packet; capture/unrelated users cannot read the room; reviewer cannot read capture originals or signer key, cannot change manifest or source images, and rejects wrong out-of-band hashes.
6. A separate 20-test offline unit suite checks signed-current-source intake, complete citation and attachment coverage, replay refusal, source revocation, symlinks, path traversal, forged manifest, missing/extra/changed PNGs, readonly permissions and release denial.

## Important evidence boundaries

- **OS identity separation is not an independently qualified critic.** The current CLI checks bytes and access control; it does **not** visually inspect images, reason about claims, corroborate buyers, score twelve checks, or issue a factual review.
- The GitHub UID exercise is an actual Linux kernel permission test under a temporary root-controlled provisioner. The provisioner remains privileged, so this does **not** establish a production trusted host, physically isolated admin, external key custody, long-lived monitoring or immutable external audit.
- CE-1N may expose internally sensitive dossier/source material inside the private packet. Its correct storage is a genuinely secured private environment with legal source rights, retention, ACLs, expiry, audit and permitted reviewer access. It is **not** safe to upload it to a public repository or artifact.
- The out-of-band packet hash is caller-supplied and **not independently anchored**. Strong third-party anchoring, reviewer governance, revocation and signed completion are still outside this increment.
- Existing PDFium native parsing is only best-effort process/resource-limited. Actual hostile source PDFs require stronger host sandbox containment and network denial.
- All returned success states remain **STAGED/READ_ONLY_HASHES_VERIFIED_REVIEW_PENDING** with `independent_review_completed=false` and `publication_authorized=false`. The global `PAUSE_AUTONOMY`, `PRODUCTION_RELEASE_CONTROLLER_CERTIFIED=False` and P0 #61 blocker remain.

## Engineering acceptance checklist

- [ ] Exact final PR-head GitHub Python 3.12 full tests pass, including 20 added unit cases, existing 978 baseline and no new fail/skip.
- [ ] Actual GitHub disposable Linux distinct-UID reviewer/capture/signer/unauthorized isolation check pass, including protected key and original PDF denial.
- [ ] CI Node, cross-UID signer, release-surface audit and clean tracked-files check pass with explicit NO-GO.
- [ ] Document quality pass; inspect patch and correct/retest defects (internal critic review, not a separate agent).
- [ ] Merge exact verified PR head; re-read merged `main` and root emergency pause/false hard lock.
- [ ] **Not a production acceptance:** no external independent reviewer agent, approved protected host, genuine source/issuer authentication, actual observed claim/page visual review, external audit anchor, admin-verified P0 OANDA workflow disable, or authorization to launch.

**Next critical-path build:** provision a truly protected reviewed reviewer runtime, a permissioned source-capture route and independent reviewer identity; wire actual visual/factual inspection of this immutable packet and require separate accountable review evidence. Do not fabricate a critic or lift the production lock from hash checks.

Related: [CE-1K](CE1K_SIGNED_PDF_CRITIC_HANDOFF.md), [CE-1L](CE1L_SIGNED_ORIGINAL_PAGE_REVIEW.md), [CE-1M](CE1M_REPRODUCIBLE_ORIGINAL_PDF_RENDER.md), [Competitive #38](https://github.com/ksolo21-web/K.O.-Enterprises/issues/38), [P0 #61](https://github.com/ksolo21-web/K.O.-Enterprises/issues/61).
