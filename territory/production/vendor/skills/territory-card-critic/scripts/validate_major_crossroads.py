"""Fail-closed evidence contract for two distinct, visible major orientation roads.

Checks record consistency, not geographic truth. Independent source and image review
must establish the facts; a fabricated record never constitutes verification.
"""
from datetime import date
from urllib.parse import urlparse

MAJOR_CLASSES = {'motorway', 'trunk', 'primary', 'secondary', 'arterial', 'major_connector'}


def text(value):
    return isinstance(value, str) and bool(value.strip())


def validate_major_crossroads(review):
    errors = []
    prefix = 'major_crossroad_review'
    if not isinstance(review, dict):
        return [f'{prefix} is required for every territory card']
    for key in ('actual_size_review_completed', 'closeup_review_completed',
                'distinct_physical_roads_verified', 'directions_reference_both'):
        if review.get(key) is not True:
            errors.append(f'{prefix}.{key} must be true')
    if not text(review.get('directions_text')):
        errors.append(f'{prefix}.directions_text is required')
    roads = review.get('roads')
    if not isinstance(roads, list) or len(roads) < 2:
        return errors + [f'{prefix} requires at least two distinct verified major cross roads']
    identities, names, road_ids_seen, label_ids_seen, features_seen = set(), set(), set(), set(), set()
    for i, road in enumerate(roads):
        tag = f'{prefix}.roads[{i}]'
        if not isinstance(road, dict):
            errors.append(f'{tag} must be an evidence record')
            continue
        for key in ('canonical_road_id', 'name', 'drawing_evidence', 'label_evidence'):
            if not text(road.get(key)):
                errors.append(f'{tag}.{key} is required')
        identity = str(road.get('canonical_road_id', '')).strip().casefold()
        name = str(road.get('name', '')).strip().casefold()
        if identity in identities or name in names:
            errors.append(f'{tag} duplicates one physical road or repeated road name')
        identities.add(identity)
        names.add(name)
        for key in ('visible', 'readable_at_output_size', 'identity_verified'):
            if road.get(key) is not True:
                errors.append(f'{tag}.{key} must be true')
        for key, seen in [('road_ids', road_ids_seen), ('label_ids', label_ids_seen)]:
            values = road.get(key)
            if not isinstance(values, list) or not values or not all(text(v) for v in values):
                errors.append(f'{tag}.{key} requires drawn object bindings')
            elif len(set(values)) != len(values) or seen.intersection(values):
                errors.append(f'{tag}.{key} reuses a drawing/label binding for another major road')
            else:
                seen.update(values)
        qualification = road.get('major_qualification', {})
        if not isinstance(qualification, dict) or qualification.get('class') not in MAJOR_CLASSES or not text(qualification.get('evidence')):
            errors.append(f'{tag}.major_qualification requires a supported major class and source-based rationale; minor/internal streets do not count')
        sources = road.get('source_evidence')
        if not isinstance(sources, list) or not sources:
            errors.append(f'{tag}.source_evidence is required')
        else:
            own_features = set()
            for source in sources:
                if not isinstance(source, dict):
                    errors.append(f'{tag}.source_evidence contains an invalid record')
                    continue
                url = source.get('url', '')
                if not isinstance(url, str) or urlparse(url).scheme not in ('https', 'http') or not urlparse(url).netloc:
                    errors.append(f'{tag}.source_evidence requires a source URL')
                try:
                    date.fromisoformat(source.get('retrieved_at', ''))
                except (TypeError, ValueError):
                    errors.append(f'{tag}.source_evidence requires an ISO retrieval date')
                if not text(source.get('evidence')):
                    errors.append(f'{tag}.source_evidence requires identity, major-road and connection evidence')
                ids = source.get('feature_ids')
                if not isinstance(ids, list) or not ids or not all(text(v) for v in ids):
                    errors.append(f'{tag}.source_evidence requires feature IDs or precise source locators')
                else:
                    own_features.update((url, item) for item in ids)
            if own_features & features_seen:
                errors.append(f'{tag} shares a source feature with another counted physical road')
            features_seen.update(own_features)
        approach = road.get('approach', {})
        if not isinstance(approach, dict):
            approach = {}
        path = approach.get('road_ids')
        if not isinstance(path, list) or not path or not all(text(v) for v in path) or not set(road.get('road_ids', []) or []).intersection(path):
            errors.append(f'{tag}.approach.road_ids must start on its drawn major road and reach the territory')
        elif path[0] not in road.get('road_ids', []):
            errors.append(f'{tag}.approach.road_ids must start on its drawn major road')
        for key in ('connected', 'geometry_verified', 'drawn'):
            if approach.get(key) is not True:
                errors.append(f'{tag}.approach.{key} must be true')
        if not text(approach.get('evidence')):
            errors.append(f'{tag}.approach.evidence is required')
        if name and name not in str(review.get('directions_text', '')).casefold():
            errors.append(f'{tag}.name must appear in the visible directions text')
    return errors
