# Learning regressions — version 3, 2026-09-07

Release requires exactly 10/10 in every scored category, unrounded weighted score 10, and every existing mandatory gate passed. A 10 is no observed defect under evidenced checks, not a guarantee of perfection. Keep honest failing scores; no rounding, averaging away a defect, or self-certifying missing evidence.

## On a returned card

1. Freeze the defective PDF, annotation, source, and earlier review with SHA-256. Record the user observation, root cause, generalizable detection rule, and scope exceptions.
2. Fix the artifact within existing permissions and preservation masks. Keep the failed attempt and exact corrected/saved PDF hashes.
3. Run the changed check on both actual artifacts. Numeric contracts require executable tests; visual or semantic rules require an independent critic inspecting fresh actual-size and close-up renders, without the answer key. Report false passes and false failures honestly. A schema assertion alone is not proof that a visual defect is detectable.
4. Add a versioned fixture entry, executed results and evidence paths. Mark unexecuted tests pending. Recheck the same defect class across the current batch, including cards previously approved under older checks; do not automatically redraw unaffected cards.
5. Preserve the updated standards, fixture manifest, results and unresolved checks in the batch recovery manifest. The next chat must load them before release. This is persistent workflow learning, not automatic model-weight training.

## Existing fixtures

See `regression-catalog.json`. Paths are relative to the revision-11 root recovered from the two durable evidence parts. Bad/corrected originals stay immutable. The catalog records known historical defects; blind replay of 28/31B/39 has executed with the limited outcomes in the catalog; other pairs remain pending. New score-threshold tests use the real saved 28 report and its exact PDF, changing only score/evidence inputs in isolated copies; these test the release contract, not visual detection.

Durable evidence parts: `libfile_233140f5527c819180889842dbfb9e0f` and `libfile_45f04d142da4819196d8be57b8166c41`. Their restore order and paths are in Territory-Batch-10-Audit-Manifest.json (`libfile_e4379d91a0448191a0f7e067297bd19c`). Do not embed large duplicate PDFs in a skill.

Executed contract-test results: `learning-contract-results.json`. Rerun the installed critic test script when changing the threshold or evidence contracts.

## Hidden replaced text — regression 39, version 2

The former revision-11 saved 39 is a rejected positive fixture. Its visible layout improved, but concealed old Burlington Dr/Ct and Saratoga Dr text remained in the actual PDF. Independent in-memory removal changed extraction while producing identical pixels at 1x, 2x and 4x. Keep the historical passing report as evidence of the miss; do not reuse it as present approval. A future repaired-positive requires fresh independent review.

For moved/replaced labels, reconcile original text-show operations with their final replacements. Require deterministic visibility evidence against actual working and saved PDF bytes: isolate each suspect old text-show operation (including nested Form XObjects), suppress its painting in a temporary copy while preserving text advance and graphics state, and compare exact renders at 1x, 2x and 4x. Bind the report to the PDF hash and event identity. A nonempty old text event whose removal changes extraction but no pixels is concealed residue and fails release. Physically remove obsolete operations; clipping, white overlays, opacity or invisible rendering are not deletion.

Checking `get_texttrace()` render type 3 alone is insufficient: clipped or occluded ordinary `Tj`/`TJ` operations can also be invisible. Preserve clip state in the experiment. Do not flag legitimate visible repeated road labels merely because their strings match. If visibility cannot be measured unambiguously, mark it unverified and fail release. Record the operation inventory, extracted counts before/after, render hashes, pixel differences and source/event bindings; a prose assertion or screenshot alone is insufficient. This requirement supplements all existing geometry, glyph and export gates without changing their thresholds.

## Parcel scope and optional-content visibility — version 3

