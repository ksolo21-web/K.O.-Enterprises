"""Reconcile the property-candidate scope of a retained full OSM response.
Does not infer housing eligibility or replace geographic/visual review.
"""
import argparse, hashlib, json, math
from pathlib import Path
import xml.etree.ElementTree as ET


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check(xml_path, project_path, pdf_path, source_id):
    errors = []
    root = ET.parse(xml_path).getroot()
    project = json.loads(Path(project_path).read_text())
    if root.tag != 'osm':
        errors.append('Expected an OSM map response root; other XML cannot establish an empty scope.')
    if any((e.text or '').strip() for e in root.iter() if e.tag in ('remark', 'error')):
        errors.append('OSM response reports an error or partial-result remark; completeness is not established.')
    objects = [e for e in root if e.tag in ('node', 'way', 'relation')]
    raw = {(e.tag, e.attrib['id']): e for e in objects}
    if len(raw) != len(objects):
        errors.append('Duplicate raw OSM object identities; do not silently overwrite source records.')
    candidates = {}
    for key, e in raw.items():
        tags = {t.attrib['k']: t.attrib['v'] for t in e.findall('tag')}
        if 'building' in tags or 'building:part' in tags or tags.get('landuse') == 'residential':
            candidates['/'.join(key)] = (e, tags)
    inventory = project.get('current_inventory_review', {})
    sources = [s for s in inventory.get('sources', []) if s.get('id') == source_id]
    rows = [r for r in inventory.get('feature_dispositions', []) if r.get('source_id') == source_id]
    if len(sources) != 1:
        errors.append('Exactly one explicit OSM property-candidate source is required, including a verified zero-count scope.')
    else:
        source = sources[0]
        ids = list(map(str, source.get('retrieved_feature_ids', [])))
        if source.get('returned_count') != len(candidates) or len(ids) != len(set(ids)) or set(ids) != set(candidates):
            errors.append('Declared source count/IDs do not equal every raw property candidate.')
        if source.get('raw_source_sha256') != sha(xml_path):
            errors.append('Raw OSM source SHA mismatch or missing binding.')
        if source.get('complete') is not True:
            errors.append('Source completeness is unresolved.')
    by_id = {}
    for row in rows:
        fid = str(row.get('feature_id'))
        if fid in by_id:
            errors.append('Duplicate property disposition: ' + fid)
        by_id[fid] = row
    if set(by_id) != set(candidates):
        errors.append('Property dispositions omit or invent raw candidates.')
    missing_references = []
    for fid, (e, tags) in candidates.items():
        row = by_id.get(fid, {})
        if row.get('tags') != tags:
            errors.append('Actual raw tags not preserved: ' + fid)
        if row.get('kind') != 'property' or row.get('disposition') not in ('matched', 'added', 'excluded') or row.get('eligibility') not in ('eligible', 'ineligible'):
            errors.append('Unresolved property disposition/eligibility: ' + fid)
        if not row.get('assignment_evidence') or not row.get('location'):
            errors.append('Missing spatial assignment rationale: ' + fid)
        if row.get('eligibility') == 'eligible' and tags.get('landuse') == 'residential' and 'building' not in tags and 'building:part' not in tags:
            errors.append('Residential land-use area is not a housing unit: ' + fid)
        stack = [e]
        seen = set()
        while stack:
            obj = stack.pop()
            key = (obj.tag, obj.attrib['id'])
            if key in seen:
                continue
            seen.add(key)
            if obj.tag == 'node':
                try:
                    lat, lon = float(obj.attrib['lat']), float(obj.attrib['lon'])
                    if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
                        raise ValueError('invalid coordinate')
                except (KeyError, ValueError, AssertionError):
                    errors.append('Referenced property node lacks usable coordinates: ' + '/'.join(key))
            refs = [('node', x.attrib['ref']) for x in obj.findall('nd')]
            refs += [(x.attrib['type'], x.attrib['ref']) for x in obj.findall('member')]
            for ref in refs:
                if ref not in raw:
                    missing_references.append({'candidate': fid, 'missing': '/'.join(ref)})
                else:
                    stack.append(raw[ref])
    if missing_references:
        errors.append('Property geometry has missing referenced objects; resolve or obtain complete source geometry before release.')
    actual_sha = sha(pdf_path)
    if project.get('output', {}).get('sha256') != actual_sha:
        errors.append('PROJECT does not bind the actual PDF.')
    return {'schema_version': 'osm-property-scope-review-1', 'status': 'FAIL' if errors else 'PASS',
            'artifact_sha256': actual_sha, 'raw_source_path': str(Path(xml_path).resolve()),
            'raw_source_sha256': sha(xml_path), 'source_id': source_id,
            'candidate_count': len(candidates), 'candidate_ids': sorted(candidates),
            'declared_dispositions': len(rows), 'missing_references': missing_references,
            'errors': errors, 'scope': 'Every retained node, way and relation with building/building:part tags or residential land use; candidate status does not establish housing eligibility.',
            'independent_geographic_eligibility_review_required': True,
            'proof_limits': 'Proves retained-response candidate enumeration, identity/tag/disposition bindings and referenced coordinate presence. Does not prove real-world coverage, server query completeness, housing eligibility, polygon validity or PDF rendering.'}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--osm', required=True)
    p.add_argument('--project', required=True)
    p.add_argument('--pdf', required=True)
    p.add_argument('--source-id', default='osm_property_candidates')
    p.add_argument('--report', required=True)
    a = p.parse_args()
    try:
        report = check(a.osm, a.project, a.pdf, a.source_id)
    except Exception as exc:
        report = {'schema_version': 'osm-property-scope-review-1', 'status': 'FAIL', 'errors': [str(exc)]}
    Path(a.report).parent.mkdir(parents=True, exist_ok=True)
    Path(a.report).write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report.get(k) for k in ('status', 'candidate_count', 'errors')}))
    raise SystemExit(0 if report['status'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
