import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from duplicate_coverage_contract import validate_duplicate_coverage

class PhysicalCoverage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.write('source', b'authoritative drawing and retained GIS')
        self.pdf = self.write('card.pdf', b'fixture artifact')
        self.roads = [{'id':'local-a', 'work_rule':'both_sides'}, {'id':'local-b', 'work_rule':'both_sides'}]
        self.segment = dict(road_id='local-a',physical_road_id='physical-1',start='0',end='100',worked_sides=['left','right'],source_locator='drawing p1 path1',from_ref='node-A',to_ref='node-B',side_evidence='canonical A to B; drawing marks both')
        self.scope = dict(version=1,registry_source=self.source,active_card_ids=['A'],scope_reason='complete retained active assignment register',physical_roads={'physical-1':dict(source=self.source,feature_refs=['way/1','alias/2'],direction_from='A',direction_to='B',measure_unit='metre',geometry_locator='way/1 chainage')},cards=[dict(card_id='A',artifact=self.pdf,assignment_source=self.source,roads=self.write('roads', self.roads),segments=[self.segment,dict(self.segment,road_id='local-b',start='100',end='200')])])
    def write(self,name,value):
        path=self.root/name
        data=value if isinstance(value,bytes) else json.dumps(value).encode()
        path.write_bytes(data)
        return dict(path=str(path),sha256=hashlib.sha256(data).hexdigest())
    def check(self, project=False, **critic_changes):
        self.scope['cards'][0]['roads']=self.write('roads',self.roads)
        scope=self.write('scope',self.scope)
        critic=dict(scope_sha256=scope['sha256'],reviewer_role='independent_territory_card_critic',reviewer_id='synthetic-test-reviewer',complete_active_scope_verified=True,canonical_identity_verified=True,measures_and_sides_verified=True,source_to_artifact_inventory_verified=True,unresolved_items=[],evidence=[self.source])
        critic.update(critic_changes)
        review=dict(scope=scope,current_card_id='A',independent_review=self.write('critic',critic))
        p=dict(roads=self.roads,output=dict(pdf=self.pdf['path']),coverage_review=dict(source_sha256=self.source['sha256'])) if project else None
        return validate_duplicate_coverage(review,p)
    def test_actual_critic_hash_binding(self):
        self.check()
        review=dict(scope=self.write('scope',self.scope), current_card_id='A', independent_review=dict(path=str(self.root/'critic'),sha256=hashlib.sha256((self.root/'critic').read_bytes()).hexdigest()))
        self.assertEqual(validate_duplicate_coverage(review,artifact_sha256=self.pdf['sha256'],source_sha256=self.source['sha256']),[])
        self.assertTrue(validate_duplicate_coverage(review,artifact_sha256='0'*64))
        self.assertTrue(validate_duplicate_coverage(review,source_sha256='0'*64))
    def test_adjacent_passes_bound_project(self): self.assertEqual(self.check(True),[])
    def test_distinct_local_ids_full_full(self):
        self.scope['cards'][0]['segments'][1]['start']='50'
        self.assertTrue(any('overlapping worked' in e for e in self.check()))
    def test_full_side(self):
        self.roads[1]['work_rule']='inside_only'
        self.scope['cards'][0]['segments'][1].update(start='50',worked_sides=['left'])
        self.assertTrue(self.check())
    def test_same_and_opposite_sides(self):
        for road in self.roads: road['work_rule']='inside_only'
        a,b=self.scope['cards'][0]['segments']
        a['worked_sides']=['left'];b.update(start='0',worked_sides=['right'])
        self.assertEqual(self.check(),[])
        b['worked_sides']=['left'];self.assertTrue(self.check())
    def test_context_red(self):
        self.roads[1]['work_rule']='do_not_work'
        self.scope['cards'][0]['segments'][1].update(start='0',worked_sides=[])
        self.assertEqual(self.check(),[])
    def test_reversed_nested_interval(self):
        self.scope['cards'][0]['segments'][1].update(start='80',end='20')
        self.assertTrue(self.check())
    def test_tiny_overlap(self):
        self.scope['cards'][0]['segments'][1]['start']='99.999999999999999999999999999'
        self.assertTrue(self.check())
    def test_cross_card(self):
        card=copy.deepcopy(self.scope['cards'][0]);card['card_id']='B'
        self.scope['cards'].append(card);self.scope['active_card_ids'].append('B')
        self.assertTrue(any('overlapping worked' in e for e in self.check()))
    def test_distinct_physical_roads(self):
        self.scope['physical_roads']['physical-2']=copy.deepcopy(self.scope['physical_roads']['physical-1'])
        self.scope['cards'][0]['segments'][1].update(start='0',physical_road_id='physical-2')
        self.assertEqual(self.check(),[])
    def test_missing_scope(self): self.assertTrue(validate_duplicate_coverage(None))
    def test_incomplete_registry(self):
        self.scope['active_card_ids'].append('missing');self.assertTrue(self.check())
    def test_stale_artifact(self):
        Path(self.pdf['path']).write_bytes(b'changed');self.assertTrue(self.check())
    def test_missing_inventory_member(self):
        self.scope['cards'][0]['segments'].pop();self.assertTrue(self.check())
    def test_unreviewed_scope(self): self.assertTrue(self.check(complete_active_scope_verified=False))
    def test_stale_critic(self): self.assertTrue(self.check(scope_sha256='0'*64))
    def test_ambiguous_side(self):
        self.scope['cards'][0]['segments'][1]['worked_sides']=['north'];self.assertTrue(self.check())
    def test_nonfinite_measure(self):
        self.scope['cards'][0]['segments'][1]['start']='NaN';self.assertTrue(self.check())

if __name__=='__main__': unittest.main()
