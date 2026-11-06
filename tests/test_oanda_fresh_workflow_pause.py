"""Fail closed on manual broker workflow dispatch from this legacy feature branch."""
import unittest
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/oanda-fresh-tournament.yml"
TITLE = "- name: Enforce global emergency pause before broker credentials"
COND = '[ -f PAUSE_AUTONOMY ] || [ "$COMPANY_OS_PAUSED" != "0" ]'

def is_guarded(src):
    checkout = src.find("- name: Check out reviewed source")
    persisted = src.find("persist-credentials: false")
    guard = src.find(TITLE)
    secret = src.find("secrets.OANDA")
    if min(checkout,persisted,guard,secret) < 0 or not(checkout < persisted < guard < secret):
        return False
    step_end=src.find("\n      - name:",guard+len(TITLE))
    step=src[guard:step_end if step_end >= 0 else len(src)]
    return src.count(TITLE)==1 and 'COMPANY_OS_PAUSED: "1"' in step and COND in step and "exit 1" in step

class FreshBrokerPauseTests(unittest.TestCase):
    def test_real_workflow_blocked_before_secrets(self):
        self.assertTrue(is_guarded(WORKFLOW.read_text(encoding="utf-8")))
    def test_missing_or_changed_guard_rejected(self):
        source=WORKFLOW.read_text(encoding="utf-8")
        self.assertFalse(is_guarded(source.replace(TITLE,"- name: Old unprotected step")))
        self.assertFalse(is_guarded(source.replace(COND,"false")))
        self.assertFalse(is_guarded(source.replace('COMPANY_OS_PAUSED: "1"','COMPANY_OS_PAUSED: "0"')))
    def test_guard_before_checkout_rejected(self):
        source=WORKFLOW.read_text(encoding="utf-8")
        start=source.index("      "+TITLE)
        end=source.index("      - name:",start+len(TITLE))
        guard=source[start:end]
        moved=(source[:start]+source[end:]).replace("      - name: Check out reviewed source",guard+"      - name: Check out reviewed source",1)
        self.assertFalse(is_guarded(moved))

if __name__=="__main__":
    unittest.main()
