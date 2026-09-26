# Territory Card Studio Android 0.1.18 — Phase 1B-3 recovered build-candidate audit

Status: **RECOVERED BUILD CANDIDATE; Phase 1B-3 remains OPEN.**

## Recovered exact artifacts
- Build-freeze ZIP SHA-256: `029d24f7a7e54192400ce637004c8b7799f140e6a9ea76d32aaedd2ec0c8ed2d`
- APK SHA-256: `d948bf76152d38fcc2c38f942d9835dd0f9454391dff633ee176b49930a689a3`
- AAB SHA-256: `311208db1e2c248bb65db06f383c94c195cacf60e55f9fc1b8c2b32a99c1c36a`
- Standalone APK/AAB bytes exactly match copies inside the build-freeze ZIP: **PASS**
- ZIP integrity for build-freeze/APK/AAB: **PASS**

## Recovered hosted-build evidence
- Phase 1B-3 build freeze: **PASS**
- Core test: **PASS**
- App compile: **PASS**
- assembleDebug: **PASS**
- bundleDebug: **PASS**
- APK v2 signature: **PASS**
- AAB JAR verify: **PASS**
- versionName/versionCode: **0.1.18 / 18**
- target SDK: **37**
- Reserved territory PDF sweep: **0**
- Adapter fail-closed mutations: **28**
- Core test adapter input SHA-256: `9e8b43359ab6c2117caab6130d91815015b2d63e1f63d3f5500ba17c76a9fcc1`
- Core test adapter output spec SHA-256: `52830a0869a78788efb3dc78f3466fe1b3494190271cbeeb8bf7fc241586e596`
- Core test non-field PDF SHA-256 was recorded as `5e88a940f81495bf5a42ea99a8ba58c67cc7b867fa581ad99fede5e2953c5ecf`, but the PDF bytes were not durably recovered.

## Exact APK contract inspection
The exact APK contains the Phase 1B-3 model surface:
- `VerifiedSiteBuildingAssignmentGeometry`
- `VerifiedSiteBuildingBinding`
- `VerifiedSiteAccessInsetGeometry`
- `PdfSiteBuildingAssignmentLayout`
- `PdfSiteAccessInsetPanel`

Seventeen required fail-closed binary contract assertions passed, covering explicit site geometry, multi-unit/site-only housing, assigned-building ownership, base-road and label ownership, source-building binding coverage, locked R48 containment, diagram/access collision, source-to-destination access mapping, road meaning/status parity, source-bound coverage, and explicit site marker rendering.

## Why Phase 1B-3 is not frozen
The durable state still lacks all of the following mandatory freeze evidence:
1. Exact 0.1.18 source package or overlay bytes.
2. Durable synthetic Phase 1B-3 NOT-FOR-FIELD-USE PDF bytes.
3. R48/R51/R52/identity/hard-override validator outputs.
4. Required 1x and 4x visual inspection evidence.
5. Second-renderer parity evidence.

Console/build evidence alone is insufficient. Therefore Phase 1B-3 remains open and no later phase is started.

## Reserved territory guard
`250T`, `257A`, `297`, `298A`, `299`, and `347TA` remain untouched and unapproved.

## Next bounded task
Stay in Phase 1B-3. Reconstruct or recover the exact site-building source delta from frozen 0.1.17 plus recovered 0.1.18 binary/source-manifest evidence; generate a synthetic NOT-FOR-FIELD-USE site-building fixture; run R48/R51/R52/identity/hard-override plus 1x/4x and second-renderer validation; then create a durable 0.1.18 source package and freeze Phase 1B-3 only if every mandatory gate passes.

## Persistence note
The native Library upload path returned `container_session_unavailable` during this run. The checkpoint, forward-only completion ledger, and this audit were therefore persisted on the existing dedicated GitHub durability branch `territory-card-studio-android-state`.
