# Explicit coverage and current inventory contract

Use this evidence gate for every card, irrespective of source age or map mode. Never invent a parcel boundary or claim polygon closure when the assignment is actually explicit colored road segments and worked sides.

## Represent the actual assignment

Set top-level `coverage_review.representation` to `closed_polygon` or `explicit_road_segment_assignment`.

- For `closed_polygon`, preserve the original strict `boundary.closed=true`, `no_self_intersections=true`, `geometry_verified=true` checks. A vector rebuild always uses this branch.
- For `explicit_road_segment_assignment`, require `preserve_supplied_map`, retain the original assignment source/hash, and enumerate every assigned segment with verified endpoints, work rule and worked side. Split IDs where endpoints or rules change. Set project `boundary.closed=null` and `boundary.no_self_intersections=null` to record that polygon tests are inapplicable; require `boundary.geometry_verified=true`. Do not set these polygon flags to true or call a known open polygon a segment assignment to escape a failure.
- This representation is not automatic permission to narrow coverage to known roads. Establish the complete assignment and audit extent from source instructions and explicit street/side assignments. Inspect immediate edges, corner/frontage cases, private access, development and eligible properties. If the assignment edge or a candidate's eligibility is unresolved, fail release regardless of representation.

Require `coverage_review` in builder and critic JSON:

```json
{
  "representation": "explicit_road_segment_assignment",
  "map_mode": "preserve_supplied_map",
  "source_ref": "Original assignment file/member and source evidence",
  "source_sha256": "64-character original source SHA-256",
  "geometry_verified": true,
  "full_coverage_resolved": true,
  "audit_extent": {"crs": "EPSG:4326", "bounds": [-84, 42, -83, 43], "evidence": "Actual query extent justified against complete assignment and immediate edges"},
  "edges_reviewed": true,
  "edge_evidence": "Retained source/feature review resolving every assignment edge",
  "unresolved_edges": [],
  "segment_assignments": [
    {"road_id": "actual-project-segment-id", "source_feature_id": "source feature ID", "from_ref": "Verified endpoint/junction ID or precise coordinate locator", "to_ref": "Verified endpoint/junction ID or precise coordinate locator", "classification": "perimeter", "work_rule": "inside_only", "inside_side": "east", "verified": true, "assignment_evidence": "Original source instruction, exact segment and worked-side evidence"}
  ]
}
```

The bounds above illustrate syntax only; never reuse them. Enumerate every assigned interior/perimeter segment; excluded segments may be included with `do_not_work`. Non-perimeter sides are `not_applicable`. In builder manifests each record must match the actual road ID, source feature ID, classification, rule and side. Existing explicit exceptions require resolving/splitting the assignment into unambiguous segment records before release. For the polygon branch, the critic additionally records `coverage_review.polygon_boundary` with the three true polygon flags; the builder uses its existing top-level `boundary`.

## Enforce full current inventory for both representations

Require top-level `current_inventory_review` in both builder and critic JSON. Keep the existing fields `check_date`, `full_boundary_and_edges_checked=true`, `source_retrieval_complete=true`, `relevant_property_eligibility_resolved=true`, `unresolved_discrepancies=[]`, and `evidence` identifying the retained dated audit. Also require:

- `unresolved_candidates=[]` (cannot omit unresolved candidates from one list to pass another);
- `audit_extent` in the same structure/CRS as coverage, containing its complete bounds and immediate edges;
- `sources`: complete source/query records, each with `id`, `url`, ISO `retrieved_at`, `source_recency` (dated dataset/imagery or explicit unknown), `query`, `retrieval_evidence` (pagination, transfer-limit and source count/ID reconciliation), `complete=true`, `returned_count`, and `retrieved_feature_ids`;
- `feature_dispositions`: one record for every and only retrieved `(source_id, feature_id)` pair, including unmatched roads, access and properties. Require `source_id`, `feature_id`, `kind` (`road`, `access`, `property`), `location`, `disposition` (`matched`, `verified_addition`, `excluded`), `eligibility` (`eligible`, `ineligible`, `not_applicable` only for non-properties), `assignment_evidence` explaining inclusion/exclusion under actual coverage rules, and supporting `evidence`.

Retain complete ID lists with no duplicates and exactly matching returned counts. Every assigned project's source road feature must have a disposition. When drawing geometry uses original PDF/path IDs rather than current GIS IDs, preserve that truthful `source_feature_id` and record `roads[].inventory_feature_refs=[{"source_id":"inventory source ID","feature_id":"current feature ID"}]`; every explicit binding must match a disposition. Include the same `inventory_feature_refs` on the corresponding `coverage_review.segment_assignments` record for the independent critic contract. Do not relabel supplied drawing geometry as GIS geometry merely to align IDs. Record additional imagery/development candidates as source features too; do not drop them because they were absent from the centerline query. Cover both road and property features. A genuinely empty property query is allowed only with a separate source record `feature_kind="property"`, complete zero-count/empty-ID retrieval, and nonempty `property_absence_evidence` explaining the verified absence. Do not equate a road query with a property eligibility review.

The deterministic gate checks evidence presence and internal consistency, not geographic truth. The critic must independently inspect source artifacts, complete extent, endpoints/sides, every unresolved/excluded candidate and fresh card screenshots. Missing or inconsistent coverage/inventory evidence blocks release and caps critic score at 8. Target 10 and minimum 9 are unchanged. A source acceptance or road-segment representation never waives discovery, property eligibility, connected major roads, preservation or any other gate.

## Keep topology and coverage evidence separate

Coverage representation never authorizes geometry changes. Source-backed authorized native additions/removals use [native-topology-gate.md](native-topology-gate.md); existing-path repairs retain their unchanged comparator and cutoffs. Keep historical generic comparator failures as history. Require immutable original identity, exact declared native deltas, actual final expected geometry/render, zero outside masks, original same-status style and independent 4x review before release.
