# Two major cross roads: mandatory orientation gate

Require at least two distinct verified major cross roads on EVERY territory card, including previously completed cards, legacy cards, the 91 accepted new drawings, and future cards. Earlier acceptance concerns supplied linework and work colors; it does not waive orientation requirements.

Count a physical road once across repeated labels, aliases, split segments and divided carriageways. Require source evidence for each road's major-road status and distinct identity. Accept a documented highway/arterial class (`motorway`, `trunk`, `primary`, `secondary`, `arterial`) or a `major_connector` with specific source-supported regional orientation importance. An ordinary collector, minor internal street, driveway or subdivision street does not qualify merely because it reaches the territory. A major boundary/work road may count without changing its assigned work status; major roads need not intersect each other if each has a verified connected approach to the territory.

Draw and readably label both roads, and show their verified connected approach. Names in directions or floating text alone never count. Preserve every accepted stroke: add only the minimum necessary verified context on a separate layer, uniformly scale the complete accepted base only if needed, and retain all existing preservation/mask/stroke checks. Never retrace accepted geometry to fit the two roads. Reference both exact verified road names in visible directions. Keep citations in separate audit evidence.

Store top-level `major_crossroad_review` in both project and critic JSON:

```json
{
  "actual_size_review_completed": true,
  "closeup_review_completed": true,
  "distinct_physical_roads_verified": true,
  "directions_reference_both": true,
  "directions_text": "Visible directions naming both verified major roads",
  "roads": [
    {
      "canonical_road_id": "one stable identity across aliases/carriageways",
      "name": "Exact verified road name",
      "identity_verified": true,
      "road_ids": ["drawn-road-object-id"],
      "label_ids": ["bound-label-object-id"],
      "visible": true,
      "readable_at_output_size": true,
      "major_qualification": {"class": "arterial", "evidence": "Source classification and why this is a major orientation road"},
      "source_evidence": [{"url": "https://source.example/roads", "retrieved_at": "2026-09-06", "feature_ids": ["source-feature-id or precise source locator"], "evidence": "Evidence of name, distinct identity, major status and connection; cite retained audit/capture"}],
      "drawing_evidence": "Actual final 1x/2x screenshot and road location; reference geometry/source binding",
      "label_evidence": "Actual-size and close-up screenshot, readable label location and road association",
      "approach": {"road_ids": ["drawn-road-object-id", "approach-road-id", "territory-road-id"], "connected": true, "geometry_verified": true, "drawn": true, "evidence": "Source feature/junction references and screenshot showing each connected hop"}
    }
  ]
}
```

The example shows one record for brevity; at least two complete distinct records are required. In the builder manifest, bind IDs to `roads`, `labels`, `navigation_context.major_road_ids` and matching ordered `approach_paths`; set `navigation_context.required=true`, and match `directions_text` exactly to `directions.text`. Direction IDs must cover both roads. For a major road already in the territory, use its documented approach to another territory segment; do not add duplicate or invented geometry.

The critic independently verifies source evidence, qualification, distinct physical identity, each drawn line, readable label and connected approach in fresh screenshots. Copying builder assertions is insufficient. Run the deterministic contract check through the existing project/critic gate. It checks required structure and consistency, not geographic truth; source and visual review remain mandatory. Missing evidence, an invented/fake second road, or fewer than two qualifying roads hard-fails release and caps critic score at 8. Aim for 10; require exactly 10 in every category and all hard gates passed.

For the September 6, 2026 batch regression, apply the user's then-current order (003–007 first, then repairs to 008, 009 and 010a). Treat this as task history, not a permanent queue or a reason to skip any card in later work.
