"""Static fail-closed checks for manual-only public-runner proposal.

These tests do not activate CI and do not prove Ollama inference.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github/workflows/home-inspection-live-synthetic-manual.yml'

class GithubManualVisionWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = WORKFLOW.read_text(encoding='utf-8')

    def test_manual_only_no_automatic_trigger(self):
        s=self.data
        self.assertIn('workflow_dispatch:',s)
        header=s.split('permissions:')[0]
        for trigger in ('push:', 'pull_request:', 'schedule:', 'repository_dispatch:', 'workflow_call:'):
            self.assertNotIn('\n  '+trigger,header)

    def test_strict_branch_and_repo_and_operator_input(self):
        for token in ("refs/heads/home-inspection-development", "github.repository == 'ksolo21-web/K.O.-Enterprises'", 'authorize_synthetic_only', "'SYNTHETIC_ONLY'"):
            self.assertIn(token,self.data)

    def test_never_runs_on_active_pause(self):
        self.assertIn('PAUSE_AUTONOMY',self.data)
        self.assertIn('exit 1',self.data)
        self.assertLess(self.data.index('PAUSE_AUTONOMY is active'),self.data.index('ollama pull'))

    def test_readonly_credentials_and_synthetic_scope(self):
        for token in ('contents: read','persist-credentials: false','--out-dir local-results/github-actions-synthetic-live','python -m scripts.generate_public_fixtures'):
            self.assertIn(token,self.data)
        self.assertNotIn('secrets.',self.data)
        self.assertNotIn('customer_data/',self.data.split('Publish non-customer acceptance')[1])

    def test_ffmpeg_and_zstd_installed_before_fixture_generation(self):
        s = self.data
        gate = s.index('Provision FFmpeg and zstd before media tests or model installation')
        self.assertLess(gate, s.index('python -m scripts.generate_public_fixtures'))
        self.assertLess(gate, s.index('python -m scripts.verify_pinned_ollama'))
        self.assertIn('for binary in ffmpeg zstd;', s)
        self.assertIn('apt-get install -y --no-install-recommends "${missing[@]}"', s)

    def test_low_model_concurrency_and_nonrelease(self):
        self.assertIn("OLLAMA_MAX_LOADED_MODELS: '1'",self.data)
        self.assertIn('scripts.run_vision_acceptance',self.data)
        self.assertIn('scripts.verify_pinned_ollama',self.data)
        self.assertNotIn('ollama.com/install.sh',self.data)
        doc=(ROOT/'docs/GITHUB_CPU_VISION_TRIAL_v1.3.md').read_text()
        self.assertIn('NOT EXECUTED',doc)
        self.assertIn('supply-chain review',doc)
        self.assertIn('not',doc.lower())

if __name__ == '__main__': unittest.main()
