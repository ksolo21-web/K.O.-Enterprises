"""Synthetic contract negatives; evidence assertions are not a visual score."""
import copy
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from validate_navigation_presentation import validate_navigation_presentation


def fixture(digest="a"*64):
    return {"artifact_sha256":digest,"actual_size_screenshot":"page-1-1x.png","closeup_screenshots":["page-1-region-5.png"],
      "entrances":{"inventory_complete":True,"inventory_source_evidence":"Synthetic complete source access inventory","representations":[{"entrance_id":"access","representation":"named_street","named_street_sufficient":True,"serving_street":"Public Rd","directions_evidence":"Enter Named Lane from Public Rd.","decision_evidence":"Named Lane is directly and unambiguously labeled."}]},
      "street_paths":{"whole_map_review_completed":True,"views_consistent":True,"unresolved_discontinuities":[],"observations":[{"road":"Named Lane","location":"Mid-road join","source_comparison":"Synthetic original and current join agree.","visual_evidence":"page-1-1x.png and page-1-region-5.png continuous join."}]},
      "label_placement":{"whole_map_review_completed":True,"post_repair_review_completed":True,"remaining_avoidable_placements":[],"observations":[{"label":"Named Lane","road":"Named Lane","usable_run_center_assessment":"Central straight run compared.","southern_whitespace_assessment":"Southern run clear of intersection.","chosen_position_reason":"Centered along usable southern run with correct road association.","visual_evidence":"page-1-1x.png and page-1-region-5.png after repair."}]}}


def bad_cases():
    for key in fixture():
        d=fixture();del d[key];yield "missing_"+key,d
    for mode in ("feature_callout","numbered_key"):
        d=fixture();d["entrances"]["representations"][0]["representation"]=mode;yield "redundant_"+mode,d
    for section,field,value in [("street_paths","views_consistent",False),("street_paths","unresolved_discontinuities",["visible mid-road step-off"]),("street_paths","observations",[]),("label_placement","post_repair_review_completed",False),("label_placement","remaining_avoidable_placements",["north placement leaves clearer south run empty"]),("label_placement","observations",[])]:
        d=fixture();d[section][field]=value;yield field,d
    for field in ("usable_run_center_assessment","southern_whitespace_assessment","chosen_position_reason"):
        d=fixture();del d["label_placement"]["observations"][0][field];yield field,d
    d=fixture();d["entrances"]["representations"]=[];yield "unexplained_empty_access",d
    d=fixture();d["artifact_sha256"]="b"*64;yield "stale_hash",d
    d=fixture();d["closeup_screenshots"]=["not-captured.png"];yield "wrong_view",d

    d=fixture();d['actual_size_screenshot'],d['closeup_screenshots']='page-1-region-5.png',['page-1-1x.png'];yield 'swapped_capture_roles',d
    d=fixture();del d['entrances']['inventory_source_evidence'];yield 'missing_source_inventory',d
    d=fixture();d['street_paths']['observations'][0]['visual_evidence']='pass';yield 'unbound_visual_claim',d


def test_valid_direct_access_and_necessary_approved_key():
    assert validate_navigation_presentation(fixture(),"a"*64,["page-1-1x.png","page-1-region-5.png"],[{"id":"access","representation":"named_street"}])==[]
    d=fixture();r=d["entrances"]["representations"][0];r.update(representation="numbered_key",named_street_sufficient=False,approval_evidence="Synthetic approved key needed for indistinguishable unnamed stems")
    assert not validate_navigation_presentation(d,"a"*64)
    del r["approval_evidence"]
    assert validate_navigation_presentation(d,"a"*64)


def test_missing_or_failed_navigation_evidence_blocks(name,review):
    assert validate_navigation_presentation(review,"a"*64,["page-1-1x.png","page-1-region-5.png"],[{"id":"access","representation":"named_street"}]),name


def test_inventory_omission_and_duplicate_block():
    d=fixture()
    assert validate_navigation_presentation(d,"a"*64,entrances=[{"id":"access"},{"id":"omitted"}])
    assert validate_navigation_presentation(d,"a"*64,entrances=[None])
    assert validate_navigation_presentation(d,"a"*64,entrances=[{"id":"access","representation":"named_street","public_road_id":"public"}],roads=[{"id":"public","name":"Other Road"}])
    d["entrances"]["representations"]*=2
    assert validate_navigation_presentation(d,"a"*64)


def test_real_pdf_critic_caps_failed_navigation(tmp_path,monkeypatch):
    # Isolate this newly added gate; separate suites own geography/glyph/topology contracts.
    import fitz
    import critic_evidence as ce
    for name in ('validate_major_crossroads','validate_label_glyph_review','validate_coverage','validate_housing_instructions','validate_topology_review'):
        monkeypatch.setattr(ce,name,lambda *args,**kwargs: [])
    pdf=tmp_path/'synthetic.pdf'
    with fitz.open() as doc:
        doc.new_page(width=300,height=200).insert_text((20,20),'Synthetic navigation gate fixture')
        doc.save(pdf)
    folder=tmp_path/'round';manifest=ce.capture(pdf,folder)
    report={'artifact_sha256':manifest['artifact_sha256'],'critic_independent':True,'categories':{k:{'score':10,'reason':'Synthetic'} for k in ce.WEIGHTS},'screenshots_inspected':manifest['screenshots'],'label_clutter_review':{'actual_size_review_completed':True,'closeup_review_completed':True,'remaining_avoidable_clusters':0,'evidence':'Synthetic'},'current_inventory_review':{'check_date':'2026-09-07','full_boundary_and_edges_checked':True,'source_retrieval_complete':True,'relevant_property_eligibility_resolved':True,'unresolved_discrepancies':[],'evidence':'Synthetic'},'card_content_review':{'source_or_audit_lines_absent':True,'evidence':'Synthetic'},'topology_mask_kinds':{},'blockers':[],'unverified':[],'overall_score':10,'release_ready':True,'navigation_presentation_review':fixture(manifest['artifact_sha256'])}
    path=folder/'review.json';path.write_text(json.dumps(report));assert ce.gate(pdf,path)['release_ready']
    for name,bad in bad_cases():
        d=copy.deepcopy(report)
        if name not in ('stale_hash','missing_artifact_sha256'):bad['artifact_sha256']=manifest['artifact_sha256']
        d['navigation_presentation_review']=bad
        path.write_text(json.dumps(d));result=ce.gate(pdf,path)
        assert not result['release_ready'] and result['overall_score']<=8,(name,result)
    del report['navigation_presentation_review'];path.write_text(json.dumps(report))
    assert not ce.gate(pdf,path)['release_ready']


if __name__ == '__main__':
    test_valid_direct_access_and_necessary_approved_key()
    test_inventory_omission_and_duplicate_block()
    for name,review in bad_cases(): test_missing_or_failed_navigation_evidence_blocks(name,review)
    import tempfile
    class Patch:
        def setattr(self,obj,name,value): setattr(obj,name,value)
    with tempfile.TemporaryDirectory() as tmp:
        test_real_pdf_critic_caps_failed_navigation(Path(tmp),Patch())
    print("PASS navigation contract positives, omissions and failure cases; integration checked")
