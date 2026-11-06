"""Guard the push-triggered OANDA Practice feature-branch workflow while paused."""
from pathlib import Path
import unittest

REPO = Path(__file__).resolve().parents[1]
PATH = REPO / ".github" / "workflows" / "oanda-forward-scan.yml"
MARKER = "- name: Enforce global emergency pause before broker credentials"
CONDITION = '[ -f PAUSE_AUTONOMY ] || [ "$COMPANY_OS_PAUSED" != "0" ]'


def protected_before_credential(source: str) -> bool:
    checkout = source.find("- name: Check out reviewed source")
    credentials_disabled = source.find("persist-credentials: false")
    guard = source.find(MARKER)
    secret = source.find("secrets.OANDA")
    if min(checkout, credentials_disabled, guard, secret) < 0:
        return False
    if not (checkout < credentials_disabled < guard < secret):
        return False
    next_step = source.find("\n      - name:", guard + len(MARKER))
    step = source[guard:next_step if next_step >= 0 else len(source)]
    return (
        source.count(MARKER) == 1
        and 'COMPANY_OS_PAUSED: "1"' in step
        and CONDITION in step
        and "exit 1" in step
    )


class ForwardPracticeWorkflowStopTests(unittest.TestCase):
    def test_guard_precedes_all_broker_credentials(self):
        self.assertTrue(protected_before_credential(PATH.read_text(encoding="utf-8")))

    def test_unguarded_original_would_fail(self):
        source = PATH.read_text(encoding="utf-8")
        self.assertFalse(protected_before_credential(source.replace(MARKER, "- name: Old workflow")))

    def test_precheckout_or_removed_pause_rejected(self):
        source = PATH.read_text(encoding="utf-8")
        precheckout = source.replace(
            "      - name: Check out reviewed source",
            "      " + MARKER + "\n      - name: Check out reviewed source",
            1,
        )
        self.assertFalse(protected_before_credential(precheckout))
        self.assertFalse(protected_before_credential(source.replace(CONDITION, 'false')))


if __name__ == "__main__":
    unittest.main()
