"""Executable corporate hierarchy, objectives, durable work, and reviews.

This module turns the descriptive company model into an enforceable internal
control plane.  It deliberately does not execute external side effects.  A
future connector layer must consume policy-bound execution permits rather than
calling remote systems directly from the work queue.
"""

from __future__ import annotations

import hashlib
import json
import math
import secrets
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Any, Iterable, Mapping, Sequence

from .errors import ConflictError, NotFoundError, ValidationError
from .organization import (
    DEPARTMENTS,
    ROLES,
    WORKERS,
    can_command,
    validate_blueprint,
)
from .runtime import require_task_transition, retry_backoff_seconds
from .storage import (
    CompanyStore,
    _normalize_timestamp,
    _require_text,
    _utc_now,
    normalize_owner_decision_packet,
)


ACTIVE_WORKER_STATUSES = frozenset({"active", "probationary", "coaching"})
TERMINAL_WORK_STATUSES = frozenset({"succeeded", "failed", "dead_letter", "cancelled"})
CONTROL_DOMAINS = frozenset(domain for role in ROLES for domain in role.block_domains)


class DecisionClass(StrEnum):
    WORK_EXECUTION = "work_execution"
    DEPARTMENT_OPERATION = "department_operation"
    EXECUTIVE_PORTFOLIO = "executive_portfolio"
    CONTROLLED_EXTERNAL = "controlled_external"
    OWNER_RESERVED = "owner_reserved"
    PROHIBITED = "prohibited"


def _json_object(value: Mapping[str, Any] | None) -> str:
    return json.dumps(value or {}, sort_keys=True, separators=(",", ":"), default=str)


def _json_array(value: Iterable[Any] | None) -> str:
    return json.dumps(list(value or ()), sort_keys=True, separators=(",", ":"), default=str)


