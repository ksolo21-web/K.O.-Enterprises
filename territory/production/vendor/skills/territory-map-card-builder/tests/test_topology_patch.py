"""Self-contained native topology gate tests; run directly, without pytest.

Synthetic geometry is declared before generating the candidate. The retained
source text represents a reviewed source fixture, not real geographic truth.
External report/manifest hash bindings belong to the integration validator.
"""
import json
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import fitz
import validate_topology_patch as gate

BASE_STREAM = b'''q
1 0 0 RG
2 w
1 J
1 j
20 150 m 60 150 l S
110 100 m 170 100 l S
20 40 m 80 40 l S
Q
'''
ADD_BEFORE = '20 150 m 60 150 l S'
ADD_AFTER = '20 150 m 80 150 l S'
REMOVE_BEFORE = '110 100 m 170 100 l S'
REMOVE_AFTER = '110 100 m 140 100 l S'


def write_source(path, raw, extra_page=False):
    doc = fitz.open()
    page = doc.new_page(width=200, height=200)
    xref = doc.get_new_xref()
    doc.update_object(xref, '<<>>')
    doc.update_stream(xref, raw)
    page.set_contents(xref)
    if extra_page:
        page = doc.new_page(width=200, height=200)
        page.insert_text((20, 20), 'Untouched second-page content')
    doc.save(path)
    doc.close()


def write_final(path, source, scale=1, dx=15, dy=20, overlay=None):
    doc = fitz.open()
    src = fitz.open(source)
    page = doc.new_page(width=260, height=260)
    page.show_pdf_page(fitz.Rect(dx, dy, dx + 200*scale, dy + 200*scale), src, 0)
    if overlay == 'text':
        page.insert_text((10, 12), 'UNDECLARED', fontsize=8)
    elif overlay == 'white':
        page.draw_rect(fitz.Rect(65, 65, 110, 80), fill=(1, 1, 1), color=None)
    elif overlay == 'path':
        page.draw_line((220, 20), (240, 20), color=(1, 0, 0), width=2)
    doc.save(path)
    src.close()
    doc.close()


def record(path, **extra):
    return dict(path=str(path), sha256=gate.sha(path), **extra)


def fixture(directory, kinds=('addition', 'removal'), scale=1, locked=False, multipart=False):
    paths = {name: directory / (name + suffix) for name, suffix in (
        ('base', '.pdf'), ('patched', '.pdf'), ('baseline', '.pdf'),
        ('final', '.pdf'), ('plan', '.json'), ('source', '.txt'), ('origin', '.json'))}
    write_source(paths['base'], BASE_STREAM)
    write_final(paths['baseline'], paths['base'], scale=scale)
    paths['source'].write_text('Synthetic reviewed source: extend A to (80,50); trim B to (140,100).')
    operations = []
    if 'addition' in kinds:
        operations.append(dict(id='extend-a', kind='addition', before=ADD_BEFORE,
            after=ADD_AFTER, expected_occurrences=1, mask_source=[57, 46, 84, 54],
            status='work', reference_box_source=[18, 155, 82, 165]))
    if 'removal' in kinds:
        operations.append(dict(id='trim-b', kind='removal', before=REMOVE_BEFORE,
            after=REMOVE_AFTER, expected_occurrences=1, mask_source=[137, 96, 174, 104],
            status='work', reference_box_source=[18, 155, 82, 165]))
    if multipart:
        # One continuous L-shaped native stroke surrounds a distinct trim.
        # Its envelope overlaps the trim, but the declared guarded unions do not.
        operations[0].update(after='20 150 m 180 150 l 180 90 l S',
            mask_source=[57, 46, 184, 114],
            mask_source_parts=[[57, 46, 184, 54], [176, 50, 184, 114]])
    # This immutable expected plan is saved before candidate creation.
    paths['origin'].write_text(json.dumps(dict(operations=operations, source_sha256=gate.sha(paths['source']))))
    plan = dict(schema_version='native-topology-patch-1',
        source_class='locked_new_drawing' if locked else 'legacy_update_candidate',
        correction_authority=dict(authorized=True, evidence='Synthetic scoped correction authorization',
                                  explicit_locked_edit_authorized=locked),
        plan_origin=record(paths['origin'], predates_candidate=True, evidence='Retained plan precedes fixture candidate generation'),
        independent_plan_review=dict(independent=True, source_geometry_verified=True,
                                     not_candidate_derived=True, evidence='Synthetic independent source/endpoint review'),
        source_evidence=[record(paths['source'], url='https://example.invalid/synthetic-source',
                                feature_ids=['a', 'b'], evidence='Source-backed expected endpoints')],
        base_source_sha256=gate.sha(paths['base']), baseline_final_sha256=gate.sha(paths['baseline']),
        original_assignment=record(paths['base'], page_index=0), source_page_index=0,
        final_page_index=0, source_to_final=dict(scale=scale, translate_x=15, translate_y=20),
        operations=operations, palette={'work': [255, 0, 0]})
    regenerate(paths, plan)
    return paths, plan