T66: independently bind every source-marked residential building and internal access to actual parcel geometry. A main property address does not prove that the complete complex occupies one parcel. Reconcile all intersecting parcels with authoritative property records, registered aerial/source evidence, coverage, housing eligibility and road dispositions. The first independent geography8 overturned a previous10 because northern parcel330710 was excluded. Corrected working round2 reached all10; retained-byte verification was blocked by HTTP502, so this is not a saved-positive fixture.

42: preserve optional-content visibility through every PDF transformation, including page extraction and embedding in a new destination document. `PdfWriter.add_page` can omit catalog `/OCProperties`; `show_pdf_page` can import Form content without the destination visibility configuration. Keeping native paths alone then exposes source-hidden Guide paints. Preserve the catalog or explicitly transfer the original OCG default ON/OFF state with correct destination bindings. Independently compare the actual embedded/final native paint and fresh renders against source-visible paint; a successful source-to-textfree check does not cover later embedding. The observed textfree and destination visibility repairs retained62drawings with zero differences; the broken destination exposed66. Keep all original paths, retain the source-hidden state, and do not delete Guide paths, widen masks, waive extra-paint failures or weaken validators to make counts pass. Card42 final approval remains pending.

The topology validator's own transformed-source probe must retain these OCG states and serialize/reopen the document before reading drawings or rendering. MuPDF can cache the prior imported visibility, so changing the catalog alone does not prove displayed state. The central probe fix passed the full42 and73 topology fixtures; a42 candidate with its OCG catalog intentionally omitted still failed unexpected native drawing operations. Actual42 probe pixels matched the original at1x/2x/4x; the unregistered negative differed. These are topology/probe checks, not complete card release approvals.

## Actual composite road ink — 42 measurement regression

Distinguish a physical street from its native paint layers. Source26 gray and48 green Olympia share exact geometry: separately rendered alpha29+29 becomes composite55 at two arrow-contact edge pixels, exceeding the unchanged35 threshold. Bind verified neutral construction underlay and colored foreground to the same physical road; do not merge different work-status roads merely because paths overlap.

Streamwood showed a separate context-dependent isolation defect: isolated native62 clipped its square endpoint, while preserving distant preceding native61 restored its actual end paint, despite identical extracted geometry/style. Gray22+red43 grouping alone did not fix this. Diagnose with actual full-context renders and native event evidence; never invent a two-pixel allowance. A tested isolated Metrics proposal attributed target ink by comparing full road context with only the source-bound target paint set suppressed, intersecting attribution with BOTH actual all-road ink and the unchanged source-binding corridor, and combining it with existing visible isolated target ink. All-road collision scope and alpha threshold remained unchanged. Do not arbitrarily add the preceding unrelated road to the target.

Observed copied-class tests: Olympia and Streamwood own-leader unrelated counts2→0; real native leaders on the other road still failed with24/12 unrelated pixels. Evidence and proposal: territory-batch-12/gate-learning/road-composite/{alpha-contributors.json,pair-check.py,counterfactual-test.json,native_metrics_proposed.py,proposed-test-results.json}. This records a tested proposal; it does not assert that shared runtime adoption or full card review has occurred. Keep shared runtime stable during active measurements; independently review and adopt a proven patch only between runs.

Parent reviewed the proposal for use in a dedicated42 runtime copy only; shared batch runtime remains unchanged. This does not claim any other card metrics have been rerun. Exact tested evidence SHA-256:

- `native_metrics_proposed.py`: `1e011d4fa3299f33310567b11edf42cf4394bc7ff1d64ad3ef1d0402cf143066`
- `proposed-test-results.json`: `e2ca9ce4f220af9fb13c3a719ed1e2a6a60f9a77b66f36fb95d2f01ef6e692a5`
- `counterfactual-test.json`: `3900cbdc0b5ab68a8aa2a13153cbdc8bc57ec7b43bb83794741c1209d2e98734`
- `alpha-contributors.json`: `1ff7172d9d019775cdf8418dc1aeadd6659dc844537595ffe904bb69fd821844`

## Explicit multiple native views — T72 topology regression

