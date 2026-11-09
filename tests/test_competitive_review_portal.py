"""CE-1P private offline visual reviewer tests. All evidence is synthetic.

No real third-party reviewer, source authenticity, live browser, network, PDF
issuer, signing keys or release authorization is implied by these tests.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import stat
import unittest
from html.parser import HTMLParser
from pathlib import Path

from company_os.competitive_review_portal import (
    PORTAL_FORMAT, _CSS, _JS, _create_html, _escape, _json_for_html,
    inspect_private_visual_portal, stage_private_visual_portal,
)
from company_os.source_provenance import EvidenceError
import test_competitive_critic_room as room_fixture


class PortalParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.images=[]
        self.selects=[]
        self.textareas=[]
        self.buttons=[]
        self.links=[]
        self.script_types=[]
        self.csp=None
    def handle_starttag(self,tag,attrs):
        attr=dict(attrs)
        if tag=="img":self.images.append(attr)
        elif tag=="select":self.selects.append(attr)
        elif tag=="textarea":self.textareas.append(attr)
        elif tag=="button":self.buttons.append(attr)
        elif tag=="a":self.links.append(attr)
        elif tag=="script":self.script_types.append(attr.get("type","javascript"))
        elif tag=="meta" and attr.get("http-equiv")=="Content-Security-Policy":self.csp=attr["content"]


class PrivateVisualPortalTests(unittest.TestCase):
    def setUp(self):
        self.fx=room_fixture.SealedCriticRoomTests(
            "test_complete_actual_PDF_page_packet_stays_reviewer_pending"
        )
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.room=self.fx.stage(room="visual-input-room")
        self.room_path=Path(self.room["workroom"])
        self.digest=self.room["manifest_sha256"]
        self.parent=self.fx.parent
        self.serial=0

    def stage(self, **kw):
        self.serial+=1
        args={
            "room":self.room_path,"private_parent":self.parent,
            "portal_id":"visual-portal-"+str(self.serial),
            "expected_manifest_sha256":self.digest,
        }
        args.update(kw)
        return stage_private_visual_portal(**args)

    def html(self):
        return _create_html(self.room_path,self.digest).decode("utf-8")

    def test_real_pdfium_png_bytes_are_embedded_exactly(self):
        output=self.html()
        parsed=PortalParser();parsed.feed(output)
        self.assertEqual(len(parsed.images),len(self.fx.images))
        expected={hashlib.sha256(data).hexdigest() for data in self.fx.images.values()}
        observed=set()
        for entry in parsed.images:
            self.assertTrue(entry["src"].startswith("data:image/png;base64,"))
            raw=base64.b64decode(entry["src"].split(",",1)[1],validate=True)
            observed.add(hashlib.sha256(raw).hexdigest())
            self.assertEqual(raw[:8],b"\x89PNG\r\n\x1a\n")
            self.assertIn("alt",entry)
        self.assertEqual(observed,expected)
        self.assertEqual(len(expected),2)

    def test_no_default_positive_critic_answers(self):
        source=self.html()
        self.assertEqual(source.count('class="page-finding"'),2)
        self.assertEqual(source.count('class="claim-disposition"'),len(self.fx.fixture.d["claims"]))
        self.assertIn('<option value="">Select after inspecting</option>',source)
        self.assertIn('<option value="">Select after evaluating</option>',source)
        self.assertNotIn('selected="selected"',source)
        self.assertNotIn('independent_critic_approved:true',source)

    def test_every_claim_and_both_support_counterevidence_visible(self):
        source=self.html()
        for claim in self.fx.fixture.d["claims"]:
            self.assertIn('id="claim-'+claim["id"]+'"',source)
            self.assertIn(_escape(claim["text"]),source)
        self.assertIn("Supporting source",source)
        self.assertIn("Counterevidence",source)
        self.assertIn("Original not in sealed issuer-PDF packet",source)
        self.assertIn("Original excerpt page in this packet",source)

    def test_original_issuer_excerpt_links_to_actual_page_section(self):
        source=self.html()
        self.assertIn('href="#page-notice-1"',source)
        self.assertIn('id="page-notice-1"',source)
        self.assertIn('id="page-attachment-1"',source)

    def test_doc_and_source_urls_are_text_not_outbound_links(self):
        parsed=PortalParser();parsed.feed(self.html())
        for anchor in parsed.links:
            self.assertTrue(anchor["href"].startswith("#"))
        self.assertIn("https://issuer.example/",self.html())
        self.assertNotIn('href="https://issuer.example/',self.html())

    def test_strict_offline_csp_no_external_network_or_asset_hosts(self):
        parsed=PortalParser();parsed.feed(self.html())
        self.assertIsNotNone(parsed.csp)
        for item in (
            "default-src 'none'", "img-src data:", "connect-src 'none'",
            "object-src 'none'", "form-action 'none'", "base-uri 'none'",
            "frame-src 'none'", "script-src 'sha256-", "style-src 'sha256-",
        ):
            self.assertIn(item,parsed.csp)
        self.assertNotIn("unsafe-inline",parsed.csp)
        self.assertNotIn("https:",parsed.csp)
        self.assertFalse(any(x["src"].startswith("http") for x in parsed.images))

    def test_script_and_style_csp_integrity_hashes_match_actual_inline_code(self):
        parsed=PortalParser();parsed.feed(self.html())
        expected_css=base64.b64encode(hashlib.sha256(_CSS.encode()).digest()).decode()
        expected_js=base64.b64encode(hashlib.sha256(_JS.encode()).digest()).decode()
        self.assertIn("style-src 'sha256-"+expected_css+"'",parsed.csp)
        self.assertIn("script-src 'sha256-"+expected_js+"'",parsed.csp)

    def test_untrusted_source_can_never_close_json_script_or_inject_html(self):
        attack="</script><img src=x onerror=alert(1)><script>alert(1)</script>"
        encoded=_json_for_html({"text":attack})
        self.assertNotIn("</script>",encoded)
        self.assertNotIn("<img",encoded)
        self.assertEqual(json.loads(encoded)["text"],attack)
        self.assertIn("&lt;script&gt;",_escape("<script>"))

    def test_image_and_claim_data_is_not_written_as_any_script_executable(self):
        text=self.html()
        self.assertIn('<script id="review-context" type="application/json">',text)
        self.assertIn('"review_completed":false',text)
        self.assertIn('"publication_authorized":false',text)
        self.assertIn('"page_tasks":',text)
        self.assertIn('"claim_tasks":',text)

    def test_save_and_reopen_unsigned_drafts_has_room_digest_binding(self):
        script=_JS
        for token in (
            "CE1P_LOCAL_DRAFT_V1","room_manifest_sha256",
            'document.getElementById("save-draft")',
            'document.getElementById("load-draft")',
            "Draft does not belong to this exact sealed room",
            "Draft page record is missing or invalid",
            "Draft claim record is missing or invalid",
        ):
            self.assertIn(token,script)

    def test_export_requires_manually_completed_observation_fields(self):
        for phrase in (
            "observationData(true)", "36–1200", "48–1500",
            "reviewerSummary.length < 60", "UNSIGNED-REVIEW-OBSERVATIONS",
            "requires_separate_root_governed_review_signing:true",
        ):
            self.assertIn(phrase,_JS)
        self.assertNotIn("sign(",_JS)
        self.assertNotIn("fetch(",_JS)

    def test_portal_stages_as_single_read_only_private_html(self):
        staged=self.stage()
        portal=Path(staged["portal"])
        self.assertEqual({p.name for p in portal.iterdir()},{"index.html"})
        self.assertEqual(stat.S_IMODE(portal.stat().st_mode),0o500)
        self.assertEqual(stat.S_IMODE((portal/"index.html").stat().st_mode),0o400)
        result=inspect_private_visual_portal(
            portal,expected_html_sha256=staged["index_sha256"],
        )
        self.assertEqual(result["state"],"PRIVATE_OFFLINE_VIEWER_BYTES_VALID_REVIEW_NOT_PERFORMED")
        self.assertFalse(result["qualified_reviewer_observed"])
        self.assertFalse(result["publication_authorized"])
        self.assertFalse(staged["independent_critic_approved"])
        self.assertFalse(staged["publication_authorized"])
        self.assertEqual(staged["page_count"],2)
        self.assertEqual(staged["claims_assessed"],0)

    def test_deterministic_byte_identical_output_for_same_sealed_room(self):
        self.assertEqual(self.html(),self.html())
        self.assertEqual(
            hashlib.sha256(self.html().encode()).hexdigest(),
            hashlib.sha256(_create_html(self.room_path,self.digest)).hexdigest()
        )

    def test_wrong_out_of_band_manifest_digest_blocks_before_writing(self):
        with self.assertRaises(EvidenceError):
            self.stage(expected_manifest_sha256="0"*64)
        self.assertEqual({x.name for x in self.parent.iterdir()},{"visual-input-room"})

    def test_modified_original_page_image_blocks_before_output(self):
        page=next((self.room_path/"pages").iterdir())
        page.chmod(0o600)
        page.write_bytes(page.read_bytes()+b"changed")
        page.chmod(0o400)
        with self.assertRaises(EvidenceError):
            self.stage()
        self.assertEqual({x.name for x in self.parent.iterdir()},{"visual-input-room"})

    def test_missing_original_page_blocks_before_output(self):
        pages=self.room_path/"pages"
        pages.chmod(0o700)
        next(pages.iterdir()).unlink()
        pages.chmod(0o500)
        with self.assertRaises((OSError,EvidenceError)):
            self.stage()
        self.assertEqual({x.name for x in self.parent.iterdir()},{"visual-input-room"})

    def test_portal_id_cannot_escape_private_parent(self):
        for bad in ("../outside","x","..","prefix/child","MIXED_CASE"):
            with self.subTest(bad=bad):
                with self.assertRaises(EvidenceError):
                    self.stage(portal_id=bad)

    def test_existing_portal_id_cannot_overwrite_prior_output(self):
        staged=self.stage(portal_id="same-reviewer-portal")
        first=(Path(staged["portal"])/"index.html").read_bytes()
        with self.assertRaises(EvidenceError):
            self.stage(portal_id="same-reviewer-portal")
        self.assertEqual((Path(staged["portal"])/"index.html").read_bytes(),first)

    def test_world_readable_staging_parent_is_rejected(self):
        self.parent.chmod(0o755)
        with self.assertRaises(EvidenceError):
            self.stage()

    def test_symlinked_parent_is_rejected(self):
        parent_link=self.fx.root/"visual-parent-link"
        parent_link.symlink_to(self.parent,target_is_directory=True)
        with self.assertRaises(EvidenceError):
            self.stage(private_parent=parent_link)

    def test_unrelated_private_directory_is_rejected(self):
        other=self.fx.root/"different-private-root"
        other.mkdir(mode=0o700)
        with self.assertRaises(EvidenceError):
            self.stage(private_parent=other)

    def test_wrong_expected_portal_html_digest_blocks(self):
        staged=self.stage()
        with self.assertRaises(EvidenceError):
            inspect_private_visual_portal(staged["portal"],expected_html_sha256="f"*64)

    def test_tampered_portal_html_after_resealing_blocks(self):
        staged=self.stage()
        dest=Path(staged["portal"])/"index.html"
        dest.chmod(0o600)
        dest.write_bytes(dest.read_bytes()+b"\n")
        dest.chmod(0o400)
        with self.assertRaises(EvidenceError):
            inspect_private_visual_portal(staged["portal"],expected_html_sha256=staged["index_sha256"])

    def test_extra_portal_file_injection_blocks(self):
        staged=self.stage()
        dest=Path(staged["portal"])
        dest.chmod(0o700)
        (dest/"claimed-approval.json").write_text('{"approved":true}')
        dest.chmod(0o500)
        with self.assertRaises(EvidenceError):
            inspect_private_visual_portal(dest,expected_html_sha256=staged["index_sha256"])

    def test_symlinked_portal_index_is_rejected(self):
        staged=self.stage()
        dest=Path(staged["portal"])
        index=dest/"index.html"
        outside=self.parent/"copy.html"
        outside.write_bytes(index.read_bytes())
        dest.chmod(0o700)
        index.unlink()
        index.symlink_to(outside)
        dest.chmod(0o500)
        with self.assertRaises(EvidenceError):
            inspect_private_visual_portal(dest,expected_html_sha256=staged["index_sha256"])

    def test_group_writable_portal_file_blocks(self):
        staged=self.stage()
        index=Path(staged["portal"])/"index.html"
        index.chmod(0o660)
        with self.assertRaises(EvidenceError):
            inspect_private_visual_portal(staged["portal"],expected_html_sha256=staged["index_sha256"])

    def test_no_release_broker_network_or_signer_api_added(self):
        import company_os.competitive_review_portal as module
        for attr in ("publish","send","sign_review","broker","approve","deploy","serve_public"):
            self.assertFalse(hasattr(module,attr))


if __name__=="__main__":
    unittest.main()
