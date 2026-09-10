# Full OSM response: property-candidate scope

Apply this check whenever retained OSM data contains a full map response. A highway-only table is a road-source scope, not a complete property-source review. Inspect the original response before filtering.

Enumerate every node, way and relation carrying `building`, `building:part`, or `landuse=residential`, including generic or nonresidential buildings and an explicit zero-candidate result. Preserve typed IDs (`way/123`), actual tags and dates. Reject malformed/error/partial responses, duplicate identities, and unresolved geometry references. Fetch missing official objects as a separate hash-bound supplement when needed; retain the original and document the exact combined snapshot. Never label converted XML as a raw Overpass JSON response.

Compare candidate geometry with the actual assigned parcels/road-side scope and immediate edges, not merely a small convenient bounding box. Determine use independently from county records and dated imagery/official evidence. A candidate is not automatically housing: neighborhood land-use polygons, sheds, offices and utility structures are not additional residences. A generic building tag alone does not resolve use. Where an OSM footprint describes an already assigned county residence, preserve the county housing classification and record the cross-reference without increasing the dwelling count.

Add a separate complete `osm_property_candidates` source to `current_inventory_review`, with `raw_source_path`, `raw_source_sha256`, typed `retrieved_feature_ids`, exact `returned_count`, and per-feature dispositions containing actual `tags`, `location`, eligibility and spatial/use rationale. Keep housing exclusions grouped by their actual basis. For eligible OSM housing, also supply genuine `raw_features.format` (`osm_xml` or `overpass_json`), raw `path`/`sha256`, exact `raw_tags`/`raw_feature_type`, and independently bound residence-use evidence required by `raw_feature_contract.py`. Supporting context must not erase or invent source objects.

Run the property-scope guard against the actual final PDF:

```sh
python scripts/validate_osm_property_scope.py --osm RAW.xml --project PROJECT.json --pdf CARD.pdf --report SCOPE.json
```

Require PASS and retain the report path/hash with the raw source and final artifact bindings. Repeat on the saved PDF or explicitly prove retained native/text/raster equivalence before rebinding. Also run the ordinary complete project and critic release gates. Scope PASS proves enumeration and evidence bindings, not housing truth, geographic coverage, server query completeness, polygon validity, or visual release approval. The independent critic must review those separately. Never loosen stroke, label or scoring thresholds to resolve source incompleteness.

## Regression evidence

Territory76 initially listed1029 highways while omitting308 property candidates from the same response. Independent exact-parcel review found306 outside-assignment objects and2 overlapping neighborhood land-use areas; no added residence or map change was required. Backchecks55–59 found129 candidates;14 T55 house-shaped footprints already represented county condominium units, not new dwellings. Their full source-only supplements preserve the existing PDF/visual evidence.

The scope utility was independently evaluated on32 cases, including valid and empty scopes, missing/duplicate declarations, stale hashes, wrong tags, missing references, error responses, non-OSM XML, duplicate raw objects, invalid coordinates and optimized Python. Its initial false acceptances were preserved and repaired. Raw-feature XML/JSON parsing passed34 independent cases without weakening residence-use requirements. Retain the actual test receipts and failed examples in batch recovery evidence; these checks do not authorize automatic card approval.
