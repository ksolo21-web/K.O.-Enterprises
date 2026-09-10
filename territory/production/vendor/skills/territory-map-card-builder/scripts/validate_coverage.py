"""Validate explicit coverage and complete inventory evidence; never infer geography.

Shared by builder and critic. Independent source/image review establishes truth.
"""
import math
from raw_feature_contract import validate_raw_feature_types
import re
from datetime import date
from urllib.parse import urlparse


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def digest(value):
    return isinstance(value, str) and bool(re.fullmatch(r'[0-9a-fA-F]{64}', value))


def extent_valid(value):
    if not isinstance(value, dict) or not nonempty(value.get('crs')) or not nonempty(value.get('evidence')):
        return False
    bounds = value.get('bounds')
    return (isinstance(bounds, list) and len(bounds) == 4
            and all(type(v) in (int, float) and math.isfinite(v) for v in bounds)
            and bounds[0] < bounds[2] and bounds[1] < bounds[3])


def validate_coverage(coverage, inventory, boundary=None, map_mode=None, roads=None):
    errors = []
    if not isinstance(coverage, dict):
        coverage = {}
        errors.append('coverage_review is required')
    declared_mode = coverage.get('map_mode')
    if declared_mode not in ('preserve_supplied_map', 'vector_rebuild') or (map_mode is not None and declared_mode != map_mode):
        errors.append('coverage_review.map_mode must match the actual map mode')
    map_mode = map_mode if map_mode is not None else declared_mode
    representation = coverage.get('representation')
    if representation not in ('closed_polygon', 'explicit_road_segment_assignment'):
        errors.append('coverage_review.representation must explicitly identify polygon or road-segment assignment')
    for key in ('source_ref', 'edge_evidence'):
        if not nonempty(coverage.get(key)):
            errors.append(f'coverage_review.{key} is required')
    if not digest(coverage.get('source_sha256')):
        errors.append('coverage_review.source_sha256 must bind the original assignment source')
    for key in ('geometry_verified', 'full_coverage_resolved', 'edges_reviewed'):
        if coverage.get(key) is not True:
            errors.append(f'coverage_review.{key} must be true')
    if coverage.get('unresolved_edges') != []:
        errors.append('coverage_review.unresolved_edges must be an empty list')
    if not extent_valid(coverage.get('audit_extent')):
        errors.append('coverage_review.audit_extent requires finite ordered bounds, CRS and extent/edge rationale')
    if representation == 'closed_polygon':
        polygon = boundary if boundary is not None else coverage.get('polygon_boundary')
        if not isinstance(polygon, dict):
            polygon = {}
        for key in ('closed', 'no_self_intersections', 'geometry_verified'):
            if polygon.get(key) is not True:
                errors.append(f'boundary.{key} must be true for closed_polygon')
    if representation == 'explicit_road_segment_assignment':
        if map_mode is not None and map_mode != 'preserve_supplied_map':
            errors.append('explicit road-segment assignments require preserve_supplied_map; vector_rebuild still requires a closed polygon')
        if boundary is not None:
            for key in ('closed', 'no_self_intersections'):
                if boundary.get(key) is not None:
                    errors.append(f'boundary.{key} must be null, not an invented polygon assertion, for segment assignments')
            if boundary.get('geometry_verified') is not True:
                errors.append('boundary.geometry_verified must be true for the explicit assignment')
        assignments = coverage.get('segment_assignments')
        if not isinstance(assignments, list) or not assignments:
            assignments = []
            errors.append('coverage_review.segment_assignments must enumerate the complete assignment')
        seen = set()
        by_id = {r.get('id'): r for r in roads or [] if isinstance(r, dict)}
        for i, item in enumerate(assignments):
            tag = f'coverage_review.segment_assignments[{i}]'
            if not isinstance(item, dict):
                errors.append(f'{tag} must be a segment record')
                continue
            for key in ('road_id', 'source_feature_id', 'from_ref', 'to_ref', 'assignment_evidence'):
                if not nonempty(item.get(key)):
                    errors.append(f'{tag}.{key} is required')
            rid = item.get('road_id')
            if not isinstance(rid, str):
                rid = ''
            if rid in seen:
                errors.append(f'{tag} duplicates a segment; split road IDs at endpoint/rule changes')
            seen.add(rid)
            expected = {'interior':'both_sides', 'perimeter':'inside_only', 'excluded':'do_not_work'}.get(item.get('classification'))
            if expected is None or item.get('work_rule') != expected:
                errors.append(f'{tag} requires a resolved classification/work-rule pairing')
            side = item.get('inside_side')
            if expected == 'inside_only':
                if side not in ('left','right','north','south','east','west','northeast','northwest','southeast','southwest'):
                    errors.append(f'{tag}.inside_side must resolve the worked side of this segment')
            elif side != 'not_applicable':
                errors.append(f'{tag}.inside_side must be not_applicable outside inside-only segments')
            if item.get('verified') is not True:
                errors.append(f'{tag}.verified must be true')
            if roads is not None:
                actual = by_id.get(rid)
                if actual is None:
                    errors.append(f'{tag}.road_id does not bind a project road')
                else:
                    for key in ('classification','work_rule','inside_side','source_feature_id'):
                        if item.get(key) != actual.get(key):
                            errors.append(f'{tag}.{key} disagrees with the project road')
        if roads is not None:
            required = {r.get('id') for r in roads if r.get('classification') in ('interior','perimeter')}
            if not required.issubset(seen):
                errors.append('segment assignments must cover every assigned interior/perimeter project road')
    if not isinstance(inventory, dict):
        return errors + ['current_inventory_review is required for every coverage representation']
    try:
        date.fromisoformat(inventory.get('check_date', ''))
    except (ValueError, TypeError):
        errors.append('current_inventory_review.check_date must be an ISO date')
    for key in ('full_boundary_and_edges_checked', 'source_retrieval_complete', 'relevant_property_eligibility_resolved'):
        if inventory.get(key) is not True:
            errors.append(f'current_inventory_review.{key} must be true')
    for key in ('unresolved_discrepancies', 'unresolved_candidates'):
        if inventory.get(key) != []:
            errors.append(f'current_inventory_review.{key} must be an empty list')
    if not nonempty(inventory.get('evidence')):
        errors.append('current_inventory_review.evidence must identify the retained dated audit')
    if not extent_valid(inventory.get('audit_extent')):
        errors.append('current_inventory_review.audit_extent requires finite bounds, CRS and evidence')
    elif extent_valid(coverage.get('audit_extent')):
        c, i = coverage['audit_extent'], inventory['audit_extent']
        cb, ib = c['bounds'], i['bounds']
        if c['crs'] != i['crs'] or not (ib[0] <= cb[0] and ib[1] <= cb[1] and ib[2] >= cb[2] and ib[3] >= cb[3]):
            errors.append('inventory extent must contain the complete coverage audit extent and immediate edges in the same CRS')
    sources = inventory.get('sources')
    if not isinstance(sources, list) or not sources:
        sources = []
        errors.append('current_inventory_review.sources must record complete queries and feature IDs')
    retrieved = set()
    source_ids = set()
    for i, source in enumerate(sources):
        tag = f'current_inventory_review.sources[{i}]'
        if not isinstance(source, dict):
            errors.append(f'{tag} must be a source record')
            continue
        sid = source.get('id')
        if not nonempty(sid) or sid in source_ids:
            errors.append(f'{tag}.id must be unique and nonempty')
            sid = f'invalid-{i}'
        source_ids.add(sid)
        url = source.get('url')
        if not isinstance(url, str) or urlparse(url).scheme not in ('https','http') or not urlparse(url).netloc:
            errors.append(f'{tag}.url is required')
        try:
            date.fromisoformat(source.get('retrieved_at', ''))
        except (ValueError, TypeError):
            errors.append(f'{tag}.retrieved_at must be an ISO date')
        for key in ('source_recency','query','retrieval_evidence'):
            if not nonempty(source.get(key)):
                errors.append(f'{tag}.{key} is required; explicitly record unknown dataset/imagery recency')
        if source.get('complete') is not True:
            errors.append(f'{tag}.complete must be true')
        ids = source.get('retrieved_feature_ids')
        if not isinstance(ids, list) or not all(nonempty(v) for v in ids) or len(set(ids)) != len(ids):
            errors.append(f'{tag}.retrieved_feature_ids must be a unique full list, including unmatched features')
            ids = []
        count = source.get('returned_count')
        if type(count) is not int or count < 0 or count != len(ids):
            errors.append(f'{tag}.returned_count must equal the complete retrieved feature-ID count')
        retrieved.update((sid, fid) for fid in ids)
    dispositions = inventory.get('feature_dispositions')
    if not isinstance(dispositions, list):
        dispositions = []
        errors.append('current_inventory_review.feature_dispositions is required')
    disposed, kinds = set(), set()
    for i, item in enumerate(dispositions):
        tag = f'current_inventory_review.feature_dispositions[{i}]'
        if not isinstance(item, dict):
            errors.append(f'{tag} must be a feature record')
            continue
        sid, fid = item.get('source_id'), item.get('feature_id')
        if not nonempty(sid) or not nonempty(fid):
            errors.append(f'{tag} requires source_id and feature_id')
            continue
        key = (sid, fid)
        if key in disposed:
            errors.append(f'{tag} has a duplicate feature disposition')
        disposed.add(key)
        kind = item.get('kind')
        if kind not in ('road','access','property'):
            errors.append(f'{tag}.kind must identify road, access or property')
        kinds.add(kind)
        if item.get('disposition') not in ('matched','verified_addition','excluded'):
            errors.append(f'{tag}.disposition must resolve the feature; pending/unknown is not releasable')
        if item.get('eligibility') not in ('eligible','ineligible','not_applicable'):
            errors.append(f'{tag}.eligibility must be resolved')
        if kind == 'property' and item.get('eligibility') == 'not_applicable':
            errors.append(f'{tag} property eligibility cannot be not_applicable')
        for field in ('location','assignment_evidence','evidence'):
            if not nonempty(item.get(field)):
                errors.append(f'{tag}.{field} is required for inclusion/exclusion and assignment rationale')
    if disposed != retrieved:
        errors.append('feature dispositions must cover every and only retrieved source feature; unmatched/extra candidates cannot be dropped')
    if 'road' not in kinds:
        errors.append('current inventory must assess road features')
    if 'property' not in kinds:
        empty_property_query = any(isinstance(s, dict) and s.get('feature_kind') == 'property' and s.get('complete') is True and s.get('returned_count') == 0 and s.get('retrieved_feature_ids') == [] for s in sources)
        if not empty_property_query or not nonempty(inventory.get('property_absence_evidence')):
            errors.append('current inventory must assess property features or evidence a complete empty property query')
    inventory_bound_roads = roads if roads is not None else coverage.get('segment_assignments', [])
    if isinstance(inventory_bound_roads, list):
        source_features = {fid for _, fid in disposed}
        for road in inventory_bound_roads:
            if not isinstance(road, dict):
                continue
            if road.get('classification') not in ('interior','perimeter'):
                continue
            bindings = road.get('inventory_feature_refs')
            if bindings is None:
                if road.get('source_feature_id') not in source_features:
                    errors.append('current inventory must contain source-feature dispositions for every assigned project road')
            elif not isinstance(bindings, list) or not bindings or any(not isinstance(ref, dict) or not nonempty(ref.get('source_id')) or not nonempty(ref.get('feature_id')) or (ref['source_id'], ref['feature_id']) not in disposed for ref in bindings):
                errors.append('roads.inventory_feature_refs must bind actual complete inventory source/feature dispositions')
    errors.extend(validate_raw_feature_types(inventory))
    return errors
