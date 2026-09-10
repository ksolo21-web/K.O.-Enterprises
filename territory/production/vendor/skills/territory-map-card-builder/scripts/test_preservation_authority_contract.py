"""Actual-PDF regressions for separate retained-card and native-map authority."""
import copy
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest
import fitz
import numpy as np
from preservation_authority_contract import validate_preservation_authorities


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class PreservationAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.original = self.root / 'original.pdf'
        self.card = self.root / 'approved.pdf'
        self.candidate = self.root / 'candidate.pdf'
        for path, retained, outside in ((self.original, False, False), (self.card, True, False),
                                         (self.candidate, True, False)):
            self.pdf(path, retained, path == self.candidate, outside)
        self.masks = [[8, 28, 32, 42]]
        self.mask_input = self.root / 'declared-masks.json'
        self.mask_input.write_text(json.dumps({'masks_final': self.masks}))
        self.plan = {'original_assignment': self.record(self.original),
                     'approved_card_baseline': self.record(self.card)}
        self.native = {'original_assignment_sha256': sha(self.original)}
        self.comparison_path = self.root / 'retained-comparison.json'
        self.comparison = {'artifact_path': str(self.candidate), 'artifact_sha256': sha(self.candidate),
                           'retained_card_path': str(self.card), 'retained_card_sha256': sha(self.card),
                           'original_assignment_path': str(self.original), 'original_assignment_sha256': sha(self.original),
                           'declared_masks_input': str(self.mask_input), 'declared_masks_input_sha256': sha(self.mask_input),
                           'masks_final': self.masks, 'checks': self.render_counts(), 'all_zero_outside': True}
        self.project = {'approved_base_path': str(self.card), 'approved_base_sha256': sha(self.card),
                        'original_assignment_path': str(self.original), 'original_assignment_sha256': sha(self.original),
                        'correction_masks': [{'id': 'label-repair', 'x': 8, 'y': 28, 'width': 24, 'height': 14}],
                        'retained_card_baseline': dict(self.record(self.card),
                            rendered_comparison_path=str(self.comparison_path),
                            actual_render_scales=[1, 2, 4], pixels_changed_outside_masks=0,
                            correction_mask_ids=['label-repair'])}
        self.review = {}
        self.bind()

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def pdf(path, retained, addition, outside):
        with fitz.open() as doc:
            page = doc.new_page(width=60, height=60)
            page.draw_line((5, 15), (50, 15), color=(.7, .1, .1), width=1.2)
            if retained:
                page.insert_text((5, 52), 'Approved', fontsize=6)
            if addition:
                page.draw_rect((10, 30, 30, 40), color=(0, 0, 0), fill=(0, 0, 0))
            if outside:
                page.draw_rect((45, 3, 55, 8), fill=(0, 0, 0))
            doc.save(path)

    @staticmethod
    def record(path):
        return {'path': str(path), 'sha256': sha(path)}

    def render_counts(self):
        rows = []
        with fitz.open(self.card) as a, fitz.open(self.candidate) as b:
            for scale in (1, 2, 4):
                pa = a[0].get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                pb = b[0].get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                aa = np.frombuffer(pa.samples, np.uint8).reshape(pa.height, pa.width, pa.n)
                bb = np.frombuffer(pb.samples, np.uint8).reshape(pb.height, pb.width, pb.n)
                delta = np.any(aa != bb, axis=2)
                mask = np.zeros(delta.shape, bool)
                for x0, y0, x1, y1 in self.masks:
                    mask[math.floor(y0*scale):math.ceil(y1*scale), math.floor(x0*scale):math.ceil(x1*scale)] = True
                rows.append({'scale': scale, 'changed_pixels': int(delta.sum()),
                             'changed_outside_masks': int((delta & ~mask).sum())})
        return rows

    def bind(self):
        self.comparison_path.write_text(json.dumps(self.comparison))
        self.project['retained_card_baseline']['rendered_comparison_sha256'] = sha(self.comparison_path)
        self.review['preservation_authorities'] = copy.deepcopy(self.project)

    def validate(self, with_project=True):
        return validate_preservation_authorities(self.review, self.plan, self.native, sha(self.candidate),
                    sha(self.original), self.project if with_project else None)

    def test_actual_dual_authority_pixels_pass(self):
        self.assertNotEqual(sha(self.original), sha(self.card))
        self.assertGreater(self.comparison['checks'][0]['changed_pixels'], 0)
        self.assertEqual(self.validate(), [])
        self.assertEqual(self.validate(False), [])

    def test_same_authority_needs_no_new_wrapper(self):
        plan = {'original_assignment': self.record(self.original)}
        project = {'approved_base_path': str(self.original), 'approved_base_sha256': sha(self.original)}
        self.assertEqual(validate_preservation_authorities({}, plan, self.native, sha(self.candidate),
                                                         sha(self.original), project), [])

    def test_critic_cannot_omit_retained_proof(self):
        self.review.clear()
        self.assertTrue(self.validate(False))

    def test_builder_requires_plan_card_binding(self):
        self.plan.pop('approved_card_baseline')
        self.assertTrue(self.validate())

    def test_stale_original_source_bytes_fail(self):
        self.original.write_bytes(self.card.read_bytes())
        self.assertTrue(self.validate())

    def test_native_original_mismatch_fails(self):
        self.native['original_assignment_sha256'] = sha(self.card)
        self.assertTrue(self.validate())

    def test_coverage_source_mismatch_fails(self):
        self.assertTrue(validate_preservation_authorities(self.review, self.plan, self.native,
                         sha(self.candidate), sha(self.card), self.project))

    def test_map_cannot_replace_approved_card(self):
        self.project['approved_base_path'] = str(self.original)
        self.project['approved_base_sha256'] = sha(self.original)
        self.bind()
        self.assertTrue(self.validate())

    def test_stale_retained_card_bytes_fail(self):
        self.card.write_bytes(self.original.read_bytes())
        self.assertTrue(self.validate())

    def test_missing_hash_bound_retained_comparison_fails(self):
        self.comparison_path.unlink()
        self.assertTrue(self.validate())

    def test_rehashed_receipt_with_different_mask_coordinates_fails(self):
        self.comparison['masks_final'] = [[0, 0, 60, 60]]
        self.bind()
        self.assertTrue(self.validate())

    def test_selected_project_mask_disagreement_fails(self):
        self.project['correction_masks'][0]['width'] = 25
        self.bind()
        self.assertTrue(self.validate())

    def test_actual_outside_change_cannot_be_hidden_by_zero_report(self):
        self.candidate.unlink()
        self.pdf(self.candidate, True, True, True)
        self.comparison['artifact_sha256'] = sha(self.candidate)
        self.comparison['checks'] = self.render_counts()
        self.assertGreater(self.comparison['checks'][0]['changed_outside_masks'], 0)
        for row in self.comparison['checks']:
            row['changed_outside_masks'] = 0
        self.bind()
        self.assertTrue(self.validate())

    def test_false_changed_pixel_count_fails(self):
        self.comparison['checks'][0]['changed_pixels'] += 1
        self.bind()
        self.assertTrue(self.validate())

    def test_missing_2x_replay_fails(self):
        self.comparison['checks'] = [self.comparison['checks'][0]]
        self.project['retained_card_baseline']['actual_render_scales'] = [1]
        self.bind()
        self.assertTrue(self.validate())

    def use_parts(self, parts):
        self.masks = parts
        self.mask_input.write_text(json.dumps({'masks_final': parts}))
        self.comparison['declared_masks_input_sha256'] = sha(self.mask_input)
        self.comparison['masks_final'] = parts
        self.comparison['checks'] = self.render_counts()
        self.project['correction_masks'][0]['parts_final'] = parts
        self.bind()

    def test_multipart_same_operation_overlap_passes_exact_union_replay(self):
        self.use_parts([[8, 28, 21, 42], [19, 28, 32, 42]])
        self.assertEqual(self.validate(), [])
        self.assertEqual(self.validate(False), [])

    def test_actual_change_inside_envelope_hole_fails_despite_false_zero(self):
        self.use_parts([[8, 28, 16, 42], [24, 28, 32, 42]])
        self.assertTrue(all(row['changed_outside_masks'] > 0 for row in self.comparison['checks']))
        for row in self.comparison['checks']:
            row['changed_outside_masks'] = 0
        self.bind()
        errors = self.validate()
        self.assertTrue(any('actual retained-card pixels changed outside' in error for error in errors), errors)

    def test_rehashed_envelope_cannot_replace_declared_actual_parts(self):
        self.use_parts([[8, 28, 21, 42], [19, 28, 32, 42]])
        self.mask_input.write_text(json.dumps({'masks_final': [[8, 28, 32, 42]]}))
        self.comparison['declared_masks_input_sha256'] = sha(self.mask_input)
        self.comparison['masks_final'] = [[8, 28, 32, 42]]
        self.bind()
        errors = self.validate()
        self.assertTrue(any('mask coordinates differ' in error for error in errors), errors)

    def test_malformed_or_out_of_envelope_parts_fail_closed(self):
        for parts in ([], None, [[8, 28, 8, 42]], [[7, 28, 32, 42]],
                      [[8, 28, float('nan'), 42]], [[8, 28, 31, 42]]):
            with self.subTest(parts=parts):
                self.project['correction_masks'][0]['parts_final'] = parts
                self.bind()
                self.assertTrue(self.validate())


if __name__ == '__main__':
    unittest.main()
