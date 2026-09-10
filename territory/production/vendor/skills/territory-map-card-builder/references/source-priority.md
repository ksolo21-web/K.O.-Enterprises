# Source Priority and Legal Data Use

## Priority for street names and topology verification

1. County or municipal GIS: road centerlines, addresses, parcels, municipal boundaries, rights-of-way.
2. State GIS open data.
3. OpenStreetMap: current local streets, private roads, service roads, and cross-source checks.
4. Census TIGER/Line: fallback road and boundary context.
5. Old territory cards: historic intent only.

## Priority for rendered linework

1. An accepted updated user-supplied hand-drawn map in `preserve_supplied_map` mode.
2. County or municipal vector geometry in `vector_rebuild` mode.
3. State GIS, OpenStreetMap, then TIGER/Line as documented fallbacks.

Live commercial maps may verify current names and topology. They must not be traced, and they do not override accepted supplied colors or geometry without an explicit user correction.

Acceptance locks the rendered-linework authority. A later request to fix a marked label, junction, endpoint, or color defect remains in `preserve_supplied_map`; it is not permission to rebuild the map. Record explicit user authorization before changing to `vector_rebuild`.

For named properties and entrances, verify the name and public access relationship with a current live map and, when available, an official property source or visible entrance signage. Commercial Street View may be used to read a sign or confirm which public road serves an entrance, but never as geometry to trace. Record the verification source and date.

## Required source record

For each source, record:

- source organization;
- dataset title;
- dataset or service URL when available;
- license or use terms;
- retrieval date;
- geographic coverage;
- layer names;
- feature IDs used;
- known limitations.

## Conflict policy

- In `preserve_supplied_map` mode, preserve the supplied geometry and use current sources to flag name or topology conflicts.
- In `vector_rebuild` mode, prefer the highest-authority legal source for geometry.
- Use a newer lower-tier source to flag possible recent construction or renaming.
- Do not silently merge conflicting lines.
- Record the conflict and the decision.
- When the conflict changes work coverage, require explicit resolution before release.

## Prohibited source behavior

- Do not trace proprietary map tiles into a new dataset.
- Do not use commercial screenshots as exact road coordinates.
- Do not redraw an accepted updated supplied map simply because a current basemap has a different visual style.
- Do not invent a street because it appears faintly in a scan.
- Do not omit a road merely because the old card omitted it.

## Current inventory discovery before completion

Run this check for every territory, including accepted new drawings and previously completed cards. Preserve accepted geometry while investigating; do not confuse a visual preservation pass with a current coverage pass.

- Query the full assigned boundary plus immediate edges, not only names already on the old card. Retain the actual query bounds and filters; reconcile all pages against service count/ID responses or document why the source returns the complete set. A truncated or partial response cannot support a “no missing streets” conclusion.
- Record a dated feature-by-feature comparison: source ID/name/type, match on the card, location within/on/outside the boundary, applicable work rule, and disposition of every unmatched feature. Include relevant private roads, unnamed access, and newly developed eligible properties; do not infer property eligibility from the presence of a road.
- Record retrieval dates separately from dataset update or imagery capture dates. Mark unknown source recency explicitly. Cross-check possible recent development with a second current source and available official site/development evidence or dated imagery. An undated basemap or a search returning no hits cannot establish absence of additions.
- Summarize confirmed additions, excluded non-work features with reasons, and unresolved candidates. If the western/eastern or other coverage edge is unknown, the full inventory remains unverified even when the known portion contains no additions.
- Keep URLs, attribution, feature inventories, recency limits, and evidence in a separate audit file. Do not print source-credit or audit lines on the territory card.

## Assignment representation and complete inventory

Apply [coverage-model.md](coverage-model.md). Both polygon and explicit road-segment assignments require complete source-bound coverage and current road/property inventory evidence. Segment assignments do not invent a closed polygon, skip immediate edges or waive unresolved candidates. Require the deterministic coverage/inventory gate and independent source review before release.
