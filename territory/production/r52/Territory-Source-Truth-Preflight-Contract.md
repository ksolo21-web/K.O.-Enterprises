# Territory Source-Truth & Pre-Critic Contract — R49 — 2026-09-12

## Purpose
R49 prevents a self-consistent but wrong reconstruction from proving itself correct. A territory card may not enter formal critic review until both geography/source truth and visible family resemblance have passed an explicit pre-critic gate.

This contract is mandatory for every new card, full rebuild, old-card conversion, material geography redraw, or repair prompted by a geography/family-resemblance rejection. It supplements, and never weakens, the existing builder, critic, coverage, family, identity, and export contracts.

## 1. Source-truth lock before drawing
Before map rendering, create an artifact-bound `source_truth_preflight` record. The builder must work from raw source evidence, not from a prior reconstruction or critic report.

For geography rebuilt or materially changed, require at least two source classes:
1. the assignment/boundary authority (current BIG/master map, approved old territory source, or explicit user-marked assignment evidence); and
2. an independent current street/topology source (official municipal/GIS/street map and/or live map used under the standing territory-map rules).

The record must inventory every worked, boundary, context, entrance, short court, cul-de-sac and connecting branch needed to understand the territory. For every navigational road/branch, record verified name, status, endpoints, intersections/parent road, cul-de-sac/dead-end/through status when applicable, source evidence, and whether it is rendered or intentionally omitted.

Hard vetoes before drawing/critic:
- any invented intersection or through-connection;
- any road shown as a through street when source evidence shows a cul-de-sac/dead end;
- any worked or boundary branch omitted without an explicit evidence-backed disposition;
- any unexplained street inside the assigned boundary whose work/disposition could alter coverage;
- any assignment boundary inferred from a screenshot box/frame instead of actual cross streets/segments;
- any source conflict left unresolved;
- any geography conclusion supported only by a builder-generated reconstruction, prior critic prose, validator output, or prior passing score.

## 2. Endpoint-to-endpoint topology trace
Before rendering, trace every named/colored road from endpoint to endpoint. Record each connection as an edge and each intersection/termination as a node. Verify each branch against the raw current source. The builder must explicitly confirm `invented_connections=0`, `unresolved_omissions=0`, and `topology_conflicts=0`.

## 3. Pre-critic visual family gate
After a candidate is rendered but before formal critic dispatch, inspect the exact candidate at actual size plus at least 2x and 4x map crops.

For newly redrawn residential/neighborhood maps, compare side-by-side against the exact saved Territory 273 as the mandatory map-drawing comparator, while A33/60AB/330 remain canonical shell authorities. Also compare against at least one additional approved New Designed card with similar density when available.

The preflight must assess, visually and not only numerically:
- street stroke weight and centerline grammar;
- natural street curvature and cul-de-sac geometry;
- direct/curved road-following label behavior;
- label size/weight and street association;
- map occupancy, whitespace and neighborhood scale;
- perimeter/context treatment;
- junction cleanliness and branch completeness;
- whether the map looks like the same hand/system as 273 and the New Designed family rather than a sparse node diagram, generic schematic, consumer-map screenshot, or arbitrary redraw.

Any obvious family mismatch must be repaired before critic dispatch. A shell/token validator PASS cannot satisfy this gate.

## 4. Formal critic must independently re-ground
The formal critic or mandatory internal reviewer must not treat `source_truth_preflight`, builder prose, prior critic reports, or deterministic validator PASS as proof that geography is correct.

The reviewer must independently inspect the raw assignment source and current topology source and reconstruct enough of the road graph to challenge the candidate. At minimum it must independently verify every worked/boundary road and every junction/termination that determines coverage. Record this in `critic_source_truth_review`.

When no separate critic-agent runtime exists, the authorized internal reviewer remains non-independent in provenance (`critic_independent:false`) but must still operate in critic-only mode and re-open the raw source evidence. It may not copy the builder's topology ledger as its own review.

## 5. Reviewer anti-anchoring rules
- Builder scores/pass claims are not evidence.
- Prior scores are not evidence when the user has rejected the artifact.
- Deterministic validators prove structure/consistency only, never geography or family resemblance.
- A user-reported visual/geographic defect immediately invalidates the affected approval and any positive fixture status derived from it.
- Territory 269's R48 false-pass is a permanent negative regression example: a technically consistent PDF can still fail source truth and family resemblance.

## 6. Required preflight schema
`source_truth_preflight` must include at least:
- `artifact_sha256` for post-render preflight (or `planned_artifact` before render);
- `assignment_sources[]` and `topology_sources[]` with raw-source identities;
- `builder_generated_source_count` (must not be the sole source class);
- `roads[]`, each with `name`, `role`, `render_disposition`, `endpoints`, `connections`, `termination_type`, `source_evidence`, `result`;
- `invented_connections: 0`;
- `unresolved_omissions: 0`;
- `topology_conflicts: 0`;
- `boundary_box_used_as_geography: false`;
- `endpoint_trace_complete: true`;
- `all_worked_boundary_context_roads_inventoried: true`;
- `precritic_family_review` with `territory_273_side_by_side: true` for residential/neighborhood redraws, `actual_size_inspected`, `two_x_inspected`, `four_x_map_inspected`, `map_drawing_match_passed`, `obvious_family_mismatch_count: 0`, and notes/evidence.

## 7. Critic schema
`critic_source_truth_review` must include:
- `raw_sources_reopened: true`;
- `builder_topology_ledger_used_as_proof: false`;
- `prior_score_used_as_proof: false`;
- `independent_topology_reconstruction_completed: true`;
- complete reviewed road/junction inventory;
- `invented_connections_found: 0`;
- `unresolved_omissions_found: 0`;
- `source_conflicts_unresolved: 0`;
- candidate-vs-source evidence and result.

Any missing/false required field or positive defect count blocks release and caps geography/family/overall at 8 until repaired.

## 8. Validator role
`validate_source_truth_preflight.py` validates schema, counts, artifact binding and anti-anchoring declarations. It cannot decide whether a street actually exists or whether a map visually matches 273. Those remain mandatory human/model visual/source judgments.

## R50 naming/label bridge — 2026-09-13
R49 topology truth must now feed the R50 label inventory. For each visible road/branch, source evidence must resolve not only geometry but also naming status: `named_public`, `named_private`, `unnamed`, or verified non-road feature. Uncertainty is not permission to omit a label; unresolved name/private status blocks preflight. The R50 `label_completeness_review` must be reconcilable to this road inventory with zero unaccounted visible roads.
