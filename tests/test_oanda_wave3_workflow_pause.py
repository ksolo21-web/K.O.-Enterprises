"""Stop Wave 3 manually triggered broker workflow until independently released."""
import unittest
from pathlib import Path
WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/oanda-wave3-preholdout.yml"
TITLE = "- name: Enforce global emergency pause before broker credentials"
COND = '[ -f PAUSE_AUTONOMY ] || [ "$COMPANY_OS_PAUSED" != "0" ]'

def is_guarded(src):
    checkout = src.find("- name: Check out reviewed source")
    persisted = src.find("persist-credentials: false")
    guard = src.find(TITLE)
    secret = src.find("secrets.OANDA")
    if min(checkout,persisted,guard,secret) < 0 or not(checkout < persisted < guard < secret):
        return False
    end=src.find("\n      - name:",guard+len(TITLE))
    step=src[guard:end if end>=0 else len(src)]
    return src.count(TITLE)==1 and 'COMPANY_OS_PAUSED: "1"' in step and COND in step and "exit 1" in step

class Wave3BrokerPauseTests(unittest.TestCase):
    def test_workflow_guard_precedes_secrets(self):
        self.assertTrue(is_guarded(WORKFLOW.read_text(encoding="utf-8")))
    def test_tamper_and_removal_rejected(self):
        source=WORKFLOW.read_text(encoding="utf-8")
        self.assertFalse(is_guarded(source.replace(TITLE,"- name: Old unprotected step")))
        self.assertFalse(is_guarded(source.replace(COND,"false")))
        self.assertFalse(is_guarded(source.replace('COMPANY_OS_PAUSED: "1"','COMPANY_OS_PAUSED: "0"')))
    def test_precheckout_guard_rejected(self):
        source=WORKFLOW.read_text(encoding="utf-8")
        start=source.index("      "+TITLE)
        end=source.index("      - name:",start+len(TITLE))
        moved=(source[:start]+source[end:]).replace("      - name: Check out reviewed source",source[start:end]+"      - name: Check out reviewed source",1)
        self.assertFalse(is_guarded(moved))

if __name__=="__main__":
    unittest.main()
