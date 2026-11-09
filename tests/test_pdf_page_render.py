"""CE-1M deterministic PDFium source page rendering, all local synthetic PDFs."""
from __future__ import annotations

import hashlib
import os
import unittest
from unittest.mock import patch

from company_os.pdf_page_render import (
    MAX_PNG_BYTES, RENDER_PROFILE, page_image_evidence, render_pdf_page,
)
from company_os.source_provenance import EvidenceError
import test_procurement_package as pdf_fixture


class OriginalPdfRenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = pdf_fixture.make_pdf(
            "Synthetic original procurement PDF rendering for private internal "
            "evidence testing, not independently verified issuer data.",
            pages=2,
        )

    def test_page_one_png_has_expected_dimensions_and_magic(self):
        png = render_pdf_page(self.raw, 1)
        self.assertTrue(png.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertEqual(png[12:16], b"IHDR")
        self.assertGreaterEqual(int.from_bytes(png[16:20], "big"), 64)
        self.assertGreaterEqual(int.from_bytes(png[20:24], "big"), 64)
        self.assertLessEqual(len(png), MAX_PNG_BYTES)

    def test_identical_original_page_renders_identically_twice(self):
        self.assertEqual(render_pdf_page(self.raw, 1), render_pdf_page(self.raw, 1))

    def test_distinct_original_pdf_documents_have_distinct_rendered_png_hashes(self):
        first = hashlib.sha256(render_pdf_page(self.raw, 1)).hexdigest()
        unrelated = pdf_fixture.make_pdf(
            "Different synthetic original notice: different page content for reviewer.",
        )
        second = hashlib.sha256(render_pdf_page(unrelated, 1)).hexdigest()
        self.assertNotEqual(first, second)

    def test_render_evidence_binds_page_and_original_pdf_sha(self):
        evidence = page_image_evidence(self.raw, 1)
        png = render_pdf_page(self.raw, 1)
        self.assertEqual(evidence["renderer_profile"], RENDER_PROFILE)
        self.assertEqual(evidence["source_pdf_sha256"], hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(evidence["rendered_png_sha256"], hashlib.sha256(png).hexdigest())
        self.assertFalse(evidence["independent_reviewer_verified"])
        self.assertFalse(evidence["visual_page_inspection_completed"])
        self.assertFalse(evidence["publication_authorized"])

    def test_refuse_invalid_page_numbers_and_booleans(self):
        for number in (0, -1, True, False, 61, "1", None):
            with self.subTest(page=number):
                with self.assertRaises(EvidenceError):
                    render_pdf_page(self.raw, number)

    def test_refuse_page_number_that_does_not_exist_in_original(self):
        with self.assertRaises(EvidenceError):
            render_pdf_page(self.raw, 3)

    def test_refuse_invalid_pdf_header(self):
        with self.assertRaises(EvidenceError):
            render_pdf_page(b"this-is-not-a-pdf" * 20, 1)

    def test_refuse_mutated_original_pdf_bytes_with_no_valid_catalog(self):
        mutated = b"%PDF-" + b"z" * 120
        with self.assertRaises(EvidenceError):
            render_pdf_page(mutated, 1)

    def test_refuse_original_pdf_past_bounded_size(self):
        from company_os.pdf_page_render import MAX_PDF_BYTES
        with self.assertRaises(EvidenceError):
            render_pdf_page(b"%PDF-" + b"x" * MAX_PDF_BYTES, 1)

    def test_renderer_requires_precisely_approved_dependency_profile(self):
        from company_os import pdf_page_render as component
        def not_approved(name):
            return "0.0.0"
        with patch("importlib.metadata.version", side_effect=not_approved):
            with self.assertRaises(EvidenceError):
                component._render_page_in_child(self.raw, 1)

    def test_no_network_or_release_execution_added_to_renderer(self):
        from company_os import pdf_page_render as component
        for name in ("publish", "send", "approve", "launch", "fetch_source"):
            self.assertFalse(hasattr(component, name))


if __name__ == "__main__":
    unittest.main()