A detail and overview may invoke one unchanged source Form twice. Count unique matching xrefs for source identity, but validate every actual view separately. Multiple views require `source_views` entries with unique `id`, positive uniform `scale`, `translate_x`, `translate_y`, and finite ordered `clip_source` inside the source page; bind their predeclared layout file/hash and authority in `source_views_provenance`. A scalar transform alone is insufficient for multiple views. Existing single-view scalar plans retain their prior transform behavior.

The topology validator builds a source probe for every declared view with original optional-content visibility, serializes/reopens, verifies invocation count and literal wrapper Matrix/BBox against baseline and final, and consumes matching native geometry records so one copy cannot satisfy two views. It maps correction masks through each view and clips before union; all full-page changes must remain inside that union. Each visible affected view retains the unchanged same-status source/native and rendered style checks. Full expected-vs-final native/raster identity still applies; no geometry distortion, extra copy, hidden-source exposure, or mask widening is permitted.

Executed regressions: single-view42 and73 plus explicit detail/overview77A(T72) pass; omitted declaration, undeclared multipleviews, wrong transform, wrong clip, omitted actualview, altered actualclip and exposedOCG fail. These are topology checks only, not final card approval. Frozen validator SHA-256 `b1ec5f5445c713f95ea49f8f818eff598de68719f7c8b9f47c0a86a8ead95a67`; evidence `territory-batch-12/gate-learning/multiview77/regression-results.json`. During validator changes, test isolated copies first and publish validated bytes atomically so active critics never consume a mid-edit implementation.

## Raw feature type before housing eligibility — reopened T44 approval

A prior retained T44 all-10 review was a false positive: generic parcel intersection promoted four OSM residential land-use polygons into mobile-home properties. Land-use names and near-total overlap are not residential-building identities. T45 also included recreation/context, T46 mixed apartment roofs with an administrative office and land-use outlines, and T47 included utilities/waterways. Keep the failed historical review; corrected contracts do not retroactively make it correct.

Preserve separate identities for county parcels, condo units, whole assigned sites, individual buildings and supporting context. A retrieved polygon intersecting an assigned parcel does not assign that entire polygon. OSM `building=yes` alone also does not establish dwelling use: current county aerial inspection split T44's 17 generic buildings into eight dwelling roofs and nine ancillary sheds. T46's administrative office is not a residence. Independently inspect actual source tags, current use and assignment evidence before entering housing references; never infer residence from a generic `kind=property` assertion.

The shared coverage validator now calls `raw_feature_contract.py`. OSM eligible-property records require hash-bound actual raw Overpass elements, matching raw tags and building type, independently resolved residence use with hash-bound local evidence plus method/narrative, and explicit rejection of intersection-only assignment. If raw context is partitioned out, relevant records and context must cover every raw element exactly once with reconciled counts. Existing housing-reference checks continue binding housing to resolved eligible properties. County parcel/unit records retain their separate evidence contract. This deterministic check verifies evidence integrity; a critic must still inspect the aerial/site evidence and assignment truth. A plausible narrative or hash alone is not proof of residential use.

Executed isolated regressions: corrected 44,45A,46A and unaffected77A pass the bounded raw-type check; the actual historical T44 false positive, missing/stale raw binding, false tags, shed promotion, stale use evidence, intersection-only assignment and land-use re-promotion fail. Integrated coverage checks also pass those four current contracts. These tests do not claim new full batch measurements or a new saved-card approval. Evidence: `territory-batch-12/gate-learning/raw-feature-types/results.json`; historical failure: `saved-audit44/regression-osm/{PROJECT-prior.json,review-prior.json,raw-eligibility-review.json}`. This is a versioned rule and regression update, not automatic model training.

## T42 mixed native addition and existing terminal repair

