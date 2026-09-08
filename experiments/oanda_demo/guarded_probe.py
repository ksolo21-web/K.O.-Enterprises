"""Guarded successor to the Practice microprobe entry point.

Scan is read-only. Execute keeps the existing exact approval and plan-specific
permit, adds conservative sizing and fresh-signal checks, and claims a permit
before submission. No scheduler or automatic order retry is implemented.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
import sys
from typing import Any

from .forward_lab import ForwardPracticeClient, _load_permit, execute_plan
from .forward_probe import build_probe_plan
from .practice_risk import guard_probe_plan, RiskError
from .lab import LabError


def build_guarded_plan(client: ForwardPracticeClient) -> dict[str, Any]:
    plan = build_probe_plan(client)
    if not plan.get('eligible'):
        return plan
    now = datetime.now(timezone.utc)
    try:
        signal = datetime.fromisoformat(plan['signal_time'].replace('Z', '+00:00'))
        generated = datetime.fromisoformat(plan['generated_at'].replace('Z', '+00:00'))
        priced = datetime.fromisoformat(plan['current_price_time'].replace('Z', '+00:00'))
    except (KeyError, ValueError, TypeError):
        raise LabError('Invalid Practice plan timestamps.') from None
    if any(stamp.tzinfo is None for stamp in (signal, generated, priced)):
        raise LabError('Practice timestamps require timezones.')
    close_age = (now - signal - timedelta(hours=1)).total_seconds()
    if not 0 <= close_age <= 3900 or not -10 <= (now-priced).total_seconds() <= 120:
        return {**plan, 'eligible': False, 'reason': 'stale_completed_signal_or_price'}
    if not 0 <= (now-generated).total_seconds() <= 120:
        return {**plan, 'eligible': False, 'reason': 'plan_generation_too_old'}
    metadata = client.instrument_metadata()[plan['instrument']]
    try:
        return guard_probe_plan(plan, metadata['minimum_trade_size'])
    except RiskError as error:
        raise LabError(str(error)) from None


def execute_guarded(client: ForwardPracticeClient, plan: dict[str, Any], permit_path: str) -> dict[str, Any]:
    if not plan.get('eligible'):
        raise LabError('No eligible guarded Practice plan.')
    try:
        checked = guard_probe_plan(plan)
    except RiskError as error:
        raise LabError(str(error)) from None
    if checked != plan or not checked.get('eligible'):
        raise LabError('Practice risk plan was not fully guarded.')
    _load_permit(permit_path, checked)
    # Claim before the POST. Even an ambiguous failure cannot reuse this local
    # permit. This marker is not a cross-run broker idempotency guarantee.
    claim = Path(permit_path + '.claimed')
    try:
        with claim.open('x', encoding='utf-8') as handle:
            handle.write('Consumed for one Practice attempt; reconcile before a new permit.\n')
    except FileExistsError:
        raise LabError('Practice permit was already claimed; do not retry.') from None
    result = execute_plan(client, checked, permit_path)
    return {**result, 'risk_sizing_version': checked['risk_sizing_version'],
        'risk_limit_is_guaranteed': False,
        'risk_warning': checked['risk_warning']}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Guarded OANDA Practice microprobe.')
    parser.add_argument('command', choices=('scan', 'execute'))
    parser.add_argument('--output', required=True)
    parser.add_argument('--permit')
    args = parser.parse_args(argv)
    try:
        client = ForwardPracticeClient.from_environment()
        plan = build_guarded_plan(client)
        if args.command == 'execute':
            if not args.permit:
                raise LabError('A plan-specific Practice permit is required.')
            result = execute_guarded(client, plan, args.permit)
        else:
            result = plan
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result, indent=2, sort_keys=True)+'\n', encoding='utf-8')
        print('Guarded Practice step: '+str(result.get('reason', result.get('status'))))
        return 0
    except (LabError, OSError, json.JSONDecodeError) as error:
        print(str(error) if isinstance(error, LabError) else 'Guarded Practice step failed.', file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