def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def _bounded_integer(name: str, value: Any, *, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValidationError(f"{name} must be an integer between {minimum} and {maximum}")
    return value


class CorporateOperations:
    """CompanyStore-backed organization and work-management service."""

    def __init__(self, store: CompanyStore) -> None:
        self.store = store

    def _record_prohibited_work_denial(
        self,
        *,
        commanded_by_worker: str,
        work_key: object,
        assigned_role_key: object,
        title: object,
    ) -> bool:
        """Persist a contained policy incident before rejecting prohibited work."""

        try:
            with self.store._transaction() as connection:
                actor = self._active_worker(connection, commanded_by_worker)
                now = _utc_now()
                incident_key = (
                    f"prohibited-work-{now.replace(':', '').replace('-', '')}-"
                    f"{secrets.token_hex(4)}"
                )
                cursor = connection.execute(
                    """
                    INSERT INTO incidents(
                        incident_key, severity, title, description, affected_scope,
                        owner_role_key, status, containment,
                        ceo_notification_required, opened_by_worker, opened_at
                    ) VALUES (?, 'sev2', ?, ?, ?, 'risk_legal_chief',
                              'contained', ?, 0, ?, ?)
                    """,
                    (
                        incident_key,
                        "Prohibited work issuance was denied",
                        f"A prohibited work request was attempted: {str(title).strip()[:300]}",
                        f"work_key={str(work_key)[:200]}; role={str(assigned_role_key)[:100]}",
                        "Denied before a work item, lease, cost, or external effect was created.",
                        commanded_by_worker,
                        now,
                    ),
                )
                incident_id = int(cursor.lastrowid)
                connection.execute(
                    """
                    INSERT INTO incident_events(
                        incident_id, event_type, actor_worker_key, detail_json, created_at
                    ) VALUES (?, 'work.prohibited_denied', ?, ?, ?)
                    """,
                    (
                        incident_id,
                        commanded_by_worker,
                        _json_object(
                            {
                                "work_key": str(work_key)[:200],
                                "assigned_role_key": str(assigned_role_key)[:100],
                                "contained": True,
                            }
                        ),
                        now,
                    ),
                )
                self.store._write_audit(
                    connection,
                    event_type="work.prohibited_denied",
                    actor=commanded_by_worker,
                    entity_type="incident",
                    entity_id=incident_id,
                    action="deny_prohibited_work",
                    details={
                        "work_key": str(work_key)[:200],
                        "assigned_role_key": str(assigned_role_key)[:100],
                        "actor_role_key": actor["role_key"],
                    },
                )
            return True
        except Exception:
            # The denial itself must remain fail-closed even if the audit store
            # is unavailable. The caller's error text exposes the logging fault.
            return False

    @staticmethod
    def _worker(connection: sqlite3.Connection, worker_key: str) -> sqlite3.Row:
        row = connection.execute(
            """
            SELECT workers.*, roles.department_slug, roles.reports_to_role_key,
                   roles.authority_level, roles.max_active_work,
                   roles.independent_control, roles.capabilities_json
            FROM workers
            JOIN roles ON roles.role_key = workers.role_key
            WHERE workers.worker_key = ?
            """,
            (_require_text("worker_key", worker_key),),
        ).fetchone()
        if row is None:
            raise NotFoundError(f"worker not found: {worker_key}")
        return row

    @classmethod
    def _active_worker(cls, connection: sqlite3.Connection, worker_key: str) -> sqlite3.Row:
        worker = cls._worker(connection, worker_key)
        if worker["status"] not in ACTIVE_WORKER_STATUSES:
            raise ConflictError(f"worker {worker_key} is not active")
        return worker

    @staticmethod
    def _role(connection: sqlite3.Connection, role_key: str) -> sqlite3.Row:
        row = connection.execute(
            "SELECT * FROM roles WHERE role_key = ?",
            (_require_text("role_key", role_key),),
        ).fetchone()
        if row is None:
            raise NotFoundError(f"role not found: {role_key}")
        if row["status"] != "active":
            raise ConflictError(f"role {role_key} is not active")
        return row

    @staticmethod
    def _work(connection: sqlite3.Connection, work_identifier: str | int) -> sqlite3.Row:
        if isinstance(work_identifier, int) or str(work_identifier).isdigit():
            row = connection.execute(
                "SELECT * FROM work_items WHERE id = ?", (int(work_identifier),)
            ).fetchone()
        else:
            row = connection.execute(
                "SELECT * FROM work_items WHERE work_key = ?", (str(work_identifier),)
            ).fetchone()
        if row is None:
            raise NotFoundError(f"work item not found: {work_identifier}")
        return row

    @staticmethod
    def _require_active_bound_approval(
        connection: sqlite3.Connection, work: sqlite3.Row
    ) -> None:
        approval_id = work["approval_id"]
        if approval_id is None:
            if work["decision_class"] == DecisionClass.OWNER_RESERVED.value:
                raise ConflictError("owner-reserved work has no bound approval")
            return
        approval = connection.execute(
            "SELECT * FROM approvals WHERE id = ?", (approval_id,)
        ).fetchone()
        if approval is None:
            raise ConflictError("bound work approval is missing")
        if approval["status"] != "approved" or approval["expires_at"] <= _utc_now():
            raise ConflictError("bound work approval is no longer active")
        if approval["approval_class"] != "ceo_approval_required":
            raise ConflictError("bound work approval is not CEO-class")
        if approval["decided_by"] != "kaleb_ceo":
            raise ConflictError("bound work approval lacks the owner decision identity")
        expected_action = f"authorize_work:{work['work_key']}"
        if approval["action"].casefold() != expected_action.casefold():
            raise ConflictError("bound work approval action does not match")
        try:
            packet, packet_digest = normalize_owner_decision_packet(
                json.loads(approval["decision_packet_json"])
            )
        except (TypeError, ValueError, json.JSONDecodeError, ValidationError) as exc:
            raise ConflictError("bound owner decision packet is invalid") from exc
        if not secrets.compare_digest(str(approval["packet_digest"]), packet_digest):
            raise ConflictError("bound owner decision packet digest does not match")
        if packet["exact_action"].casefold() != expected_action.casefold():
            raise ConflictError("bound owner decision packet action does not match")
        if int(approval["estimated_cost_cents"]) < int(work["estimated_cost_cents"]):
            raise ConflictError("bound approval cost ceiling is below the work estimate")

    @staticmethod
    def _objective(
        connection: sqlite3.Connection, objective_identifier: str | int
    ) -> sqlite3.Row:
        if isinstance(objective_identifier, int) or str(objective_identifier).isdigit():
            row = connection.execute(
                "SELECT * FROM objectives WHERE id = ?", (int(objective_identifier),)
            ).fetchone()
        else:
            row = connection.execute(
                "SELECT * FROM objectives WHERE objective_key = ?",
                (str(objective_identifier),),
            ).fetchone()
        if row is None:
            raise NotFoundError(f"objective not found: {objective_identifier}")
        return row

    @classmethod
    def _can_manage_objective(
        cls,
        connection: sqlite3.Connection,
        actor_role_key: str,
        objective: sqlite3.Row,
    ) -> bool:
        return (
            objective["owner_role_key"] == actor_role_key
            or cls._db_can_command(
                connection, actor_role_key, objective["owner_role_key"]
            )
        )

    @staticmethod
    def _record_work_event(
        connection: sqlite3.Connection,
        *,
        work_id: int,
        event_type: str,
        actor_worker_key: str,
        from_status: str | None,
        to_status: str | None,
        details: Mapping[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> None:
        connection.execute(
            """
            INSERT INTO work_events(
                work_id, event_type, actor_worker_key, from_status, to_status,
                detail_json, correlation_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                work_id,
                event_type,
                actor_worker_key,
                from_status,
                to_status,
                _json_object(details),
                correlation_id or secrets.token_hex(12),
                _utc_now(),
            ),
        )

    @staticmethod
    def _db_can_command(
        connection: sqlite3.Connection, commander_role_key: str, target_role_key: str
    ) -> bool:
        """Check the persisted tree, never a caller-supplied authority level."""

        if commander_role_key == target_role_key:
            return False
        commander = connection.execute(
            "SELECT capabilities_json FROM roles WHERE role_key = ? AND status = 'active'",
            (commander_role_key,),
        ).fetchone()
        if commander is None:
            return False
        capabilities = json.loads(commander["capabilities_json"])
        if not any(str(capability).startswith("command:") for capability in capabilities):
            return False
        seen: set[str] = set()
        current = target_role_key
        while current and current not in seen:
            seen.add(current)
            row = connection.execute(
                "SELECT reports_to_role_key FROM roles WHERE role_key = ? AND status = 'active'",
                (current,),
            ).fetchone()
            if row is None:
                return False
            current = row["reports_to_role_key"]
            if current == commander_role_key:
                return True
        return False

    def bootstrap_organization(self, *, actor: str = "company_os") -> dict[str, Any]:
        """Install or reconcile the version-controlled organization blueprint."""

        validate_blueprint()
        now = _utc_now()
        with self.store._transaction() as connection:
            for department in DEPARTMENTS:
                connection.execute(
                    """
                    INSERT INTO departments(
                        slug, name, mission, parent_slug, executive_role_key,
                        service_level_cycles, wip_limit, status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
                    ON CONFLICT(slug) DO UPDATE SET
                        name = excluded.name,
                        mission = excluded.mission,
                        parent_slug = excluded.parent_slug,
                        executive_role_key = excluded.executive_role_key,
                        service_level_cycles = excluded.service_level_cycles,
                        wip_limit = excluded.wip_limit,
                        updated_at = excluded.updated_at
                    """,
                    (
                        department.slug,
                        department.name,
                        department.mission,
                        department.parent_slug,
                        department.executive_role_key,
                        department.service_level_cycles,
                        department.wip_limit,
                        now,
                        now,
                    ),
                )
            for role in ROLES:
                connection.execute(
                    """
                    INSERT INTO roles(
                        role_key, department_slug, title, reports_to_role_key,
                        authority_level, worker_type, mandate, capabilities_json,
                        kpis_json, max_active_work, independent_control, status,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
                    ON CONFLICT(role_key) DO UPDATE SET
                        department_slug = excluded.department_slug,
                        title = excluded.title,
                        reports_to_role_key = excluded.reports_to_role_key,
                        authority_level = excluded.authority_level,
                        worker_type = excluded.worker_type,
                        mandate = excluded.mandate,
                        capabilities_json = excluded.capabilities_json,
                        kpis_json = excluded.kpis_json,
                        max_active_work = excluded.max_active_work,
                        independent_control = excluded.independent_control,
                        updated_at = excluded.updated_at
                    """,
                    (
                        role.role_key,
                        role.department_slug,
                        role.title,
                        role.reports_to_role_key,
                        role.authority_level,
                        role.worker_type,
                        role.mandate,
                        _json_array(role.capabilities),
                        _json_array(role.kpis),
                        role.max_active_work,
                        int(role.independent_control),
                        now,
                        now,
                    ),
                )
            for worker in WORKERS:
                connection.execute(
                    """
                    INSERT INTO workers(
                        worker_key, display_name, role_key, manager_worker_key,
                        worker_type, status, capacity_units, quality_floor,
                        appointed_by, appointed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(worker_key) DO UPDATE SET
                        display_name = excluded.display_name,
                        role_key = excluded.role_key,
                        manager_worker_key = excluded.manager_worker_key,
                        worker_type = excluded.worker_type,
                        capacity_units = excluded.capacity_units,
                        quality_floor = excluded.quality_floor
                    """,
                    (
                        worker.worker_key,
                        worker.display_name,
                        worker.role_key,
                        worker.manager_worker_key,
                        worker.worker_type,
                        worker.status,
                        worker.capacity_units,
                        worker.quality_floor,
                        actor,
                        now,
                    ),
                )
            self.store._write_audit(
                connection,
                event_type="organization.bootstrapped",
                actor=actor,
                entity_type="organization",
                entity_id="ko-enterprises",
                action="bootstrap_organization",
                details={
                    "departments": len(DEPARTMENTS),
                    "roles": len(ROLES),
                    "workers": len(WORKERS),
                },
            )
        return {
            "departments": len(DEPARTMENTS),
            "roles": len(ROLES),
            "workers": len(WORKERS),
        }

    def organization_snapshot(self) -> dict[str, list[dict[str, Any]]]:
        self.store.initialize()
        with self.store._connection() as connection:
            departments = [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM departments ORDER BY rowid"
                ).fetchall()
            ]
            roles = [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM roles ORDER BY authority_level DESC, role_key"
                ).fetchall()
            ]
            workers = [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM workers ORDER BY worker_key"
                ).fetchall()
            ]
        for role in roles:
            role["capabilities"] = json.loads(role.pop("capabilities_json"))
            role["kpis"] = json.loads(role.pop("kpis_json"))
            role["independent_control"] = bool(role["independent_control"])
        return {"departments": departments, "roles": roles, "workers": workers}

    def command_authorized(self, commander_worker: str, target_role_key: str) -> bool:
        self.store.initialize()
        with self.store._connection() as connection:
            commander = self._active_worker(connection, commander_worker)
            self._role(connection, target_role_key)
            return self._db_can_command(connection, commander["role_key"], target_role_key)

    def create_objective(
        self,
        *,
        objective_key: str,
        title: str,
        owner_role_key: str,
        commanded_by_worker: str,
        description: str = "",
        priority: int = 50,
        parent_objective_id: int | None = None,
        starts_at: str | None = None,
        due_at: str | None = None,
    ) -> dict[str, Any]:
        objective_key = _require_text("objective_key", objective_key)
        title = _require_text("title", title)
        priority = _bounded_integer("priority", priority, minimum=0, maximum=100)
        normalized_start = _normalize_timestamp(starts_at, default_now=True)
        normalized_due = _normalize_timestamp(due_at)
        if normalized_due is not None and normalized_due <= normalized_start:
            raise ValidationError("due_at must be later than starts_at")
        with self.store._transaction() as connection:
            commander = self._active_worker(connection, commanded_by_worker)
            owner_role = self._role(connection, owner_role_key)
            if not self._db_can_command(connection, commander["role_key"], owner_role_key):
                raise ConflictError(
                    f"{commanded_by_worker} cannot command role {owner_role_key}"
                )
            if parent_objective_id is not None:
                parent = connection.execute(
                    "SELECT id FROM objectives WHERE id = ?", (parent_objective_id,)
                ).fetchone()
                if parent is None:
                    raise NotFoundError(f"parent objective not found: {parent_objective_id}")
            now = _utc_now()
            try:
                cursor = connection.execute(
                    """
                    INSERT INTO objectives(
                        objective_key, parent_objective_id, title, description,
                        owner_role_key, department_slug, commanded_by_worker,
                        priority, status, starts_at, due_at, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?)
                    """,
                    (
                        objective_key,
                        parent_objective_id,
                        title,
                        description.strip(),
                        owner_role_key,
                        owner_role["department_slug"],
                        commanded_by_worker,
                        priority,
                        normalized_start,
                        normalized_due,
                        now,
                        now,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ConflictError(f"objective key already exists: {objective_key}") from exc
            objective_id = int(cursor.lastrowid)
            self.store._write_audit(
                connection,
                event_type="objective.created",
                actor=commanded_by_worker,
                entity_type="objective",
                entity_id=objective_id,
                action="create_objective",
                details={"objective_key": objective_key, "owner_role_key": owner_role_key},
            )
            result = connection.execute(
                "SELECT * FROM objectives WHERE id = ?", (objective_id,)
            ).fetchone()
        return dict(result)

    def get_objective(self, objective_identifier: str | int) -> dict[str, Any]:
        self.store.initialize()
        with self.store._connection() as connection:
            row = self._objective(connection, objective_identifier)
            result = dict(row)
            result["key_results"] = [
                dict(item)
                for item in connection.execute(
                    "SELECT * FROM key_results WHERE objective_id = ? ORDER BY id",
                    (row["id"],),
                ).fetchall()
            ]
        return result

    def list_objectives(self, status: str | None = None) -> list[dict[str, Any]]:
        self.store.initialize()
        query = """
            SELECT objectives.*,
                   COUNT(key_results.id) AS key_result_count,
                   SUM(CASE WHEN key_results.status = 'achieved' THEN 1 ELSE 0 END)
                       AS achieved_key_results
            FROM objectives
            LEFT JOIN key_results ON key_results.objective_id = objectives.id
        """
        params: tuple[Any, ...] = ()
        if status is not None:
            query += " WHERE objectives.status = ?"
            params = (status,)
        query += " GROUP BY objectives.id ORDER BY objectives.priority DESC, objectives.created_at"
        with self.store._connection() as connection:
            return [dict(row) for row in connection.execute(query, params).fetchall()]

    def create_key_result(
        self,
        objective_identifier: str | int,
        *,
        result_key: str,
        description: str,
        metric_name: str,
        baseline: float,
        target: float,
        unit: str,
        actor_worker: str,
    ) -> dict[str, Any]:
        if isinstance(baseline, bool) or isinstance(target, bool):
            raise ValidationError("key-result baseline and target must be numeric")
        try:
            baseline_value = float(baseline)
            target_value = float(target)
        except (TypeError, ValueError) as exc:
            raise ValidationError("key-result baseline and target must be numeric") from exc
        if not math.isfinite(baseline_value) or not math.isfinite(target_value):
            raise ValidationError("key-result baseline and target must be finite")
        if baseline_value == target_value:
            raise ValidationError("key-result target must differ from its baseline")
        with self.store._transaction() as connection:
            actor = self._active_worker(connection, actor_worker)
            objective = self._objective(connection, objective_identifier)
            if not self._can_manage_objective(connection, actor["role_key"], objective):
                raise ConflictError("worker cannot manage this objective")
            if objective["status"] not in {"active", "at_risk"}:
                raise ConflictError("key results require an active objective")
            now = _utc_now()
            try:
                cursor = connection.execute(
                    """
                    INSERT INTO key_results(
                        objective_id, result_key, description, metric_name,
                        baseline, target, current_value, unit, status, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)
                    """,
                    (
                        objective["id"],
                        _require_text("result_key", result_key),
                        _require_text("description", description),
                        _require_text("metric_name", metric_name),
                        baseline_value,
                        target_value,
                        baseline_value,
                        _require_text("unit", unit),
                        now,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ConflictError(f"key result could not be created: {exc}") from exc
            result_id = int(cursor.lastrowid)
            self.store._write_audit(
                connection,
                event_type="objective.key_result_created",
                actor=actor_worker,
                entity_type="key_result",
                entity_id=result_id,
                action="create_key_result",
                details={"objective_id": objective["id"], "result_key": result_key},
            )
            row = connection.execute(
                "SELECT * FROM key_results WHERE id = ?", (result_id,)
            ).fetchone()
        return dict(row)

    def update_key_result(
        self,
        key_result_id: int,
        *,
        current_value: float,
        evidence_reference: str,
        actor_worker: str,
        status: str | None = None,
    ) -> dict[str, Any]:
        if isinstance(current_value, bool):
            raise ValidationError("current_value must be numeric")
        try:
            numeric_value = float(current_value)
        except (TypeError, ValueError) as exc:
            raise ValidationError("current_value must be numeric") from exc
        if not math.isfinite(numeric_value):
            raise ValidationError("current_value must be finite")
        if status is not None and status not in {"active", "at_risk", "achieved", "cancelled"}:
            raise ValidationError("invalid key-result status")
        evidence_reference = _require_text("evidence_reference", evidence_reference)
        with self.store._transaction() as connection:
            actor = self._active_worker(connection, actor_worker)
            row = connection.execute(
                """
                SELECT key_results.*, objectives.owner_role_key,
                       objectives.status AS objective_status
                FROM key_results
                JOIN objectives ON objectives.id = key_results.objective_id
                WHERE key_results.id = ?
                """,
                (key_result_id,),
            ).fetchone()
            if row is None:
                raise NotFoundError(f"key result not found: {key_result_id}")
            if row["objective_status"] not in {"active", "at_risk"}:
                raise ConflictError("key results can only change while their objective is active")
            if row["status"] in {"achieved", "cancelled"}:
                raise ConflictError(
                    "terminal key results are immutable; create a new objective version to continue"
                )
            if not (
                row["owner_role_key"] == actor["role_key"]
                or self._db_can_command(
                    connection, actor["role_key"], row["owner_role_key"]
                )
            ):
                raise ConflictError("worker cannot update this objective's key results")
            reached = (
                numeric_value >= row["target"]
                if row["target"] > row["baseline"]
                else numeric_value <= row["target"]
            )
            target_status = status or ("achieved" if reached else "active")
            if target_status == "achieved" and not reached:
                raise ConflictError("key result cannot be achieved before its target is reached")
            connection.execute(
                """
                UPDATE key_results
                SET current_value = ?, evidence_reference = ?, status = ?, updated_at = ?
                WHERE id = ?
                """,
                (numeric_value, evidence_reference, target_status, _utc_now(), key_result_id),
            )
            self.store._write_audit(
                connection,
                event_type="objective.key_result_updated",
                actor=actor_worker,
                entity_type="key_result",
                entity_id=key_result_id,
                action="update_key_result",
                details={
                    "current_value": numeric_value,
                    "status": target_status,
                    "evidence_reference": evidence_reference,
                },
            )
            updated = connection.execute(
                "SELECT * FROM key_results WHERE id = ?", (key_result_id,)
            ).fetchone()
        return dict(updated)

    def set_objective_status(
        self,
        objective_identifier: str | int,
        *,
        status: str,
        rationale: str,
        actor_worker: str,
    ) -> dict[str, Any]:
        if status not in {"active", "at_risk", "achieved", "cancelled"}:
            raise ValidationError("invalid objective status")
        rationale = _require_text("rationale", rationale)
        with self.store._transaction() as connection:
            actor = self._active_worker(connection, actor_worker)
            objective = self._objective(connection, objective_identifier)
            if not self._can_manage_objective(connection, actor["role_key"], objective):
                raise ConflictError("worker cannot change this objective")
            if objective["status"] in {"achieved", "cancelled"}:
                if status == objective["status"]:
                    return dict(objective)
                raise ConflictError(
                    "terminal objectives are immutable; create a new objective version"
                )
            if status == "achieved":
                progress = connection.execute(
                    """
                    SELECT COUNT(*) AS total,
                           SUM(CASE WHEN status = 'achieved' THEN 1 ELSE 0 END) AS achieved
                    FROM key_results WHERE objective_id = ?
                    """,
                    (objective["id"],),
                ).fetchone()
                if not progress["total"] or progress["achieved"] != progress["total"]:
                    raise ConflictError(
                        "objective cannot be achieved until every key result is achieved"
                    )
            if status == "achieved":
                in_flight = int(
                    connection.execute(
                        """
                        SELECT COUNT(*) AS count FROM work_items
                        WHERE objective_id = ? AND status IN ('leased','running','review')
                        """,
                        (objective["id"],),
                    ).fetchone()["count"]
                )
                if in_flight:
                    raise ConflictError(
                        "objective cannot be achieved while linked work is leased, running, or in review"
                    )
            if status in {"achieved", "cancelled"}:
                queued = connection.execute(
                    """
                    SELECT * FROM work_items
                    WHERE objective_id = ?
                      AND status NOT IN ('succeeded','failed','dead_letter','cancelled')
                    ORDER BY id
                    """,
                    (objective["id"],),
                ).fetchall()
                for work in queued:
                    require_task_transition(work["status"], "cancelled")
                    connection.execute(
                        """
                        UPDATE work_items
                        SET status = 'cancelled', error_text = ?,
                            lease_owner = NULL, lease_token = NULL,
                            lease_expires_at = NULL, lease_epoch = lease_epoch + 1,
                            updated_at = ?
                        WHERE id = ?
                        """,
                        (f"objective {status}", _utc_now(), work["id"]),
                    )
                    self._record_work_event(
                        connection,
                        work_id=work["id"],
                        event_type="work.cancelled_by_objective",
                        actor_worker_key=actor_worker,
                        from_status=work["status"],
                        to_status="cancelled",
                        details={"objective_id": objective["id"], "objective_status": status},
                    )
            connection.execute(
                "UPDATE objectives SET status = ?, updated_at = ? WHERE id = ?",
                (status, _utc_now(), objective["id"]),
            )
            self.store._write_audit(
                connection,
                event_type="objective.status_changed",
                actor=actor_worker,
                entity_type="objective",
                entity_id=objective["id"],
                action="set_objective_status",
                details={"from": objective["status"], "to": status, "rationale": rationale},
            )
            updated = connection.execute(
                "SELECT * FROM objectives WHERE id = ?", (objective["id"],)
            ).fetchone()
        return dict(updated)

    def create_cycle(
        self,
        *,
        cycle_key: str,
        mode: str,
        triggered_by_worker: str,
        scheduled: bool = False,
        max_work_items: int = 20,
        plan: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if mode not in {"simulation", "internal", "shadow", "external"}:
            raise ValidationError("unknown operating cycle mode")
        max_work_items = _bounded_integer(
            "max_work_items", max_work_items, minimum=1, maximum=1000
        )
        with self.store._transaction() as connection:
            self._active_worker(connection, triggered_by_worker)
            existing = connection.execute(
                "SELECT * FROM operating_cycles WHERE cycle_key = ?", (cycle_key,)
            ).fetchone()
            if existing is not None:
                return dict(existing)
            running = connection.execute(
                "SELECT cycle_key FROM operating_cycles WHERE status = 'running' LIMIT 1"
            ).fetchone()
            if running is not None:
                raise ConflictError(
                    f"operating coordinator is already running cycle {running['cycle_key']}"
                )
            cursor = connection.execute(
                """
                INSERT INTO operating_cycles(
                    cycle_key, mode, status, triggered_by_worker, scheduled,
                    max_work_items, plan_json, started_at
                ) VALUES (?, ?, 'running', ?, ?, ?, ?, ?)
                """,
                (
                    _require_text("cycle_key", cycle_key),
                    mode,
                    triggered_by_worker,
                    int(scheduled),
                    max_work_items,
                    _json_object(plan),
                    _utc_now(),
                ),
            )
            cycle_id = int(cursor.lastrowid)
            self.store._write_audit(
                connection,
                event_type="cycle.started",
                actor=triggered_by_worker,
                entity_type="operating_cycle",
                entity_id=cycle_id,
                action="create_cycle",
                details={"mode": mode, "scheduled": scheduled},
            )
            row = connection.execute(
                "SELECT * FROM operating_cycles WHERE id = ?", (cycle_id,)
            ).fetchone()
        return dict(row)

    def recover_stale_cycles(
        self,
        *,
        actor_worker: str = "sre_operator",
        max_age_seconds: int = 3600,
    ) -> int:
        """Fail closed any coordinator cycle abandoned by a dead process."""

        max_age_seconds = _bounded_integer(
            "max_age_seconds", max_age_seconds, minimum=60, maximum=86400
        )
        now_dt = datetime.now(timezone.utc)
        now = now_dt.isoformat(timespec="seconds").replace("+00:00", "Z")
        cutoff = (now_dt - timedelta(seconds=max_age_seconds)).isoformat(
            timespec="seconds"
        ).replace("+00:00", "Z")
        recovered = 0
        with self.store._transaction() as connection:
            self._active_worker(connection, actor_worker)
            stale = connection.execute(
                """
                SELECT * FROM operating_cycles
                WHERE status = 'running' AND started_at <= ?
                ORDER BY id
                """,
                (cutoff,),
            ).fetchall()
            for cycle in stale:
                summary = {
                    "external_effects_executed": 0,
                    "aborted_by_stale_coordinator_recovery": True,
                    "stale_after_seconds": max_age_seconds,
                }
                connection.execute(
                    """
                    UPDATE operating_cycles
                    SET status = 'failed', summary_json = ?, completed_at = ?
                    WHERE id = ? AND status = 'running'
                    """,
                    (_json_object(summary), now, cycle["id"]),
                )
                self.store._write_audit(
                    connection,
                    event_type="cycle.stale_recovered",
                    actor=actor_worker,
                    entity_type="operating_cycle",
                    entity_id=cycle["id"],
                    action="recover_stale_cycles",
                    details={"cycle_key": cycle["cycle_key"], **summary},
                )
                recovered += 1
        return recovered

    def finish_cycle(
        self,
        cycle_id: int,
        *,
        status: str,
        summary: Mapping[str, Any],
        actor_worker: str,
    ) -> dict[str, Any]:
        if status not in {"awaiting_workers", "completed", "failed", "paused"}:
            raise ValidationError("invalid final cycle status")
        with self.store._transaction() as connection:
            self._active_worker(connection, actor_worker)
            existing = connection.execute(
                "SELECT * FROM operating_cycles WHERE id = ?", (cycle_id,)
            ).fetchone()
            if existing is None:
                raise NotFoundError(f"operating cycle not found: {cycle_id}")
            previous_status = existing["status"]
            if previous_status != "running":
                if previous_status == status:
                    return dict(existing)
                if not (previous_status == "awaiting_workers" and status == "completed"):
                    raise ConflictError("operating cycle is already finalized")
            completed_at = _utc_now() if status != "awaiting_workers" else None
            connection.execute(
                """
                UPDATE operating_cycles
                SET status = ?, summary_json = ?, completed_at = ?
                WHERE id = ?
                """,
                (status, _json_object(summary), completed_at, cycle_id),
            )
            self.store._write_audit(
                connection,
                event_type="cycle.status_changed",
                actor=actor_worker,
                entity_type="operating_cycle",
                entity_id=cycle_id,
                action="finish_cycle",
                details={"from": previous_status, "to": status, "summary": dict(summary)},
            )
            row = connection.execute(
                "SELECT * FROM operating_cycles WHERE id = ?", (cycle_id,)
            ).fetchone()
        return dict(row)

    def reconcile_cycles(self, *, actor_worker: str = "company_president") -> int:
        """Complete waiting cycles after every work item in their scope is terminal."""

        terminal = ("succeeded", "failed", "dead_letter", "cancelled")
        completed = 0
        now = _utc_now()
        with self.store._transaction() as connection:
            self._active_worker(connection, actor_worker)
            cycles = connection.execute(
                "SELECT * FROM operating_cycles WHERE status = 'awaiting_workers' ORDER BY id"
            ).fetchall()
            for cycle in cycles:
                unfinished = int(
                    connection.execute(
                        """
                        SELECT COUNT(*) AS count
                        FROM work_items
                        WHERE cycle_id = ? AND status NOT IN (?, ?, ?, ?)
                        """,
                        (cycle["id"], *terminal),
                    ).fetchone()["count"]
                )
                if unfinished:
                    continue
                connection.execute(
                    """
                    UPDATE operating_cycles
                    SET status = 'completed', completed_at = ?
                    WHERE id = ? AND status = 'awaiting_workers'
                    """,
                    (now, cycle["id"]),
                )
                self.store._write_audit(
                    connection,
                    event_type="cycle.status_changed",
                    actor=actor_worker,
                    entity_type="operating_cycle",
                    entity_id=cycle["id"],
                    action="reconcile_cycles",
                    details={"from": "awaiting_workers", "to": "completed"},
                )
                completed += 1
        return completed

    def create_work(
        self,
        *,
        work_key: str,
        commanded_by_worker: str,
        assigned_role_key: str,
        task_type: str,
        title: str,
        description: str,
        acceptance_criteria: str,
        decision_class: DecisionClass | str = DecisionClass.WORK_EXECUTION,
        priority: int = 50,
        risk_level: str = "low",
        external_effect: bool = False,
        estimated_cost_cents: int = 0,
        idempotency_key: str | None = None,
        assigned_worker_key: str | None = None,
        reviewer_role_key: str | None = None,
        cycle_id: int | None = None,
        objective_id: int | None = None,
        opportunity_id: int | None = None,
        product_id: int | None = None,
        parent_work_id: int | None = None,
        dependencies: Sequence[int] = (),
        input_data: Mapping[str, Any] | None = None,
        max_attempts: int = 3,
        next_run_at: str | None = None,
        deadline_at: str | None = None,
    ) -> dict[str, Any]:
        try:
            decision = DecisionClass(decision_class)
        except ValueError as exc:
            raise ValidationError(f"unknown decision class: {decision_class}") from exc
        if decision is DecisionClass.PROHIBITED:
            recorded = self._record_prohibited_work_denial(
                commanded_by_worker=commanded_by_worker,
                work_key=work_key,
                assigned_role_key=assigned_role_key,
                title=title,
            )
            suffix = "" if recorded else "; denial recording also failed"
            raise ConflictError(
                "prohibited work cannot be issued or approved" + suffix
            )
        if risk_level not in {"low", "medium", "high", "critical"}:
            raise ValidationError("risk_level must be low, medium, high, or critical")
        if risk_level in {"high", "critical"} and decision is not DecisionClass.OWNER_RESERVED:
            raise ConflictError(
                "high- or critical-risk work must use the owner_reserved decision class"
            )
        priority = _bounded_integer("priority", priority, minimum=0, maximum=100)
        max_attempts = _bounded_integer("max_attempts", max_attempts, minimum=1, maximum=20)
        if type(estimated_cost_cents) is not int or estimated_cost_cents < 0:
            raise ValidationError("estimated_cost_cents must be a non-negative integer")
        if type(objective_id) is not int or objective_id <= 0:
            raise ValidationError("every work order requires a positive objective_id")
        if estimated_cost_cents > 0 and decision is not DecisionClass.OWNER_RESERVED:
            raise ConflictError("work with cash cost must use owner_reserved decision class")
        if external_effect and decision not in {
            DecisionClass.CONTROLLED_EXTERNAL,
            DecisionClass.OWNER_RESERVED,
        }:
            raise ConflictError("external work must be controlled_external or owner_reserved")

        work_key = _require_text("work_key", work_key)
        idempotency_key = _require_text("idempotency_key", idempotency_key or work_key)
        task_type = _require_text("task_type", task_type)
        title = _require_text("title", title)
        description = _require_text("description", description)
        acceptance_criteria = _require_text("acceptance_criteria", acceptance_criteria)
        input_json = _json_object(input_data)
        normalized_next_run = _normalize_timestamp(next_run_at)
        normalized_deadline = _normalize_timestamp(deadline_at)
        with self.store._transaction() as connection:
            commander = self._active_worker(connection, commanded_by_worker)
            target_role = self._role(connection, assigned_role_key)
            if decision in {
                DecisionClass.EXECUTIVE_PORTFOLIO,
                DecisionClass.CONTROLLED_EXTERNAL,
            } and commander["role_key"] not in {"owner_ceo", "company_president"}:
                raise ConflictError(
                    f"{decision.value} work requires Company President or owner authority"
                )
            if not self._db_can_command(connection, commander["role_key"], assigned_role_key):
                raise ConflictError(
                    f"{commanded_by_worker} cannot command role {assigned_role_key}"
                )
            objective = connection.execute(
                "SELECT * FROM objectives WHERE id = ?", (objective_id,)
            ).fetchone()
            if objective is None:
                raise NotFoundError(f"objective not found: {objective_id}")
            if objective["status"] not in {"active", "at_risk"}:
                raise ConflictError("work can only be issued against an active objective")
            if (
                objective["owner_role_key"] != commander["role_key"]
                and not self._db_can_command(
                    connection, commander["role_key"], objective["owner_role_key"]
                )
            ):
                raise ConflictError("commander has no authority over the linked objective")
            if assigned_worker_key is not None:
                assigned = self._active_worker(connection, assigned_worker_key)
                if assigned["role_key"] != assigned_role_key:
                    raise ConflictError("assigned worker does not occupy the assigned role")
            if reviewer_role_key is None:
                reviewer_role_key = target_role["reports_to_role_key"]
            if reviewer_role_key is None:
                raise ConflictError("work requires an independent reviewer role")
            reviewer_role = self._role(connection, reviewer_role_key)
            reviewer_is_manager = (
                reviewer_role_key != assigned_role_key
                and self._db_can_command(connection, reviewer_role_key, assigned_role_key)
            )
            if not reviewer_is_manager and not reviewer_role["independent_control"]:
                raise ConflictError(
                    "reviewer must be a manager in the reporting chain or an independent control"
                )
            if assigned_worker_key is not None:
                reviewer = connection.execute(
                    """
                    SELECT worker_key FROM workers
                    WHERE role_key = ? AND status IN ('active','probationary','coaching')
                    ORDER BY worker_key LIMIT 1
                    """,
                    (reviewer_role_key,),
                ).fetchone()
                if reviewer and reviewer["worker_key"] == assigned_worker_key:
                    raise ConflictError("producer and reviewer must be different workers")
            for dependency in dependencies:
                if type(dependency) is not int:
                    raise ValidationError("dependency identifiers must be integers")
                if connection.execute(
                    "SELECT id FROM work_items WHERE id = ?", (dependency,)
                ).fetchone() is None:
                    raise NotFoundError(f"dependency work item not found: {dependency}")
            if parent_work_id is not None and connection.execute(
                "SELECT id FROM work_items WHERE id = ?", (parent_work_id,)
            ).fetchone() is None:
                raise NotFoundError(f"parent work item not found: {parent_work_id}")

            existing = connection.execute(
                "SELECT * FROM work_items WHERE idempotency_key = ? OR work_key = ?",
                (idempotency_key, work_key),
            ).fetchone()
            if existing is not None:
                requested_scope: dict[str, Any] = {
                    "work_key": work_key,
                    "idempotency_key": idempotency_key,
                    "parent_work_id": parent_work_id,
                    "objective_id": objective_id,
                    "opportunity_id": opportunity_id,
                    "product_id": product_id,
                    "commanded_by_worker": commanded_by_worker,
                    "assigned_role_key": assigned_role_key,
                    "reviewer_role_key": reviewer_role_key,
                    "task_type": task_type,
                    "title": title,
                    "description": description,
                    "acceptance_criteria": acceptance_criteria,
                    "decision_class": decision.value,
                    "priority": priority,
                    "risk_level": risk_level,
                    "external_effect": int(external_effect),
                    "estimated_cost_cents": estimated_cost_cents,
                    "input_json": input_json,
                    "max_attempts": max_attempts,
                    "deadline_at": normalized_deadline,
                }
                if assigned_worker_key is not None:
                    requested_scope["assigned_worker_key"] = assigned_worker_key
                mismatches = sorted(
                    field
                    for field, requested in requested_scope.items()
                    if existing[field] != requested
                )
                existing_dependencies = [
                    int(item["depends_on_work_id"])
                    for item in connection.execute(
                        """
                        SELECT depends_on_work_id FROM work_dependencies
                        WHERE work_id = ? ORDER BY depends_on_work_id
                        """,
                        (existing["id"],),
                    ).fetchall()
                ]
                if existing_dependencies != sorted(dependencies):
                    mismatches.append("dependencies")
                if mismatches:
                    raise ConflictError(
                        "idempotency key or work key already exists with different scope: "
                        + ", ".join(mismatches)
                    )
                return dict(existing)

            status = "waiting_policy" if external_effect or decision is DecisionClass.OWNER_RESERVED else (
                "waiting_dependency" if dependencies else "ready"
            )
            now = _utc_now()
            try:
                cursor = connection.execute(
                    """
                    INSERT INTO work_items(
                        work_key, parent_work_id, cycle_id, objective_id,
                        opportunity_id, product_id, department_slug,
                        commanded_by_worker, assigned_role_key, assigned_worker_key,
                        reviewer_role_key, task_type, title, description,
                        acceptance_criteria, decision_class, priority, risk_level,
                        external_effect, estimated_cost_cents, status, input_json,
                        idempotency_key, max_attempts, next_run_at, deadline_at,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        work_key,
                        parent_work_id,
                        cycle_id,
                        objective_id,
                        opportunity_id,
                        product_id,
                        target_role["department_slug"],
                        commanded_by_worker,
                        assigned_role_key,
                        assigned_worker_key,
                        reviewer_role_key,
                        task_type,
                        title,
                        description,
                        acceptance_criteria,
                        decision.value,
                        priority,
                        risk_level,
                        int(external_effect),
                        estimated_cost_cents,
                        status,
                        input_json,
                        idempotency_key,
                        max_attempts,
                        normalized_next_run,
                        normalized_deadline,
                        now,
                        now,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ConflictError(f"work item could not be created: {exc}") from exc
            work_id = int(cursor.lastrowid)
            for dependency in dependencies:
                connection.execute(
                    """
                    INSERT INTO work_dependencies(work_id, depends_on_work_id, created_at)
                    VALUES (?, ?, ?)
                    """,
                    (work_id, dependency, now),
                )
            self._record_work_event(
                connection,
                work_id=work_id,
                event_type="work.issued",
                actor_worker_key=commanded_by_worker,
                from_status=None,
                to_status=status,
                details={"assigned_role_key": assigned_role_key, "dependencies": list(dependencies)},
            )
            self.store._write_audit(
                connection,
                event_type="work.created",
                actor=commanded_by_worker,
                entity_type="work_item",
                entity_id=work_id,
                action="create_work",
                details={
                    "work_key": work_key,
                    "assigned_role_key": assigned_role_key,
                    "decision_class": decision.value,
                    "status": status,
                },
            )
            row = connection.execute(
                "SELECT * FROM work_items WHERE id = ?", (work_id,)
            ).fetchone()
        return dict(row)

    def authorize_internal_work(
        self,
        work_identifier: str | int,
        *,
        approval_id: int,
        actor_worker: str,
    ) -> dict[str, Any]:
        """Bind an exact CEO approval to held internal work and release it safely."""

        self.store.expire_approvals(actor="company_os")
        with self.store._transaction() as connection:
            actor = self._active_worker(connection, actor_worker)
            if actor["role_key"] not in {"owner_ceo", "company_president"}:
                raise ConflictError(
                    "only the owner CEO or Company President may bind an owner approval"
                )
            work = self._work(connection, work_identifier)
            if work["status"] != "waiting_policy":
                raise ConflictError("only policy-held work can be authorized")
            if work["external_effect"]:
                raise ConflictError(
                    "external work remains held until a connector-specific execution permit exists"
                )
            approval = connection.execute(
                "SELECT * FROM approvals WHERE id = ?", (approval_id,)
            ).fetchone()
            if approval is None:
                raise NotFoundError(f"approval not found: {approval_id}")
            expected_action = f"authorize_work:{work['work_key']}"
            if approval["action"].casefold() != expected_action.casefold():
                raise ConflictError(
                    f"approval must be bound to exact action {expected_action}"
                )
            if approval["status"] != "approved" or approval["expires_at"] <= _utc_now():
                raise ConflictError("approval is not active and approved")
            if approval["approval_class"] != "ceo_approval_required":
                raise ConflictError("owner-reserved work requires CEO-class approval")
            if approval["decided_by"] != "kaleb_ceo":
                raise ConflictError("approval decision is not bound to the owner identity")
            try:
                packet, packet_digest = normalize_owner_decision_packet(
                    json.loads(approval["decision_packet_json"])
                )
            except (TypeError, ValueError, json.JSONDecodeError, ValidationError) as exc:
                raise ConflictError(
                    "owner-reserved work requires a complete valid decision packet"
                ) from exc
            if not secrets.compare_digest(
                str(approval["packet_digest"]), packet_digest
            ):
                raise ConflictError("owner decision packet digest does not match")
            if packet["exact_action"].casefold() != expected_action.casefold():
                raise ConflictError("owner decision packet is bound to a different action")
            if int(approval["estimated_cost_cents"]) < int(work["estimated_cost_cents"]):
                raise ConflictError("approval cost ceiling is below the work estimate")
            dependency_count = int(
                connection.execute(
                    "SELECT COUNT(*) AS count FROM work_dependencies WHERE work_id = ?",
                    (work["id"],),
                ).fetchone()["count"]
            )
            target = "waiting_dependency" if dependency_count else "ready"
            require_task_transition(work["status"], target)
            now = _utc_now()
            connection.execute(
                """
                UPDATE work_items
                SET status = ?, approval_id = ?, updated_at = ?
                WHERE id = ? AND status = 'waiting_policy'
                """,
                (target, approval_id, now, work["id"]),
            )
            self._record_work_event(
                connection,
                work_id=work["id"],
                event_type="work.owner_authorized",
                actor_worker_key=actor_worker,
                from_status="waiting_policy",
                to_status=target,
                details={"approval_id": approval_id, "action": expected_action},
            )
            self.store._write_audit(
                connection,
                event_type="work.owner_authorized",
                actor=actor_worker,
                entity_type="work_item",
                entity_id=work["id"],
                action="authorize_internal_work",
                details={"approval_id": approval_id, "to": target},
            )
            row = connection.execute(
                "SELECT * FROM work_items WHERE id = ?", (work["id"],)
            ).fetchone()
        return dict(row)

    def get_work(self, work_identifier: str | int) -> dict[str, Any]:
        self.store.initialize()
        with self.store._connection() as connection:
            row = self._work(connection, work_identifier)
            result = dict(row)
            dependencies = connection.execute(
                """
                SELECT depends_on_work_id, failure_policy
                FROM work_dependencies WHERE work_id = ? ORDER BY depends_on_work_id
                """,
                (row["id"],),
            ).fetchall()
            result["dependencies"] = [dict(item) for item in dependencies]
            result["input"] = json.loads(result.pop("input_json"))
            result_json = result.pop("result_json")
            result["result"] = json.loads(result_json)
            result["submission_digest"] = (
                hashlib.sha256(result_json.encode("utf-8")).hexdigest()
                if result["submitted_at"] is not None
                else None
            )
            return result

    def list_work(
        self,
        *,
        status: str | None = None,
        department: str | None = None,
        cycle_id: int | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        limit = _bounded_integer("limit", limit, minimum=1, maximum=1000)
        clauses: list[str] = []
        params: list[Any] = []
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        if department is not None:
            clauses.append("department_slug = ?")
            params.append(department)
        if cycle_id is not None:
            clauses.append("cycle_id = ?")
            params.append(cycle_id)
        query = "SELECT * FROM work_items"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY priority DESC, created_at, id LIMIT ?"
        params.append(limit)
        self.store.initialize()
        with self.store._connection() as connection:
            return [dict(row) for row in connection.execute(query, tuple(params)).fetchall()]

    def release_ready_work(self, *, actor_worker: str = "company_president") -> int:
        """Release dependency-waiting and retry-wait work when safely eligible."""

        now = _utc_now()
        changed = 0
        with self.store._transaction() as connection:
            self._active_worker(connection, actor_worker)
            expired_approvals = connection.execute(
                """
                SELECT work_items.* FROM work_items
                JOIN approvals ON approvals.id = work_items.approval_id
                WHERE work_items.status IN (
                    'proposed','waiting_dependency','retry_wait','ready','blocked'
                )
                  AND (approvals.status <> 'approved' OR approvals.expires_at <= ?)
                ORDER BY work_items.id
                """,
                (now,),
            ).fetchall()
            for work in expired_approvals:
                require_task_transition(work["status"], "waiting_policy")
                connection.execute(
                    """
                    UPDATE work_items
                    SET status = 'waiting_policy', next_run_at = NULL, updated_at = ?
                    WHERE id = ?
                    """,
                    (now, work["id"]),
                )
                self._record_work_event(
                    connection,
                    work_id=work["id"],
                    event_type="work.approval_expired",
                    actor_worker_key=actor_worker,
                    from_status=work["status"],
                    to_status="waiting_policy",
                    details={"approval_id": work["approval_id"]},
                )
                changed += 1
            candidates = connection.execute(
                """
                SELECT work_items.*, objectives.status AS objective_status
                FROM work_items
                JOIN objectives ON objectives.id = work_items.objective_id
                WHERE work_items.status IN ('waiting_dependency','retry_wait','proposed')
                  AND (next_run_at IS NULL OR next_run_at <= ?)
                ORDER BY priority DESC, created_at
                """,
                (now,),
            ).fetchall()
            for work in candidates:
                if work["objective_status"] not in {"active", "at_risk"}:
                    target = "cancelled"
                    require_task_transition(work["status"], target)
                    connection.execute(
                        "UPDATE work_items SET status = ?, updated_at = ? WHERE id = ?",
                        (target, now, work["id"]),
                    )
                    self._record_work_event(
                        connection,
                        work_id=work["id"],
                        event_type="work.cancelled_by_objective",
                        actor_worker_key=actor_worker,
                        from_status=work["status"],
                        to_status=target,
                    )
                    changed += 1
                    continue
                dependencies = connection.execute(
                    """
                    SELECT dep.failure_policy, upstream.status
                    FROM work_dependencies AS dep
                    JOIN work_items AS upstream ON upstream.id = dep.depends_on_work_id
                    WHERE dep.work_id = ?
                    """,
                    (work["id"],),
                ).fetchall()
                hard_failure = any(
                    item["status"] in {"failed", "dead_letter", "cancelled"}
                    and item["failure_policy"] != "continue"
                    for item in dependencies
                )
                if hard_failure:
                    target = "blocked"
                elif all(
                    item["status"] == "succeeded"
                    or (
                        item["status"] in {"failed", "dead_letter", "cancelled"}
                        and item["failure_policy"] == "continue"
                    )
                    for item in dependencies
                ):
                    target = "ready"
                else:
                    continue
                require_task_transition(work["status"], target)
                connection.execute(
                    "UPDATE work_items SET status = ?, updated_at = ? WHERE id = ?",
                    (target, now, work["id"]),
                )
                self._record_work_event(
                    connection,
                    work_id=work["id"],
                    event_type="work.dependencies_evaluated",
                    actor_worker_key=actor_worker,
                    from_status=work["status"],
                    to_status=target,
                )
                changed += 1
            if changed:
                self.store._write_audit(
                    connection,
                    event_type="work.queue_reconciled",
                    actor=actor_worker,
                    entity_type="work_queue",
                    entity_id="ready",
                    action="release_ready_work",
                    details={"changed": changed},
                )
        return changed

    def recover_expired_leases(self, *, actor_worker: str = "sre_operator") -> int:
        now = _utc_now()
        recovered = 0
        with self.store._transaction() as connection:
            self._active_worker(connection, actor_worker)
            expired = connection.execute(
                """
                SELECT * FROM work_items
                WHERE status IN ('leased','running')
                  AND lease_expires_at IS NOT NULL AND lease_expires_at <= ?
                ORDER BY id
                """,
                (now,),
            ).fetchall()
            for work in expired:
                target = "dead_letter" if work["attempt_count"] >= work["max_attempts"] else "retry_wait"
                require_task_transition(work["status"], target)
                next_run = None
                if target == "retry_wait":
                    next_run = (
                        datetime.now(timezone.utc)
                        + timedelta(
                            seconds=retry_backoff_seconds(
                                int(work["attempt_count"]),
                                jitter_key=work["work_key"],
                            )
                        )
                    ).isoformat(timespec="seconds").replace("+00:00", "Z")
                connection.execute(
                    """
                    UPDATE work_items
                    SET status = ?, next_run_at = ?, lease_owner = NULL,
                        lease_token = NULL, lease_expires_at = NULL,
                        error_text = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (target, next_run, "worker lease expired", now, work["id"]),
                )
                self._record_work_event(
                    connection,
                    work_id=work["id"],
                    event_type="work.lease_expired",
                    actor_worker_key=actor_worker,
                    from_status=work["status"],
                    to_status=target,
                    details={"expired_epoch": work["lease_epoch"]},
                )
                recovered += 1
            if recovered:
                self.store._write_audit(
                    connection,
                    event_type="work.leases_recovered",
                    actor=actor_worker,
                    entity_type="work_queue",
                    entity_id="leases",
                    action="recover_expired_leases",
                    details={"count": recovered},
                )
        return recovered

    def claim_work(
        self,
        *,
        worker_key: str,
        lease_seconds: int = 900,
    ) -> dict[str, Any] | None:
        lease_seconds = _bounded_integer(
            "lease_seconds", lease_seconds, minimum=30, maximum=86400
        )
        now_dt = datetime.now(timezone.utc)
        now = now_dt.isoformat(timespec="seconds").replace("+00:00", "Z")
        expires = (now_dt + timedelta(seconds=lease_seconds)).isoformat(
            timespec="seconds"
        ).replace("+00:00", "Z")
        with self.store._transaction() as connection:
            worker = self._active_worker(connection, worker_key)
            active_count = int(
                connection.execute(
                    """
                    SELECT COUNT(*) AS count FROM work_items
                    WHERE assigned_worker_key = ? AND status IN ('leased','running')
                    """,
                    (worker_key,),
                ).fetchone()["count"]
            )
            max_active = min(int(worker["max_active_work"]), int(worker["capacity_units"]))
            if active_count >= max_active:
                return None
            candidate = connection.execute(
                """
                SELECT work.* FROM work_items AS work
                JOIN objectives ON objectives.id = work.objective_id
                JOIN departments AS department ON department.slug = work.department_slug
                WHERE work.status = 'ready'
                  AND objectives.status IN ('active','at_risk')
                  AND (work.next_run_at IS NULL OR work.next_run_at <= ?)
                  AND (work.assigned_worker_key IS NULL OR work.assigned_worker_key = ?)
                  AND work.assigned_role_key = ?
                  AND (
                      work.approval_id IS NULL OR EXISTS (
                          SELECT 1 FROM approvals AS bound_approval
                          WHERE bound_approval.id = work.approval_id
                            AND bound_approval.status = 'approved'
                            AND bound_approval.expires_at > ?
                      )
                  )
                  AND (
                      SELECT COUNT(*) FROM work_items AS active
                      WHERE active.department_slug = work.department_slug
                        AND active.status IN ('leased','running','review')
                  ) < department.wip_limit
                  AND NOT EXISTS (
                      SELECT 1 FROM work_dependencies AS dep
                      JOIN work_items AS upstream ON upstream.id = dep.depends_on_work_id
                      WHERE dep.work_id = work.id
                        AND upstream.status <> 'succeeded'
                        AND dep.failure_policy <> 'continue'
                  )
                ORDER BY work.priority DESC,
                         CASE WHEN work.deadline_at IS NULL THEN 1 ELSE 0 END,
                         work.deadline_at,
                         work.created_at,
                         work.id
                LIMIT 1
                """,
                (now, worker_key, worker["role_key"], now),
            ).fetchone()
            if candidate is None:
                return None
            self._require_active_bound_approval(connection, candidate)
            require_task_transition(candidate["status"], "leased")
            # A raw URL-safe token may begin with "-", which command-line parsers
            # can misread as an option when the token is passed as a value.
            token = f"lease_{secrets.token_urlsafe(24)}"
            epoch = int(candidate["lease_epoch"]) + 1
            updated = connection.execute(
                """
                UPDATE work_items
                SET status = 'leased', assigned_worker_key = ?, lease_owner = ?,
                    lease_token = ?, lease_epoch = ?, lease_expires_at = ?,
                    attempt_count = attempt_count + 1, updated_at = ?
                WHERE id = ? AND status = 'ready'
                """,
                (worker_key, worker_key, token, epoch, expires, now, candidate["id"]),
            )
            if updated.rowcount != 1:
                return None
            self._record_work_event(
                connection,
                work_id=candidate["id"],
                event_type="work.leased",
                actor_worker_key=worker_key,
                from_status="ready",
                to_status="leased",
                details={"lease_epoch": epoch, "lease_expires_at": expires},
            )
            self.store._write_audit(
                connection,
                event_type="work.leased",
                actor=worker_key,
                entity_type="work_item",
                entity_id=candidate["id"],
                action="claim_work",
                details={"lease_epoch": epoch, "lease_expires_at": expires},
            )
            row = connection.execute(
                "SELECT * FROM work_items WHERE id = ?", (candidate["id"],)
            ).fetchone()
        return dict(row)

    def _lease_transition(
        self,
        work_identifier: str | int,
        *,
        worker_key: str,
        lease_token: str,
        lease_epoch: int,
        from_status: str,
        to_status: str,
        event_type: str,
        result: Mapping[str, Any] | None = None,
        error_text: str | None = None,
    ) -> dict[str, Any]:
        now = _utc_now()
        with self.store._transaction() as connection:
            self._active_worker(connection, worker_key)
            work = self._work(connection, work_identifier)
            self._require_active_bound_approval(connection, work)
            if work["status"] != from_status:
                raise ConflictError(f"work must be {from_status} before it can become {to_status}")
            if (
                work["lease_owner"] != worker_key
                or work["lease_token"] != lease_token
                or work["lease_epoch"] != lease_epoch
            ):
                raise ConflictError("stale or mismatched work lease")
            if work["lease_expires_at"] is None or work["lease_expires_at"] <= now:
                raise ConflictError("work lease has expired")
            require_task_transition(work["status"], to_status)
            submitted_at = now if to_status == "review" else work["submitted_at"]
            connection.execute(
                """
                UPDATE work_items
                SET status = ?, result_json = ?, error_text = ?, submitted_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    to_status,
                    _json_object(result) if result is not None else work["result_json"],
                    error_text if error_text is not None else work["error_text"],
                    submitted_at,
                    now,
                    work["id"],
                ),
            )
            self._record_work_event(
                connection,
                work_id=work["id"],
                event_type=event_type,
                actor_worker_key=worker_key,
                from_status=from_status,
                to_status=to_status,
                details={"lease_epoch": lease_epoch},
            )
            self.store._write_audit(
                connection,
                event_type=event_type,
                actor=worker_key,
                entity_type="work_item",
                entity_id=work["id"],
                action=event_type,
                details={"from": from_status, "to": to_status, "lease_epoch": lease_epoch},
            )
            row = connection.execute(
                "SELECT * FROM work_items WHERE id = ?", (work["id"],)
            ).fetchone()
        return dict(row)

    def start_work(
        self,
        work_identifier: str | int,
        *,
        worker_key: str,
        lease_token: str,
        lease_epoch: int,
    ) -> dict[str, Any]:
        return self._lease_transition(
            work_identifier,
            worker_key=worker_key,
            lease_token=lease_token,
            lease_epoch=lease_epoch,
            from_status="leased",
            to_status="running",
            event_type="work.started",
        )

    def submit_work(
        self,
        work_identifier: str | int,
        *,
        worker_key: str,
        lease_token: str,
        lease_epoch: int,
        result: Mapping[str, Any],
    ) -> dict[str, Any]:
        if not result:
            raise ValidationError("submitted work requires a non-empty result")
        return self._lease_transition(
            work_identifier,
            worker_key=worker_key,
            lease_token=lease_token,
            lease_epoch=lease_epoch,
            from_status="running",
            to_status="review",
            event_type="work.submitted",
            result=result,
        )

    def review_work(
        self,
        work_identifier: str | int,
        *,
        reviewer_worker_key: str,
        decision: str,
        notes: str,
        quality_score: float | None = None,
    ) -> dict[str, Any]:
        if decision not in {"accept", "reject"}:
            raise ValidationError("review decision must be accept or reject")
        if quality_score is not None and (
            isinstance(quality_score, bool) or not 0.0 <= float(quality_score) <= 1.0
        ):
            raise ValidationError("quality_score must be between 0 and 1")
        now_dt = datetime.now(timezone.utc)
        now = now_dt.isoformat(timespec="seconds").replace("+00:00", "Z")
        with self.store._transaction() as connection:
            reviewer = self._active_worker(connection, reviewer_worker_key)
            work = self._work(connection, work_identifier)
            self._require_active_bound_approval(connection, work)
            if work["status"] != "review":
                raise ConflictError("only submitted work can be reviewed")
            if reviewer_worker_key == work["assigned_worker_key"]:
                raise ConflictError("a producer cannot review their own work")
            if reviewer["role_key"] != work["reviewer_role_key"]:
                raise ConflictError("worker does not occupy the required reviewer role")
            if decision == "accept":
                if quality_score is None:
                    raise ConflictError("accepted work requires an explicit quality score")
                producer = connection.execute(
                    "SELECT quality_floor FROM workers WHERE worker_key = ?",
                    (work["assigned_worker_key"],),
                ).fetchone()
                if producer is None:
                    raise ConflictError("accepted work has no accountable producer")
                if float(quality_score) < float(producer["quality_floor"]):
                    raise ConflictError(
                        "quality score is below the producer assignment's acceptance floor"
                    )
                submission_digest = hashlib.sha256(
                    work["result_json"].encode("utf-8")
                ).hexdigest()
                unresolved_controls = connection.execute(
                    """
                    SELECT latest.control_domain,
                           CASE
                               WHEN latest.expires_at IS NOT NULL
                                AND latest.expires_at <= ? THEN 'expired'
                               WHEN latest.artifact_digest <> ? THEN 'artifact_mismatch'
                               ELSE latest.status
                           END AS status
                    FROM control_reviews AS latest
                    JOIN (
                        SELECT control_domain, MAX(id) AS latest_id
                        FROM control_reviews
                        WHERE work_id = ?
                        GROUP BY control_domain
                    ) AS current ON current.latest_id = latest.id
                    WHERE latest.status <> 'passed'
                       OR (latest.expires_at IS NOT NULL AND latest.expires_at <= ?)
                       OR latest.artifact_digest <> ?
                    ORDER BY latest.control_domain
                    """,
                    (now, submission_digest, work["id"], now, submission_digest),
                ).fetchall()
                if unresolved_controls:
                    summary = ", ".join(
                        f"{item['control_domain']}={item['status']}"
                        for item in unresolved_controls
                    )
                    raise ConflictError(
                        f"work has unresolved independent control findings: {summary}"
                    )
                target = "succeeded"
                next_run = None
                accepted_at = now
            else:
                target = (
                    "dead_letter"
                    if work["attempt_count"] >= work["max_attempts"]
                    else "retry_wait"
                )
                next_run = None
                if target == "retry_wait":
                    next_run = (
                        now_dt
                        + timedelta(
                            seconds=retry_backoff_seconds(
                                max(1, int(work["attempt_count"])),
                                base_seconds=60,
                                jitter_key=work["work_key"],
                            )
                        )
                    ).isoformat(
                        timespec="seconds"
                    ).replace("+00:00", "Z")
                accepted_at = None
            require_task_transition(work["status"], target)
            connection.execute(
                """
                UPDATE work_items
                SET status = ?, next_run_at = ?, accepted_at = ?,
                    lease_owner = NULL, lease_token = NULL, lease_expires_at = NULL,
                    error_text = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    target,
                    next_run,
                    accepted_at,
                    "" if decision == "accept" else _require_text("notes", notes),
                    now,
                    work["id"],
                ),
            )
            self._record_work_event(
                connection,
                work_id=work["id"],
                event_type=f"work.review_{decision}",
                actor_worker_key=reviewer_worker_key,
                from_status="review",
                to_status=target,
                details={"notes": notes, "quality_score": quality_score},
            )
            self.store._write_audit(
                connection,
                event_type=f"work.review_{decision}",
                actor=reviewer_worker_key,
                entity_type="work_item",
                entity_id=work["id"],
                action="review_work",
                details={"decision": decision, "quality_score": quality_score},
            )
            row = connection.execute(
                "SELECT * FROM work_items WHERE id = ?", (work["id"],)
            ).fetchone()
        return dict(row)

    def create_escalation(
        self,
        *,
        raised_by_worker: str,
        routed_to_role_key: str,
        decision_class: DecisionClass | str,
        reason_code: str,
        title: str,
        context: str,
        recommendation: str,
        safe_default: str,
        work_id: int | None = None,
        options: Sequence[Mapping[str, Any]] = (),
        owner_packet: Mapping[str, Any] | None = None,
        due_at: str | None = None,
    ) -> dict[str, Any]:
        try:
            decision = DecisionClass(decision_class)
        except ValueError as exc:
            raise ValidationError(f"unknown decision class: {decision_class}") from exc
        if decision is DecisionClass.WORK_EXECUTION:
            raise ValidationError("routine work must escalate through management, not this queue")
        normalized_packet: dict[str, str] = {}
        if decision is DecisionClass.OWNER_RESERVED and routed_to_role_key == "owner_ceo":
            if not isinstance(owner_packet, Mapping):
                raise ValidationError("owner-reserved escalation requires a complete owner packet")
            normalized_packet, _packet_digest = normalize_owner_decision_packet(
                owner_packet
            )
        elif owner_packet:
            normalized_packet = {
                str(key): str(value) for key, value in owner_packet.items()
            }
        with self.store._transaction() as connection:
            raiser = self._active_worker(connection, raised_by_worker)
            target = self._role(connection, routed_to_role_key)
            if work_id is not None:
                self._work(connection, work_id)
            manager = connection.execute(
                """
                SELECT manager.role_key
                FROM workers AS worker
                LEFT JOIN workers AS manager ON manager.worker_key = worker.manager_worker_key
                WHERE worker.worker_key = ?
                """,
                (raised_by_worker,),
            ).fetchone()
            next_role = manager["role_key"] if manager is not None else None
            control_direct = (
                bool(raiser["independent_control"])
                and routed_to_role_key == "owner_ceo"
                and decision in {DecisionClass.OWNER_RESERVED, DecisionClass.PROHIBITED}
            )
            if routed_to_role_key != next_role and not control_direct:
                raise ConflictError("escalation must route to the next manager in the command chain")
            owner_attention = (
                routed_to_role_key == "owner_ceo"
                and decision in {DecisionClass.OWNER_RESERVED, DecisionClass.PROHIBITED}
            )
            cursor = connection.execute(
                """
                INSERT INTO escalations(
                    work_id, department_slug, raised_by_worker, routed_to_role_key,
                    decision_class, reason_code, title, context, options_json,
                    recommendation, safe_default, owner_attention, status,
                    due_at, created_at, decision_packet_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'routed', ?, ?, ?)
                """,
                (
                    work_id,
                    raiser["department_slug"],
                    raised_by_worker,
                    routed_to_role_key,
                    decision.value,
                    _require_text("reason_code", reason_code),
                    _require_text("title", title),
                    _require_text("context", context),
                    _json_array(options),
                    _require_text("recommendation", recommendation),
                    _require_text("safe_default", safe_default),
                    int(owner_attention),
                    _normalize_timestamp(due_at),
                    _utc_now(),
                    _json_object(normalized_packet),
                ),
            )
            escalation_id = int(cursor.lastrowid)
            self.store._write_audit(
                connection,
                event_type="escalation.created",
                actor=raised_by_worker,
                entity_type="escalation",
                entity_id=escalation_id,
                action="create_escalation",
                details={
                    "routed_to_role_key": routed_to_role_key,
                    "decision_class": decision.value,
                    "owner_attention": owner_attention,
                },
            )
            row = connection.execute(
                "SELECT * FROM escalations WHERE id = ?", (escalation_id,)
            ).fetchone()
        return dict(row)

    def list_escalations(
        self, *, owner_attention: bool | None = None, status: str | None = None
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if owner_attention is not None:
            clauses.append("owner_attention = ?")
            params.append(int(owner_attention))
        if status is not None:
            clauses.append("status = ?")
            params.append(status)
        query = "SELECT * FROM escalations"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY owner_attention DESC, created_at, id"
        self.store.initialize()
        with self.store._connection() as connection:
            return [dict(row) for row in connection.execute(query, tuple(params)).fetchall()]

    def resolve_escalation(
        self,
        escalation_id: int,
        *,
        actor_worker: str,
        decision: str,
        resolution: str,
    ) -> dict[str, Any]:
        if decision not in {"resolved", "dismissed"}:
            raise ValidationError("escalation decision must be resolved or dismissed")
        resolution = _require_text("resolution", resolution)
        with self.store._transaction() as connection:
            actor = self._active_worker(connection, actor_worker)
            escalation = connection.execute(
                "SELECT * FROM escalations WHERE id = ?", (escalation_id,)
            ).fetchone()
            if escalation is None:
                raise NotFoundError(f"escalation not found: {escalation_id}")
            if escalation["status"] not in {"open", "routed"}:
                raise ConflictError("escalation is already closed")
            if actor["role_key"] != escalation["routed_to_role_key"]:
                raise ConflictError("only the routed decision role may close this escalation")
            now = _utc_now()
            connection.execute(
                """
                UPDATE escalations
                SET status = ?, resolution = ?, resolved_at = ?
                WHERE id = ?
                """,
                (decision, resolution, now, escalation_id),
            )
            self.store._write_audit(
                connection,
                event_type=f"escalation.{decision}",
                actor=actor_worker,
                entity_type="escalation",
                entity_id=escalation_id,
                action="resolve_escalation",
                details={"resolution": resolution},
            )
            row = connection.execute(
                "SELECT * FROM escalations WHERE id = ?", (escalation_id,)
            ).fetchone()
        return dict(row)

    def record_control_review(
        self,
        *,
        reviewer_worker_key: str,
        control_domain: str,
        status: str,
        finding: str,
        severity: str = "low",
        conditions: str = "",
        work_id: int | None = None,
        opportunity_id: int | None = None,
        product_id: int | None = None,
        artifact_digest: str = "",
        expires_at: str | None = None,
    ) -> dict[str, Any]:
        if control_domain not in CONTROL_DOMAINS:
            raise ValidationError("unknown control domain")
        if status not in {"pending", "passed", "blocked", "changes_required", "expired"}:
            raise ValidationError("unknown control review status")
        if severity not in {"low", "medium", "high", "critical"}:
            raise ValidationError("unknown control severity")
        if work_id is None and opportunity_id is None and product_id is None:
            raise ValidationError("a control review must identify its reviewed scope")
        finding_text = finding.strip()
        normalized_artifact_digest = artifact_digest.strip().lower()
        normalized_expiry = _normalize_timestamp(expires_at)
        if status == "passed":
            if not finding_text:
                raise ValidationError("a passed control review requires a finding")
            if not (
                len(normalized_artifact_digest) == 64
                and all(character in "0123456789abcdef" for character in normalized_artifact_digest)
            ):
                raise ValidationError(
                    "a passed control review requires a SHA-256 artifact digest"
                )
            if normalized_expiry is None or normalized_expiry <= _utc_now():
                raise ValidationError(
                    "a passed control review requires a future expiry"
                )
        with self.store._transaction() as connection:
            reviewer = self._active_worker(connection, reviewer_worker_key)
            if not reviewer["independent_control"]:
                raise ConflictError("reviewer is not an independent control worker")
            capabilities = set(json.loads(reviewer["capabilities_json"]))
            if f"review:{control_domain}" not in capabilities:
                raise ConflictError(
                    f"reviewer lacks independent {control_domain} review authority"
                )
            if work_id is not None:
                work = self._work(connection, work_id)
                if work["assigned_worker_key"] == reviewer_worker_key:
                    raise ConflictError("a producer cannot control-review their own work")
                if status == "passed":
                    if work["status"] != "review":
                        raise ConflictError(
                            "a work control pass requires the submitted artifact"
                        )
                    expected_digest = hashlib.sha256(
                        work["result_json"].encode("utf-8")
                    ).hexdigest()
                    if not secrets.compare_digest(
                        normalized_artifact_digest, expected_digest
                    ):
                        raise ConflictError(
                            "control review artifact digest does not match the submission"
                        )
            cursor = connection.execute(
                """
                INSERT INTO control_reviews(
                    work_id, opportunity_id, product_id, control_domain,
                    reviewer_worker_key, status, severity, finding, conditions,
                    artifact_digest, expires_at, created_at, decided_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    work_id,
                    opportunity_id,
                    product_id,
                    control_domain,
                    reviewer_worker_key,
                    status,
                    severity,
                    finding_text,
                    conditions.strip(),
                    normalized_artifact_digest,
                    normalized_expiry,
                    _utc_now(),
                    _utc_now() if status != "pending" else None,
                ),
            )
            review_id = int(cursor.lastrowid)
            self.store._write_audit(
                connection,
                event_type="control.review_recorded",
                actor=reviewer_worker_key,
                entity_type="control_review",
                entity_id=review_id,
                action="record_control_review",
                details={"domain": control_domain, "status": status, "severity": severity},
            )
            row = connection.execute(
                "SELECT * FROM control_reviews WHERE id = ?", (review_id,)
            ).fetchone()
        return dict(row)

    def record_metric(
        self,
        *,
        metric_name: str,
        metric_type: str,
        value: float,
        unit: str,
        source_reference: str,
        evidence_type: str,
        observed_at: str | None = None,
        department_slug: str | None = None,
        worker_key: str | None = None,
        objective_id: int | None = None,
        work_id: int | None = None,
        opportunity_id: int | None = None,
        actor_worker: str = "data_analyst",
    ) -> dict[str, Any]:
        if metric_type not in {"actual", "estimate", "forecast"}:
            raise ValidationError("metric_type must be actual, estimate, or forecast")
        if isinstance(value, bool):
            raise ValidationError("metric value must be numeric")
        try:
            numeric_value = float(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError("metric value must be numeric") from exc
        if not math.isfinite(numeric_value):
            raise ValidationError("metric value must be finite")
        with self.store._transaction() as connection:
            self._active_worker(connection, actor_worker)
            cursor = connection.execute(
                """
                INSERT INTO metric_events(
                    metric_name, metric_type, value, unit, department_slug,
                    worker_key, objective_id, work_id, opportunity_id,
                    source_reference, evidence_type, observed_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _require_text("metric_name", metric_name),
                    metric_type,
                    numeric_value,
                    _require_text("unit", unit),
                    department_slug,
                    worker_key,
                    objective_id,
                    work_id,
                    opportunity_id,
                    _require_text("source_reference", source_reference),
                    _require_text("evidence_type", evidence_type),
                    _normalize_timestamp(observed_at, default_now=True),
                    _utc_now(),
                ),
            )
            metric_id = int(cursor.lastrowid)
            self.store._write_audit(
                connection,
                event_type="metric.recorded",
                actor=actor_worker,
                entity_type="metric_event",
                entity_id=metric_id,
                action="record_metric",
                details={"metric_name": metric_name, "metric_type": metric_type},
            )
            row = connection.execute(
                "SELECT * FROM metric_events WHERE id = ?", (metric_id,)
            ).fetchone()
        return dict(row)

    def open_incident(
        self,
        *,
        incident_key: str,
        severity: str,
        title: str,
        description: str,
        affected_scope: str,
        owner_role_key: str,
        opened_by_worker: str,
        containment: str = "",
    ) -> dict[str, Any]:
        if severity not in {"sev0", "sev1", "sev2", "sev3"}:
            raise ValidationError("severity must be sev0, sev1, sev2, or sev3")
        with self.store._transaction() as connection:
            self._active_worker(connection, opened_by_worker)
            self._role(connection, owner_role_key)
            ceo_required = severity in {"sev0", "sev1"}
            cursor = connection.execute(
                """
                INSERT INTO incidents(
                    incident_key, severity, title, description, affected_scope,
                    owner_role_key, status, containment, ceo_notification_required,
                    opened_by_worker, opened_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _require_text("incident_key", incident_key),
                    severity,
                    _require_text("title", title),
                    _require_text("description", description),
                    _require_text("affected_scope", affected_scope),
                    owner_role_key,
                    "contained" if containment.strip() else "open",
                    containment.strip(),
                    int(ceo_required),
                    opened_by_worker,
                    _utc_now(),
                ),
            )
            incident_id = int(cursor.lastrowid)
            connection.execute(
                """
                INSERT INTO incident_events(
                    incident_id, event_type, actor_worker_key, detail_json, created_at
                ) VALUES (?, 'incident.opened', ?, ?, ?)
                """,
                (
                    incident_id,
                    opened_by_worker,
                    _json_object({"severity": severity, "containment": containment}),
                    _utc_now(),
                ),
            )
            self.store._write_audit(
                connection,
                event_type="incident.opened",
                actor=opened_by_worker,
                entity_type="incident",
                entity_id=incident_id,
                action="open_incident",
                details={"severity": severity, "ceo_notification_required": ceo_required},
            )
            row = connection.execute(
                "SELECT * FROM incidents WHERE id = ?", (incident_id,)
            ).fetchone()
        return dict(row)

    def performance_report(self) -> list[dict[str, Any]]:
        """Derive a provisional throughput signal, never a staffing decision by itself."""

        self.store.initialize()
        with self.store._connection() as connection:
            rows = connection.execute(
                """
                SELECT workers.worker_key, workers.display_name, workers.role_key,
                       workers.status,
                       SUM(CASE WHEN work.status = 'succeeded' THEN 1 ELSE 0 END) AS accepted_work,
                       SUM(CASE WHEN work.status IN ('dead_letter','failed') THEN 1 ELSE 0 END) AS failed_work,
                       COALESCE(rejections.rejected_reviews, 0) AS rejected_reviews
                FROM workers
                LEFT JOIN work_items AS work
                    ON work.assigned_worker_key = workers.worker_key
                   AND work.task_type <> 'system_integrity_check'
                LEFT JOIN (
                    SELECT assigned_worker_key, COUNT(*) AS rejected_reviews
                    FROM work_events
                    JOIN work_items ON work_items.id = work_events.work_id
                    WHERE work_events.event_type = 'work.review_reject'
                      AND work_items.task_type <> 'system_integrity_check'
                    GROUP BY assigned_worker_key
                ) AS rejections ON rejections.assigned_worker_key = workers.worker_key
                GROUP BY workers.worker_key, workers.display_name, workers.role_key,
                         workers.status, rejections.rejected_reviews
                ORDER BY workers.worker_key
                """
            ).fetchall()
        results: list[dict[str, Any]] = []
        for item in rows:
            record = dict(item)
            accepted = int(record["accepted_work"] or 0)
            failed = int(record["failed_work"] or 0)
            rejected = int(record["rejected_reviews"] or 0)
            sample = accepted + failed + rejected
            record["sample_size"] = sample
            record["performance_state"] = "insufficient_sample" if sample < 5 else (
                "effective" if accepted / max(1, sample) >= 0.8 else "coaching"
            )
            results.append(record)
        return results

    def operations_summary(self) -> dict[str, Any]:
        self.store.initialize()
        with self.store._connection() as connection:
            queue = {
                row["status"]: int(row["count"])
                for row in connection.execute(
                    "SELECT status, COUNT(*) AS count FROM work_items GROUP BY status"
                ).fetchall()
            }
            departments = {
                row["department_slug"]: int(row["count"])
                for row in connection.execute(
                    """
                    SELECT department_slug, COUNT(*) AS count FROM work_items
                    WHERE status NOT IN ('succeeded','failed','dead_letter','cancelled')
                    GROUP BY department_slug
                    """
                ).fetchall()
            }
            open_escalations = int(
                connection.execute(
                    "SELECT COUNT(*) AS count FROM escalations WHERE status IN ('open','routed')"
                ).fetchone()["count"]
            )
            owner_attention = int(
                connection.execute(
                    """
                    SELECT COUNT(*) AS count FROM escalations
                    WHERE owner_attention = 1 AND status IN ('open','routed')
                    """
                ).fetchone()["count"]
            )
            open_incidents = int(
                connection.execute(
                    "SELECT COUNT(*) AS count FROM incidents WHERE status <> 'closed'"
                ).fetchone()["count"]
            )
            active_objectives = int(
                connection.execute(
                    "SELECT COUNT(*) AS count FROM objectives WHERE status IN ('active','at_risk')"
                ).fetchone()["count"]
            )
        return {
            "queue": queue,
            "active_work_by_department": departments,
            "open_escalations": open_escalations,
            "owner_attention": owner_attention,
            "open_incidents": open_incidents,
            "active_objectives": active_objectives,
        }


__all__ = ["CorporateOperations", "DecisionClass", "TERMINAL_WORK_STATUSES"]
