import json
import os
from pathlib import Path
import tempfile
import unittest
from inspection_engine.core import DataError
from inspection_engine.proposal_evidence import PrivateProposalAudit


class PrivateProposalAuditTests(unittest.TestCase):
    def test_exact_events_private_and_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'evidence'
            event = {'kind':'generation_request', 'payload':{'prompt':'text', 'images':['UE5H']}}
            with PrivateProposalAudit(root) as audit:
                audit(event)
                audit({'kind':'generation_response', 'envelope':{'response':'{}'}})
            manifest = json.loads((root/'manifest.json').read_text())
            self.assertEqual(manifest['status'], 'COMPLETED')
            self.assertEqual(manifest['event_count'], 2)
            self.assertEqual(json.loads((root/'0001-generation_request.json').read_text()),event)
            if os.name == 'posix':
                self.assertEqual(root.stat().st_mode & 0o777, 0o700)
                self.assertEqual((root/'0001-generation_request.json').stat().st_mode & 0o777, 0o600)

    def test_failed_call_persists_request_without_forged_response(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)/'evidence'
            with self.assertRaises(RuntimeError):
                with PrivateProposalAudit(root) as audit:
                    audit({'kind':'generation_request','payload':{'model':'pinned'}})
                    raise RuntimeError('synthetic timeout')
            self.assertEqual(json.loads((root/'manifest.json').read_text())['status'],'FAILED')
            self.assertEqual(list(root.glob('*response*')),[])

    def test_symlink_parent_and_existing_directory_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'evidence'
            root.mkdir()
            with self.assertRaises(DataError):PrivateProposalAudit(root)
            if hasattr(os,'symlink'):
                link=Path(d)/'linked'
                link.symlink_to(root,target_is_directory=True)
                with self.assertRaises(DataError):PrivateProposalAudit(link/'new')

    def test_invalid_events_and_oversize_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'evidence'
            with PrivateProposalAudit(root) as audit:
                for e in ({'kind':'bad','payload':{}}, {'kind':'generation_response','payload':{}},
                          {'kind':'generation_request','payload':{},'unknown':'x'}):
                    with self.assertRaises(DataError):audit(e)
                with self.assertRaises(DataError):audit({'kind':'generation_request',
                                                        'payload':{'prompt':'x'*25_000_001}})
                self.assertEqual(audit.events,[])
            self.assertEqual(json.loads((root/'manifest.json').read_text())['event_count'],0)

    def test_close_rejects_future_events(self):
        with tempfile.TemporaryDirectory() as d:
            with PrivateProposalAudit(Path(d)/'evidence') as audit: pass
            with self.assertRaises(DataError):audit({'kind':'generation_request','payload':{}})

if __name__=='__main__':unittest.main()
