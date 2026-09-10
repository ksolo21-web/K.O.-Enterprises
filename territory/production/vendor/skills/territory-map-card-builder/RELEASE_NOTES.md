# Territory Map Card Builder v2.2.5

## Legend visual-standard gate

- Replaced the old presence-only legend check with measured sidebar requirements for readable label size, compact rounded swatches, consistent row spacing, and left alignment.
- Made the approved lower divider, calendar icon, `UPDATED` label, and date block mandatory template elements.
- Added a final-size visual comparison and a release failure for compressed legend rows, undersized text, missing sidebar elements, or excessive unused space.
- Added validator regression tests for undersized legend labels, missing calendar icons, and excessive legend dead space.

## v2.2.4

## Final-render, same-status gate repair

- Compare green, yellow, and red independently so a multistatus junction cannot borrow another status's width, color, softness, or texture; keep curvature tied to the combined approved source path across valid status handoffs.
- Compare width, softness, and texture against same-status local approved pixels, with optional explicit untouched reference boxes for sparse junctions.
- Run the gate on the actual final-PDF raster and tolerate only a fixed low-level resampling floor for centerline sampling; exact outside-mask preservation and all other style checks remain fail-closed.
- Set the 2x centerline limit to 2.00 px, exactly one approved-source pixel, and retain the human 4x visual veto.

## v2.2.3

## Repaired-stroke style fidelity gate

- Added a deterministic final-2x analyzer for repaired stroke width, status color, edge softness, centerline/curvature, texture, mask-boundary seams, and unexpected work-status pixels.
- Added a mandatory paired-4x visual review with a human-visible mismatch veto, including endpoint character that automated measurements can miss.
- Made analyzer reports, report hashes, per-mask measurements, and zero repaired-style mismatches required release evidence whenever a correction touches colored linework.
- Locked the numeric tolerances so projects may make them stricter but cannot loosen them to force a repair through.
- Validated the gate against the current visibly redrawn Territory 252a candidate; the analyzer rejects all three repaired junction masks.

## v2.2.2

## Approved-map preservation lock

- Locked `preserve_supplied_map` after a user accepts a supplied map; local correction requests no longer permit a full geometry rebuild.
- Added approved-base hashes, explicit full-redraw authorization state, and declared correction masks.
- Added release-blocking gates for unauthorized mode changes and for any rendered pixel changed outside the declared correction masks.
- Replaced the blanket ban on overlays with a narrow rule: localized corrections to an approved raster or PDF must use a mask-locked layer over the immutable base and pass an identical-size rendered comparison.

## v2.2.1

## Status-transition geometry hotfix

- Added release-blocking counters for mixed-status stroke overlap, colored endpoint artifacts, and branch endpoint overshoots.
- Required one explicit owner for every work-status transition node; adjacent status strokes must terminate cleanly without stacked caps or blended junction blobs.
- Added a 2x-render inspection for orphan colored dots and for side branches that protrude into a differently colored boundary road.

## v2.2.0

## Named-site, entrance, and navigation-context update

- Added verified apartment-complex and named-property labels, with one unobstructed regular-weight site name centered in the property zone.
- Added exact verified entrance inventories and concise entrance callouts such as `North Entrance` and `West Entrance`.
- Added entrance-arrow binding to the actual access stem, target-box and access-distance validation, map-scale leader ranges, single-shaft enforcement, filled-marker binding, and collision checks outside the target radius.
- Added connected major-road navigation context. A major-road name without a drawn, verified approach path now fails release.
- Added declared, uniform supplied-map scale and translation checks; stretching, clipping, hidden colored pixels, and non-uniform scaling now fail.
- Added directions checks that require every entrance to be associated with its serving public street and every displayed major road to be named.
- Added a Territory 252 regression fixture for Forest Ridge Apartments, its North and West entrances, W University Dr, S Main St, W 2nd St, and Wilcox St.

## v2.1.0

## Label-quality and supplied-map update

- Added `preserve_supplied_map` as the default mode for approved updated hand-drawn maps; live maps verify names but do not replace accepted colored linework.
- Made direct placement mandatory whenever a full street name fits; arrows are now limited to genuinely short streets.
- Added the 2-15 px direct-label spacing gate and an 8 px maximum gap spread so curved labels cannot be flush at one end and lifted at the other.
- Added hard failures for street-line coverage, wrong-road labels, bold or inconsistent street fonts, unnecessary callouts, malformed arrowheads, arrow/label overlap, arrow/arrow overlap, wrong arrow targets, and leaders crossing unrelated roads.
- Required arrows to use one clean leader with a filled triangular head and terminate on the assigned street stem rather than only its cul-de-sac bulb.
- Required a one-page front, no back, no do-not-work list, and a final PDF smaller than 300,000 bytes.
- Added manifest-level label audits and regression tests for partial-lift labels, unnecessary arrows, arrow overlap, bold labels, and file-size failure.

## v2.0.0

## Major changes

- Rebuilt as a GIS-first territory-card skill.
- Added automatic trigger coverage for territory-card creation, revision, conversion, coverage-gap analysis, Canva styling, PDF export, and numbered territories.
- Added negative trigger boundaries for geopolitical, fantasy, navigation, and sales-territory tasks.
- Prohibited copy/paste redraws, screenshot tracing, AI-generated street geometry, and cosmetic patch-over corrections.
- Added authoritative source hierarchy and cross-source conflict handling.
- Added segment-level work rules and mandatory territory-facing side for perimeter streets.
- Added vector SVG/PDF workflow, professional label rules, page-fit controls, and correction persistence.
- Added fail-closed QA counters, JSON Schema, semantic validator, trigger-contract validator, examples, and regression tests.
