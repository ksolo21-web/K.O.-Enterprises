"""Source-bound physical occupancy replay; independent geographic review is mandatory."""
import hashlib
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def validate_duplicate_coverage(review, project=None, *, artifact_sha256=None, source_sha256=None):
    errors = []
    def need(ok, message):
        if not ok:
            errors.append('duplicate_coverage: ' + message)
    def bound(ref, label, parse=False):
        if not isinstance(ref, dict):
            raise ValueError(label + ' file binding required')
        path = Path(ref.get('path', ''))
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != ref.get('sha256'):
            raise ValueError(label + ' stale SHA-256')
        return json.loads(data) if parse else data
    try:
        if not isinstance(review, dict):
            raise ValueError('duplicate_coverage_review required')
        scope = bound(review.get('scope'), 'scope', True)
        need(scope.get('version') == 1, 'scope version must equal 1')
        bound(scope.get('registry_source'), 'active assignment registry source')
        registry = scope['active_card_ids']
        need(isinstance(registry, list) and bool(registry) and len(set(registry)) == len(registry), 'unique complete active card registry required')
        need(bool(scope.get('scope_reason')), 'source-backed scope rationale required')
        roads = scope['physical_roads']
        need(isinstance(roads, dict) and bool(roads), 'canonical physical roads required')
        for key, road in roads.items():
            bound(road.get('source'), 'physical road ' + key)
            need(bool(road.get('feature_refs')) and bool(road.get('direction_from')) and bool(road.get('direction_to')) and road.get('direction_from') != road.get('direction_to'), 'physical road source features and canonical direction required: ' + key)
            need(bool(road.get('measure_unit')) and bool(road.get('geometry_locator')), 'source measure system and geometry locator required: ' + key)
        cards = scope['cards']
        need(set(registry) == {c['card_id'] for c in cards} and len(cards) == len(registry), 'scope must contain every active card exactly once')
        occupancy = []
        current = []
        for card in cards:
            cid = card['card_id']
            bound(card.get('artifact'), 'card artifact ' + cid)
            bound(card.get('assignment_source'), 'authoritative assignment ' + cid)
            inventory = bound(card.get('roads'), 'road inventory ' + cid, True)
            need(isinstance(inventory, list) and bool(inventory), 'complete road inventory required: ' + cid)
            by_id = {r['id']: r for r in inventory}
            need(len(by_id) == len(inventory), 'road inventory IDs must be unique: ' + cid)
            records = card['segments']
            covered = set()
            for seg in records:
                rid = seg['road_id']
                covered.add(rid)
                road = by_id[rid]
                physical = seg['physical_road_id']
                need(physical in roads, 'unknown canonical physical road ' + physical)
                need(bool(seg.get('source_locator')) and bool(seg.get('from_ref')) and bool(seg.get('to_ref')), 'source-bound segment endpoints required')
                # Decimal strings preserve tiny positive overlap; no numeric epsilon waiver.
                a, b = seg['start'], seg['end']
                need(isinstance(a, str) and isinstance(b, str), 'measures must be exact decimal strings')
                a, b = Decimal(a), Decimal(b)
                if not a.is_finite() or not b.is_finite() or a == b:
                    raise ValueError('finite distinct measured endpoints required')
                sides = seg['worked_sides']
                need(isinstance(sides, list) and len(set(sides)) == len(sides) and set(sides) <= {'left', 'right'}, 'canonical worked sides must be unique left/right')
                rule = road.get('work_rule')
                need(rule in {'both_sides', 'inside_only', 'do_not_work', 'context_only'}, 'unsupported work rule')
                need((rule == 'both_sides' and set(sides) == {'left', 'right'}) or (rule == 'inside_only' and len(sides) == 1) or (rule in {'do_not_work', 'context_only'} and not sides), 'worked sides disagree with road inventory')
                need(bool(seg.get('side_evidence')), 'canonical side conversion evidence required, including reversed/cardinal assignments')
                if sides:
                    occupancy.append((physical, min(a,b), max(a,b), set(sides), cid, rid))
            need(covered == set(by_id), 'segments must cover every road inventory entry: ' + cid)
            if cid == review.get('current_card_id'):
                current.append(card)
                if artifact_sha256 is not None:
                    need(artifact_sha256 == card['artifact']['sha256'], 'critic actual artifact differs from scope')
                if source_sha256 is not None:
                    need(source_sha256 == card['assignment_source']['sha256'], 'critic assignment source differs from scope')
                if project is not None:
                    need(inventory == project.get('roads'), 'current project roads differ from bound inventory')
                    p = Path(project.get('output', {}).get('pdf', ''))
                    need(hashlib.sha256(p.read_bytes()).hexdigest() == card['artifact']['sha256'], 'current artifact differs from scope')
                    source_hash = project.get('coverage_review', {}).get('source_sha256')
                    need(source_hash == card['assignment_source']['sha256'], 'current authoritative assignment source differs from scope')
        need(len(current) == 1, 'current card must occur exactly once')
        for i, left in enumerate(occupancy):
            for right in occupancy[i+1:]:
                if left[0] == right[0] and max(left[1],right[1]) < min(left[2],right[2]) and left[3] & right[3]:
                    errors.append('duplicate_coverage: overlapping worked physical segment/side: ' + str((left[4:], right[4:], left[0], sorted(left[3] & right[3]))))
        critic = bound(review.get('independent_review'), 'independent geographic review', True)
        need(critic.get('scope_sha256') == review['scope']['sha256'], 'critic must bind exact scope bytes')
        need(critic.get('reviewer_role') == 'independent_territory_card_critic' and bool(critic.get('reviewer_id')), 'independent critic identity required')
        for field in ('complete_active_scope_verified', 'canonical_identity_verified', 'measures_and_sides_verified', 'source_to_artifact_inventory_verified'):
            need(critic.get(field) is True, 'independent critic must verify ' + field)
        need(critic.get('unresolved_items') == [], 'independent review has unresolved evidence')
        evidence = critic.get('evidence', [])
        need(bool(evidence), 'independent source and actual-artifact inspection evidence required')
        for ref in evidence:
            bound(ref, 'critic inspection evidence')
    except (OSError, ValueError, TypeError, KeyError, InvalidOperation, AttributeError) as exc:
        errors.append('duplicate_coverage: missing/invalid evidence: ' + str(exc))
    return errors
