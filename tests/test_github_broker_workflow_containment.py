"""P0 broker-workflow emergency containment tests: offline mocked GitHub API.

All workflow IDs and GitHub responses are synthetic. No admin mutation, no
network access and no OANDA secret is used by any unit test.
"""
from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from company_os.github_broker_workflow_containment import (
    CONFIRMATION, REPO, TARGET_PATHS, ContainmentError,
    _validate_inventory, api_transport, disable_registered_oanda_workflows,
)


class FakeGitHubWorkflowAdmin:
    def __init__(self):
        self.states = {
            1001 + index: {"id": 1001 + index, "path": path, "state": "active"}
            for index, path in enumerate(TARGET_PATHS)
        }
        self.operations = []
        self.changing_response = None
        self.fail_at_id = None
        self.unknown = None

    def __call__(self, method, path):
        self.operations.append((method, path))
        if method == "GET" and path.endswith("?per_page=100"):
            rows = [copy.deepcopy(v) for v in self.states.values()]
            if self.unknown is not None:
                rows.append(copy.deepcopy(self.unknown))
            return {"total_count": len(rows), "workflows": rows}
        ident = path.rsplit("/", 2)[-2] if path.endswith("/disable") else path.rsplit("/", 1)[-1]
        try:
            ident = int(ident)
        except ValueError as exc:
            raise AssertionError("unexpected fake GitHub path") from exc
        if method == "GET":
            record = copy.deepcopy(self.states[ident])
            if self.changing_response == ident:
                record["state"] = "disabled_manually"
            return record
        if method == "PUT" and path.endswith("/disable"):
            if self.fail_at_id == ident:
                raise ContainmentError("simulated GitHub disable API failure")
            self.states[ident]["state"] = "disabled_manually"
            return None
        raise AssertionError("fake GitHub only accepts exact inventory or disable")


class BrokerWorkflowContainmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.root.joinpath("PAUSE_AUTONOMY").write_text("PAUSED\n")
        guard = self.root / "src/company_os/competitive_launch_guard.py"
        guard.parent.mkdir(parents=True)
        guard.write_text("PRODUCTION_RELEASE_CONTROLLER_CERTIFIED = False\n")
        self.env = {
            "GITHUB_REPOSITORY": REPO,
            "GITHUB_ACTOR": "ksolo21-web",
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "KO_WORKFLOW_ADMIN_PRODUCTION_DISABLE": "1",
            "KO_OWNER_APPROVAL": CONFIRMATION,
        }
        self.api = FakeGitHubWorkflowAdmin()

    def run_admin(self, *, approved=True, env=None, api=None, root=None):
        return disable_registered_oanda_workflows(
            api or self.api, env=self.env if env is None else env,
            root=self.root if root is None else root, owner_approved=approved,
        )

    def test_owner_explicit_confirmation_disables_all_registered_broker_workflows(self):
        result = self.run_admin()
        self.assertEqual(result["target_workflows_verified_disabled"], 5)
        self.assertEqual(result["workflows_changed_this_run"], 5)
        self.assertEqual(
            result["status"], "REGISTERED_OANDA_WORKFLOWS_DISABLED_RECHECK_EXTERNAL_SCOPE",
        )
        self.assertTrue(all(x["state"] == "disabled_manually" for x in self.api.states.values()))
        self.assertEqual(len([x for x in self.api.operations if x[0] == "PUT"]), 5)
        self.assertFalse(result["release_authorized"])
        self.assertFalse(result["secrets_read_or_modified"])

    def test_second_run_idempotently_only_verifies_five_disabled_workflows(self):
        self.run_admin()
        self.api.operations.clear()
        result = self.run_admin()
        self.assertEqual(result["workflows_changed_this_run"], 0)
        self.assertEqual(len([x for x in self.api.operations if x[0] == "PUT"]), 0)

    def test_default_invocation_without_owner_approval_blocks_without_network(self):
        with self.assertRaises(ContainmentError):
            self.run_admin(approved=False)
        self.assertEqual(self.api.operations, [])

    def test_wrong_confirmation_blocks_before_api_access(self):
        env = {**self.env, "KO_OWNER_APPROVAL": "CANCEL_NO_CHANGES"}
        with self.assertRaises(ContainmentError):
            self.run_admin(env=env)
        self.assertEqual(self.api.operations, [])

    def test_wrong_actor_blocks_before_api_access(self):
        with self.assertRaises(ContainmentError):
            self.run_admin(env={**self.env, "GITHUB_ACTOR": "unrelated"})
        self.assertEqual(self.api.operations, [])

    def test_wrong_repository_blocks_before_api_access(self):
        with self.assertRaises(ContainmentError):
            self.run_admin(env={**self.env, "GITHUB_REPOSITORY": "other/repo"})
        self.assertEqual(self.api.operations, [])

    def test_nonmain_branch_blocks_before_api_access(self):
        with self.assertRaises(ContainmentError):
            self.run_admin(env={**self.env, "GITHUB_REF": "refs/heads/old-branch"})
        self.assertEqual(self.api.operations, [])

    def test_push_event_not_approved(self):
        with self.assertRaises(ContainmentError):
            self.run_admin(env={**self.env, "GITHUB_EVENT_NAME": "push"})
        self.assertEqual(self.api.operations, [])

    def test_missing_administrative_opt_in_blocks(self):
        with self.assertRaises(ContainmentError):
            self.run_admin(env={**self.env, "KO_WORKFLOW_ADMIN_PRODUCTION_DISABLE": "0"})
        self.assertEqual(self.api.operations, [])

    def test_missing_global_emergency_pause_blocks(self):
        self.root.joinpath("PAUSE_AUTONOMY").unlink()
        with self.assertRaises(ContainmentError):
            self.run_admin()
        self.assertEqual(self.api.operations, [])

    def test_if_production_lock_was_changed_operation_blocks(self):
        guard = self.root/"src/company_os/competitive_launch_guard.py"
        guard.write_text("PRODUCTION_RELEASE_CONTROLLER_CERTIFIED = True\n")
        with self.assertRaises(ContainmentError):
            self.run_admin()
        self.assertEqual(self.api.operations, [])

    def test_missing_registered_target_blocks_without_disabling_anything(self):
        self.api.states.pop(1005)
        with self.assertRaises(ContainmentError):
            self.run_admin()
        self.assertEqual(len([x for x in self.api.operations if x[0] == "PUT"]), 0)

    def test_unrecognized_registered_broker_workflow_blocks_containment(self):
        self.api.unknown = {
            "id": 3001, "path": ".github/workflows/oanda-shadow.yml", "state": "active",
        }
        with self.assertRaises(ContainmentError):
            self.run_admin()
        self.assertEqual(len([x for x in self.api.operations if x[0] == "PUT"]), 0)

    def test_duplicate_registered_workflow_id_blocks(self):
        self.api.unknown = {
            "id": 1001, "path": ".github/workflows/ci.yml", "state": "active",
        }
        with self.assertRaises(ContainmentError):
            self.run_admin()
        self.assertEqual(len([x for x in self.api.operations if x[0] == "PUT"]), 0)

    def test_unknown_workflow_state_blocks(self):
        self.api.states[1001]["state"] = "queued"
        with self.assertRaises(ContainmentError):
            self.run_admin()
        self.assertEqual(len([x for x in self.api.operations if x[0] == "PUT"]), 0)

    def test_preflight_concurrent_status_change_blocks_before_mutation(self):
        self.api.changing_response = 1003
        with self.assertRaises(ContainmentError):
            self.run_admin()
        self.assertEqual(len([x for x in self.api.operations if x[0] == "PUT"]), 0)

    def test_partial_api_failure_never_returns_a_false_success(self):
        self.api.fail_at_id = 1003
        with self.assertRaises(ContainmentError):
            self.run_admin()
        self.assertEqual(self.api.states[1001]["state"], "disabled_manually")
        self.assertEqual(self.api.states[1002]["state"], "disabled_manually")
        self.assertEqual(self.api.states[1003]["state"], "active")

    def test_an_unlisted_workflow_cannot_be_dispatched_or_modified(self):
        self.assertFalse(hasattr(self.api, "broker_token"))
        with self.assertRaises(ContainmentError):
            api_transport("synthetic-github-token-123")(
                "PUT", "/repos/" + REPO + "/actions/workflows/1/enable",
            )

    def test_transport_rejects_arbitrary_endpoint_and_post_methods(self):
        transport = api_transport("synthetic-github-token-123")
        for method, path in (
            ("POST", "/repos/" + REPO + "/actions/workflows/1001/disable"),
            ("PUT", "/repos/" + REPO + "/actions/workflows/1001/enable"),
            ("PUT", "/repos/other/repo/actions/workflows/1001/disable"),
            ("GET", "/repos/" + REPO + "/actions/secrets"),
            ("GET", "/repos/" + REPO + "/actions/workflows/../secrets"),
            ("PUT", "/repos/" + REPO + "/actions/workflows/0/disable"),
        ):
            with self.subTest(method=method, path=path):
                with self.assertRaises(ContainmentError):
                    transport(method, path)

    def test_transport_fails_missing_github_token_before_network(self):
        with self.assertRaises(ContainmentError):
            api_transport("")

    def test_unapproved_default_five_workflows_do_not_get_secret_values(self):
        calls = []
        def guard(method, path):
            calls.append((method, path))
            raise AssertionError("must not reach admin API")
        with self.assertRaises(ContainmentError):
            disable_registered_oanda_workflows(
                guard, env={**self.env, "KO_OWNER_APPROVAL": ""}, root=self.root,
                owner_approved=True,
            )
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
