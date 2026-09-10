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


def test_builder_integration_requires_contract():
    from validate_project import semantic_validate
    d=json.loads((ROOT/'examples/territory-project.example.json').read_text())
    d.pop('navigation_presentation_review',None)
    assert any('navigation_presentation_review is required' in e for e in semantic_validate(d))
    d['navigation_presentation_review']=fixture()
    d['navigation_presentation_review']['entrances']={'inventory_complete':True,'inventory_source_evidence':'Synthetic complete source access inventory','representations':[],'no_entrances_evidence':'Synthetic example has no site entrances.'}
    assert not [e for e in semantic_validate(d) if e.startswith('navigation_presentation_review')]
    d['navigation_presentation_review']['street_paths']['unresolved_discontinuities']=['Unexplained kink']
    assert any('unresolved_discontinuities' in e for e in semantic_validate(d))


if __name__ == '__main__':
    test_valid_direct_access_and_necessary_approved_key()
    test_inventory_omission_and_duplicate_block()
    for name,review in bad_cases(): test_missing_or_failed_navigation_evidence_blocks(name,review)
    test_builder_integration_requires_contract()
    print("PASS navigation contract positives, omissions and failure cases; integration checked")
