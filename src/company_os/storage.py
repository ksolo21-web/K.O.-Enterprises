"""SQLite persistence, migrations, ledgers, and tamper-evident audit events."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

from .errors import ConflictError, NotFoundError, StorageError, ValidationError
from .policy import ActionRequest, ApprovalClass, classify_action, is_paused
from .scoring import MarketVoidScore


OPPORTUNITY_STATUSES = frozenset(
    {
        "candidate",
        "researching",
        "validating",
        "selected",
        "building",
        "launched",
        "hold",
        "rejected",
        "killed",
    }
)
# These labels assert that an opportunity has advanced beyond open-ended
# research.  They must be backed by the latest executable score, not merely by
# a caller choosing a more optimistic status string.
OPPORTUNITY_ADVANCEMENT_STATUSES = frozenset({"validating", "selected", "building"})
OPPORTUNITY_INITIAL_STATUSES = OPPORTUNITY_STATUSES - (
    OPPORTUNITY_ADVANCEMENT_STATUSES | {"launched"}
)
EXPERIMENT_STATUSES = frozenset(
    {"planned", "active", "succeeded", "failed", "inconclusive", "cancelled"}
)
EVIDENCE_STRENGTHS = frozenset({"weak", "moderate", "strong"})
APPROVAL_STATUSES = frozenset({"pending", "approved", "rejected", "expired", "cancelled"})
SQLITE_MAX_INTEGER = 9_223_372_036_854_775_807
_INITIALIZE_LOCK = threading.RLock()
OWNER_DECISION_PACKET_FIELDS = (
    "exact_action",
    "why_now",
    "source_evidence",
    "resource_ceiling",
    "accounts_data_public_surfaces",
    "control_findings",
    "reversibility",
    "success_threshold",
    "kill_threshold",
    "monitoring",
    "expiry",
    "consequence_of_rejection_or_delay",
)


@contextmanager
def _cross_process_initialize_lock(db_path: str) -> Iterator[None]:
    """Serialize migrations across independent CLI and worker processes."""

    if db_path == ":memory:":
        yield
        return
    lock_path = Path(f"{db_path}.initialize.lock").expanduser().resolve()
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_file = lock_path.open("a+b")
    except OSError as exc:
        raise StorageError(f"cannot open migration lock for {db_path}: {exc}") from exc
    with lock_file:
        lock_file.seek(0, os.SEEK_END)
        if lock_file.tell() == 0:
            lock_file.write(b"\0")
            lock_file.flush()
        deadline = time.monotonic() + 30.0
        while True:
            try:
                lock_file.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as exc:
                if time.monotonic() >= deadline:
                    raise StorageError(
                        f"timed out waiting for migration lock for {db_path}"
                    ) from exc
                time.sleep(0.05)
        try:
            yield
        finally:
            try:
                lock_file.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            except OSError:
                # Closing the handle releases the OS lock even if explicit
                # unlock reporting itself fails during interpreter shutdown.
                pass


MIGRATIONS: tuple[tuple[int, str, str], ...] = (
    (
        1,
        "initial_company_ledger",
        """
        CREATE TABLE IF NOT EXISTS opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            buyer TEXT NOT NULL DEFAULT '',
            budget_holder TEXT NOT NULL DEFAULT '',
            why_now TEXT NOT NULL DEFAULT '',
            cost_of_inaction TEXT NOT NULL DEFAULT '',
            current_alternative TEXT NOT NULL DEFAULT '',
            entry_wedge TEXT NOT NULL DEFAULT '',
            distribution_path TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'candidate',
            latest_score REAL,
            last_scored_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            CHECK (status IN ('candidate','researching','validating','selected','building','launched','hold','rejected','killed'))
        );

        CREATE TABLE IF NOT EXISTS evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opportunity_id INTEGER NOT NULL REFERENCES opportunities(id) ON DELETE RESTRICT,
            criterion TEXT NOT NULL,
            claim TEXT NOT NULL,
            source_uri TEXT NOT NULL,
            source_type TEXT NOT NULL DEFAULT 'public_web',
            strength TEXT NOT NULL,
            rating REAL NOT NULL,
            confidence REAL NOT NULL,
            observed_at TEXT NOT NULL,
            expires_at TEXT,
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            CHECK (strength IN ('weak','moderate','strong')),
            CHECK (rating >= 0.0 AND rating <= 1.0),
            CHECK (confidence >= 0.0 AND confidence <= 1.0)
        );

        CREATE TABLE IF NOT EXISTS experiments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opportunity_id INTEGER NOT NULL REFERENCES opportunities(id) ON DELETE RESTRICT,
            name TEXT NOT NULL,
            hypothesis TEXT NOT NULL,
            method TEXT NOT NULL,
            success_metric TEXT NOT NULL,
            kill_metric TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'planned',
            planned_cost_cents INTEGER NOT NULL DEFAULT 0,
            started_at TEXT,
            ended_at TEXT,
            outcome TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            CHECK (planned_cost_cents >= 0),
            CHECK (status IN ('planned','active','succeeded','failed','inconclusive','cancelled'))
        );

        CREATE TABLE IF NOT EXISTS approvals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            rationale TEXT NOT NULL,
            risk TEXT NOT NULL DEFAULT '',
            estimated_cost_cents INTEGER NOT NULL DEFAULT 0,
            reversibility TEXT NOT NULL DEFAULT 'reversible',
            approval_class TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            requested_by TEXT NOT NULL,
            requested_at TEXT NOT NULL,
            decided_by TEXT,
            decided_at TEXT,
            expires_at TEXT,
            decision_notes TEXT NOT NULL DEFAULT '',
            CHECK (estimated_cost_cents >= 0),
            CHECK (approval_class IN ('auto_allowed','policy_gated','ceo_approval_required')),
            CHECK (status IN ('pending','approved','rejected','expired','cancelled'))
        );

        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opportunity_id INTEGER REFERENCES opportunities(id) ON DELETE RESTRICT,
            experiment_id INTEGER REFERENCES experiments(id) ON DELETE RESTRICT,
            title TEXT NOT NULL,
            decision TEXT NOT NULL,
            rationale TEXT NOT NULL,
            evidence_summary TEXT NOT NULL DEFAULT '',
            decision_type TEXT NOT NULL DEFAULT 'operating',
            decided_by TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS costs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opportunity_id INTEGER REFERENCES opportunities(id) ON DELETE RESTRICT,
            experiment_id INTEGER REFERENCES experiments(id) ON DELETE RESTRICT,
            amount_cents INTEGER NOT NULL,
            currency TEXT NOT NULL DEFAULT 'USD',
            cost_type TEXT NOT NULL DEFAULT 'direct',
            status TEXT NOT NULL DEFAULT 'incurred',
            description TEXT NOT NULL,
            vendor TEXT NOT NULL DEFAULT '',
            occurred_at TEXT NOT NULL,
            source_reference TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            CHECK (amount_cents >= 0),
            CHECK (status IN ('estimated','committed','incurred','paid','void'))
        );

        CREATE TABLE IF NOT EXISTS revenues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opportunity_id INTEGER REFERENCES opportunities(id) ON DELETE RESTRICT,
            experiment_id INTEGER REFERENCES experiments(id) ON DELETE RESTRICT,
            amount_cents INTEGER NOT NULL,
            currency TEXT NOT NULL DEFAULT 'USD',
            entry_type TEXT NOT NULL DEFAULT 'revenue',
            status TEXT NOT NULL DEFAULT 'realized',
            description TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            external_reference TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            CHECK (amount_cents >= 0),
            CHECK (entry_type IN ('revenue','refund','projection')),
            CHECK (status IN ('projected','realized','cleared','void'))
        );

        CREATE TABLE IF NOT EXISTS risks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opportunity_id INTEGER REFERENCES opportunities(id) ON DELETE RESTRICT,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            likelihood INTEGER NOT NULL,
            impact INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            mitigation TEXT NOT NULL DEFAULT '',
            owner TEXT NOT NULL DEFAULT '',
            review_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            CHECK (likelihood >= 1 AND likelihood <= 5),
            CHECK (impact >= 1 AND impact <= 5),
            CHECK (status IN ('open','mitigating','accepted','closed'))
        );

        CREATE TABLE IF NOT EXISTS opportunity_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opportunity_id INTEGER NOT NULL REFERENCES opportunities(id) ON DELETE RESTRICT,
            base_score REAL NOT NULL,
            penalty_score REAL NOT NULL,
            final_score REAL NOT NULL,
            eligible_for_advancement INTEGER NOT NULL,
            inputs_json TEXT NOT NULL,
            result_json TEXT NOT NULL,
            scored_at TEXT NOT NULL,
            scored_by TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            actor TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            action TEXT NOT NULL,
            detail_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            previous_hash TEXT NOT NULL,
            event_hash TEXT NOT NULL UNIQUE
        );
        """,
    ),
    (
        2,
        "operating_indexes",
        """
        CREATE INDEX IF NOT EXISTS idx_opportunities_status_score
            ON opportunities(status, latest_score DESC);
        CREATE INDEX IF NOT EXISTS idx_evidence_opportunity_criterion
            ON evidence(opportunity_id, criterion, expires_at);
        CREATE INDEX IF NOT EXISTS idx_experiments_status
            ON experiments(status, opportunity_id);
        CREATE INDEX IF NOT EXISTS idx_approvals_status
            ON approvals(status, requested_at);
        CREATE INDEX IF NOT EXISTS idx_costs_occurred
            ON costs(currency, status, occurred_at);
        CREATE INDEX IF NOT EXISTS idx_revenues_occurred
            ON revenues(currency, entry_type, status, occurred_at);
        CREATE INDEX IF NOT EXISTS idx_risks_status
            ON risks(status, likelihood, impact);
        CREATE INDEX IF NOT EXISTS idx_scores_opportunity
            ON opportunity_scores(opportunity_id, scored_at DESC);
        """,
    ),
    (
        3,
        "append_only_audit_events",
        """
        CREATE TRIGGER IF NOT EXISTS audit_events_no_update
        BEFORE UPDATE ON audit_events
        BEGIN
            SELECT RAISE(ABORT, 'audit_events are append-only');
        END;

        CREATE TRIGGER IF NOT EXISTS audit_events_no_delete
        BEFORE DELETE ON audit_events
        BEGIN
            SELECT RAISE(ABORT, 'audit_events are append-only');
        END;
        """,
    ),
    (
        4,
        "ledger_reference_idempotency",
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_costs_source_reference
            ON costs(currency, source_reference)
            WHERE source_reference <> '';
        CREATE UNIQUE INDEX IF NOT EXISTS uq_revenues_external_reference
            ON revenues(entry_type, currency, external_reference)
            WHERE external_reference <> '';
        """,
    ),
    (
        5,
        "corporate_organization_and_objectives",
        """
        CREATE TABLE IF NOT EXISTS departments (
            slug TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            mission TEXT NOT NULL,
            parent_slug TEXT REFERENCES departments(slug) ON DELETE RESTRICT,
            executive_role_key TEXT NOT NULL,
            service_level_cycles INTEGER NOT NULL DEFAULT 2,
            wip_limit INTEGER NOT NULL DEFAULT 3,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            CHECK (service_level_cycles >= 1),
            CHECK (wip_limit >= 1),
            CHECK (status IN ('active','paused','retired'))
        );

        CREATE TABLE IF NOT EXISTS roles (
            role_key TEXT PRIMARY KEY,
            department_slug TEXT NOT NULL REFERENCES departments(slug) ON DELETE RESTRICT,
            title TEXT NOT NULL,
            reports_to_role_key TEXT REFERENCES roles(role_key) ON DELETE RESTRICT,
            authority_level TEXT NOT NULL,
            worker_type TEXT NOT NULL DEFAULT 'digital',
            mandate TEXT NOT NULL,
            capabilities_json TEXT NOT NULL DEFAULT '[]',
            kpis_json TEXT NOT NULL DEFAULT '[]',
            max_active_work INTEGER NOT NULL DEFAULT 2,
            independent_control INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            CHECK (authority_level IN ('owner','company_executive','department_executive','specialist')),
            CHECK (worker_type IN ('human','digital','service')),
            CHECK (max_active_work >= 1),
            CHECK (independent_control IN (0,1)),
            CHECK (status IN ('active','paused','retired'))
        );

        CREATE TABLE IF NOT EXISTS workers (
            worker_key TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            role_key TEXT NOT NULL REFERENCES roles(role_key) ON DELETE RESTRICT,
            manager_worker_key TEXT REFERENCES workers(worker_key) ON DELETE RESTRICT,
            worker_type TEXT NOT NULL DEFAULT 'digital',
            status TEXT NOT NULL DEFAULT 'active',
            capacity_units INTEGER NOT NULL DEFAULT 10,
            quality_floor REAL NOT NULL DEFAULT 0.80,
            appointed_by TEXT NOT NULL,
            appointed_at TEXT NOT NULL,
            suspended_at TEXT,
            CHECK (worker_type IN ('human','digital','service')),
            CHECK (status IN ('active','probationary','coaching','suspended','disabled','retired')),
            CHECK (capacity_units >= 0),
            CHECK (quality_floor >= 0.0 AND quality_floor <= 1.0)
        );

        CREATE TABLE IF NOT EXISTS objectives (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            objective_key TEXT NOT NULL UNIQUE,
            parent_objective_id INTEGER REFERENCES objectives(id) ON DELETE RESTRICT,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            owner_role_key TEXT NOT NULL REFERENCES roles(role_key) ON DELETE RESTRICT,
            department_slug TEXT NOT NULL REFERENCES departments(slug) ON DELETE RESTRICT,
            commanded_by_worker TEXT NOT NULL REFERENCES workers(worker_key) ON DELETE RESTRICT,
            priority INTEGER NOT NULL DEFAULT 50,
            status TEXT NOT NULL DEFAULT 'active',
            starts_at TEXT NOT NULL,
            due_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            CHECK (priority >= 0 AND priority <= 100),
            CHECK (status IN ('draft','active','at_risk','achieved','cancelled'))
        );

        CREATE TABLE IF NOT EXISTS key_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            objective_id INTEGER NOT NULL REFERENCES objectives(id) ON DELETE RESTRICT,
            result_key TEXT NOT NULL,
            description TEXT NOT NULL,
            metric_name TEXT NOT NULL,
            baseline REAL NOT NULL DEFAULT 0,
            target REAL NOT NULL,
            current_value REAL NOT NULL DEFAULT 0,
            unit TEXT NOT NULL,
            evidence_reference TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            updated_at TEXT NOT NULL,
            UNIQUE(objective_id, result_key),
            CHECK (status IN ('active','at_risk','achieved','cancelled'))
        );

        CREATE TABLE IF NOT EXISTS resource_allocations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            allocation_key TEXT NOT NULL UNIQUE,
            parent_allocation_id INTEGER REFERENCES resource_allocations(id) ON DELETE RESTRICT,
            department_slug TEXT REFERENCES departments(slug) ON DELETE RESTRICT,
            objective_id INTEGER REFERENCES objectives(id) ON DELETE RESTRICT,
            opportunity_id INTEGER REFERENCES opportunities(id) ON DELETE RESTRICT,
            resource_type TEXT NOT NULL,
            unit TEXT NOT NULL,
            ceiling INTEGER NOT NULL,
            reserved INTEGER NOT NULL DEFAULT 0,
            consumed INTEGER NOT NULL DEFAULT 0,
            approved_by_worker TEXT NOT NULL REFERENCES workers(worker_key) ON DELETE RESTRICT,
            starts_at TEXT NOT NULL,
            expires_at TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            CHECK (resource_type IN ('capacity','cash','compute','human_review','storage')),
            CHECK (ceiling >= 0 AND reserved >= 0 AND consumed >= 0),
            CHECK (reserved + consumed <= ceiling),
            CHECK (status IN ('draft','active','exhausted','expired','closed'))
        );

        CREATE TABLE IF NOT EXISTS performance_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            worker_key TEXT NOT NULL REFERENCES workers(worker_key) ON DELETE RESTRICT,
            period_start TEXT NOT NULL,
            period_end TEXT NOT NULL,
            accepted_work INTEGER NOT NULL DEFAULT 0,
            rejected_work INTEGER NOT NULL DEFAULT 0,
            weighted_quality REAL,
            objective_contribution REAL,
            sla_reliability REAL,
            resource_efficiency REAL,
            audit_completeness REAL,
            handoff_quality REAL,
            composite_score REAL,
            status TEXT NOT NULL,
            reviewed_by_worker TEXT NOT NULL REFERENCES workers(worker_key) ON DELETE RESTRICT,
            evidence_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            UNIQUE(worker_key, period_start, period_end),
            CHECK (accepted_work >= 0 AND rejected_work >= 0),
            CHECK (status IN ('insufficient_sample','effective','coaching','reassigned','disabled','red'))
        );

        CREATE INDEX IF NOT EXISTS idx_roles_reports_to ON roles(reports_to_role_key);
        CREATE INDEX IF NOT EXISTS idx_workers_role_status ON workers(role_key, status);
        CREATE INDEX IF NOT EXISTS idx_objectives_department_status ON objectives(department_slug, status, priority DESC);
        CREATE INDEX IF NOT EXISTS idx_allocations_scope_status ON resource_allocations(department_slug, status);
        CREATE INDEX IF NOT EXISTS idx_performance_worker_period ON performance_snapshots(worker_key, period_end DESC);
        """,
    ),
    (
        6,
        "autonomous_operations_runtime",
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_key TEXT NOT NULL UNIQUE,
            opportunity_id INTEGER NOT NULL REFERENCES opportunities(id) ON DELETE RESTRICT,
            name TEXT NOT NULL,
            value_proposition TEXT NOT NULL,
            owner_role_key TEXT NOT NULL REFERENCES roles(role_key) ON DELETE RESTRICT,
            stage TEXT NOT NULL DEFAULT 'concept',
            acceptance_criteria TEXT NOT NULL DEFAULT '',
            repository_uri TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            CHECK (stage IN ('concept','prototype','validation','build','release_candidate','live','hold','retired'))
        );

        CREATE TABLE IF NOT EXISTS operating_cycles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_key TEXT NOT NULL UNIQUE,
            mode TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'running',
            triggered_by_worker TEXT NOT NULL REFERENCES workers(worker_key) ON DELETE RESTRICT,
            scheduled INTEGER NOT NULL DEFAULT 0,
            max_work_items INTEGER NOT NULL DEFAULT 20,
            plan_json TEXT NOT NULL DEFAULT '{}',
            summary_json TEXT NOT NULL DEFAULT '{}',
            started_at TEXT NOT NULL,
            completed_at TEXT,
            CHECK (mode IN ('simulation','internal','shadow','external')),
            CHECK (status IN ('running','awaiting_workers','completed','failed','paused')),
            CHECK (scheduled IN (0,1)),
            CHECK (max_work_items >= 1 AND max_work_items <= 1000)
        );

        CREATE TABLE IF NOT EXISTS work_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_key TEXT NOT NULL UNIQUE,
            parent_work_id INTEGER REFERENCES work_items(id) ON DELETE RESTRICT,
            cycle_id INTEGER REFERENCES operating_cycles(id) ON DELETE RESTRICT,
            objective_id INTEGER REFERENCES objectives(id) ON DELETE RESTRICT,
            opportunity_id INTEGER REFERENCES opportunities(id) ON DELETE RESTRICT,
            product_id INTEGER REFERENCES products(id) ON DELETE RESTRICT,
            department_slug TEXT NOT NULL REFERENCES departments(slug) ON DELETE RESTRICT,
            commanded_by_worker TEXT NOT NULL REFERENCES workers(worker_key) ON DELETE RESTRICT,
            assigned_role_key TEXT NOT NULL REFERENCES roles(role_key) ON DELETE RESTRICT,
            assigned_worker_key TEXT REFERENCES workers(worker_key) ON DELETE RESTRICT,
            reviewer_role_key TEXT REFERENCES roles(role_key) ON DELETE RESTRICT,
            task_type TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            acceptance_criteria TEXT NOT NULL,
            decision_class TEXT NOT NULL,
            priority INTEGER NOT NULL DEFAULT 50,
            risk_level TEXT NOT NULL DEFAULT 'low',
            external_effect INTEGER NOT NULL DEFAULT 0,
            estimated_cost_cents INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'proposed',
            input_json TEXT NOT NULL DEFAULT '{}',
            result_json TEXT NOT NULL DEFAULT '{}',
            error_text TEXT NOT NULL DEFAULT '',
            idempotency_key TEXT NOT NULL UNIQUE,
            attempt_count INTEGER NOT NULL DEFAULT 0,
            max_attempts INTEGER NOT NULL DEFAULT 3,
            next_run_at TEXT,
            lease_owner TEXT,
            lease_token TEXT,
            lease_epoch INTEGER NOT NULL DEFAULT 0,
            lease_expires_at TEXT,
            deadline_at TEXT,
            submitted_at TEXT,
            accepted_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            CHECK (decision_class IN ('work_execution','department_operation','executive_portfolio','controlled_external','owner_reserved','prohibited')),
            CHECK (priority >= 0 AND priority <= 100),
            CHECK (risk_level IN ('low','medium','high','critical')),
            CHECK (external_effect IN (0,1)),
            CHECK (estimated_cost_cents >= 0),
            CHECK (status IN ('proposed','waiting_dependency','waiting_policy','ready','leased','running','review','retry_wait','succeeded','failed','dead_letter','cancelled','blocked')),
            CHECK (attempt_count >= 0 AND max_attempts >= 1)
        );

        CREATE TABLE IF NOT EXISTS work_dependencies (
            work_id INTEGER NOT NULL REFERENCES work_items(id) ON DELETE RESTRICT,
            depends_on_work_id INTEGER NOT NULL REFERENCES work_items(id) ON DELETE RESTRICT,
            failure_policy TEXT NOT NULL DEFAULT 'block',
            created_at TEXT NOT NULL,
            PRIMARY KEY(work_id, depends_on_work_id),
            CHECK (work_id <> depends_on_work_id),
            CHECK (failure_policy IN ('block','cancel','continue'))
        );

        CREATE TABLE IF NOT EXISTS work_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_id INTEGER NOT NULL REFERENCES work_items(id) ON DELETE RESTRICT,
            event_type TEXT NOT NULL,
            actor_worker_key TEXT NOT NULL REFERENCES workers(worker_key) ON DELETE RESTRICT,
            from_status TEXT,
            to_status TEXT,
            detail_json TEXT NOT NULL DEFAULT '{}',
            correlation_id TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS control_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_id INTEGER REFERENCES work_items(id) ON DELETE RESTRICT,
            opportunity_id INTEGER REFERENCES opportunities(id) ON DELETE RESTRICT,
            product_id INTEGER REFERENCES products(id) ON DELETE RESTRICT,
            control_domain TEXT NOT NULL,
            reviewer_worker_key TEXT NOT NULL REFERENCES workers(worker_key) ON DELETE RESTRICT,
            status TEXT NOT NULL DEFAULT 'pending',
            severity TEXT NOT NULL DEFAULT 'low',
            finding TEXT NOT NULL DEFAULT '',
            conditions TEXT NOT NULL DEFAULT '',
            artifact_digest TEXT NOT NULL DEFAULT '',
            expires_at TEXT,
            created_at TEXT NOT NULL,
            decided_at TEXT,
            CHECK (control_domain IN ('finance','legal','compliance','security','privacy','quality','audit','claims')),
            CHECK (status IN ('pending','passed','blocked','changes_required','expired')),
            CHECK (severity IN ('low','medium','high','critical'))
        );

        CREATE TABLE IF NOT EXISTS escalations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_id INTEGER REFERENCES work_items(id) ON DELETE RESTRICT,
            department_slug TEXT NOT NULL REFERENCES departments(slug) ON DELETE RESTRICT,
            raised_by_worker TEXT NOT NULL REFERENCES workers(worker_key) ON DELETE RESTRICT,
            routed_to_role_key TEXT NOT NULL REFERENCES roles(role_key) ON DELETE RESTRICT,
            decision_class TEXT NOT NULL,
            reason_code TEXT NOT NULL,
            title TEXT NOT NULL,
            context TEXT NOT NULL,
            options_json TEXT NOT NULL DEFAULT '[]',
            recommendation TEXT NOT NULL,
            safe_default TEXT NOT NULL,
            owner_attention INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'open',
            resolution TEXT NOT NULL DEFAULT '',
            due_at TEXT,
            created_at TEXT NOT NULL,
            resolved_at TEXT,
            CHECK (decision_class IN ('department_operation','executive_portfolio','controlled_external','owner_reserved','prohibited')),
            CHECK (owner_attention IN (0,1)),
            CHECK (status IN ('open','routed','resolved','dismissed'))
        );

        CREATE TABLE IF NOT EXISTS metric_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            metric_name TEXT NOT NULL,
            metric_type TEXT NOT NULL,
            value REAL NOT NULL,
            unit TEXT NOT NULL,
            department_slug TEXT REFERENCES departments(slug) ON DELETE RESTRICT,
            worker_key TEXT REFERENCES workers(worker_key) ON DELETE RESTRICT,
            objective_id INTEGER REFERENCES objectives(id) ON DELETE RESTRICT,
            work_id INTEGER REFERENCES work_items(id) ON DELETE RESTRICT,
            opportunity_id INTEGER REFERENCES opportunities(id) ON DELETE RESTRICT,
            source_reference TEXT NOT NULL,
            evidence_type TEXT NOT NULL,
            observed_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            CHECK (metric_type IN ('actual','estimate','forecast'))
        );

        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_key TEXT NOT NULL UNIQUE,
            severity TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            affected_scope TEXT NOT NULL,
            owner_role_key TEXT NOT NULL REFERENCES roles(role_key) ON DELETE RESTRICT,
            status TEXT NOT NULL DEFAULT 'open',
            containment TEXT NOT NULL DEFAULT '',
            root_cause TEXT NOT NULL DEFAULT '',
            resolution TEXT NOT NULL DEFAULT '',
            ceo_notification_required INTEGER NOT NULL DEFAULT 0,
            opened_by_worker TEXT NOT NULL REFERENCES workers(worker_key) ON DELETE RESTRICT,
            opened_at TEXT NOT NULL,
            resolved_at TEXT,
            CHECK (severity IN ('sev0','sev1','sev2','sev3')),
            CHECK (status IN ('open','contained','monitoring','resolved','closed')),
            CHECK (ceo_notification_required IN (0,1))
        );

        CREATE TABLE IF NOT EXISTS incident_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            incident_id INTEGER NOT NULL REFERENCES incidents(id) ON DELETE RESTRICT,
            event_type TEXT NOT NULL,
            actor_worker_key TEXT NOT NULL REFERENCES workers(worker_key) ON DELETE RESTRICT,
            detail_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            schedule_key TEXT NOT NULL UNIQUE,
            task_type TEXT NOT NULL,
            commanded_by_worker TEXT NOT NULL REFERENCES workers(worker_key) ON DELETE RESTRICT,
            assigned_role_key TEXT NOT NULL REFERENCES roles(role_key) ON DELETE RESTRICT,
            interval_seconds INTEGER NOT NULL,
            next_run_at TEXT NOT NULL,
            max_catchup INTEGER NOT NULL DEFAULT 1,
            external_effect INTEGER NOT NULL DEFAULT 0,
            enabled INTEGER NOT NULL DEFAULT 0,
            payload_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            CHECK (interval_seconds >= 60),
            CHECK (max_catchup >= 0 AND max_catchup <= 100),
            CHECK (external_effect IN (0,1)),
            CHECK (enabled IN (0,1))
        );

        CREATE TABLE IF NOT EXISTS schedule_occurrences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            schedule_id INTEGER NOT NULL REFERENCES schedules(id) ON DELETE RESTRICT,
            scheduled_for TEXT NOT NULL,
            work_id INTEGER REFERENCES work_items(id) ON DELETE RESTRICT,
            created_at TEXT NOT NULL,
            UNIQUE(schedule_id, scheduled_for)
        );

        CREATE TRIGGER IF NOT EXISTS work_events_no_update
        BEFORE UPDATE ON work_events BEGIN
            SELECT RAISE(ABORT, 'work_events are append-only');
        END;
        CREATE TRIGGER IF NOT EXISTS work_events_no_delete
        BEFORE DELETE ON work_events BEGIN
            SELECT RAISE(ABORT, 'work_events are append-only');
        END;
        CREATE TRIGGER IF NOT EXISTS metric_events_no_update
        BEFORE UPDATE ON metric_events BEGIN
            SELECT RAISE(ABORT, 'metric_events are append-only');
        END;
        CREATE TRIGGER IF NOT EXISTS metric_events_no_delete
        BEFORE DELETE ON metric_events BEGIN
            SELECT RAISE(ABORT, 'metric_events are append-only');
        END;
        CREATE TRIGGER IF NOT EXISTS incident_events_no_update
        BEFORE UPDATE ON incident_events BEGIN
            SELECT RAISE(ABORT, 'incident_events are append-only');
        END;
        CREATE TRIGGER IF NOT EXISTS incident_events_no_delete
        BEFORE DELETE ON incident_events BEGIN
            SELECT RAISE(ABORT, 'incident_events are append-only');
        END;

        CREATE INDEX IF NOT EXISTS idx_work_queue ON work_items(status, priority DESC, next_run_at, created_at);
        CREATE INDEX IF NOT EXISTS idx_work_assignment ON work_items(assigned_worker_key, assigned_role_key, status);
        CREATE INDEX IF NOT EXISTS idx_work_cycle ON work_items(cycle_id, status);
        CREATE INDEX IF NOT EXISTS idx_work_events_work ON work_events(work_id, id);
        CREATE INDEX IF NOT EXISTS idx_control_reviews_scope ON control_reviews(work_id, opportunity_id, product_id, status);
        CREATE INDEX IF NOT EXISTS idx_escalations_attention ON escalations(owner_attention, status, created_at);
        CREATE INDEX IF NOT EXISTS idx_metric_name_time ON metric_events(metric_name, observed_at);
        CREATE INDEX IF NOT EXISTS idx_incidents_status_severity ON incidents(status, severity, opened_at);
        CREATE INDEX IF NOT EXISTS idx_schedules_due ON schedules(enabled, next_run_at);
        """,
    ),
    (
        7,
        "expand_independent_control_domains",
        """
        DROP INDEX IF EXISTS idx_control_reviews_scope;
        ALTER TABLE control_reviews RENAME TO control_reviews_v6;
        CREATE TABLE control_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_id INTEGER REFERENCES work_items(id) ON DELETE RESTRICT,
            opportunity_id INTEGER REFERENCES opportunities(id) ON DELETE RESTRICT,
            product_id INTEGER REFERENCES products(id) ON DELETE RESTRICT,
            control_domain TEXT NOT NULL,
            reviewer_worker_key TEXT NOT NULL REFERENCES workers(worker_key) ON DELETE RESTRICT,
            status TEXT NOT NULL DEFAULT 'pending',
            severity TEXT NOT NULL DEFAULT 'low',
            finding TEXT NOT NULL DEFAULT '',
            conditions TEXT NOT NULL DEFAULT '',
            artifact_digest TEXT NOT NULL DEFAULT '',
            expires_at TEXT,
            created_at TEXT NOT NULL,
            decided_at TEXT,
            CHECK (control_domain IN (
                'accessibility','audit','budget','claims','data','evidence_quality',
                'finance','ip','legal','opportunity_advancement','performance',
                'permissions','platform_policy','policy','privacy','quality',
                'regulatory','release','reliability','risk','security','unit_economics'
            )),
            CHECK (status IN ('pending','passed','blocked','changes_required','expired')),
            CHECK (severity IN ('low','medium','high','critical'))
        );
        INSERT INTO control_reviews(
            id, work_id, opportunity_id, product_id, control_domain,
            reviewer_worker_key, status, severity, finding, conditions,
            artifact_digest, expires_at, created_at, decided_at
        )
        SELECT id, work_id, opportunity_id, product_id, control_domain,
               reviewer_worker_key, status, severity, finding, conditions,
               artifact_digest, expires_at, created_at, decided_at
        FROM control_reviews_v6;
        DROP TABLE control_reviews_v6;
        CREATE INDEX idx_control_reviews_scope
            ON control_reviews(work_id, opportunity_id, product_id, status);
        """,
    ),
    (
        8,
        "bind_owner_packets_and_work_approvals",
        """
        ALTER TABLE escalations
            ADD COLUMN decision_packet_json TEXT NOT NULL DEFAULT '{}';
        ALTER TABLE work_items
            ADD COLUMN approval_id INTEGER REFERENCES approvals(id) ON DELETE RESTRICT;
        ALTER TABLE approvals
            ADD COLUMN decision_packet_json TEXT NOT NULL DEFAULT '{}';
        ALTER TABLE approvals
            ADD COLUMN packet_digest TEXT NOT NULL DEFAULT '';
        CREATE INDEX IF NOT EXISTS idx_work_approval
            ON work_items(approval_id, status);
        """,
    ),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _normalize_timestamp(value: str | date | datetime | None, *, default_now: bool = False) -> str | None:
    if value is None:
        return _utc_now() if default_now else None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime.combine(value, datetime.min.time(), tzinfo=timezone.utc)
    else:
        text = str(value).strip()
        if not text:
            return _utc_now() if default_now else None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            try:
                parsed = datetime.combine(date.fromisoformat(text), datetime.min.time())
            except ValueError as exc:
                raise ValidationError(f"invalid ISO date/time: {value}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def normalize_owner_decision_packet(
    packet: Mapping[str, Any],
) -> tuple[dict[str, str], str]:
    """Validate and canonicalize a complete, expiring CEO decision packet."""

    if not isinstance(packet, Mapping):
        raise ValidationError("owner decision packet must be a JSON object")
    normalized: dict[str, str] = {}
    missing: list[str] = []
    for field in OWNER_DECISION_PACKET_FIELDS:
        value = str(packet.get(field, "")).strip()
        if not value:
            missing.append(field)
        else:
            normalized[field] = value
    if missing:
        raise ValidationError("owner decision packet is missing: " + ", ".join(missing))
    packet_expiry = _normalize_timestamp(normalized["expiry"])
    if packet_expiry is None or packet_expiry <= _utc_now():
        raise ValidationError("owner decision packet expiry must be in the future")
    normalized["expiry"] = packet_expiry
    canonical = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return normalized, digest


def _require_text(name: str, value: Any) -> str:
    text = str(value).strip() if value is not None else ""
    if not text:
        raise ValidationError(f"{name} must not be empty")
    return text


def _unit_value(name: str, value: Any) -> float:
    if isinstance(value, bool):
        raise ValidationError(f"{name} must be a number between 0 and 1, not boolean")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{name} must be a number between 0 and 1") from exc
    if not 0.0 <= result <= 1.0:
        raise ValidationError(f"{name} must be between 0 and 1")
    return result


def _non_negative_cents(name: str, value: Any) -> int:
    """Validate integer cents without silently truncating floats or booleans."""

    if type(value) is not int:
        raise ValidationError(f"{name} must be an integer number of cents")
    if value < 0:
        raise ValidationError(f"{name} must be non-negative")
    if value > SQLITE_MAX_INTEGER:
        raise ValidationError(f"{name} exceeds SQLite's integer range")
    return value


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug:
        raise ValidationError("title or slug must contain at least one letter or number")
    return slug


def _currency_code(value: Any) -> str:
    currency = _require_text("currency", value).upper()
    if re.fullmatch(r"[A-Z]{3}", currency) is None:
        raise ValidationError("currency must be a three-letter uppercase code")
    return currency


def _row_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


class CompanyStore:
    """Durable company state with one transaction per public mutation."""

    def __init__(self, db_path: str | Path = "state/company_os.db") -> None:
        self.db_path = str(db_path)
        self._memory_connection: sqlite3.Connection | None = None
        if self.db_path == ":memory:":
            self._memory_connection = self._new_connection(self.db_path)

    def __enter__(self) -> "CompanyStore":
        self.initialize()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        if self._memory_connection is not None:
            self._memory_connection.close()
            self._memory_connection = None

    @staticmethod
    def _new_connection(path: str) -> sqlite3.Connection:
        connection = sqlite3.connect(path, timeout=30)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA busy_timeout = 30000")
            connection.execute("PRAGMA foreign_keys = ON")
            if path != ":memory:":
                connection.execute("PRAGMA journal_mode = WAL")
            return connection
        except sqlite3.Error as exc:
            connection.close()
            raise StorageError(f"cannot configure SQLite connection for {path}: {exc}") from exc

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        if self.db_path == ":memory:":
            if self._memory_connection is None:
                self._memory_connection = self._new_connection(self.db_path)
            yield self._memory_connection
            return
        connection = self._new_connection(self.db_path)
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        self.initialize()
        with self._connection() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                yield connection
                connection.commit()
            except Exception:
                connection.rollback()
                raise

    def initialize(self) -> dict[str, Any]:
        """Create or migrate the database and return migration state."""

        with _INITIALIZE_LOCK:
            with _cross_process_initialize_lock(self.db_path):
                return self._initialize_locked()

    def _initialize_locked(self) -> dict[str, Any]:
        """Initialize while serialized against other stores in this process."""

        if self.db_path != ":memory:":
            try:
                Path(self.db_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise StorageError(f"cannot create database directory for {self.db_path}: {exc}") from exc
        applied_now: list[int] = []
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TEXT NOT NULL
                )
                """
            )
            connection.commit()
            applied = {
                int(row["version"])
                for row in connection.execute("SELECT version FROM schema_migrations")
            }
            supported_versions = {version for version, _name, _sql in MIGRATIONS}
            unknown_versions = sorted(applied - supported_versions)
            if unknown_versions:
                raise StorageError(
                    "database contains unsupported migration version(s): "
                    + ", ".join(str(version) for version in unknown_versions)
                )
            for version, name, sql in MIGRATIONS:
                if version in applied:
                    continue
                try:
                    connection.executescript(sql)
                    connection.execute(
                        "INSERT INTO schema_migrations(version, name, applied_at) VALUES (?, ?, ?)",
                        (version, name, _utc_now()),
                    )
                    connection.commit()
                    applied_now.append(version)
                except sqlite3.Error as exc:
                    connection.rollback()
                    raise StorageError(f"migration {version} ({name}) failed: {exc}") from exc
        return {"database": self.db_path, "schema_version": self.schema_version(), "applied": applied_now}

    def schema_version(self) -> int:
        if self.db_path != ":memory:" and not Path(self.db_path).exists():
            return 0
        try:
            with self._connection() as connection:
                row = connection.execute("SELECT MAX(version) AS version FROM schema_migrations").fetchone()
        except sqlite3.Error:
            return 0
        return int(row["version"] or 0) if row else 0

    @staticmethod
    def _write_audit(
        connection: sqlite3.Connection,
        *,
        event_type: str,
        actor: str,
        entity_type: str,
        entity_id: str | int,
        action: str,
        details: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        created_at = _utc_now()
        previous = connection.execute(
            "SELECT event_hash FROM audit_events ORDER BY id DESC LIMIT 1"
        ).fetchone()
        previous_hash = str(previous["event_hash"]) if previous else "GENESIS"
        detail_json = json.dumps(details or {}, sort_keys=True, separators=(",", ":"), default=str)
        payload = "|".join(
            [previous_hash, event_type, actor, entity_type, str(entity_id), action, detail_json, created_at]
        )
        event_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        cursor = connection.execute(
            """
            INSERT INTO audit_events(
                event_type, actor, entity_type, entity_id, action, detail_json,
                created_at, previous_hash, event_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_type,
                actor,
                entity_type,
                str(entity_id),
                action,
                detail_json,
                created_at,
                previous_hash,
                event_hash,
            ),
        )
        return {
            "id": cursor.lastrowid,
            "event_hash": event_hash,
            "previous_hash": previous_hash,
            "created_at": created_at,
        }

    @staticmethod
    def _resolve_opportunity(connection: sqlite3.Connection, identifier: str | int) -> sqlite3.Row:
        if isinstance(identifier, int) or str(identifier).isdigit():
            row = connection.execute(
                "SELECT * FROM opportunities WHERE id = ?", (int(identifier),)
            ).fetchone()
        else:
            row = connection.execute(
                "SELECT * FROM opportunities WHERE slug = ?", (str(identifier),)
            ).fetchone()
        if row is None:
            raise NotFoundError(f"opportunity not found: {identifier}")
        return row

    @staticmethod
    def _resolve_experiment(connection: sqlite3.Connection, identifier: int) -> sqlite3.Row:
        row = connection.execute("SELECT * FROM experiments WHERE id = ?", (identifier,)).fetchone()
        if row is None:
            raise NotFoundError(f"experiment not found: {identifier}")
        return row

    def create_opportunity(
        self,
        title: str,
        *,
        slug: str | None = None,
        description: str = "",
        buyer: str = "",
        budget_holder: str = "",
        why_now: str = "",
        cost_of_inaction: str = "",
        current_alternative: str = "",
        entry_wedge: str = "",
        distribution_path: str = "",
        status: str = "candidate",
        actor: str = "company_os",
    ) -> dict[str, Any]:
        title = _require_text("title", title)
        normalized_slug = _slugify(slug or title)
        if status not in OPPORTUNITY_INITIAL_STATUSES:
            raise ValidationError(
                f"invalid initial opportunity status: {status}; advancement labels "
                "require a stored opportunity and an eligible score"
            )
        now = _utc_now()
        with self._transaction() as connection:
            try:
                cursor = connection.execute(
                    """
                    INSERT INTO opportunities(
                        slug, title, description, buyer, budget_holder, why_now,
                        cost_of_inaction, current_alternative, entry_wedge,
                        distribution_path, status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        normalized_slug,
                        title,
                        description.strip(),
                        buyer.strip(),
                        budget_holder.strip(),
                        why_now.strip(),
                        cost_of_inaction.strip(),
                        current_alternative.strip(),
                        entry_wedge.strip(),
                        distribution_path.strip(),
                        status,
                        now,
                        now,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ConflictError(f"opportunity slug already exists: {normalized_slug}") from exc
            opportunity_id = int(cursor.lastrowid)
            self._write_audit(
                connection,
                event_type="opportunity.created",
                actor=actor,
                entity_type="opportunity",
                entity_id=opportunity_id,
                action="create",
                details={"slug": normalized_slug, "status": status},
            )
            row = connection.execute(
                "SELECT * FROM opportunities WHERE id = ?", (opportunity_id,)
            ).fetchone()
        return dict(row)

    def get_opportunity(self, identifier: str | int) -> dict[str, Any]:
        self.initialize()
        with self._connection() as connection:
            return dict(self._resolve_opportunity(connection, identifier))

    def list_opportunities(self, status: str | None = None) -> list[dict[str, Any]]:
        self.initialize()
        if status is not None and status not in OPPORTUNITY_STATUSES:
            raise ValidationError(f"invalid opportunity status: {status}")
        with self._connection() as connection:
            if status is None:
                rows = connection.execute(
                    "SELECT * FROM opportunities ORDER BY COALESCE(latest_score, -1) DESC, id"
                ).fetchall()
            else:
                rows = connection.execute(
                    """SELECT * FROM opportunities WHERE status = ?
                       ORDER BY COALESCE(latest_score, -1) DESC, id""",
                    (status,),
                ).fetchall()
        return [dict(row) for row in rows]

    def set_opportunity_status(
        self, identifier: str | int, status: str, *, actor: str = "company_os"
    ) -> dict[str, Any]:
        if status not in OPPORTUNITY_STATUSES:
            raise ValidationError(f"invalid opportunity status: {status}")
        if status == "launched":
            raise ValidationError(
                "launched status requires a governed external launch workflow "
                "that is not implemented by the internal-only runtime"
            )
        with self._transaction() as connection:
            existing = self._resolve_opportunity(connection, identifier)
            if status in OPPORTUNITY_ADVANCEMENT_STATUSES:
                latest_score = connection.execute(
                    """
                    SELECT eligible_for_advancement, inputs_json
                    FROM opportunity_scores
                    WHERE opportunity_id = ?
                    ORDER BY scored_at DESC, id DESC LIMIT 1
                    """,
                    (existing["id"],),
                ).fetchone()
                if latest_score is None or not bool(
                    latest_score["eligible_for_advancement"]
                ):
                    raise ConflictError(
                        f"status {status} requires the latest Market Void score "
                        "to pass every advancement gate"
                    )
                try:
                    score_inputs = json.loads(str(latest_score["inputs_json"]))
                except (TypeError, ValueError, json.JSONDecodeError):
                    score_inputs = {}
                evidence_ids = (
                    score_inputs.get("evidence_ids")
                    if isinstance(score_inputs, dict)
                    else None
                )
                evidence_ids_are_traceable = (
                    isinstance(evidence_ids, list)
                    and bool(evidence_ids)
                    and all(type(item) is int and item > 0 for item in evidence_ids)
                    and len(set(evidence_ids)) == len(evidence_ids)
                )
                if not evidence_ids_are_traceable:
                    raise ConflictError(
                        f"status {status} requires the latest eligible score to cite "
                        "current, traceable evidence"
                    )
                assert isinstance(evidence_ids, list)
                placeholders = ",".join("?" for _ in evidence_ids)
                active_evidence = connection.execute(
                    f"""
                    SELECT COUNT(*) AS count FROM evidence
                    WHERE opportunity_id = ?
                      AND id IN ({placeholders})
                      AND expires_at IS NOT NULL
                      AND expires_at > ?
                    """,
                    (existing["id"], *evidence_ids, _utc_now()),
                ).fetchone()
                if active_evidence is None or int(active_evidence["count"]) != len(
                    evidence_ids
                ):
                    raise ConflictError(
                        f"status {status} requires the latest eligible score to cite "
                        "current, traceable evidence"
                    )
            connection.execute(
                "UPDATE opportunities SET status = ?, updated_at = ? WHERE id = ?",
                (status, _utc_now(), existing["id"]),
            )
            self._write_audit(
                connection,
                event_type="opportunity.status_changed",
                actor=actor,
                entity_type="opportunity",
                entity_id=existing["id"],
                action="set_status",
                details={"from": existing["status"], "to": status},
            )
            row = connection.execute(
                "SELECT * FROM opportunities WHERE id = ?", (existing["id"],)
            ).fetchone()
        return dict(row)

    def add_evidence(
        self,
        opportunity: str | int,
        *,
        criterion: str,
        claim: str,
        source_uri: str,
        source_type: str = "public_web",
        strength: str = "moderate",
        rating: float = 0.5,
        confidence: float = 0.7,
        observed_at: str | date | datetime | None = None,
        expires_at: str | date | datetime | None = None,
        notes: str = "",
        actor: str = "company_os",
    ) -> dict[str, Any]:
        criterion = _require_text("criterion", criterion)
        claim = _require_text("claim", claim)
        source_uri = _require_text("source_uri", source_uri)
        if strength not in EVIDENCE_STRENGTHS:
            raise ValidationError(f"invalid evidence strength: {strength}")
        rating = _unit_value("rating", rating)
        confidence = _unit_value("confidence", confidence)
        observed = _normalize_timestamp(observed_at, default_now=True)
        expiry = _normalize_timestamp(expires_at)
        if expiry is None:
            raise ValidationError(
                "expires_at is required so every evidence claim has a revalidation date"
            )
        assert observed is not None
        if observed > _utc_now():
            raise ValidationError("observed_at cannot be in the future")
        if expiry <= observed:
            raise ValidationError("expires_at must be later than observed_at")
        with self._transaction() as connection:
            opportunity_row = self._resolve_opportunity(connection, opportunity)
            cursor = connection.execute(
                """
                INSERT INTO evidence(
                    opportunity_id, criterion, claim, source_uri, source_type,
                    strength, rating, confidence, observed_at, expires_at, notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    opportunity_row["id"],
                    criterion,
                    claim,
                    source_uri,
                    source_type.strip() or "public_web",
                    strength,
                    rating,
                    confidence,
                    observed,
                    expiry,
                    notes.strip(),
                    _utc_now(),
                ),
            )
            evidence_id = int(cursor.lastrowid)
            self._write_audit(
                connection,
                event_type="evidence.added",
                actor=actor,
                entity_type="evidence",
                entity_id=evidence_id,
                action="add",
                details={
                    "opportunity_id": opportunity_row["id"],
                    "criterion": criterion,
                    # Keep the immutable audit useful without copying a URL
                    # that may contain private paths or query credentials.
                    "source_fingerprint": hashlib.sha256(
                        source_uri.encode("utf-8")
                    ).hexdigest(),
                    "expires_at": expiry,
                },
            )
            row = connection.execute("SELECT * FROM evidence WHERE id = ?", (evidence_id,)).fetchone()
        return dict(row)

    def list_evidence(
        self,
        opportunity: str | int | None = None,
        *,
        include_expired: bool = False,
    ) -> list[dict[str, Any]]:
        self.initialize()
        with self._connection() as connection:
            clauses: list[str] = []
            parameters: list[Any] = []
            if opportunity is not None:
                opportunity_row = self._resolve_opportunity(connection, opportunity)
                clauses.append("opportunity_id = ?")
                parameters.append(opportunity_row["id"])
            if not include_expired:
                clauses.append("(expires_at IS NULL OR expires_at > ?)")
                parameters.append(_utc_now())
            where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            rows = connection.execute(
                f"SELECT * FROM evidence {where} ORDER BY observed_at DESC, id DESC", parameters
            ).fetchall()
        return [dict(row) for row in rows]

    def save_score(
        self,
        opportunity: str | int,
        score: MarketVoidScore,
        *,
        inputs: Mapping[str, Any] | None = None,
        actor: str = "company_os",
    ) -> dict[str, Any]:
        scored_at = _utc_now()
        score_dict = score.to_dict()
        inputs_json = json.dumps(inputs or {}, sort_keys=True, default=str)
        result_json = json.dumps(score_dict, sort_keys=True)
        with self._transaction() as connection:
            opportunity_row = self._resolve_opportunity(connection, opportunity)
            cursor = connection.execute(
                """
                INSERT INTO opportunity_scores(
                    opportunity_id, base_score, penalty_score, final_score,
                    eligible_for_advancement, inputs_json, result_json, scored_at, scored_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    opportunity_row["id"],
                    score.base_score,
                    score.penalty_score,
                    score.final_score,
                    int(score.eligible_for_advancement),
                    inputs_json,
                    result_json,
                    scored_at,
                    actor,
                ),
            )
            score_id = int(cursor.lastrowid)
            connection.execute(
                "UPDATE opportunities SET latest_score = ?, last_scored_at = ?, updated_at = ? WHERE id = ?",
                (score.final_score, scored_at, scored_at, opportunity_row["id"]),
            )
            self._write_audit(
                connection,
                event_type="opportunity.scored",
                actor=actor,
                entity_type="opportunity_score",
                entity_id=score_id,
                action="score",
                details={
                    "opportunity_id": opportunity_row["id"],
                    "final_score": score.final_score,
                    "eligible": score.eligible_for_advancement,
                },
            )
            row = connection.execute(
                "SELECT * FROM opportunity_scores WHERE id = ?", (score_id,)
            ).fetchone()
        result = dict(row)
        result["inputs"] = json.loads(result.pop("inputs_json"))
        result["result"] = json.loads(result.pop("result_json"))
        result["eligible_for_advancement"] = bool(result["eligible_for_advancement"])
        return result

    def latest_score(self, opportunity: str | int) -> dict[str, Any] | None:
        self.initialize()
        with self._connection() as connection:
            opportunity_row = self._resolve_opportunity(connection, opportunity)
            row = connection.execute(
                """SELECT * FROM opportunity_scores WHERE opportunity_id = ?
                   ORDER BY scored_at DESC, id DESC LIMIT 1""",
                (opportunity_row["id"],),
            ).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["inputs"] = json.loads(result.pop("inputs_json"))
        result["result"] = json.loads(result.pop("result_json"))
        result["eligible_for_advancement"] = bool(result["eligible_for_advancement"])
        return result

    def request_approval(
        self,
        *,
        action: str,
        rationale: str,
        risk: str = "",
        estimated_cost_cents: int = 0,
        reversibility: str = "reversible",
        approval_class: ApprovalClass | str | None = None,
        requested_by: str = "company_os",
        expires_at: str | date | datetime | None = None,
        decision_packet: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        action = _require_text("action", action)
        rationale = _require_text("rationale", rationale)
        requested_by = _require_text("requested_by", requested_by)
        estimated_cost_cents = _non_negative_cents(
            "estimated_cost_cents", estimated_cost_cents
        )
        policy_floor = classify_action(
            ActionRequest(
                action=action,
                estimated_cost_cents=estimated_cost_cents,
                external=True,
                reversible=reversibility.strip().lower() == "reversible",
                risk_level="high" if risk.strip().lower() in {"high", "critical"} else "medium",
            )
        )
        if approval_class is None:
            inferred = policy_floor
        else:
            try:
                requested_class = ApprovalClass(approval_class)
            except (TypeError, ValueError) as exc:
                raise ValidationError(f"invalid approval class: {approval_class}") from exc
            class_rank = {
                ApprovalClass.AUTO_ALLOWED: 0,
                ApprovalClass.POLICY_GATED: 1,
                ApprovalClass.CEO_APPROVAL_REQUIRED: 2,
            }
            # A caller may request stricter review, but never downgrade the
            # executable policy's classification.
            inferred = max(
                (policy_floor, requested_class), key=class_rank.__getitem__
            )
        now = _utc_now()
        normalized_expiry = _normalize_timestamp(expires_at)
        if normalized_expiry is None:
            raise ValidationError("expires_at is required for every approval request")
        if normalized_expiry <= now:
            raise ValidationError("expires_at must be in the future")
        normalized_packet: dict[str, str] = {}
        packet_digest = ""
        if decision_packet:
            normalized_packet, packet_digest = normalize_owner_decision_packet(
                decision_packet
            )
            if normalized_packet["exact_action"].casefold() != action.casefold():
                raise ValidationError(
                    "owner decision packet exact_action must match the approval action"
                )
            if normalized_expiry > normalized_packet["expiry"]:
                raise ValidationError(
                    "approval expiry cannot exceed the owner decision packet expiry"
                )
        with self._transaction() as connection:
            cursor = connection.execute(
                """
                INSERT INTO approvals(
                    action, rationale, risk, estimated_cost_cents, reversibility,
                    approval_class, status, requested_by, requested_at, expires_at,
                    decision_packet_json, packet_digest
                ) VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?)
                """,
                (
                    action,
                    rationale,
                    risk.strip(),
                    estimated_cost_cents,
                    reversibility.strip() or "reversible",
                    inferred.value,
                    requested_by,
                    now,
                    normalized_expiry,
                    json.dumps(
                        normalized_packet, sort_keys=True, separators=(",", ":")
                    ),
                    packet_digest,
                ),
            )
            approval_id = int(cursor.lastrowid)
            self._write_audit(
                connection,
                event_type="approval.requested",
                actor=requested_by,
                entity_type="approval",
                entity_id=approval_id,
                action="request",
                details={
                    "action": action,
                    "approval_class": inferred.value,
                    "estimated_cost_cents": estimated_cost_cents,
                    "packet_digest": packet_digest,
                    "packet_complete": bool(packet_digest),
                },
            )
            row = connection.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone()
        return dict(row)

    def list_approvals(self, status: str | None = None) -> list[dict[str, Any]]:
        self.expire_approvals()
        self.initialize()
        if status is not None and status not in APPROVAL_STATUSES:
            raise ValidationError(f"invalid approval status: {status}")
        with self._connection() as connection:
            if status is None:
                rows = connection.execute(
                    "SELECT * FROM approvals ORDER BY requested_at DESC, id DESC"
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM approvals WHERE status = ? ORDER BY requested_at DESC, id DESC",
                    (status,),
                ).fetchall()
        return [dict(row) for row in rows]

    def get_approval(self, approval_id: int) -> dict[str, Any]:
        self.expire_approvals()
        self.initialize()
        with self._connection() as connection:
            row = connection.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone()
        if row is None:
            raise NotFoundError(f"approval not found: {approval_id}")
        return dict(row)

    def decide_approval(
        self,
        approval_id: int,
        *,
        decision: str,
        decided_by: str,
        notes: str = "",
    ) -> dict[str, Any]:
        self.expire_approvals()
        decision = decision.lower()
        if decision not in {"approved", "rejected"}:
            raise ValidationError("approval decision must be approved or rejected")
        decided_by = _require_text("decided_by", decided_by)
        with self._transaction() as connection:
            existing = connection.execute(
                "SELECT * FROM approvals WHERE id = ?", (approval_id,)
            ).fetchone()
            if existing is None:
                raise NotFoundError(f"approval not found: {approval_id}")
            if existing["status"] != "pending":
                raise ConflictError(f"approval {approval_id} is already {existing['status']}")
            if decision == "approved" and (
                decided_by.strip().casefold() == str(existing["requested_by"]).strip().casefold()
            ):
                raise ValidationError("the requester cannot approve its own gated action")
            if (
                decision == "approved"
                and existing["approval_class"]
                == ApprovalClass.CEO_APPROVAL_REQUIRED.value
            ):
                if decided_by != "kaleb_ceo":
                    raise ConflictError(
                        "CEO-class approval must be decided by the owner identity"
                    )
                try:
                    packet = json.loads(existing["decision_packet_json"])
                    normalized_packet, packet_digest = normalize_owner_decision_packet(
                        packet
                    )
                except (TypeError, ValueError, json.JSONDecodeError, ValidationError) as exc:
                    raise ConflictError(
                        "CEO-class approval requires a complete valid owner decision packet"
                    ) from exc
                if not hmac.compare_digest(
                    str(existing["packet_digest"]), packet_digest
                ):
                    raise ConflictError("owner decision packet digest does not match")
                if existing["expires_at"] > normalized_packet["expiry"]:
                    raise ConflictError(
                        "approval expiry exceeds the owner decision packet expiry"
                    )
            if (
                decision == "approved"
                and existing["expires_at"] is not None
                and str(existing["expires_at"]) <= _utc_now()
            ):
                raise ConflictError(f"approval {approval_id} has expired and cannot be approved")
            now = _utc_now()
            connection.execute(
                """UPDATE approvals SET status = ?, decided_by = ?, decided_at = ?, decision_notes = ?
                   WHERE id = ?""",
                (decision, decided_by, now, notes.strip(), approval_id),
            )
            self._write_audit(
                connection,
                event_type=f"approval.{decision}",
                actor=decided_by,
                entity_type="approval",
                entity_id=approval_id,
                action=decision,
                details={
                    "requested_by": existing["requested_by"],
                    "action": existing["action"],
                    "packet_digest": existing["packet_digest"],
                },
            )
            row = connection.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone()
        return dict(row)

    def find_approval_for_action(self, action: str) -> dict[str, Any] | None:
        self.expire_approvals()
        self.initialize()
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT * FROM approvals
                WHERE lower(action) = lower(?) AND status = 'approved'
                  AND expires_at > ?
                ORDER BY decided_at DESC, id DESC LIMIT 1
                """,
                (action, _utc_now()),
            ).fetchone()
        return _row_dict(row)

    def expire_approvals(self, *, actor: str = "company_os") -> int:
        """Mark elapsed pending or approved grants expired and audit the transition."""

        now = _utc_now()
        expired_count = 0
        with self._transaction() as connection:
            rows = connection.execute(
                """
                SELECT id, action, status FROM approvals
                WHERE status IN ('pending', 'approved')
                  AND (expires_at IS NULL OR expires_at <= ?)
                ORDER BY id
                """,
                (now,),
            ).fetchall()
            for row in rows:
                connection.execute(
                    "UPDATE approvals SET status = 'expired', decided_at = ? WHERE id = ?",
                    (now, row["id"]),
                )
                self._write_audit(
                    connection,
                    event_type="approval.expired",
                    actor=actor,
                    entity_type="approval",
                    entity_id=row["id"],
                    action="expire",
                    details={"action": row["action"], "from": row["status"]},
                )
                expired_count += 1
        return expired_count

    def create_experiment(
        self,
        opportunity: str | int,
        *,
        name: str,
        hypothesis: str,
        method: str,
        success_metric: str,
        kill_metric: str,
        status: str = "planned",
        planned_cost_cents: int = 0,
        actor: str = "company_os",
    ) -> dict[str, Any]:
        if status not in EXPERIMENT_STATUSES:
            raise ValidationError(f"invalid experiment status: {status}")
        planned_cost_cents = _non_negative_cents(
            "planned_cost_cents", planned_cost_cents
        )
        fields = {
            "name": _require_text("name", name),
            "hypothesis": _require_text("hypothesis", hypothesis),
            "method": _require_text("method", method),
            "success_metric": _require_text("success_metric", success_metric),
            "kill_metric": _require_text("kill_metric", kill_metric),
        }
        now = _utc_now()
        with self._transaction() as connection:
            opportunity_row = self._resolve_opportunity(connection, opportunity)
            cursor = connection.execute(
                """
                INSERT INTO experiments(
                    opportunity_id, name, hypothesis, method, success_metric, kill_metric,
                    status, planned_cost_cents, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    opportunity_row["id"],
                    fields["name"],
                    fields["hypothesis"],
                    fields["method"],
                    fields["success_metric"],
                    fields["kill_metric"],
                    status,
                    planned_cost_cents,
                    now,
                    now,
                ),
            )
            experiment_id = int(cursor.lastrowid)
            self._write_audit(
                connection,
                event_type="experiment.created",
                actor=actor,
                entity_type="experiment",
                entity_id=experiment_id,
                action="create",
                details={"opportunity_id": opportunity_row["id"], "status": status},
            )
            row = connection.execute(
                "SELECT * FROM experiments WHERE id = ?", (experiment_id,)
            ).fetchone()
        return dict(row)

    def list_experiments(self, status: str | None = None) -> list[dict[str, Any]]:
        self.initialize()
        if status is not None and status not in EXPERIMENT_STATUSES:
            raise ValidationError(f"invalid experiment status: {status}")
        with self._connection() as connection:
            if status is None:
                rows = connection.execute(
                    "SELECT * FROM experiments ORDER BY created_at DESC, id DESC"
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM experiments WHERE status = ? ORDER BY created_at DESC, id DESC",
                    (status,),
                ).fetchall()
        return [dict(row) for row in rows]

    def record_decision(
        self,
        *,
        title: str,
        decision: str,
        rationale: str,
        decided_by: str,
        opportunity: str | int | None = None,
        experiment_id: int | None = None,
        evidence_summary: str = "",
        decision_type: str = "operating",
    ) -> dict[str, Any]:
        title = _require_text("title", title)
        decision = _require_text("decision", decision)
        rationale = _require_text("rationale", rationale)
        decided_by = _require_text("decided_by", decided_by)
        with self._transaction() as connection:
            opportunity_id = None
            if opportunity is not None:
                opportunity_id = int(self._resolve_opportunity(connection, opportunity)["id"])
            if experiment_id is not None:
                experiment = self._resolve_experiment(connection, experiment_id)
                if opportunity_id is not None and experiment["opportunity_id"] != opportunity_id:
                    raise ValidationError("experiment does not belong to the selected opportunity")
                opportunity_id = opportunity_id or int(experiment["opportunity_id"])
            cursor = connection.execute(
                """
                INSERT INTO decisions(
                    opportunity_id, experiment_id, title, decision, rationale,
                    evidence_summary, decision_type, decided_by, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    opportunity_id,
                    experiment_id,
                    title,
                    decision,
                    rationale,
                    evidence_summary.strip(),
                    decision_type.strip() or "operating",
                    decided_by,
                    _utc_now(),
                ),
            )
            decision_id = int(cursor.lastrowid)
            self._write_audit(
                connection,
                event_type="decision.recorded",
                actor=decided_by,
                entity_type="decision",
                entity_id=decision_id,
                action="record",
                details={"decision": decision, "opportunity_id": opportunity_id},
            )
            row = connection.execute("SELECT * FROM decisions WHERE id = ?", (decision_id,)).fetchone()
        return dict(row)

    def list_decisions(self, *, limit: int = 20) -> list[dict[str, Any]]:
        self.initialize()
        if limit < 1:
            raise ValidationError("limit must be positive")
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM decisions ORDER BY created_at DESC, id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]

    def record_cost(
        self,
        *,
        amount_cents: int,
        description: str,
        currency: str = "USD",
        cost_type: str = "direct",
        status: str = "incurred",
        opportunity: str | int | None = None,
        experiment_id: int | None = None,
        vendor: str = "",
        occurred_at: str | date | datetime | None = None,
        source_reference: str = "",
        actor: str = "finance_control",
    ) -> dict[str, Any]:
        amount_cents = _non_negative_cents("amount_cents", amount_cents)
        if status not in {"estimated", "committed", "incurred", "paid", "void"}:
            raise ValidationError(f"invalid cost status: {status}")
        description = _require_text("description", description)
        currency = _currency_code(currency)
        source_reference = source_reference.strip()
        if status in {"incurred", "paid"} and not source_reference:
            raise ValidationError(
                "source_reference is required for incurred or paid costs"
            )
        normalized_occurred_at = _normalize_timestamp(occurred_at, default_now=True)
        assert normalized_occurred_at is not None
        if status in {"incurred", "paid"} and normalized_occurred_at > _utc_now():
            raise ValidationError("actual cost occurred_at cannot be in the future")
        with self._transaction() as connection:
            opportunity_id = None
            if opportunity is not None:
                opportunity_id = int(self._resolve_opportunity(connection, opportunity)["id"])
            if experiment_id is not None:
                experiment = self._resolve_experiment(connection, experiment_id)
                if opportunity_id is not None and experiment["opportunity_id"] != opportunity_id:
                    raise ValidationError("experiment does not belong to the selected opportunity")
                opportunity_id = opportunity_id or int(experiment["opportunity_id"])
            try:
                cursor = connection.execute(
                    """
                    INSERT INTO costs(
                        opportunity_id, experiment_id, amount_cents, currency, cost_type,
                        status, description, vendor, occurred_at, source_reference, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        opportunity_id,
                        experiment_id,
                        amount_cents,
                        currency,
                        cost_type.strip() or "direct",
                        status,
                        description,
                        vendor.strip(),
                        normalized_occurred_at,
                        source_reference,
                        _utc_now(),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ConflictError(
                    f"cost source_reference already recorded for {currency}: {source_reference}"
                ) from exc
            cost_id = int(cursor.lastrowid)
            self._write_audit(
                connection,
                event_type="cost.recorded",
                actor=actor,
                entity_type="cost",
                entity_id=cost_id,
                action="record",
                details={"amount_cents": amount_cents, "currency": currency, "status": status},
            )
            row = connection.execute("SELECT * FROM costs WHERE id = ?", (cost_id,)).fetchone()
        return dict(row)

    def record_revenue(
        self,
        *,
        amount_cents: int,
        description: str,
        currency: str = "USD",
        entry_type: str = "revenue",
        status: str = "realized",
        opportunity: str | int | None = None,
        experiment_id: int | None = None,
        occurred_at: str | date | datetime | None = None,
        external_reference: str = "",
        notes: str = "",
        actor: str = "finance_control",
    ) -> dict[str, Any]:
        amount_cents = _non_negative_cents("amount_cents", amount_cents)
        if entry_type not in {"revenue", "refund", "projection"}:
            raise ValidationError(f"invalid revenue entry_type: {entry_type}")
        if status not in {"projected", "realized", "cleared", "void"}:
            raise ValidationError(f"invalid revenue status: {status}")
        if entry_type == "projection" and status != "projected":
            raise ValidationError("projection entries must have projected status")
        if entry_type != "projection" and status == "projected":
            raise ValidationError("projected status requires projection entry_type")
        description = _require_text("description", description)
        currency = _currency_code(currency)
        external_reference = external_reference.strip()
        if entry_type in {"revenue", "refund"} and status in {"realized", "cleared"}:
            if not external_reference:
                raise ValidationError(
                    "external_reference is required for realized or cleared revenue/refunds"
                )
        normalized_occurred_at = _normalize_timestamp(occurred_at, default_now=True)
        assert normalized_occurred_at is not None
        if (
            entry_type in {"revenue", "refund"}
            and status in {"realized", "cleared"}
            and normalized_occurred_at > _utc_now()
        ):
            raise ValidationError("actual revenue/refund occurred_at cannot be in the future")
        with self._transaction() as connection:
            opportunity_id = None
            if opportunity is not None:
                opportunity_id = int(self._resolve_opportunity(connection, opportunity)["id"])
            if experiment_id is not None:
                experiment = self._resolve_experiment(connection, experiment_id)
                if opportunity_id is not None and experiment["opportunity_id"] != opportunity_id:
                    raise ValidationError("experiment does not belong to the selected opportunity")
                opportunity_id = opportunity_id or int(experiment["opportunity_id"])
            try:
                cursor = connection.execute(
                    """
                    INSERT INTO revenues(
                        opportunity_id, experiment_id, amount_cents, currency, entry_type,
                        status, description, occurred_at, external_reference, notes, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        opportunity_id,
                        experiment_id,
                        amount_cents,
                        currency,
                        entry_type,
                        status,
                        description,
                        normalized_occurred_at,
                        external_reference,
                        notes.strip(),
                        _utc_now(),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ConflictError(
                    "revenue external_reference already recorded for "
                    f"{entry_type}/{currency}: {external_reference}"
                ) from exc
            revenue_id = int(cursor.lastrowid)
            self._write_audit(
                connection,
                event_type="revenue.recorded",
                actor=actor,
                entity_type="revenue",
                entity_id=revenue_id,
                action="record",
                details={
                    "amount_cents": amount_cents,
                    "currency": currency,
                    "entry_type": entry_type,
                    "status": status,
                },
            )
            row = connection.execute("SELECT * FROM revenues WHERE id = ?", (revenue_id,)).fetchone()
        return dict(row)

    def set_cost_status(
        self,
        cost_id: int,
        status: str,
        *,
        source_reference: str | None = None,
        occurred_at: str | date | datetime | None = None,
        actor: str = "finance_control",
    ) -> dict[str, Any]:
        """Advance a cost through its lifecycle without double-recording it."""

        transitions = {
            "estimated": {"committed", "incurred", "paid", "void"},
            "committed": {"incurred", "paid", "void"},
            "incurred": {"paid", "void"},
            "paid": {"void"},
            "void": set(),
        }
        if status not in transitions:
            raise ValidationError(f"invalid cost status: {status}")
        with self._transaction() as connection:
            existing = connection.execute(
                "SELECT * FROM costs WHERE id = ?", (cost_id,)
            ).fetchone()
            if existing is None:
                raise NotFoundError(f"cost not found: {cost_id}")
            if status not in transitions[str(existing["status"])]:
                raise ConflictError(
                    f"cost {cost_id} cannot transition from {existing['status']} to {status}"
                )
            reference = (
                source_reference.strip()
                if source_reference is not None
                else str(existing["source_reference"])
            )
            if existing["source_reference"] and source_reference is not None:
                if reference != existing["source_reference"]:
                    raise ValidationError("an existing cost source_reference cannot be replaced")
            if status in {"incurred", "paid"} and not reference:
                raise ValidationError(
                    "source_reference is required before a cost becomes incurred or paid"
                )
            normalized_occurred_at = (
                _normalize_timestamp(occurred_at)
                if occurred_at is not None
                else str(existing["occurred_at"])
            )
            if status in {"incurred", "paid"} and (
                normalized_occurred_at is None
                or normalized_occurred_at > _utc_now()
            ):
                raise ValidationError(
                    "actual cost occurred_at cannot be in the future; provide the "
                    "actual occurrence time when advancing a future estimate"
                )
            try:
                connection.execute(
                    """UPDATE costs
                       SET status = ?, source_reference = ?, occurred_at = ?
                       WHERE id = ?""",
                    (status, reference, normalized_occurred_at, cost_id),
                )
            except sqlite3.IntegrityError as exc:
                raise ConflictError(
                    f"cost source_reference already recorded for {existing['currency']}: {reference}"
                ) from exc
            self._write_audit(
                connection,
                event_type="cost.status_changed",
                actor=actor,
                entity_type="cost",
                entity_id=cost_id,
                action="set_status",
                details={
                    "from": existing["status"],
                    "to": status,
                    "occurred_at": normalized_occurred_at,
                },
            )
            row = connection.execute(
                "SELECT * FROM costs WHERE id = ?", (cost_id,)
            ).fetchone()
        return dict(row)

    def set_revenue_status(
        self,
        revenue_id: int,
        status: str,
        *,
        actor: str = "finance_control",
    ) -> dict[str, Any]:
        """Advance realized revenue to cleared, or void a mistaken entry."""

        transitions = {
            "projected": {"void"},
            "realized": {"cleared", "void"},
            "cleared": {"void"},
            "void": set(),
        }
        if status not in transitions:
            raise ValidationError(f"invalid revenue status: {status}")
        with self._transaction() as connection:
            existing = connection.execute(
                "SELECT * FROM revenues WHERE id = ?", (revenue_id,)
            ).fetchone()
            if existing is None:
                raise NotFoundError(f"revenue not found: {revenue_id}")
            if status not in transitions[str(existing["status"])]:
                raise ConflictError(
                    f"revenue {revenue_id} cannot transition from "
                    f"{existing['status']} to {status}"
                )
            connection.execute(
                "UPDATE revenues SET status = ? WHERE id = ?", (status, revenue_id)
            )
            self._write_audit(
                connection,
                event_type="revenue.status_changed",
                actor=actor,
                entity_type="revenue",
                entity_id=revenue_id,
                action="set_status",
                details={"from": existing["status"], "to": status},
            )
            row = connection.execute(
                "SELECT * FROM revenues WHERE id = ?", (revenue_id,)
            ).fetchone()
        return dict(row)

    def record_risk(
        self,
        *,
        category: str,
        title: str,
        description: str,
        likelihood: int,
        impact: int,
        opportunity: str | int | None = None,
        status: str = "open",
        mitigation: str = "",
        owner: str = "",
        review_at: str | date | datetime | None = None,
        actor: str = "risk_control",
    ) -> dict[str, Any]:
        if (
            type(likelihood) is not int
            or type(impact) is not int
            or likelihood not in range(1, 6)
            or impact not in range(1, 6)
        ):
            raise ValidationError("likelihood and impact must be integers from 1 to 5")
        if status not in {"open", "mitigating", "accepted", "closed"}:
            raise ValidationError(f"invalid risk status: {status}")
        now = _utc_now()
        with self._transaction() as connection:
            opportunity_id = None
            if opportunity is not None:
                opportunity_id = int(self._resolve_opportunity(connection, opportunity)["id"])
            cursor = connection.execute(
                """
                INSERT INTO risks(
                    opportunity_id, category, title, description, likelihood, impact,
                    status, mitigation, owner, review_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    opportunity_id,
                    _require_text("category", category),
                    _require_text("title", title),
                    _require_text("description", description),
                    likelihood,
                    impact,
                    status,
                    mitigation.strip(),
                    owner.strip(),
                    _normalize_timestamp(review_at),
                    now,
                    now,
                ),
            )
            risk_id = int(cursor.lastrowid)
            self._write_audit(
                connection,
                event_type="risk.recorded",
                actor=actor,
                entity_type="risk",
                entity_id=risk_id,
                action="record",
                details={"likelihood": likelihood, "impact": impact, "status": status},
            )
            row = connection.execute("SELECT * FROM risks WHERE id = ?", (risk_id,)).fetchone()
        return dict(row)

    def list_risks(self, status: str | None = None) -> list[dict[str, Any]]:
        self.initialize()
        if status is not None and status not in {"open", "mitigating", "accepted", "closed"}:
            raise ValidationError(f"invalid risk status: {status}")
        with self._connection() as connection:
            if status is None:
                rows = connection.execute(
                    "SELECT *, likelihood * impact AS severity FROM risks ORDER BY severity DESC, id"
                ).fetchall()
            else:
                rows = connection.execute(
                    """SELECT *, likelihood * impact AS severity FROM risks
                       WHERE status = ? ORDER BY severity DESC, id""",
                    (status,),
                ).fetchall()
        return [dict(row) for row in rows]

    def financial_summary(self) -> dict[str, dict[str, int]]:
        self.initialize()
        with self._connection() as connection:
            currencies = {
                row["currency"]
                for row in connection.execute(
                    "SELECT currency FROM costs UNION SELECT currency FROM revenues"
                )
            }
            summary: dict[str, dict[str, int]] = {}
            for currency in sorted(currencies or {"USD"}):
                revenue = connection.execute(
                    """
                    SELECT
                      COALESCE(SUM(CASE WHEN entry_type = 'revenue' AND status IN ('realized','cleared') THEN amount_cents ELSE 0 END), 0) AS actual_revenue,
                      COALESCE(SUM(CASE WHEN entry_type = 'revenue' AND status = 'cleared' THEN amount_cents ELSE 0 END), 0) AS cleared_revenue,
                      COALESCE(SUM(CASE WHEN entry_type = 'refund' AND status IN ('realized','cleared') THEN amount_cents ELSE 0 END), 0) AS refunds,
                      COALESCE(SUM(CASE WHEN entry_type = 'projection' AND status = 'projected' THEN amount_cents ELSE 0 END), 0) AS projected_revenue
                    FROM revenues WHERE currency = ?
                    """,
                    (currency,),
                ).fetchone()
                costs = connection.execute(
                    """
                    SELECT
                      COALESCE(SUM(CASE WHEN status IN ('incurred','paid') THEN amount_cents ELSE 0 END), 0) AS actual_costs,
                      COALESCE(SUM(CASE WHEN status = 'incurred' THEN amount_cents ELSE 0 END), 0) AS incurred_costs,
                      COALESCE(SUM(CASE WHEN status = 'paid' THEN amount_cents ELSE 0 END), 0) AS paid_costs,
                      COALESCE(SUM(CASE WHEN status IN ('estimated','committed') THEN amount_cents ELSE 0 END), 0) AS estimated_costs
                    FROM costs WHERE currency = ?
                    """,
                    (currency,),
                ).fetchone()
                actual_revenue = int(revenue["actual_revenue"])
                refunds = int(revenue["refunds"])
                actual_costs = int(costs["actual_costs"])
                cleared_revenue = int(revenue["cleared_revenue"])
                paid_costs = int(costs["paid_costs"])
                summary[currency] = {
                    "actual_revenue_cents": actual_revenue,
                    "cleared_revenue_cents": cleared_revenue,
                    "refunds_cents": refunds,
                    "actual_costs_cents": actual_costs,
                    "incurred_costs_cents": int(costs["incurred_costs"]),
                    "paid_costs_cents": paid_costs,
                    "estimated_costs_cents": int(costs["estimated_costs"]),
                    "projected_revenue_cents": int(revenue["projected_revenue"]),
                    "net_cash_contribution_cents": cleared_revenue - refunds - paid_costs,
                }
        return summary

    def status(self, *, repo_root: str | Path | None = None) -> dict[str, Any]:
        self.expire_approvals()
        self.initialize()
        with self._connection() as connection:
            table_counts = {}
            for table in (
                "opportunities",
                "evidence",
                "experiments",
                "approvals",
                "decisions",
                "costs",
                "revenues",
                "risks",
                "audit_events",
                "departments",
                "roles",
                "workers",
                "objectives",
                "work_items",
                "operating_cycles",
                "control_reviews",
                "escalations",
                "metric_events",
                "incidents",
            ):
                table_counts[table] = int(
                    connection.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()["count"]
                )
            pending_approvals = int(
                connection.execute(
                    "SELECT COUNT(*) AS count FROM approvals WHERE status = 'pending'"
                ).fetchone()["count"]
            )
            stale_evidence = int(
                connection.execute(
                    "SELECT COUNT(*) AS count FROM evidence WHERE expires_at IS NOT NULL AND expires_at <= ?",
                    (_utc_now(),),
                ).fetchone()["count"]
            )
        return {
            "database": self.db_path,
            "schema_version": self.schema_version(),
            "paused": is_paused(repo_root),
            "counts": table_counts,
            "pending_approvals": pending_approvals,
            "stale_evidence": stale_evidence,
            "financials": self.financial_summary(),
        }

    def list_audit_events(self, *, limit: int = 100) -> list[dict[str, Any]]:
        self.initialize()
        if limit < 1:
            raise ValidationError("limit must be positive")
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM audit_events ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        results = []
        for row in rows:
            item = dict(row)
            item["details"] = json.loads(item.pop("detail_json"))
            results.append(item)
        return results

    def verify_audit_chain(self) -> tuple[bool, int | None]:
        """Verify audit ordering and hashes; return (valid, first_bad_event_id)."""

        self.initialize()
        with self._connection() as connection:
            rows: Sequence[sqlite3.Row] = connection.execute(
                "SELECT * FROM audit_events ORDER BY id"
            ).fetchall()
        previous_hash = "GENESIS"
        for row in rows:
            payload = "|".join(
                [
                    previous_hash,
                    row["event_type"],
                    row["actor"],
                    row["entity_type"],
                    row["entity_id"],
                    row["action"],
                    row["detail_json"],
                    row["created_at"],
                ]
            )
            expected = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            if row["previous_hash"] != previous_hash or row["event_hash"] != expected:
                return False, int(row["id"])
            previous_hash = row["event_hash"]
        return True, None
