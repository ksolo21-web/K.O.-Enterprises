"""Bind OSM housing eligibility to raw feature type and independent use evidence.

This checks evidence integrity, not the truth of an aerial interpretation. A
critic must still inspect use, footprint, assignment and neighboring exclusions.
"""
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path


def _bound_file(path, digest):
    try:
        data = Path(path).read_bytes()
        return data if hashlib.sha256(data).hexdigest() == digest else None
    except (OSError, TypeError, ValueError):
        return None


def validate_raw_feature_types(inventory):
    errors = []
    rows = inventory.get('feature_dispositions', [])
    for source in inventory.get('sources', []):
        sid = source.get('id')
        selected = [r for r in rows if r.get('source_id') == sid]
        eligible = [r for r in selected if r.get('kind') == 'property' and r.get('eligibility') == 'eligible']
        url = source.get('url', '').lower()
        raw = source.get('raw_features') or {}
        osm = 'openstreetmap' in url or 'overpass' in url or raw.get('format') in ('overpass_json', 'osm_xml')
        if not osm or (not eligible and not raw):
            continue
        tag = f'current_inventory_review raw source {sid}'
        data = _bound_file(raw.get('path'), raw.get('sha256'))
        if raw.get('format') not in ('overpass_json', 'osm_xml') or data is None:
            errors.append(f'{tag}: OSM property eligibility requires actual hash-bound raw OSM XML or Overpass elements')
            continue
        try:
            if raw.get('format') == 'osm_xml':
                root = ET.fromstring(data)
                if root.tag != 'osm' or any((e.text or '').strip() for e in root.iter() if e.tag in ('remark', 'error')):
                    raise ValueError('not a complete OSM response')
                elements = [{'type': e.tag, 'id': e.attrib['id'], 'tags': {t.attrib['k']: t.attrib['v'] for t in e.findall('tag')}} for e in root if e.tag in ('node', 'way', 'relation')]
            else:
                response = json.loads(data)
                if response.get('remark') or response.get('error'):
                    raise ValueError('partial or error Overpass response')
                elements = response['elements']
            if not isinstance(elements, list) or any(not isinstance(e, dict) or not isinstance(e.get('tags', {}), dict) for e in elements):
                raise ValueError('malformed elements/tags')
            actual = {f"{e['type']}/{e['id']}": e.get('tags', {}) for e in elements}
            if len(actual) != len(elements):
                raise ValueError('duplicate raw feature IDs')
        except (ValueError, KeyError, TypeError, ET.ParseError):
            errors.append(f'{tag}: malformed or duplicate raw elements')
            continue
        context = []
        if any(k in source for k in ('supporting_context_ref','raw_response_object_count','supporting_context_object_count')):
            try:
                context = json.loads(Path(source['supporting_context_ref']).read_text())
                ids = [r['feature_id'] for r in selected + context]
                if len(ids) != len(set(ids)) or set(ids) != set(actual):
                    raise ValueError('incomplete partition')
                if len(context) != source.get('supporting_context_object_count') or len(actual) != source.get('raw_response_object_count'):
                    raise ValueError('incorrect raw counts')
            except (OSError, ValueError, KeyError, TypeError):
                errors.append(f'{tag}: relevant and supporting context must partition all raw elements exactly')
                context = []
        for row in selected + context:
            fid = row.get('feature_id')
            tags = actual.get(fid)
            label = f'{tag}/{fid}'
            if tags is None or row.get('raw_tags') != tags:
                errors.append(f'{label}: raw tags must equal the retained source element')
                continue
            declared = row.get('raw_feature_type')
            if declared != 'other' and declared not in tags:
                errors.append(f'{label}: raw feature type is not present in source tags')
            if declared == 'other' and any(k in tags for k in ('building','highway','landuse','leisure','power','waterway')):
                errors.append(f'{label}: substantive raw feature type cannot be erased as other')
            if row in context and row.get('eligibility') == 'eligible':
                errors.append(f'{label}: supporting context cannot contain eligible housing or assigned roads')
            if not (row.get('kind') == 'property' and row.get('eligibility') == 'eligible'):
                continue
            if declared != 'building' or tags.get('building') in (None, '', 'no'):
                errors.append(f'{label}: land use, recreation, utility and other context are not residential buildings')
            if row.get('residential_role') != 'residence':
                errors.append(f'{label}: eligible housing requires independently resolved residence use, excluding sheds/offices')
            evidence = row.get('residential_role_evidence') or {}
            if (_bound_file(evidence.get('source_ref'), evidence.get('source_sha256')) is None
                    or evidence.get('verified') is not True
                    or not all(isinstance(evidence.get(k), str) and evidence[k].strip() for k in ('method','narrative'))):
                errors.append(f'{label}: residence use requires hash-bound independent evidence and review method')
            if row.get('intersection_confers_assignment') is not False:
                errors.append(f'{label}: intersection alone cannot establish whole-property assignment')
    return errors
