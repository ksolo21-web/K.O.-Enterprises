# Rendering Standard

## Geometry

- In `preserve_supplied_map` mode, retain the accepted supplied colored linework as one immutable source layer before any declared uniform transform. Do not redraw, recolor, straighten, or trace over it outside explicit user-directed correction masks.
- Record the approved-base hash and lock its map mode. A local correction request never authorizes replacing the base with newly reconstructed geometry.
- For requested defects on an already accepted map, leave the approved base immutable and place each repair on a separate layer confined to a declared rectangular or polygonal correction mask. Masks may include a minimal guard for renderer interpolation, but must not encompass unrelated streets or labels.
- Compare identically sized approved-base and candidate renders. Every changed pixel must fall inside a declared correction mask; a single changed pixel outside all masks blocks release.
- A correction mask is not permission to change the source drawing style. When a repair touches a colored street or boundary stroke, compare the repaired pixels with nearby untouched approved strokes at the final 2x render. Match width, status color, edge softness and antialiasing, curvature/centerline character, texture, seam continuity, and endpoint profile.
- Run the deterministic repaired-stroke analyzer and inspect paired 4x crops for every stroke-repair mask. A visible mismatch blocks release even if automated metrics pass; a small or local redraw is still a redraw.
- Reuse the approved path and adjacent source-stroke properties whenever possible. Do not substitute a newly generated line, and never loosen the style thresholds to force acceptance.
- A supplied map may be translated and uniformly scaled only when label clearance or verified approach-road context requires it. Record `scale_x`, `scale_y`, and translation; require `scale_x == scale_y` within 0.001. Do not stretch, crop, or hide any supplied colored segment.
- In `vector_rebuild` mode, keep roads as SVG paths or equivalent vector objects.
- Preserve topology: connected source streets must connect in the drawing.
- Simplification may reduce vertices but must not change intersections, road order, loops, cul-de-sacs, or boundary relationships.
- Assign exactly one work status to each rendered segment. At a status transition, designate one node owner and trim adjacent strokes to clean tangent endpoints; do not stack differently colored strokes or caps.
- End side branches before a differently colored boundary stroke. A branch must not protrude into or through that boundary, and no orphan colored dot or cap fragment may remain after trimming.
- Inspect status transitions and branch endpoints in the final 2x render as well as in vector geometry; anti-aliased mixed-color blobs count as failures even when the centerlines appear mathematically connected.
- Maintain a modest outside context buffer.

## Labels

- Attach each label to a source road feature or an explicit label anchor.
- Use one regular-weight typeface across the map; street names must never be bold.
- Place direct labels 2-15 px from the assigned street with no street-line coverage.
- Curve a name with its road when needed. Measure the guide at multiple points: minimum and maximum gaps must stay within 2-15 px, and the spread must not exceed 8 px.
- Audit adjacent letters within a curved word using actual isolated glyph ink, not only whole-label boxes or road gaps. Apply [label-glyph-review.md](label-glyph-review.md); preserve natural kerning and regular type while repairing guide-induced overlap or visible touching.
- If a full name fits directly or on a curve, do not use an arrow.
- For a genuinely short street, use one straight or gently routed leader with a filled triangular arrowhead. Start just outside the label, do not cross labels, other arrows, or unrelated roads, and terminate on the assigned street stem rather than only its bulb.
- Keep required labels at readable print size.
- Prevent labels from crossing page edges, intersections, legends, or territory numbers.
- Use repeat labels when a long or split street would otherwise be ambiguous.

## Approved numbered-key reference connectors

Preserve the connector convention of a user's approved original numbered-key map. Original A2 markers such as 10 and 15 use short neutral, single-segment reference ticks without arrowheads. Keep that source style and explicitly record the connector as an approved numbered-key reference with no arrowheads. Do not add a triangular head merely because the connector resembles a callout. New street callouts and entrance callouts continue to require filled triangular heads and their specified target contact.

