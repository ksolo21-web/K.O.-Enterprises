"""Unverified positional table groups and exact source-page boundary context.

These functions never infer headers, blank cells, semantic joins or findings.
Layout/OCR must first pass the source-bound upstream validators, as in the viewer.
Unsigned OCR receipts identify supplied untrusted text, not authentic OCR output.
"""
from __future__ import annotations

from copy import deepcopy

from .core import DataError
from .report_reading_order import build_reading_order, _row_words
from .report_review_queue import digest, validate_review_queue

MIN_CELL_GAP = .045
ANCHOR_TOLERANCE = .025
MAX_ROW_DISTANCE = .09
MAX_COLUMNS = 8


def _bounds(words):
    boxes = [word['bbox_normalized'] for word in words]
    return [min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes)]


def _segments(row, words):
    groups = []
    for ident in row['word_indices']:
        if (not groups or words[ident]['bbox_normalized'][0]
                - max(words[i]['bbox_normalized'][2] for i in groups[-1]) >= MIN_CELL_GAP):
            groups.append([])
        groups[-1].append(ident)
    return groups


def build_structure_candidates(layout, ocr_record=None):
    # Shared validator also checks receipt identities, page bounds and lossless rows.
    build_reading_order(layout, ocr_record)
    records = {p['page']: p for p in ocr_record['pages']} if ocr_record else {}
    pages = []
    for page in layout['pages']:
        record = records.get(page['page'])
        candidates = []
        words = record['untrusted_ocr_words'] if record else []
        if record:
            rows, wordmap = _row_words(page, words)
            pending = []

            def flush():
                if len(pending) >= 3:
                    cell_rows = []
                    for row, groups in pending:
                        cells = []
                        for column, ids in enumerate(groups, 1):
                            source = [wordmap[i] for i in ids]
                            cells.append({'column_candidate': column, 'word_indices': list(ids),
                                'source_words_untrusted': deepcopy(source),
                                'bbox_normalized': _bounds(source),
                                'text_untrusted': ' '.join(w['text_untrusted'] for w in source)})
                        cell_rows.append({'source_row_id': row['row_id'], 'cells_unverified': cells})
                    candidates.append({'candidate_id': f'P{page["page"]:04d}-GRID-{len(candidates)+1:03d}',
                        'rows_unverified': cell_rows, 'column_count_candidate': len(pending[0][1]),
                        'table_structure_confirmed': False, 'headers_identified': False,
                        'blank_cells_inferred': False, 'multiline_cells_joined': False,
                        'warnings': ['ALIGNED_PROSE_OR_COLUMNS_MAY_MIMIC_A_TABLE',
                            'RAGGED_ROWS_AND_MULTILINE_CELLS_REQUIRE_VISUAL_REVIEW',
                            'NO_CELL_MEANING_OR_HEADER_ROLE_ESTABLISHED']})
                pending.clear()

            for row in sorted(rows, key=lambda r: (r['center_y'], r['row_id'])):
                groups = _segments(row, wordmap)
                if not 2 <= len(groups) <= MAX_COLUMNS:
                    flush()
                    continue
                anchors = [wordmap[g[0]]['bbox_normalized'][0] for g in groups]
                if pending:
                    first_groups = pending[0][1]
                    first_anchors = [wordmap[g[0]]['bbox_normalized'][0] for g in first_groups]
                    if (len(groups) != len(first_groups)
                            or row['center_y'] - pending[-1][0]['center_y'] > MAX_ROW_DISTANCE
                            or any(abs(a-b) > ANCHOR_TOLERANCE for a, b in zip(anchors, first_anchors))):
                        flush()
                pending.append((row, groups))
            flush()
        assigned = [i for c in candidates for row in c['rows_unverified']
                    for cell in row['cells_unverified'] for i in cell['word_indices']]
        assigned_set = set(assigned)
        unassigned = [w['word_index'] for w in words if w['word_index'] not in assigned_set]
        if sorted(assigned + unassigned) != list(range(1, len(words)+1)):
            raise DataError('Structure candidates lost or repeated OCR source words')
        pages.append({'page': page['page'], 'ocr_performed': record is not None,
            'table_candidates_unverified': candidates, 'unassigned_word_indices': unassigned,
            'all_ocr_words_accounted_for_once': True,
            'status': 'POSITIONAL_CANDIDATES_REQUIRE_REVIEW' if candidates else 'NO_TABLE_STRUCTURE_ESTABLISHED'})
    result = {'schema_version': 1, 'kind': 'M3_UNVERIFIED_STRUCTURE_CANDIDATES_V6',
        'case_id': layout['case_id'], 'layout_index_sha256': layout['index_sha256'],
        'ocr_record_sha256': layout.get('ocr_record_sha256'), 'pages': pages,
        'table_structure_verified': False, 'training_approved': False, 'customer_release_allowed': False}
    result['structure_sha256'] = digest(result)
    return result


def validate_structure_candidates(record, layout, ocr_record=None):
    if not isinstance(record, dict) or record != build_structure_candidates(layout, ocr_record):
        raise DataError('Structure candidates stale, altered or incomplete')
    return record


def build_boundary_context(bundle, registry, text_queue, rendered_pages):
    """Show both sides of each physical page break, never resolve continuation.

    Exact chunks are copied whole, with offsets and hashes. Image-only pages do
    not borrow text from a more distant page. Physical PDF page ordinals are used.
    """
    validate_review_queue(text_queue, bundle, registry)
    numbers = [p['number'] for p in bundle['pages']]
    if (not isinstance(rendered_pages, list)
            or any(type(n) is not int or n not in numbers for n in rendered_pages)
            or rendered_pages != sorted(set(rendered_pages))):
        raise DataError('Boundary context render coverage invalid')
    rendered = set(rendered_pages)
    spans = {n: [] for n in numbers}
    for span in text_queue['spans']:
        spans[span['page']].append(span)
    boundaries = []
    for left, right in zip(numbers, numbers[1:]):
        if right != left + 1:
            raise DataError('Original page sequence is incomplete')
        sides = []
        for number, selection in ((left, spans[left][-2:]), (right, spans[right][:2])):
            sides.append({'page': number, 'rendered_image_available': number in rendered,
                'source_spans': deepcopy(selection), 'extractable_text_available': bool(spans[number]),
                'status': 'SOURCE_CONTEXT_UNVERIFIED' if number in rendered else 'MISSING_RENDERED_PAGE'})
        boundaries.append({'boundary_id': f'P{left:04d}-P{right:04d}', 'sides': sides,
            'semantic_continuation_established': False, 'text_joined': False,
            'both_page_images_available': left in rendered and right in rendered})
    result = {'schema_version': 1, 'kind': 'M3_SOURCE_PAGE_BOUNDARIES_V6',
        'case_id': bundle['case_id'], 'reference_bundle_sha256': bundle['bundle_sha256'],
        'text_queue_sha256': text_queue['queue_sha256'], 'rendered_pages': list(rendered_pages),
        'boundaries': boundaries, 'physical_page_ordinals_not_printed_page_labels': True,
        'semantic_understanding_verified': False, 'training_approved': False, 'customer_release_allowed': False}
    result['context_sha256'] = digest(result)
    return result
