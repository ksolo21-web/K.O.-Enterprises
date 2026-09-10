# Independent duplicate worked-coverage review

Require `duplicate_coverage_review` with `current_card_id`, hash-bound `scope` and hash-bound `independent_review`. The local `scripts/duplicate_coverage_contract.py` replays canonical physical road intervals and side intersections. The critic gate must bind the current scope card to the actual candidate PDF hash and authoritative assignment-source hash, not merely to another retained PDF.

Inspect the complete active-card registry and every bound card artifact, assignment source and road inventory. Check all worked roads in polygon and explicit-segment cards, including immediate edges and related neighboring cards. Record evidence for scope completeness; a chosen subset with no overlaps is insufficient. A card’s assignment inventory must correspond to its actual rendered work colors and instructions.

Normalize source-backed physical road identities across aliases, drawing path IDs, dataset feature IDs and subdivisions. Verify the declared source measurement system, canonical direction, exact measured endpoints, and side conversion. Relative left/right must respect canonical direction; cardinal sides require source evidence. Independent inspection must verify complete represented lengths, not merely the presence of a road ID. Unresolved identity, endpoints, sides, incomplete retrieval or stale artifacts block release.

Both-sides contributes both physical side tokens. One-side contributes only its verified physical side. Excluded and context-only segments contribute no worked occupancy. Any positive-length same-side interval overlap within one card or across cards fails, including partial and nested overlaps, aliases and different subdivisions. Opposite physical sides, disjoint intervals, and endpoint-only contact are not duplicated worked coverage. Do not reject matching street names alone.

The independent review JSON binds `scope_sha256`, `reviewer_role="independent_territory_card_critic"`, actual `reviewer_id`, retained hash-bound source/actual-card inspection `evidence`, `unresolved_items=[]`, and true `complete_active_scope_verified`, `canonical_identity_verified`, `measures_and_sides_verified`, `source_to_artifact_inventory_verified`. These fields record performed independent review; do not manufacture them to satisfy the script. A synthetic gate regression is not a real-card geographic pass.

Missing, stale, incomplete or conflicting evidence blocks release and caps score at 8. Preserve every existing preservation, inventory, visual, source, topology and score gate. Report detected source conflicts; duplicate detection does not authorize redrawing or changing work assignments.

## Scope schema and replay


Every file reference below is `{ "path": "absolute/path", "sha256": "actual retained-byte digest" }`. Files must exist and hashes must match; there is no missing-scope waiver. Project `duplicate_coverage_review` contains `scope` (JSON file reference), `current_card_id`, and `independent_review` (JSON file reference).

The scope JSON has:

- `version: 1`, `registry_source` (retained authoritative active-assignment registry evidence), `active_card_ids` (unique complete relevant card identities), and `scope_reason` explaining the geographic and assignment universe checked. A single-card scope needs positive independent evidence that no other active card can share this assignment. Never define scope merely as files conveniently available.
- `physical_roads`: object keyed by source-reviewed canonical physical road identity. Each road contains `source` (file reference), `feature_refs` (all relevant drawing/GIS feature aliases), `direction_from`, `direction_to`, `measure_unit`, and `geometry_locator`. Use one common measure origin and direction over the entire physical road, independent of local IDs, source subdivisions, labels or aliases. Give distinct physical roads distinct identities even if names match. The critic must identify improperly split aliases or merged roads by inspecting geometry.
- `cards`: exactly one entry per active card. Each has `card_id`, `artifact` (actual final PDF file reference), `assignment_source` (authoritative drawing file reference), `roads` (JSON file reference containing the complete project roads array), and `segments`.
- Every segment contains `road_id` binding its inventory row, `physical_road_id`, `start` and `end` as exact finite decimal strings in the canonical road's measure system, `from_ref`, `to_ref`, `source_locator`, `side_evidence`, and `worked_sides`. Every inventory road requires a segment; represent polygon and explicit-segment assignments using this same occupancy model. Split roads at every work-rule or side change. Include every physical portion, not merely one representative segment per road.
- `worked_sides` uses canonical `left` and/or `right`. Both-sides requires both tokens; inside-only exactly one; red/do-not-work/context requires an empty array. Side evidence must prove the conversion from cardinal or local left/right notation to the canonical direction. Reversing recorded endpoints does not reverse canonical sides. Ambiguous geometry or side conversion blocks release.

The algorithm expands both-sides occupancy and compares all records within and across cards. The same physical road, positive-length interval intersection, and nonempty worked-side intersection is a hard failure. Full/full, full/side, same-side, partial and nested overlaps fail regardless of local IDs or segmentation. Opposite sides, disjoint/endpoint-adjacent intervals, and unworked red context pass this gate only. Decimal arithmetic uses no overlap tolerance or rounding waiver.