Use [mixed-native-existing-chain.md](mixed-native-existing-chain.md) for the strictly bounded addition-then-terminal-repair chain. Keep the immutable original authority and both exact source stages. The T42 historical whole-ROI medial-width tests at actual2x/4x failed because disconnected stray-tip components polluted the stem-width median; source16x PASS was not accepted as a final2x substitute. Independently reviewed source-only matched normal stations give maximum delta0 at2x and1.1px at4x, within the unchanged1.25px limit. Preserve both historical FAIL reports. No status, style, original-native identity, source geometry, outside-mask, glyph or full-final evidence may be skipped. Every changed native paint must appear in the palette and all original style checks at both scales; disabled checks and threshold overrides fail. Two coincident source paints are both green: narrowing one may be visually hidden by the other, so exact native style proof remains mandatory.

Executed: one actual42 mixed-chain positive; twelve missing/stale/wrongbase/mask/actualnativewidth/narrowing/status/omittedstatus/palette/disabled4x/rejectedreview/threshold negatives; source-bound estimator bitmap and actualPDF mutations; four evidence-contract tests; unchanged single-view73 and multi-view72 topology contracts. Full actual42 PROJECT integration leaves independent visual flags false and has no stage/final/authority or numeric-style mismatch; stale other pretrim evidence remains pending. Neither this scientific correction nor its tests constitute full42 release approval. See `mixed-chain-regression-results.json`.

## T72 western entrance continuity and square-cap ownership

An initially clean-looking two-view card still had a real gap between western River Oaks and Butler. Independent county feature45783/47058 shared-node evidence confirmed the connection. Replacing the original first M moved rasterization along the old segment and failed the unchanged outside-mask test; do not widen masks to hide this. A new subpath preserved every old segment command. A centerline-ended square cap initially protruded beyond the later red owner and was independently rejected; the source-backed final cap retreat kept the red-owned edge clean. The accepted native operation and same-mask zero-delta proof preceded final approval. Butler's county Major classification was recorded honestly even where OSM called it residential; do not erase a source conflict to justify the separate Adams/Hamlin pair.

Final retained T72 bytes a264b55b4dd69ed36e316784c28bbf4eb4f2737ec43c9218603aa90949722fd2 received fresh independent whole/region captures, actual retained native topology replay, and independent native/glyph/1x2x4x equivalence. Quantitative metrics were explicitly transitively bound, not falsely called fresh measurements. Evidence: `territory-batch-12/saved-audit72/critic/independent-retained/{review.json,release-gate.json,retained-equivalence.json}`. The old failed gap and square-cap plans remain regression fixtures.

## Full-response property scope

Apply [osm-property-scope.md](osm-property-scope.md). Highway-only normalization must not hide property candidates from a retained full OSM response. Keep failed candidate scopes, corrected full scopes and independent regression results; recheck other cards produced by the same parser without assuming their map coverage is wrong.

## Dark arrowhead self-occlusion regression (A51, September7 2026)

When measuring road ink beneath callouts, exclude the actual neutral annotation paint from BOTH the rendered-road and no-road comparison. Do not identify arrows only by a minimum RGB brightness: valid #27343C and black filled heads were below the old minimum and punched false triangular holes in the target-road mask. The retained A51 South tip at [210,190] was correctly on its native green centerline but falsely measured1px away.

In the retained NativePDF/native_metrics adapter, the independently tested correction is `leaderindices = self.annotation_vector_indices - roadindices`, using the existing short-single-shaft/filled-triangle shape classifier and explicit road-index exclusion. It replaces the broad brightness-only leader filter; it changes no gap, width, collision, style, or scoring threshold. Native road/label bindings and actual arrow shapes still require verification; the classifier is not semantic proof. Opaque nonannotation rectangles/crops must remain in the visibility comparison. Do not erase a rectangle merely because its color is neutral.

