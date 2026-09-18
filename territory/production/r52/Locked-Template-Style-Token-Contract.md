# R48 Locked Canonical Template, Style Tokens & Identity Layer - 2026-09-12

## Purpose
R48 preserves the locked shell/style system and adds fail-closed canonical card identity/filename normalization from all new current-format territory cards. The builder must start from the locked R48 renderer and token set, not reconstruct the sidebar, panels, typography, icons, or spacing by eye.

## New-output authority
- Token file: `references/R48-Canonical-Style-Tokens.json`.
- Renderer: `scripts/render_locked_template.py`.
- Strict final-artifact validator: `scripts/validate_style_token_layer.py`.
- Human-inspection asset: `assets/Canonical-New-Designed-Template-R48.pdf`.
- Locked directions badge: `assets/a33-directions-car.png`.

For a new card, old-card conversion, or full current-format rebuild, the exact final PDF must retain R48 token provenance and pass the R48 strict token validator and the existing canonical family validator. A script pass never replaces actual-size critic review.

## Fixed shell
The 768 x 480.5 pt page, sidebar, map panel, directions panel, palette, legend swatches, calendar/update block, directions badge, compass treatment, margins and gutters are fixed by tokens. Builders may not widen the sidebar or alter panel geometry to solve map density.

## Locked responsive variants
Only these responsive shell behaviors are allowed without explicit user approval:
1. `one_line_locality`: A33-style divider/legend placement.
2. `two_line_locality`: controlled divider/legend shift for localities such as `Oakland Township` or `Rochester / Rochester Hills`.
3. Territory ID: DejaVu Sans Condensed Bold, 40 pt when it fits; decrease only enough to fit the 117 pt locked ID box, never below 28 pt. Do not wrap the territory ID and do not widen the sidebar.

## Typography
All newly rendered shell text uses DejaVu Sans / DejaVu Sans Bold, except the territory ID which uses DejaVu Sans Condensed Bold. Ordinary street labels remain regular weight. A33/60AB Helvetica is grandfathered reference evidence, not permission to substitute fonts in new R48 output.

## Map-layout modes
R48 preserves the allowed R46 family modes: `full_map`, `full_plus_detail`, `split_detail`, and `site_building_assignment`. The outer shell never changes. 330 supplies the locked split-detail divider coordinates. Internal full-plus-detail/site diagrams may vary only inside the map panel and remain subject to family, label, clutter, and map-balance gates.

## Existing-card revisions
A bounded edit to a previously approved exact card does not force a wholesale rebase merely to add R48 metadata. Preserve the approved base under correction-mask rules. But a newly built/rebuilt card may not use this grandfathering rule to avoid R48.

## Test fixture truthfulness
R48 `TEST-*-R48-FIT.pdf` files and `R48-Canonical-Identity-Template-Fit-NOT-FOR-FIELD-USE.pdf` are shell/layout stress fixtures only. They do not certify geography, work colors, labels, boundaries or assignment status. Current-master crops used for missing territories are evidence of layout fit only.

## Fail-closed release rules
New/rebuilt output fails if any of these are missing or false:
- exact R48 token provenance;
- strict style-token validator PASS;
- canonical family validator PASS;
- allowed locality/ID variant;
- mandatory internal critic review and all R46/R45/R44 gates;
- final exact-saved-PDF recapture/review.


## R48 canonical identity/naming integration — 2026-09-12
R48 adds `Territory-Identity-Naming-Contract.md` as a hard prerequisite. Source/master labels remain source aliases only. New/rebuilt cards must use a verified `card_identity`, the derived congregation-facing display ID, and the exact derived canonical filename. The locked renderer and internal/critic release path fail closed on identity mismatch.

R48 production output must also pass `scripts/validate_territory_identity.py` and `scripts/validate_pdf_identity.py`.