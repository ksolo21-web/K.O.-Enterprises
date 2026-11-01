"""A10 authorization is new and cannot reuse the consumed A09 record."""
from pathlib import Path
import unittest
import test_a09_scope as legacy_scope_tests
from scripts.a10_scope import scope,AUTH,APPROVAL
from scripts.a09_scope import verify_scope
from inspection_engine.core import DataError

ROOT=Path(__file__).resolve().parents[1]
WORKFLOW=ROOT.parent.parent/'.github/workflows/home-inspection-one-time-20261031-a10.yml'
if not WORKFLOW.is_file():WORKFLOW=ROOT/'docs/workflows/A10_RETIRED_WORKFLOW.yml'


class A10ScopeTests(unittest.TestCase):
    def setUp(self):
        self.base=legacy_scope_tests.A09ScopeTests();self.base.setUp();self.addCleanup(self.base.doCleanups)
    def add(self,auth=AUTH):
        b=self.base;parent=b.g('rev-parse','HEAD');p=b.root/APPROVAL
        p.write_text('Authorization-ID: '+auth+'\nAuthorization-Scope: one synthetic-only GitHub-hosted CPU reconciliation trial, no customers, no secrets, no deployment\nSource-Commit: '+parent+'\n')
        b.g('add','.');b.g('commit','-qm','trial(home-inspection): '+AUTH);b.env['GITHUB_SHA']=b.g('rev-parse','HEAD')
        return p
    def test_new_A10_can_follow_consumed_A09_without_reusing_it(self):
        self.add();self.assertEqual(scope(self.base.root,self.base.env)['writer_input_compaction_version'],1)
    def test_A09_identity_cannot_authorize_A10(self):
        self.add(auth='OWNER_APPROVED_SYNTHETIC_CPU_RUN_20261031_A09')
        with self.assertRaises(DataError):scope(self.base.root,self.base.env)
    def test_unknown_nonce_pair_is_rejected(self):
        with self.assertRaises(DataError):verify_scope(self.base.root,self.base.env,auth_id='invented',approval_path='invented.md')
    def test_A10_consumed_record_modification_is_rejected(self):
        p=self.add();b=self.base;parent=b.g('rev-parse','HEAD');text=p.read_text()
        p.write_text(text[:text.index('Source-Commit: ')]+'Source-Commit: '+parent+'\n')
        b.g('add','.');b.g('commit','-qm','trial(home-inspection): '+AUTH);b.env['GITHUB_SHA']=b.g('rev-parse','HEAD')
        with self.assertRaises(DataError):scope(b.root,b.env)
    def test_same_compute_model_limits_and_no_retry_or_promotion(self):
        s=WORKFLOW.read_text()
        for value in ['scripts.a10_scope','scripts.a09_resources',"github.run_attempt == '1'",'timeout-minutes: 45',
            'remaining > 1800','--writer-model qwen2.5vl:3b','--review-model granite3.2-vision:2b','--reasoning-model qwen2.5:7b',
            'scripts.run_m2_reconciliation_trial','fetch-depth: 2']:
            self.assertIn(value,s)
        self.assertNotIn('workflow_dispatch:',s);self.assertNotIn('secrets.',s)
