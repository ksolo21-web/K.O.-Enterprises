# Duplicate worked physical street coverage

Apply this mandatory gate to every card, including closed-polygon assignments and legacy cards. Treat the user's new drawings as authoritative assignments. A fully worked street must not be assigned again within its territory; inspect relevant active cards together. Never repair a duplicate by changing the authorized work rule without permission. Source conflicts remain blocked.

Use `scripts/duplicate_coverage_contract.py::validate_duplicate_coverage(review, project=None, *, artifact_sha256=None, source_sha256=None)`. `validate_project.py` invokes it unconditionally. The critic must pass its actual artifact hash and authoritative source hash through the keyword arguments. This is additional to all existing coverage, geographic, preservation and release gates.

## Evidence contract

Every file reference below is `{ "path": "absolute/path", "sha256": "actual retained-byte digest" }`. Files must exist and hashes must match; there is no missing-scope waiver. Project `duplicate_coverage_review` contains `scope` (JSON file reference), `current_card_id`, and `independent_review` (JSON file reference).

The scope JSON has:

- `version: 1`, `registry_source` (retained authoritative active-assignment registry evidence), `active_card_ids` (unique complete relevant card identities), and `scope_reason` explaining the geographic and assignment universe checked. A single-card scope needs positive independent evidence that no other active card can share this assignment. Never define scope merely as files conveniently available.
- `physical_roads`: object keyed by source-reviewed canonical physical road identity. Each road contains `source` (file reference), `feature_refs` (all relevant drawing/GIS feature aliases), `direction_from`, `direction_to`, `measure_unit`, and `geometry_locator`. Use one common measure origin and direction over the entire physical road, independent of local IDs, source subdivisions, labels or aliases. Give distinct physical roads distinct identities even if names match. The critic must identify improperly split aliases or merged roads by inspecting geometry.
- `cards`: exactly one entry per active card. Each has `card_id`, `artifact` (actual final PDF file reference), `assignment_source` (authoritative drawing file reference), `roads` (JSON file reference containing the complete project roads array), and `segments`.
- Every segment contains `road_id` binding its inventory row, `physical_road_id`, `start` and `end` as exact finite decimal strings in the canonical road's measure system, `from_ref`, `to_ref`, `source_locator`, `side_evidence`, and `worked_sides`. Every inventory road requires a segment; represent polygon and explicit-segment assignments using this same occupancy model. Split roads at every work-rule or side change. Include every physical portion, not merely one representative segment per road.
- `worked_sides` uses canonical `left` and/or `right`. Both-sides requires both tokens; inside-only exactly one; red/do-not-work/context requires an empty array. Side evidence must prove the conversion from cardinal or local left/right notation to the canonical direction. Reversing recorded endpoints does not reverse canonical sides. Ambiguous geometry or side conversion blocks release.

The algorithm expands both-sides occupancy and compares all records within and across cards. The same physical road, positive-length interval intersection, and nonempty worked-side intersection is a hard failure. Full/full, full/side, same-side, partial and nested overlaps fail regardless of local IDs or segmentation. Opposite sides, disjoint/endpoint-adjacent intervals, and unworked red context pass this gate only. Decimal arithmetic uses no overlap tolerance or rounding waiver.

## Independent evidence, not self-certification

The separate critic must inspect the retained active registry, authoritative new drawings, source geometry and every actual final card. It must independently establish complete scope, canonical identity/aliases, complete source-to-render inventory, intervals and worked-side conversion. It must inspect omissions, subdivisions and physical overlaps even if deterministic replay passes. A manually labeled scope or a builder-authored pass boolean is not evidence of actual review. Hash binding proves identity, not geographic truth or reviewer independence; preserve the independent execution/review record.

After that inspection, the critic creates the independent review JSON with `scope_sha256`, `reviewer_role: "independent_territory_card_critic"`, `reviewer_id`, `complete_active_scope_verified: true`, `canonical_identity_verified: true`, `measures_and_sides_verified: true`, `source_to_artifact_inventory_verified: true`, `unresolved_items: []`, and nonempty `evidence` (file references to actual inspection records and source/final-image evidence). Any unresolved or unavailable card, registry, source, physical identity, endpoint, or side blocks release. Do not fill true values to satisfy the parser. Any scope, source, inventory or final-PDF change invalidates the review and requires fresh review. No score overrides a failure.

Run regression coverage with `python -m unittest discover -s tests -p test_duplicate_coverage.py -v`. Synthetic fixture passes validate algorithm behavior only and never approve a real card.
