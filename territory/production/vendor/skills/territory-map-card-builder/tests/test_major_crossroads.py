"""Adversarial orientation checks; fixtures are deliberately synthetic."""
import copy
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from validate_project import semantic_validate, schema_validate
from validate_major_crossroads import validate_major_crossroads


def fixture():
    return json.loads((ROOT/'examples/territory-project.example.json').read_text())


def test_two_evidenced_bound_roads_pass():
    data = fixture()
    assert semantic_validate(data) == []
    assert schema_validate(data, ROOT/'schemas/territory-project.schema.json') == []


def test_insufficient_or_fake_second_road_fails():
    for mutation in ['missing','one','same_identity','same_name','same_feature','minor','no_source','floating','unreadable','unverified','disconnected','directions_only','wrong_label','unknown_approach','optional']:
        data=fixture();review=data['major_crossroad_review'];road=review['roads'][1]
        if mutation=='missing': del data['major_crossroad_review']
        elif mutation=='one': review['roads'].pop()
        elif mutation=='same_identity': road['canonical_road_id']=review['roads'][0]['canonical_road_id']
        elif mutation=='same_name': road['name']=review['roads'][0]['name']
        elif mutation=='same_feature': road['source_evidence']=copy.deepcopy(review['roads'][0]['source_evidence'])
        elif mutation=='minor': road['major_qualification']['class']='residential'
        elif mutation=='no_source': road['source_evidence']=[]
        elif mutation=='floating': road['road_ids']=[]
        elif mutation=='unreadable': road['readable_at_output_size']=False
        elif mutation=='unverified': road['identity_verified']=False
        elif mutation=='disconnected': road['approach']['connected']=False
        elif mutation=='directions_only': data['roads'][-1]['visible']=False
        elif mutation=='wrong_label': road['label_ids']=[data['labels'][0]['id']]
        elif mutation=='unknown_approach': road['approach']['road_ids'][-1]='invented'
        elif mutation=='optional': data['navigation_context']['required']=False
        assert semantic_validate(data), mutation
    

def test_directions_must_name_both():
    data=fixture();data['directions']['text']='Use Example Major Road 1.'
    data['major_crossroad_review']['directions_text']=data['directions']['text']
    assert any('visible directions' in e for e in semantic_validate(data))


def test_repeated_labels_or_carriageways_do_not_make_two_roads():
    data=fixture();review=data['major_crossroad_review']
    review['roads']=[review['roads'][0],copy.deepcopy(review['roads'][0])]
    review['roads'][1]['name']='Other alias of Example Major Road 1'
    review['roads'][1]['road_ids']=['opposite-carriageway']
    review['roads'][1]['label_ids']=['repeated-label']
    assert any('physical road' in e for e in validate_major_crossroads(review))
