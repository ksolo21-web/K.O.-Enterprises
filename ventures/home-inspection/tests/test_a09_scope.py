"""One-shot scope and pinned identities. Tests never execute Ollama or GitHub."""
from pathlib import Path
import shutil,subprocess,tempfile,unittest,sys
from unittest.mock import patch
from inspection_engine.core import DataError
from scripts.a09_scope import verify_scope,verify_models,MODELS,AUTH,APPROVAL,check_resource_budget
from scripts.a09_resources import sample,stop_owned

ROOT=Path(__file__).resolve().parents[1]
WORKFLOW=ROOT.parent.parent/'.github/workflows/home-inspection-one-time-20261031-a09.yml'


class A09ScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.g('init','-q');self.g('config','user.name','Synthetic Test');self.g('config','user.email','synthetic@example.invalid')
        repo=ROOT.parent.parent;shutil.copyfile(repo/'PAUSE_AUTONOMY',self.root/'PAUSE_AUTONOMY')
        self.g('add','.');self.g('commit','-qm','synthetic source')
        parent=self.g('rev-parse','HEAD');self.path=self.root/APPROVAL;self.path.parent.mkdir(parents=True)
        self.path.write_text('Authorization-ID: '+AUTH+'\nAuthorization-Scope: one synthetic-only GitHub-hosted CPU reconciliation trial, no customers, no secrets, no deployment\nSource-Commit: '+parent+'\n')
        self.g('add','.');self.g('commit','-qm','trial(home-inspection): '+AUTH)
        self.env={'GITHUB_REPOSITORY':'ksolo21-web/K.O.-Enterprises','GITHUB_REF':'refs/heads/home-inspection-development',
            'GITHUB_EVENT_NAME':'push','GITHUB_RUN_ATTEMPT':'1','A09_REPOSITORY_VISIBILITY':'public','GITHUB_SHA':self.g('rev-parse','HEAD')}
    def g(self,*args):return subprocess.check_output(['git','-C',str(self.root),*args],text=True,stderr=subprocess.DEVNULL).strip()
    def test_exact_source_parent_pause_and_one_doc_commit_pass(self):
        self.assertTrue(verify_scope(self.root,self.env)['pause_preserved'])
    def test_repeat_private_wrongbranch_or_nonpush_rejected(self):
        for key,val in [('GITHUB_RUN_ATTEMPT','2'),('A09_REPOSITORY_VISIBILITY','private'),('GITHUB_REF','refs/heads/main'),('GITHUB_EVENT_NAME','workflow_dispatch')]:
            with self.subTest(key=key),self.assertRaises(DataError):verify_scope(self.root,dict(self.env,**{key:val}))
    def test_changed_pause_or_wrongcheckout_rejected(self):
        with self.assertRaises(DataError):verify_scope(self.root,dict(self.env,GITHUB_SHA='a'*40))
        (self.root/'PAUSE_AUTONOMY').write_text('changed')
        with self.assertRaises(DataError):verify_scope(self.root,self.env)
    def test_changed_unreviewed_code_in_trigger_rejected(self):
        (self.root/'unreviewed.py').write_text('untrusted')
        self.g('add','.');self.g('commit','--amend','--no-edit','-q');self.env['GITHUB_SHA']=self.g('rev-parse','HEAD')
        with self.assertRaises(DataError):verify_scope(self.root,self.env)
    def test_consumed_or_mismatched_source_parent_rejected(self):
        self.path.write_text(self.path.read_text().replace('Source-Commit: ','Source-Commit: 0'))
        with self.assertRaises(DataError):verify_scope(self.root,self.env)
    def test_consumed_authorization_cannot_be_reused_by_a_new_commit(self):
        old=self.g('rev-parse','HEAD')
        text=self.path.read_text();text=text[:text.index('Source-Commit: ')]+'Source-Commit: '+old+'\n'
        self.path.write_text(text);self.g('add','.');self.g('commit','-qm','trial(home-inspection): '+AUTH)
        self.env['GITHUB_SHA']=self.g('rev-parse','HEAD')
        with self.assertRaisesRegex(DataError,'NEW'):verify_scope(self.root,self.env)
    def test_cleanup_waits_until_an_actual_owned_process_stops(self):
        from concurrent.futures import ThreadPoolExecutor
        child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'])
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                reaped=pool.submit(child.wait,10)
                result=stop_owned([child.pid],grace=1);self.assertTrue(result['all_stopped']);reaped.result(timeout=2)
        finally:
            if child.poll() is None:child.kill();child.wait()
    def test_customer_directory_blocks_before_any_model_action(self):
        (self.root/'ventures/home-inspection/private_case').mkdir()
        with self.assertRaises(DataError):verify_scope(self.root,self.env)
    def test_only_all_exact_weight_digests_pass(self):
        inventory={'models':[{'name':n,'digest':v} for n,v in MODELS.items()]}
        with patch('scripts.a09_scope.local_json',return_value=inventory):
            r=verify_models();self.assertEqual(len(r['models']),3);self.assertFalse(r['promoted'])
        inventory['models'][-1]['digest']='0'*64
        with patch('scripts.a09_scope.local_json',return_value=inventory),self.assertRaises(DataError):verify_models()
    def test_resource_budget_covers_three_models_and_context(self):
        gib=1024**3
        self.assertEqual(check_resource_budget(20*gib,12*gib,16*gib)['three_model_layer_bytes'],10321565265)
        for disk,available,total in [(17,12,16),(20,9,16),(20,12,13)]:
            with self.assertRaises(DataError):check_resource_budget(disk*gib,available*gib,total*gib)
    def test_sampler_never_requests_command_arguments(self):
        fake=subprocess.CompletedProcess([],0,stdout='PID PPID CPU MEM RSS ETIME COMMAND\n1 2 1 1 100 1:00 ollama\n2 3 0 0 1 1:00 safe\n')
        with patch('scripts.a09_resources.subprocess.run',return_value=fake) as p:r=sample()
        self.assertEqual(len(r['processes']),1);self.assertNotIn('args',p.call_args.args[0][-1]);self.assertTrue(r['process_names_only'])


class A09WorkflowTests(unittest.TestCase):
    def test_narrow_one_shot_limits_and_preserved_pause(self):
        s=WORKFLOW.read_text()
        for expected in ["github.run_attempt == '1'",'timeout-minutes: 45','fetch-depth: 2','contents: read',
            'persist-credentials: false','OWNER_APPROVED_SYNTHETIC_CPU_RUN_20261031_A09','18 * 1024 * 1024',
            'scripts.a09_scope --models','scripts.run_m2_reconciliation_trial','--reasoning-model qwen2.5:7b',
            'tail -c 131072','scripts.a09_resources','process_final.json','if: always()']:
            self.assertIn(expected,s)
        self.assertNotIn('secrets.',s);self.assertNotIn('workflow_dispatch:',s)
        self.assertLess(s.index('unittest discover'),s.index('ollama pull'))
        self.assertIn('remaining > 1800',s);self.assertIn(' - 180 ',s)