def regenerate(paths, plan, raw_override=None, **final_options):
    raw = BASE_STREAM
    for op in plan['operations']:
        raw = raw.replace(op['before'].encode(), op['after'].encode())
    if raw_override is not None:
        raw = raw_override
    write_source(paths['patched'], raw)
    write_final(paths['final'], paths['patched'], scale=plan['source_to_final']['scale'], **final_options)
    paths['plan'].write_text(json.dumps(plan))


def verify(paths, plan):
    paths['plan'].write_text(json.dumps(plan))
    return gate.verify(paths['plan'], paths['base'], paths['patched'], paths['baseline'], paths['final'])


def rejected(paths, plan, expected):
    try:
        verify(paths, plan)
    except (ValueError, TypeError, KeyError, IndexError, OSError) as exc:
        assert expected.lower() in str(exc).lower(), (expected, str(exc))
        return
    raise AssertionError('Invalid topology fixture passed: ' + expected)


def test_addition_removal_combination_and_uniform_scale_pass():
    for kinds, scale, locked in [(('addition',), 1, False), (('removal',), 1, False),
                                (('addition', 'removal'), 1, False),
                                (('addition', 'removal'), .8, True)]:
        with tempfile.TemporaryDirectory() as temp:
            paths, plan = fixture(Path(temp), kinds, scale, locked)
            report = verify(paths, plan)
            assert report['status'] == 'PASS'
            assert report['artifact_sha256'] == gate.sha(paths['final'])
            assert report['plan_sha256'] == gate.sha(paths['plan'])
            assert report['pixels_changed_outside_declared_masks'] == 0
            assert len(report['results']) == len(kinds)
            for result in report['results']:
                assert result['passed'] and result['native_operations_verified']
                delta = 'added_length_source_pt' if result['kind'] == 'addition' else 'removed_length_source_pt'
                assert result[delta] > 10
                assert result['original_reference_native_style_verified']


def test_authority_provenance_and_retained_evidence_fail_closed():
    cases = [
        ('authority', lambda p: p['correction_authority'].update(authorized=False), 'authority'),
        ('authority_evidence', lambda p: p['correction_authority'].update(evidence=''), 'authority'),
        ('locked', lambda p: p.update(source_class='locked_new_drawing'), 'locked'),
        ('class', lambda p: p.update(source_class='unclassified'), 'classified'),
        ('origin_hash', lambda p: p['plan_origin'].update(sha256='0'*64), 'file/hash'),
        ('origin_timing', lambda p: p['plan_origin'].update(predates_candidate=False), 'predates'),
        ('independent', lambda p: p['independent_plan_review'].update(independent=False), 'independent'),
        ('source_review', lambda p: p['independent_plan_review'].update(source_geometry_verified=False), 'source_geometry'),
        ('candidate_derived', lambda p: p['independent_plan_review'].update(not_candidate_derived=False), 'not_candidate'),
        ('source_hash', lambda p: p['source_evidence'][0].update(sha256='0'*64), 'file/hash'),
        ('source_missing', lambda p: p.update(source_evidence=[]), 'source evidence'),
        ('source_feature', lambda p: p['source_evidence'][0].update(feature_ids=[]), 'URL/features'),
        ('base_hash', lambda p: p.update(base_source_sha256='0'*64), 'base source hash'),
        ('baseline_hash', lambda p: p.update(baseline_final_sha256='0'*64), 'baseline hash'),
        ('assignment_hash', lambda p: p['original_assignment'].update(sha256='0'*64), 'file/hash'),
    ]
    for name, mutate, error in cases:
        with tempfile.TemporaryDirectory(prefix=name) as temp:
            paths, plan = fixture(Path(temp))
            mutate(plan)
            rejected(paths, plan, error)


