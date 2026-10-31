"""Source-of-truth policy must actually reach bounded specialist work orders."""
import tempfile
from pathlib import Path
import unittest
from PIL import Image
from inspection_engine.agents import execute_specialists
from inspection_engine.core import sha256
from inspection_engine.descriptors import REQUIRED_FEATURES
from inspection_engine.source_of_truth import load_guidance

class KnowledgePromptIntegration(unittest.TestCase):
    def test_curated_system_vocabulary_exactly_matches_live_engine(self):
        actual=load_guidance()['systems']
        self.assertEqual(set(actual),set(REQUIRED_FEATURES))
        for system, codes in REQUIRED_FEATURES.items():
            self.assertEqual(actual[system]['feature_codes'],list(codes),system)

    def test_provisional_agent_receives_authoritative_reference_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            Image.new('RGB',(128,128),(240,240,240)).save(root/'exterior.png')
            doc={'project_id':'SYNTH-KNOWLEDGE-PROMPT','property':{
                'label':'Synthetic only','inspection_date':'2026-10-31','synthetic':True},
                'media':[{'id':'P0001','kind':'photo','path':'exterior.png','area':'exterior',
                          'sha256':sha256(root/'exterior.png')}],
                'observations':[],'findings':[],'equipment':[],'limitations':[]}
            prompts=[]
            def provider(image,prompt):
                prompts.append(prompt)
                return {'candidates':[],'requests':[]}
            updated,dossier=execute_specialists(doc,root,provider,media_ids=['P0001'])
            self.assertEqual(len(prompts),1)
            self.assertIn('KNOWLEDGE_SOURCE_POLICY_V2',prompts[0])
            self.assertIn('ASHI_CURRENT_SOP',prompts[0])
            self.assertNotIn('ASHI_PENDING_2026',prompts[0])
            self.assertIn('NO LIVE SOURCE LOOKUP',prompts[0])
            self.assertFalse(dossier['customer_release_allowed'])
            self.assertEqual(updated['observations'],[])
