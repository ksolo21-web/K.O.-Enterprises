"""CE-4D: broker-connected GitHub workflows must fail closed before secrets.

These source regression checks cannot substitute for an enforced GitHub
ruleset, authenticated runtime enforcement or an independent external review.
"""
from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WORKFLOWS = REPO / ".github" / "workflows"
GUARD_TITLE = "- name: Enforce global emergency pause before broker credentials"
REQUIRED_ENV = 'COMPANY_OS_PAUSED: "1"'
REQUIRED_CONDITION = '[ -f PAUSE_AUTONOMY ] || [ "$COMPANY_OS_PAUSED" != "0" ]'
BROKER_MARKERS = ("secrets.OANDA", "experiments.oanda_demo")


def has_precredential_pause_guard(source: str) -> bool:
    positions = [source.find(marker) for marker in BROKER_MARKERS if marker in source]
    if not positions:
        return False
    first_use = min(positions)
    guard_at = source.find(GUARD_TITLE)
    if guard_at < 0 or source.count(GUARD_TITLE) != 1 or guard_at >= first_use:
        return False
    checkout_at = source.find("- name: Check out reviewed source")
    checked_out_at = source.find("persist-credentials: false", checkout_at)
    if not (0 <= checkout_at < checked_out_at < guard_at):
        return False
    next_step = source.find("\n      - name:", guard_at + len(GUARD_TITLE))
    guard_step = source[guard_at:next_step if next_step >= 0 else len(source)]
    return (
        REQUIRED_ENV in guard_step
        and REQUIRED_CONDITION in guard_step
        and 'exit 1' in guard_step
        and 'run: |' in guard_step
    )


class BrokerWorkflowPauseTests(unittest.TestCase):
    def test_all_current_broker_workflows_reject_before_credential_use(self):
        found = []
        for path in sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml")):
            source = path.read_text(encoding="utf-8")
            if any(marker in source for marker in BROKER_MARKERS):
                found.append(path.name)
                with self.subTest(workflow=path.name):
                    self.assertTrue(
                        has_precredential_pause_guard(source),
                        "An OANDA-connected workflow lacks an early deny-by-default pause guard",
                    )
        self.assertEqual(
            set(found),
            {
                "oanda-practice-research.yml",
                "oanda-forward-scan.yml",
                "oanda-fresh-tournament.yml",
                "oanda-wave3-preholdout.yml",
                "oanda-wave4-preholdout.yml",
            },
            "New or removed broker workflows require explicit review and test expansion",
        )

    def test_missing_guard_is_rejected(self):
        source = (
            "steps:\n      - name: Probe\n"
            "        run: python -m experiments.oanda_demo.token_probe\n"
            "        env:\n          OANDA_DEMO_TOKEN: ${{ secrets.OANDA_demo_API_token }}\n"
        )
        self.assertFalse(has_precredential_pause_guard(source))

    def test_guard_after_broker_credential_is_rejected(self):
        source = (
            "steps:\n      - name: Probe\n"
            "        env:\n          TOKEN: ${{ secrets.OANDA_demo_API_token }}\n"
            "      " + GUARD_TITLE + "\n"
            "        env:\n          " + REQUIRED_ENV + "\n"
            "        run: |\n          if " + REQUIRED_CONDITION + "; then\n"
            "            exit 1\n          fi\n"
        )
        self.assertFalse(has_precredential_pause_guard(source))

    def test_guard_before_checkout_is_rejected(self):
        source = (
            "steps:\n      " + GUARD_TITLE + "\n"
            "        env:\n          " + REQUIRED_ENV + "\n"
            "        run: |\n          if " + REQUIRED_CONDITION + "; then\n"
            "            exit 1\n          fi\n"
            "      - name: Check out reviewed source\n"
            "        uses: actions/checkout@pinned\n"
            "        with:\n          persist-credentials: false\n"
            "      - name: Probe\n"
            "        env:\n          TOKEN: ${{ secrets.OANDA_demo_API_token }}\n"
        )
        self.assertFalse(has_precredential_pause_guard(source))

    def test_weakened_guard_is_rejected(self):
        original = (
            "steps:\n      - name: Check out reviewed source\n"
            "        uses: actions/checkout@pinned\n"
            "        with:\n          persist-credentials: false\n"
            "      " + GUARD_TITLE + "\n"
            "        env:\n          " + REQUIRED_ENV + "\n"
            "        run: |\n          if " + REQUIRED_CONDITION + "; then\n"
            "            exit 1\n          fi\n"
            "      - name: Probe\n"
            "        env:\n          TOKEN: ${{ secrets.OANDA_demo_API_token }}\n"
        )
        self.assertTrue(has_precredential_pause_guard(original))
        for changed in (
            original.replace(REQUIRED_ENV, 'COMPANY_OS_PAUSED: "0"'),
            original.replace(REQUIRED_CONDITION, '[ ! -f PAUSE_AUTONOMY ]'),
            original.replace("exit 1", "exit 0"),
            original.replace(GUARD_TITLE, "- name: Review documentation"),
        ):
            with self.subTest(changed=changed[:120]):
                self.assertFalse(has_precredential_pause_guard(changed))


if __name__ == "__main__":
    unittest.main()