def test_native_operations_and_style_fail_closed():
    for name, raw, error in [
        ('wrong_endpoint', BASE_STREAM.replace(ADD_BEFORE.encode(), b'20 150 m 90 150 l S').replace(REMOVE_BEFORE.encode(), REMOVE_AFTER.encode()), 'undeclared'),
        ('missing_removal', BASE_STREAM.replace(ADD_BEFORE.encode(), ADD_AFTER.encode()), 'undeclared'),
        ('extra_removal', BASE_STREAM.replace(ADD_BEFORE.encode(), ADD_AFTER.encode()).replace(REMOVE_BEFORE.encode(), b'110 100 m 125 100 l S'), 'undeclared'),
        ('width', BASE_STREAM.replace(b'2 w', b'3 w').replace(ADD_BEFORE.encode(), ADD_AFTER.encode()).replace(REMOVE_BEFORE.encode(), REMOVE_AFTER.encode()), 'undeclared'),
        ('color', BASE_STREAM.replace(b'1 0 0 RG', b'0 0 1 RG').replace(ADD_BEFORE.encode(), ADD_AFTER.encode()).replace(REMOVE_BEFORE.encode(), REMOVE_AFTER.encode()), 'undeclared'),
        ('extra_path', BASE_STREAM.replace(ADD_BEFORE.encode(), ADD_AFTER.encode()).replace(REMOVE_BEFORE.encode(), REMOVE_AFTER.encode()) + b'20 20 m 40 20 l S\n', 'undeclared'),
    ]:
        with tempfile.TemporaryDirectory(prefix=name) as temp:
            paths, plan = fixture(Path(temp))
            regenerate(paths, plan, raw_override=raw)
            rejected(paths, plan, error)
    for name, mutate, error in [
        ('wrong_kind', lambda p: p['operations'][0].update(kind='removal'), 'no verified native'),
        ('mixed_delta', lambda p: p['operations'][0].update(after='30 150 m 80 150 l S', mask_source=[18, 46, 84, 54]), 'opposite topology'),
        ('no_delta', lambda p: p['operations'][0].update(after='20 150 m 60 150 l 60 150 l S'), 'no verified native'),
        ('count', lambda p: p['operations'][0].update(expected_occurrences=2), 'count mismatch'),
        ('style_operator', lambda p: p['operations'][0].update(after='3 w '+ADD_AFTER), 'prohibited'),
        ('transform', lambda p: p['operations'][0].update(after='1 0 0 1 2 0 cm '+ADD_AFTER), 'transforms'),
    ]:
        with tempfile.TemporaryDirectory(prefix=name) as temp:
            paths, plan = fixture(Path(temp))
            mutate(plan)
            regenerate(paths, plan)
            rejected(paths, plan, error)


def test_final_artifact_geometry_visibility_and_masks_fail_closed():
    for name, mutate, options, error in [
        ('wrong_transform', lambda p: p['source_to_final'].update(translate_x=16), {}, 'uniform transform'),
        ('moved_final', lambda p: None, {'dx': 17}, 'geometry/style/order'),
        ('extra_final_path', lambda p: None, {'overlay': 'path'}, 'drawing operations'),
        ('hidden_patch', lambda p: None, {'overlay': 'white'}, 'drawing operations'),
        ('extra_final_text', lambda p: None, {'overlay': 'text'}, 'final render'),
        ('narrow_mask', lambda p: p['operations'][0].update(mask_source=[57, 48, 70, 52]), {}, 'outside declared'),
        ('overlap', lambda p: p['operations'][0].update(mask_source=[57, 46, 180, 110]), {}, 'masks overlap'),
        ('changed_reference', lambda p: p['operations'][0].update(reference_box_source=[60, 46, 84, 54]), {}, 'reference must remain'),
        ('empty_reference', lambda p: p['operations'][0].update(reference_box_source=[180, 180, 190, 190]), {}, 'reference pixels'),
    ]:
        with tempfile.TemporaryDirectory(prefix=name) as temp:
            paths, plan = fixture(Path(temp))
            mutate(plan)
            if options:
                regenerate(paths, plan, **options)
            rejected(paths, plan, error)
    with tempfile.TemporaryDirectory() as temp:
        paths, plan = fixture(Path(temp))
        paths['final'].write_bytes(paths['baseline'].read_bytes())
        rejected(paths, plan, 'source-map Form stream')


