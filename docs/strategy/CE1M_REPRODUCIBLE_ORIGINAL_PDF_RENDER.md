# CE-1M — Reproducible original-PDF page images

**Checkpoint:** 2026-11-09. **State:** internal engineering; exact-head GitHub CI required. **No production authorization.**

## Why this matters

Prior CE-1K/1L validated the issuer PDF source bytes, quoted page text and signed reviewer-supplied PNG bytes, but did **not** establish that those PNGs represented the correct source-PDF pages. An arbitrary structurally valid PNG could have satisfied all local signed metadata checks if an authorized key signed its hash. A signing key cannot prove a page is visually faithful.

This increment adds an actual reproducible renderer to the existing evidence path:

`signed staged issuer PDF bytes → CE-1K real PDFium page rendering → exact PNG SHA-256 embedded in current source-page worklist → CE-1L strict signed reviewer PNG hash and byte match → internal HOLD`.

The new `src/company_os/pdf_page_render.py` uses fixed `pypdfium2==5.15.1` and `Pillow==12.3.0`, RGB, default rotation, **108 DPI** (scale 1.5), predictable PNG compression, version-string checking and a distinct subprocess with best-effort POSIX memory/CPU limits. It accepts only bounded source PDF bytes and single pages 1–60, caps page pixel area at 5 million and output at 3 MB. It does **not** open network connections or write images to disk; the caller receives source-PDF-page PNG bytes locally.

The CE-1K page worklist now includes a fixed `renderer_profile`, exact deterministic `rendered_png_sha256`, page width and height for **every** captured issuer PDF page in the original package. The worklist digest already covers all pages, and the CE-1L source-page review receipt is bound to that digest. CE-1L now rejects syntactically valid, reviewer-signed PNGs that do not exactly equal the renderer's current original PDF page output, regardless of reviewer assertions.

The previously synthetic placeholder PNG fixtures in `tests/test_competitive_source_page_review.py` are now generated from the **actual synthetic PDF bytes**, and synthetic unrelated PNGs are tested as rejection cases. A separate renderer test suite checks reproducibility, actual rendered pixel dimensions, different-document images, exact original PDF bytes binding, invalid page/type, PDF size/structure and pinned renderer version. It is still not a genuine real-world issuer or independent reviewer.

## Source licensing and operational caution

- PDFium and its Python bindings are permissively licensed, but commercial redistribution or deployment requires the applicable PDFium, bundled dependency and Pillow notices and compliance checks; see [pypdfium2 licensing](https://pypi.org/project/pypdfium2/).
- PDFium is native C++ parsing code. A Python subprocess with resource limits is **not a security sandbox**. Real untrusted PDFs must be handled in independently provisioned OS/container isolation, without network permissions, with filesystem restrictions, resource/secret isolation and approval.
- Reproducibility is claimed for the **same pinned PDFium/Pillow profile and platform**, not across changing PDF rendering implementations/operating systems. Renderer upgrades require regeneration and re-signing of source-page evidence.
- A precise digital PNG comparison demonstrates that local reviewer evidence matches our controlled rasterizer, **not** that someone actually inspected the pixels, interpreted claims correctly or that the original bytes came from the real issuer. The independent critic still must do a real page-by-page visual assessment, fact check, report check, and issue a qualified, independently authenticated decision >9.0/10 with all twelve mandatory checks.

## Acceptance criteria

- [ ] GitHub CI on **exact final PR head** passes pinned PDFium/Pillow installation, source/test compile, full Python 3.12 security suite including new real-PDF-PNG tests, cross-UID signer test, Node tests, release-surface no-go inventory and clean tracked-files verification.
- [ ] Offline document-quality workflow successful on exact final head.
- [ ] Internal code/patch review, correcting any discovered deficiencies and re-testing.
- [ ] Confirm merged `main` preserves `PAUSE_AUTONOMY` and literal `PRODUCTION_RELEASE_CONTROLLER_CERTIFIED=False`.
- [ ] Keep no production claims: no approved host, genuinely independent reviewer, issuer transport authentication, screenshot viewing by a separate agent, protected runtime isolation, external audit anchor or universal release-channel enforcement proven.

**Next critical path**: provision a real protected sandbox/host with actual legally obtained original PDF evidence and a genuinely separate reviewer to inspect the renderer's actual pages; enforce trusted separate identities, secure monitoring, source freshness and all-channel no-bypass controls (including [P0 #61](https://github.com/ksolo21-web/K.O.-Enterprises/issues/61)). All commercial, customer, broker, payment and production activity remains paused. See [CE-1K](CE1K_SIGNED_PDF_CRITIC_HANDOFF.md), [CE-1L](CE1L_SIGNED_ORIGINAL_PAGE_REVIEW.md), [Competitive blocker #38](https://github.com/ksolo21-web/K.O.-Enterprises/issues/38) and [Market Intelligence #32](https://github.com/ksolo21-web/K.O.-Enterprises/issues/32).