Require the actual-case replay plus dark-gray and black heads, a true tip gap, an unrelated road crossing, a white crop, an opaque neutral rectangle, and colored source overpaint. Eight independent measured invariants passed: actualtip gap1→0 with15roadpixels restored; genuine gap15px, opaque-crop14px and unrelated crossings still fail. The false-failure PDF hash was8b8762ea707d90e150ecb73389a388de32f307e10004b8d5a2d1464b7be74d28; before runtime8a958b8e3cf018a56a75db4b2681d777744dff7e9d11bd30d6af214f64bba0e8; tested runtime d62bfdf26096fc17adc87aa10d0254633e8b56d830ee46047142db9c51229e9e. Preserve before/proposed code, executable fixtures, actual mask crops, and reports with the batch checkpoint. This utility test does not approve A51 or any other card.

A second A51 failure showed stale final drawing indices after mutating a reused native PDF Form. Reopen the serialized actual PDF before assigning final drawing IDs; compare each actual path geometry/style to its source binding. All overview target masks were empty before correction. A cached pre-patch page is not final-artifact evidence. Keep the failure and source-bound corrected reconciliation; do not substitute an arbitrary nonempty road mask.


## A53b: unnamed direct access must remain truthful

A directly readable West access descriptor cannot be recategorized as a named street merely to bypass a callout requirement. Conversely, a verified unnamed entrance need not acquire an unnecessary arrow when the checked `descriptive_access` contract establishes a direct fit. Preserve both real entrances, their source/serving-road/site bindings, and explicit directions. Regression tests must reject named roads misclassified as unnamed; missing or stale source, artifact, road, site and label bindings; hidden or duplicate entrances; false direct fits; collisions; off-segment glyphs; and directions mismatch. Existing named-street, feature-callout and approved numbered-key contracts remain unchanged. Synthetic contract fixtures do not establish a card's geographic or visual approval.

V3 reconstructed enforcement requires independent original-map and authoritative-inventory corroboration, complete hash-bound site entrance inventory, and fresh actual-PDF native glyph/visibility/collision/gap recomputation. Rebinding claimed metrics cannot substitute for measurement. This proposal requires new independent review.

V4 regression: when one native path contains multiple named or descriptive segments, measure each label only against its verified contiguous source subsegment. Select actual native operators with their existing graphics state and transforms; a nearby return leg cannot provide substitute target ink. Preserve exact gap thresholds, and require both a wrong-subpath negative and truthful same-PDF positive control.


## A69b/A69c: hidden source backgrounds are not visible road obstacles

Do not isolate chromatic primitives while dropping later neutral paint: that exposes hidden colored backgrounds and falsely reports label collisions. Compare the original all-vector native render to its neutral-vector-only render with text excluded, retaining neutral paint, order, graphics state, clips and transparency in both. Every exactly differing RGB pixel is visible colored contribution; require zero descriptor-glyph intersection. No whitelist, per-card mask or color tolerance exception is allowed. Tests must accept a colored background fully covered by original white paint, reject visible or partially/translucently covered colored fills and real street/building overlaps (including faint visible contribution), and still reject an erased label. The earlier v4 false-positive evidence remains retained.

### Uniform-scale native join extraction
PyMuPDF exposes lineJoin multiplied by uniform view scale. Compare its exact float32 scaled source value while keeping every other native style field exact. Independent real4x descriptor and changed-join rejection plus .95/1.35/3 scale controls passed; no tolerance changed.

### A69c: test excluded building paint before handoff

Run the installed visible-colored-contribution check on descriptive labels before declaring builder measurements complete. Road and purple-building masks alone omit red excluded-building fills. The retained dcc2b6a919e073d369f3bbf7481dc8c4af53e964d676a5bd84614c261a6419ed card passed generic measurements but failed on one West glyph pixel over a visible red-building fringe. The corrected 9e00f01692bc8760917fd07ccc9ce730d80a1e2ef5ee6fec0e636e4059216259 retains9pt text and all native drawings, with zero colored contact and the original minimum gap. Preserve this failed/corrected pair; a generic measurement pass never replaces the actual-ink gate or independent final review.