Verify the complete number → connector → currently verified street → key binding against current street evidence and the approved source. Record honest street-end proximity measurements and their source/render scale, preserving any small approved source gap rather than claiming literal contact. Require unambiguous association with the intended street, close and clear association at the number end, and separation from the number's glyph ink. Inspect actual-size and close-up evidence for wrong-road association, confusing label proximity, and collisions with labels, other connectors or unrelated streets. Preserve all applicable spacing, readability and collision gates; neither an old number nor its tick establishes a street identity or permits an inferred name.

## Named sites and entrances

- Place a verified apartment-complex or property name once in open interior whitespace, centered in its verified site zone when practical.
- Match the map's regular-weight font family. Keep the site name clear of streets, colored routes, building/work shapes, and other labels.
- When the site name is already present, use concise entrance labels such as `North Entrance` and `West Entrance`.
- Attach each entrance callout to a verified access stem or junction. Use one clean leader and a filled triangular arrowhead.
- The arrow tip must land inside the entrance target box and within the declared tolerance of the access line. It must not stop on the adjacent public road, site center, building, parking area, or only a cul-de-sac bulb.
- Allow an entrance arrow to touch route geometry only within its declared target radius. Keep the rest of the arrow clear of every road, label, and other arrow.

## Major-road navigation context

- Every card must show at least two distinct verified major cross roads, visibly drawn and readably labeled with connected approach; add the minimum verified context needed to meet this requirement.
- Draw the major road and its verified approach connection; a label with no connected line does not pass.
- Keep added context outside the accepted supplied-map layer. Use the applicable work-status color; verified non-work context is red.
- Do not shrink the working area more than necessary. Scaling must be uniform, documented, and visually checked at final export size.

## Page fit

- Include safe margins on all sides.
- The full territory and every required road must fit.
- Never cut off the top, bottom, or sides to enlarge one section.
- Use crop marks or bleed only when intentionally requested.
- Export one front page only. Do not include a card back or do-not-work address list.
- Keep the final PDF below 300,000 bytes.
- Include brief directions that associate every labeled entrance with its serving public street.

## Styling

- Work meaning outranks decoration.
- Pair color with line style, marker, label, or legend so the map remains understandable in imperfect printing.
- Maintain text contrast against every background.
- The approved sidebar legend is a measured layout component. Render the three rows in this exact order: yellow `Work Inside Only`, green `Work Both Sides`, red `Do Not Work`.
- Use regular legend labels of at least 9.5 pt, compact rounded swatches 18-24 pt wide and high, and consistent 36-50 pt center-to-center row spacing. Keep swatches and labels left-aligned within 2 px.
- Preserve the lower sidebar divider, calendar icon, `UPDATED` label, and date block when the approved card template includes them. Reject compressed rows, undersized labels, missing template elements, or excessive dead space between the legend and update block.
- Compare the final sidebar at output size with the approved legend reference; the presence of the correct words and colors alone is not a pass.

For the fail-closed limits and required evidence for localized linework repairs, read [stroke-style-gate.md](stroke-style-gate.md).

## Mandatory two-major-cross-road evidence

Apply [major-crossroads.md](major-crossroads.md) to every card. Require at least two distinct verified physical major roads and a complete `major_crossroad_review`. Repeated names, aliases, divided carriageways, floating labels, directions-only mentions and minor internal streets cannot count. A missing or unverified second major road hard-fails release; the critic caps at 8 with release false. Preserve accepted linework and add minimal separate-layer verified context with uniform scaling only when necessary.

## Typed native topology edits

For source-backed authorized native additions/removals only, apply [native-topology-gate.md](native-topology-gate.md). Keep `contains_stroke_repair=true`, distinguish typed topology masks from existing-path repairs, and run every applicable gate. The original repair comparator and numeric cutoffs are unchanged; do not falsely report an old centerline failure as passed or bypass it by omitting colored edits.

Require the bidirectional map-versus-housing-instructions gate in `housing-instructions.md`. The marked assignment controls obsolete housing restrictions; preserve all map-side, exclusion and other-territory/access limits. Review actual full-page text, including work notes, and record the user decision.
