import copy,json,math,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import fitz
import numpy as np
import engine,repair

class RepairTests(unittest.TestCase):
    def setUp(self):
        # These generated fixtures exercise local repairs; test_cloud_input_guard
        # separately verifies that unauthenticated public CI remains blocked.
        local=patch.dict('os.environ',{'GITHUB_ACTIONS':'false'})
        local.start();self.addCleanup(local.stop)
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.source=self.root/'source.pdf'
        d=fitz.open();p=d.new_page(width=400,height=240);p.draw_line((30,150),(370,150),color=(0.1,0.7,0.2),width=4);p.insert_text((100,65),'Source Road',fontsize=10)
        box=list(p.search_for('Source Road')[0]);font=p.get_fonts()[0][4];d.save(self.source);d.close()
        self.recipe={'mode':'approved_vector_label_revision','source':{'file':'source.pdf','sha256':engine.sha(self.source)},'approved_masks':[[80,40,270,148]],'labels':[{'old_box':box,'text':'Source Road','font_resource':font,'font_size':10,'road_id':'fixture-road-1','road_polyline':[[30,150],[370,150]],'road_width':4,'placements':[{'kind':'direct','baseline':[100,80]},{'kind':'direct','baseline':[100,144]}]}]}
    def tearDown(self):self.temp.cleanup()
    def run_recipe(self,recipe=None):
        p=self.root/'recipe.json';engine.json_write(p,recipe or self.recipe)
        return repair.repair(p,self.root/'output')
    def test_number_nan(self):
        with self.assertRaises(repair.RepairError):repair.number(float('nan'),0,10)
    def test_number_bool(self):
        with self.assertRaises(repair.RepairError):repair.number(True,0,10)
    def test_number_infinite(self):
        with self.assertRaises(repair.RepairError):repair.number(float('inf'),0,10)
    def test_points_degenerate(self):
        with self.assertRaises(repair.RepairError):repair.points([[1,1],[1,1]])
    def test_points_shape(self):
        with self.assertRaises(repair.RepairError):repair.points([[1,1]])
    def test_curve_fit(self):
        self.assertEqual(repair.positions([(0,0),(20,0)],[5,5],0),[((0.0,0.0),-0.0),((5.0,0.0),-0.0)])
    def test_curve_overflow(self):
        with self.assertRaises(repair.RepairError):repair.positions([(0,0),(5,0)],[10],0)
    def test_curve_turn(self):
        result=repair.positions([(0,0),(10,0),(10,20)],[12,5],0);self.assertAlmostEqual(result[1][1],-90)
    def test_mask_no_expansion(self):
        a=repair.allowed_mask((20,20),[(1.2,1.2,4.2,4.2)],2);self.assertFalse(a[2,2]);self.assertTrue(a[3,3])
    def test_same_pdf_invariants(self):self.assertFalse(repair.invariant_check(self.source,self.source,[[0,0,400,240]])['visual_approval'])
    def test_unauthorized_pixel_change(self):
        other=self.root/'changed.pdf'
        with fitz.open(self.source) as d:d[0].insert_text((20,20),'UNAUTHORIZED');d.save(other)
        with self.assertRaises(repair.RepairError):repair.invariant_check(self.source,other,[[80,40,270,148]])
    def test_colored_road_change(self):
        other=self.root/'changed.pdf'
        with fitz.open(self.source) as d:d[0].draw_rect((180,145,190,155),color=None,fill=(1,1,1));d.save(other)
        with self.assertRaises(repair.RepairError):repair.invariant_check(self.source,other,[[0,0,400,240]])
    def test_full_repair_loop(self):
        digest=engine.sha(self.source);r=self.run_recipe()
        self.assertEqual(r['rounds'],2);self.assertEqual(r['candidates'],1);self.assertIsNotNone(r['selected']);self.assertFalse(r['release_ready']);self.assertEqual(engine.sha(self.source),digest)
    def test_curved_label_candidate(self):
        self.recipe['labels'][0]['placements']=[{'kind':'curved','baseline_curve':[[100,144],[240,144]],'start':0}]
        self.assertEqual(self.run_recipe()['candidates'],1)
    def test_wrong_text_rejected(self):
        self.recipe['labels'][0]['text']='Different Road'
        with self.assertRaises(repair.RepairError):self.run_recipe()
    def test_wrong_font_rejected(self):
        self.recipe['labels'][0]['font_resource']='Missing'
        with self.assertRaises(repair.RepairError):self.run_recipe()
    def test_wrong_source_hash(self):
        self.recipe['source']['sha256']='0'*64
        with self.assertRaises(engine.GateError):self.run_recipe()
    def test_no_masks(self):
        self.recipe['approved_masks']=[]
        with self.assertRaises(repair.RepairError):self.run_recipe()
    def test_mask_outside_page(self):
        self.recipe['approved_masks']=[[0,0,999,999]]
        with self.assertRaises(repair.RepairError):self.run_recipe()
    def test_old_text_not_masked(self):
        self.recipe['approved_masks']=[[80,120,270,148]]
        with self.assertRaises(repair.RepairError):self.run_recipe()
    def test_output_must_be_new(self):
        (self.root/'output').mkdir()
        with self.assertRaises(repair.RepairError):self.run_recipe()
    def test_missing_road_identity(self):
        self.recipe['labels'][0]['road_id']=''
        with self.assertRaises(repair.RepairError):self.run_recipe()
    def test_bound_alternatives(self):
        self.recipe['labels'][0]['placements']*=40
        with self.assertRaises(repair.RepairError):self.run_recipe()
    def test_wrong_mode(self):
        self.recipe['mode']='redraw_everything'
        with self.assertRaises(repair.RepairError):self.run_recipe()
    def test_cloud_input_guard(self):
        with patch.dict('os.environ',{'GITHUB_ACTIONS':'true'}),self.assertRaises(engine.GateError):self.run_recipe()
    def test_no_qualifying_candidate(self):
        self.recipe['labels'][0]['placements']=[{'kind':'direct','baseline':[100,80]}]
        r=self.run_recipe();self.assertEqual(r['candidates'],0);self.assertIsNone(r['selected']);self.assertFalse(r['release_ready'])
    def test_existing_ink_collision(self):
        other=self.root/'other.pdf'
        with fitz.open(self.source) as d:d[0].insert_text((100,144),'Other Label',fontsize=10);d.save(other)
        self.recipe['source']={'file':'other.pdf','sha256':engine.sha(other)}
        self.assertEqual(self.run_recipe()['candidates'],0)
    def test_overlay_unsupported(self):
        with self.assertRaises(repair.RepairError):repair.label_overlay((400,240),'a',{'kind':'invented'},(fitz.Font('helv'),None,'helv'),10)

if __name__=='__main__':unittest.main()