def test_unrelated_final_page_text_change_fails():
    with tempfile.TemporaryDirectory() as temp:
        paths, plan = fixture(Path(temp))
        for key, label in [('baseline', 'Approved second page'), ('final', 'Unauthorized replacement')]:
            doc = fitz.open(paths[key])
            page = doc.new_page(width=260, height=260)
            page.insert_text((20, 30), label)
            doc.saveIncr()
            doc.close()
        plan['baseline_final_sha256'] = gate.sha(paths['baseline'])
        rejected(paths, plan, 'one front page')


def test_multipart_union_preserves_continuous_native_stroke_and_capture_envelope():
    with tempfile.TemporaryDirectory() as temp:
        paths, plan = fixture(Path(temp), multipart=True)
        assert fitz.Rect(plan['operations'][0]['mask_source']).intersects(
            fitz.Rect(plan['operations'][1]['mask_source']))
        report = gate.verify(paths['plan'], paths['base'], paths['patched'],
            paths['baseline'], paths['final'], Path(temp) / 'evidence')
        result = report['results'][0]
        assert report['status'] == 'PASS' and report['expected_final_render_identical']
        assert result['mask_source_parts'] == plan['operations'][0]['mask_source_parts']
        assert result['mask_source'] == plan['operations'][0]['mask_source']
        assert result['isolated_delta_contained']
        assert result['isolated_pixels_changed_outside_mask'] == 0
        assert result['added_length_outside_mask_source_pt'] == 0
        assert result['removed_length_outside_mask_source_pt'] == 0
        assert result['mask_renderer_guard_2x_px'] == 1
        assert all(Path(pair['after_4x']['path']).is_file() for pair in report['paired_4x_screenshots'])
        # No replacement joins were manufactured: the patched path is one drawing.
        with fitz.open(paths['patched']) as document:
            assert len(document[0].get_drawings()) == 3


def test_multipart_invalid_parts_and_cross_operation_overlap_fail_closed():
    cases = [
        ('empty', [], 'nonempty'),
        ('null', None, 'nonempty'),
        ('inverted', [[57, 54, 184, 46]], 'ordered'),
        ('nonfinite', [[57, 46, float('nan'), 114]], 'finite'),
        ('boolean', [[True, 46, 184, 114]], 'finite'),
        ('outside_envelope', [[56, 46, 184, 114]], 'within'),
        ('loose_envelope', [[58, 46, 184, 114]], 'tight'),
        ('cross_operation_overlap', [[57, 46, 184, 114]], 'masks overlap'),
        # Geometrically disjoint rectangles still overlap after the fixed guard.
        ('guard_overlap', [[57, 46, 184, 54], [174.5, 50, 184, 114]], 'masks overlap'),
    ]
    for name, parts, error in cases:
        with tempfile.TemporaryDirectory(prefix=name) as temp:
            paths, plan = fixture(Path(temp), multipart=True)
            plan['operations'][0]['mask_source_parts'] = parts
            rejected(paths, plan, error)
    with tempfile.TemporaryDirectory() as temp:
        paths, plan = fixture(Path(temp), multipart=True)
        plan['operations'][1]['id'] = plan['operations'][0]['id']
        rejected(paths, plan, 'unique')


def test_multipart_holes_cannot_hide_native_or_pixel_delta():
    for name, parts, extra_path, error in [
        ('missing_middle', [[57, 46, 184, 54], [176, 70, 184, 114]], '', 'native geometry changed outside'),
        ('paint_outside', [[57, 46, 184, 50], [176, 50, 184, 114]], '', 'rendered pixels changed outside'),
        ('hidden_in_envelope', [[57, 46, 184, 54], [176, 50, 184, 114]],
         ' 125 110 m 130 110 l S', 'native geometry changed outside'),
        # One operation cannot hide a delta under a second operation's mask.
        ('hidden_in_other_operation', [[57, 46, 184, 54], [176, 50, 184, 114]],
         ' 145 98 m 160 98 l S', 'native geometry changed outside'),
    ]:
        with tempfile.TemporaryDirectory(prefix=name) as temp:
            paths, plan = fixture(Path(temp), multipart=True)
            plan['operations'][0]['mask_source_parts'] = parts
            plan['operations'][0]['after'] += extra_path
            regenerate(paths, plan)
            rejected(paths, plan, error)


if __name__ == '__main__':
    tests = [value for name, value in sorted(globals().items()) if name.startswith('test_') and callable(value)]
    for test in tests:
        test()
        print('PASS', test.__name__)
    print(f'{len(tests)} topology test functions passed, including legacy rectangles and multipart unions.')
