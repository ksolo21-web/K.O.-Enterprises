"""P0: controlled, owner-triggered, repository-wide OANDA Actions disable.

GitHub workflow status is repository-wide (not tied to a branch). This action
requires deliberate owner invocation; importing this module does not change
permissions or run any network request. It never reads broker secrets.

This does not revoke credentials, audit all refs/tags, or prove every other
execution surface is disabled. Keep emergency pause and production hard lock.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Mapping

TARGET_FILES = (
    "oanda-forward-scan.yml",
    "oanda-fresh-tournament.yml",
    "oanda-practice-research.yml",
    "oanda-wave3-preholdout.yml",
    "oanda-wave4-preholdout.yml",
)
TARGET_PATHS = tuple(".github/workflows/" + name for name in TARGET_FILES)
REPO = "ksolo21-web/K.O.-Enterprises"
CONFIRMATION = "DISABLE_ALL_FIVE_OANDA_WORKFLOWS"
GITHUB_API = "https://api.github.com"
ALLOWED_STATES = frozenset({
    "active", "disabled_manually", "disabled_inactivity",
})
TARGET_DISABLED = frozenset({"disabled_manually", "disabled_inactivity"})
MAX_WORKFLOWS = 100


class ContainmentError(ValueError):
    """No information about live tokens, broker accounts or payloads."""


def _require_identity(
    env: Mapping[str, str], *, owner_approved: bool, root: Path,
) -> None:
    """Fail closed unless actual user workflow_dispatch on guarded main."""
    if (
        not owner_approved
        or env.get("GITHUB_REPOSITORY") != REPO
        or env.get("GITHUB_ACTOR") != REPO.split("/")[0]
        or env.get("GITHUB_REF") != "refs/heads/main"
        or env.get("GITHUB_EVENT_NAME") != "workflow_dispatch"
        or env.get("KO_WORKFLOW_ADMIN_PRODUCTION_DISABLE") != "1"
        or env.get("KO_OWNER_APPROVAL") != CONFIRMATION
    ):
        raise ContainmentError("owner-approved main-only containment invocation required")
    if not root.is_dir() or not (root / "PAUSE_AUTONOMY").is_file():
        raise ContainmentError("root emergency pause is absent or unsafe")
    guard_file = root / "src/company_os/competitive_launch_guard.py"
    if (guard_file.is_symlink() or not guard_file.is_file()
            or "PRODUCTION_RELEASE_CONTROLLER_CERTIFIED = False"
            not in guard_file.read_text("utf-8")):
        raise ContainmentError("global production hard lock must stay false")


def _validate_inventory(reply: Any) -> dict[str, dict[str, Any]]:
    if (not isinstance(reply, dict) or type(reply.get("total_count")) is not int
            or reply["total_count"] < len(TARGET_FILES)
            or reply["total_count"] > MAX_WORKFLOWS):
        raise ContainmentError("GitHub Actions workflow inventory absent or excessive")
    registered = reply.get("workflows")
    if not isinstance(registered, list) or len(registered) != reply["total_count"]:
        raise ContainmentError("incomplete paged GitHub Actions workflow inventory")
    found: dict[str, dict[str, Any]] = {}
    workflow_ids: set[int] = set()
    for item in registered:
        if not isinstance(item, dict):
            raise ContainmentError("malformed GitHub Actions workflow record")
        path, state, identity = item.get("path"), item.get("state"), item.get("id")
        if (not isinstance(path, str) or not path.startswith(".github/workflows/")
                or type(identity) is not int or identity <= 0
                or identity in workflow_ids or not isinstance(state, str)
                or state not in ALLOWED_STATES):
            raise ContainmentError("GitHub Actions workflow identity/state invalid")
        workflow_ids.add(identity)
        name = path.rsplit("/", 1)[-1]
        if ("oanda" in name.casefold() or "broker" in name.casefold()) and path not in TARGET_PATHS:
            raise ContainmentError("unrecognized broker-related workflow; manual admin review required")
        if path in TARGET_PATHS:
            if path in found:
                raise ContainmentError("duplicate OANDA workflow path")
            found[path] = {"id": identity, "state": state}
    if set(found) != set(TARGET_PATHS):
        raise ContainmentError("not all five registered OANDA workflows were discovered")
    return found


def _checked_single(reply: Any, *, expected_id: int, expected_path: str) -> str:
    if (not isinstance(reply, dict) or reply.get("path") != expected_path
            or type(reply.get("id")) is not int or reply["id"] != expected_id
            or reply.get("state") not in ALLOWED_STATES):
        raise ContainmentError("GitHub workflow identity changed during containment")
    return reply["state"]


def disable_registered_oanda_workflows(
    api: Callable[[str, str], Any],
    *,
    env: Mapping[str, str],
    root: Path | str,
    owner_approved: bool = False,
) -> dict[str, Any]:
    """Disable known repository-global Actions workflow IDs, then verify state.

    All owner/lock/inventory checks happen before the first mutation. The
    caller must inject the API transport; tests use only a memory transport.
    Mid-operation failures block and require an admin to reconcile state.
    """
    _require_identity(env, owner_approved=owner_approved, root=Path(root))
    base = "/repos/" + REPO + "/actions/workflows"
    records = _validate_inventory(api("GET", base + "?per_page=100"))
    for path in TARGET_PATHS:
        item = records[path]
        current = _checked_single(
            api("GET", base + "/" + str(item["id"])),
            expected_id=item["id"], expected_path=path,
        )
        if current != item["state"]:
            raise ContainmentError("broker workflow state changed during containment preflight")
    # All reads completed; never enable any workflow in this action.
    changed: list[str] = []
    for path in TARGET_PATHS:
        item = records[path]
        if item["state"] == "active":
            result = api("PUT", base + "/" + str(item["id"]) + "/disable")
            if result not in (None, {}):
                raise ContainmentError("broker workflow disable endpoint gave unexpected response")
            changed.append(path)
        current = _checked_single(
            api("GET", base + "/" + str(item["id"])),
            expected_id=item["id"], expected_path=path,
        )
        if current not in TARGET_DISABLED:
            raise ContainmentError("GitHub did not verify disabled broker workflow state")
    # In case another admin added a workflow mid-operation, re-enumerate.
    final = _validate_inventory(api("GET", base + "?per_page=100"))
    if (set(final) != set(records)
            or any(final[p]["id"] != records[p]["id"]
                   or final[p]["state"] not in TARGET_DISABLED for p in TARGET_PATHS)):
        raise ContainmentError("broker workflow registry changed during containment")
    return {
        "status": "REGISTERED_OANDA_WORKFLOWS_DISABLED_RECHECK_EXTERNAL_SCOPE",
        "target_workflows_verified_disabled": len(TARGET_FILES),
        "workflows_changed_this_run": len(changed),
        "executed_broker_network_calls": False,
        "secrets_read_or_modified": False,
        "all_branches_and_tags_independently_audited": False,
        "effective_secret_scopes_independently_verified": False,
        "release_authorized": False,
    }


def api_transport(token: str) -> Callable[[str, str], Any]:
    """Restricted GitHub Actions metadata transport; no arbitrary network URL."""
    if not isinstance(token, str) or len(token) < 10:
        raise ContainmentError("GitHub Actions administrative token unavailable")

    def call(method: str, relative: str) -> Any:
        if (
            method not in ("GET", "PUT")
            or not isinstance(relative, str)
            or not re.fullmatch(
                r"/repos/ksolo21-web/K[.]O[.]-Enterprises/actions/workflows"
                r"(?:[?]per_page=100|/[1-9][0-9]*(?:/disable)?)?", relative,
            )
            or (method == "PUT" and not relative.endswith("/disable"))
            or (method == "GET" and relative.endswith("/disable"))
        ):
            raise ContainmentError("GitHub Actions administrative request not allowlisted")
        request = urllib.request.Request(
            GITHUB_API + relative,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": "Bearer " + token,
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "KO-Emergency-Workflow-Containment",
            },
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=12) as response:
                if method == "PUT":
                    if response.status not in (200, 204):
                        raise ContainmentError("GitHub rejected workflow disable")
                    return None
                if response.status != 200:
                    raise ContainmentError("GitHub Actions inventory HTTP status invalid")
                raw = response.read(120_001)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ContainmentError("GitHub Actions admin request failed") from exc
        if len(raw) > 120_000:
            raise ContainmentError("GitHub Actions workflow inventory too large")
        try:
            return json.loads(raw)
        except (ValueError, UnicodeDecodeError) as exc:
            raise ContainmentError("GitHub Actions workflow metadata invalid") from exc

    return call


def main() -> int:
    # No shell interpolation and no live broker secrets in process environment.
    token = os.environ.get("GITHUB_TOKEN", "")
    try:
        result = disable_registered_oanda_workflows(
            api_transport(token),
            env=os.environ,
            root=Path.cwd(),
            owner_approved=True,
        )
    except (ContainmentError, OSError, ValueError) as exc:
        print("BLOCK: GitHub Actions workflow containment not certified: " + str(exc))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
