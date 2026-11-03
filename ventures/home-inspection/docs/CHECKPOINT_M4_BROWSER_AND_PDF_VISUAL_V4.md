# Milestone 4 — V4 synthetic browser + PDF visual acceptance checkpoint

**Code branch:** `home-inspection-development` in `ksolo21-web/K.O.-Enterprises`.  
**Current validated code SHA:** `6af4724d75c867cf1cc4b131da2be0c282332666`.  
**Status:** PASS for this synthetic engineering test increment only; Milestone 4 production approval remains **BLOCKED**.

## Implemented and observed in this increment

1. **Uncropped source evidence:** `inspection_engine/report.py` now draws source photo, native zoom, context, and extracted video stills using `evidence_img`, preserving the full image and original aspect ratio. The editorial cover intentionally retains crop-to-fill to match the approved Option 2 design.
2. **Actual visual defect discovered and repaired:** The first real 13-page raster run showed a small source photo at roughly half the intended size on gallery page 7. The old helper divided by a fixed 2× processing cap, despite small source images never reaching that cap. The corrected helper computes fitted display size from the actual pixel dimensions. The revised page was inspected in full-page raster form and fills the gallery evidence rectangle appropriately without cropping.
3. **Pixel-level negative regression:** `tests/test_m4_evidence_image_fidelity.py` creates a source with colored left/right edge strips, embeds it as evidence, rasterizes the actual PDF, and verifies that both extremes remain visible and the photo spans the intended frame width. A helper-identity check ensures evidence and editorial cover images use separate functions.
4. **True browser acceptance:** `scripts/m4_browser_visual_acceptance.py` runs the ACTUAL private worksheet in real headless Chromium/Playwright with the network disabled, at desktop 1440×900, Android portrait 393×852, and Android landscape 852×393. Each mode verifies all 13 system controls, full records and media controls, the source thumbnail, no JS failures, no horizontal overflow, no broken images, and no external requests. It verifies that export is blocked with required choices missing; it then completes the decisions and downloads a valid unsigned review response. The desktop output is authenticated against a synthetic transient Ed25519 key only; this is NOT real inspector identity authentication.
5. **Full private PDF page rasterization:** the same flow constructs a private, source-bound synthetic Option 2 report and runs `m4_pdf_audit.audit_private_pdf` to rasterize and hash all **13** pages, create a contact sheet, verify original source IDs in the PDF, and reject apparent blank pages. Images from the final visual run were retrieved from the GitHub Actions artifact and inspected: entire contact sheet plus individual cover, gallery, and complete-record pages. No gross clipping or header/footer collision was seen in this limited fixture.
6. **CI:** `.github/workflows/home-inspection-m4-visual-synthetic.yml` uses a dedicated offline Chromium + Playwright job; its artifact is explicitly synthetic-only. `m4_browser_visual_acceptance.py` creates no real inspector, real media, customer data, cloud models, or outgoing browser requests.

## Evidence and tests

- Full offline regression: [GitHub Actions run 41553046723](https://github.com/ksolo21-web/K.O.-Enterprises/actions/runs/41553046723) — **892/892 tests passed**, compile / M3 regressions / tracked source check also green, on source commit `6af4724d75...`.
- Browser and PDF visual synthetic CI: [GitHub Actions run 41553019351](https://github.com/ksolo21-web/K.O.-Enterprises/actions/runs/41553019351) — **PASSED** on image scaling fix commit `96f8efb6...` (the later pixel regression test is covered by the full offline run).
- Synthetic evidence artifact (no real photos or people): GitHub Actions artifact `m4-v4-synthetic-browser-pdf-evidence`; downloaded and examined: `desktop_worksheet.png`, `android_portrait_worksheet.png`, `android_landscape_worksheet.png`, 13 `pdf_pages/page_NNNN.png`, `pdf_pages/all_pages_contact_sheet.png`, `acceptance_summary.json`, and explicit unsigned response JSON for each layout.
- Actual browser result: 3/3 viewports completed unsigned output, 0 horizontal overflows, 0 broken images, 0 JS errors, 0 external network requests; 1 locally signed synthetic review, still 0 customer release authority.
- Human inspection note: these pages were visually reviewed **by the engineering assistant against a synthetic fixture**, not by an independent qualified home inspector. The contact sheet and sampled full-page images cannot certify full accessibility, technical inspection accuracy, or all edge cases.

## Internal critic findings and remaining acceptance gates

**Corrected defect:** Evidence pages previously shrank small source photos. Fixed and regression-covered.

**Open / mandatory before production:**

- Real legally authorized professional credential validation, independent reviewer authentication, revocation/access-control and legally scoped final signoff.
- Genuine pilot-case evidence and independent professionally labeled serious-defect benchmarks including false negatives and false positives, with consent and held-out evaluation.
- Full real-device mobile/browser accessibility, keyboard and touch ergonomics, screen-reader testing, large long-form property samples, real text wrap and varying photo orientations.
- Qualified **human** page-by-page visual review of complete production-size reports. Current synthetic page-raster proof is an engineering acceptance check only.
- Secure persistent data lifecycle, private storage, customer authorization, payments and delivery (no existing release path is enabled).
- Independent critic agent not run because no callable independent agent runtime was exposed; review documented here is internal, with actual screenshots, source and test logs.

**Disposition: The V4 synthetic visual/browser engineering increment passes its limited test contract, but the overall Milestone 4 remains unapproved and customer release remains false. Do not change existing M1–M3 baselines, `main`, or `PAUSE_AUTONOMY`.**

**Next executable critical-path increment:** use actual page samples of different source aspect ratios and longer dossiers to expand visual regression coverage; then design a qualified-reviewer credential-verification and credential-revocation gateway that fails closed when external professional authority has not been independently checked.
