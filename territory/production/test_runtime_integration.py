"""Full synthetic worker path: encryption, confinement, build/repair and original capture.
No geography, approvals, renderer, cryptography or dependency imports are mocked.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import fitz
import batch,engine,privacy,sealed

class IntegratedRuntimeTests(unittest.TestCase):
    def test_encrypted_two_card_job_with_real_original_capture(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'synthetic';source.mkdir()
            def pin(name):return {'file':name,'sha256':engine.sha(source/name)}
            with fitz.open() as doc:
                page=doc.new_page(width=480,height=300)
                page.insert_text((12,22),'SYNTHETIC TEMPLATE TEST',fontsize=12)
                doc.save(source/'template.pdf')
            with fitz.open() as doc:
                page=doc.new_page(width=400,height=240)
                page.draw_line((30,150),(370,150),color=(.1,.7,.2),width=4)
                page.insert_text((100,65),'Source Road',fontsize=10)
                box=list(page.search_for('Source Road')[0]);font=page.get_fonts()[0][4]
                doc.save(source/'map.pdf')
            build={'mode':'preserve_supplied_map','approved_blank_template':True,
                   'source_class':'individually_approved_map','filename':'Territory - 999a.pdf',
                   'template':pin('template.pdf'),'map':pin('map.pdf'),'map_box':[130,40,460,285],
                   'approved_texts':[]}
            repair={'mode':'approved_vector_label_revision','source':pin('map.pdf'),
                    'approved_masks':[[80,40,270,148]],'labels':[{'old_box':box,'text':'Source Road',
                    'font_resource':font,'font_size':10,'road_id':'synthetic-road',
                    'road_polyline':[[30,150],[370,150]],'road_width':4,
                    'placements':[{'kind':'direct','baseline':[100,80]},
                                  {'kind':'direct','baseline':[100,144]}]}]}
            engine.json_write(source/'build.json',build);engine.json_write(source/'repair.json',repair)
            plan={'schema_version':1,'cards':[{'id':'999a','action':'build','recipe':pin('build.json')},
                                            {'id':'999b','action':'repair','recipe':pin('repair.json')}]}
            engine.json_write(source/'job.json',plan)
            original={p.name:engine.sha(p) for p in source.iterdir()}
            key=sealed.new_key();sid=sealed.new_session()
            ciphertext=sealed.seal(sealed.pack(source),sealed.public(key),sid,'job')
            payload=sealed.unseal(ciphertext,key,sid,'job');job=root/'extracted'
            sealed.unpack(payload,job)
            event=root/'event.json';engine.json_write(event,{'repository':{'full_name':'ksolo21-web/K.O.-Enterprises','private':False},'sender':{'login':'ksolo21-web'}})
            with patch.dict('os.environ',{'GITHUB_ACTIONS':'true','RUNNER_TEMP':str(root),
                    'GITHUB_EVENT_PATH':str(event),'GITHUB_REF':'refs/heads/territory-card-production'}):
                with privacy.authenticated_session(job,payload):
                    report=batch.run(job,root/'result')
            self.assertFalse(privacy.active());self.assertEqual(report['processed'],2)
            self.assertEqual(report['released'],0);self.assertFalse(report['release_ready'])
            for record in report['cards']:
                self.assertEqual(record['status'],'candidate_requires_independent_review',record.get('error'))
                folder=root/'result'/record['id'];pdf=folder/f"Territory - {record['id']}.pdf"
                self.assertEqual(record['capture']['artifact_sha256'],engine.sha(pdf))
                self.assertEqual(len(record['capture']['screenshots']),8)
                for image in record['capture']['screenshots']:
                    self.assertGreater((folder/'final-evidence'/image).stat().st_size,0)
            self.assertEqual(report['cards'][1]['repair']['selected']['round'],2)
            for view in report['cards'][1]['repair']['selected']['invariants']['views']:
                self.assertEqual(view['changed_outside_masks'],0);self.assertEqual(view['changed_colored_ink'],0)
            self.assertEqual({p.name:engine.sha(p) for p in source.iterdir()},original)
            result_cipher=sealed.seal(sealed.pack(root/'result'),sealed.public(key),sid,'result')
            sealed.unpack(sealed.unseal(result_cipher,key,sid,'result'),root/'owner-return')
            self.assertEqual(json.loads((root/'owner-return/CHECKPOINT.json').read_text()),report)

if __name__=='__main__':unittest.main()
