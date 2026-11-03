"""Synthetic-only M4 live-browser and every-page PDF acceptance evidence.

Uses the exact existing synthetic end-to-end M4 fixture, not a mock HTML app.
Runs in real headless Chromium with Playwright. Never contacts a model, website,
professional credential service or customer system. All outputs synthetic.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from test_m4_human_review import HumanReviewTests

from inspection_engine.m4_review_ui import build_review_worksheet
from inspection_engine.m4_pdf_audit import audit_private_pdf
from inspection_engine.m4_human_review import sign_review, verify_reviews


def run(output: Path) -> dict:
    output=Path(output).resolve()
    output.mkdir(parents=True,exist_ok=True)
    fixture=HumanReviewTests("test_two_distinct_key_verified_reviews_never_release")
    fixture.setUp()
    try:
        ws=build_review_worksheet(fixture.work)
        audit=audit_private_pdf(fixture.work)
        worksheet=Path(ws["worksheet"])
        result={"schema_version":1, "synthetic":True,
                "pdf_audit":json.loads(Path(audit["audit_json"]).read_text()),
                "browser":{}, "customer_release_allowed":False}
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True, executable_path=(
                os.environ.get("M4_CHROMIUM") or None), args=["--no-sandbox"])
            try:
                for mode, width, height in [("desktop",1440,900),("android_portrait",393,852),
                                            ("android_landscape",852,393)]:
                    context=browser.new_context(viewport={"width":width,"height":height},
                                                accept_downloads=True,device_scale_factor=1,
                                                offline=True)
                    external=[]
                    errors=[]
                    context.on("request",lambda request: external.append(request.url)
                               if request.url.startswith(("https://","http://")) else None)
                    page=context.new_page()
                    page.on("pageerror",lambda error: errors.append(str(error)))
                    page.goto(worksheet.as_uri())
                    page.locator("section#systems .card").first.wait_for()
                    assert page.locator("section#systems .card").count() == 13
                    assert page.locator("section#media .card").count() == len(fixture.packet["media"])
                    assert page.locator("section#records .card").count() == len(fixture.packet["items"])
                    assert page.locator('img[src^="data:image/jpeg;base64,"]').count()==1
                    assert not errors, (mode,errors)
                    page.locator("#export").click()
                    assert "Select role" in page.locator("#error").inner_text()
                    page.locator("#role").select_option("qualified_inspector")
                    page.locator("#reviewer").fill(fixture.ids[0])
                    page.locator("#summary").fill("Synthetic demonstration; all real conditions unverified")
                    page.locator("#export").click()
                    assert "Every record" in page.locator("#error").inner_text()
                    for card in page.locator("#records .card").all():
                        card.locator("select").select_option("insufficient_evidence")
                        card.locator("textarea").fill("Real property evidence and field inspection required")
                    for card in page.locator("#media .card").all():
                        card.locator("select").select_option("not_reviewed")
                    for card in page.locator("#systems .card").all():
                        card.locator("select").select_option("not_verified")
                    with page.expect_download() as d:
                        page.locator("#export").click()
                    download=d.value
                    assert download.suggested_filename.endswith("UNSIGNED.json")
                    saved=output/(mode+"_"+download.suggested_filename)
                    download.save_as(str(saved))
                    form=json.loads(saved.read_text())
                    assert form["request_digest"]==fixture.response(0)["request_digest"]
                    assert len(form["systems"])==13
                    assert len(form["items"])==len(fixture.packet["items"])
                    assert len(form["media"])==len(fixture.packet["media"])
                    dimensions=page.evaluate("""() => ({
                        outerWidth:window.innerWidth,
                        documentWidth:document.documentElement.scrollWidth,
                        bodyWidth:document.body.scrollWidth,
                        brokenImages:[...document.images].filter(i=>!i.complete||i.naturalWidth===0).length,
                        focusable:document.querySelectorAll('select,textarea,input,button').length
                    })""")
                    assert dimensions["documentWidth"]<=dimensions["outerWidth"]+2,dimensions
                    assert dimensions["brokenImages"]==0
                    assert not external
                    assert not errors
                    page.screenshot(path=str(output/(mode+"_worksheet.png")),full_page=True)
                    result["browser"][mode]={"viewport":[width,height], "dimensions":dimensions,
                        "external_requests":len(external),"js_errors":errors,
                        "unsigned_form_generated":True,
                        "customer_release_allowed":False}
                    if mode=="desktop":
                        sign_review(fixture.work,fixture.trust,fixture.private_keys[0],form)
                    context.close()
            finally:
                browser.close()
        signature_state=verify_reviews(fixture.work,fixture.trust)
        assert signature_state["signatures_verified"]==1
        assert signature_state["customer_release_allowed"] is False
        result["one_signature_state"]=signature_state
        result["pdf_page_count"]=audit["raster_pages"]
        report=output/"acceptance_summary.json"
        report.write_text(json.dumps(result,indent=2)+"\n")
        return result
    finally:
        fixture.doCleanups()


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    result=run(p.parse_args().output)
    print(json.dumps({"browser_modes":list(result["browser"]),
                      "pdf_pages":result["pdf_page_count"],
                      "one_signature_verified":result["one_signature_state"]["signatures_verified"],
                      "customer_release_allowed":False},indent=2))
