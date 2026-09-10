#!/usr/bin/env python3
"""Report evidence-backed readiness. Missing evidence never becomes approval."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL_DIGEST = '0533d74300e4f9bc367d675d4e64ffd073d50ff16a2b4096cc2e8a1cf8c96319'

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read_json(path: Path):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise ValueError('Duplicate JSON key')
            out[key] = value
        return out
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))

def source_check(home: Path) -> dict:
    from verify_originals import verify_capsule
    return verify_capsule(home)


def calibration_check(path: Path) -> dict:
    r = read_json(path)
    cases = r.get('cases', [])
    required = r.get('required')
    if type(required) is not int or required < 8 or len(cases) != required:
        raise ValueError('Incomplete calibration inventory')
    if r.get('completed') != required or r.get('passed') != required:
        raise ValueError('Calibration contains a failure or unfinished case')
    if len({c.get('id') for c in cases}) != required:
        raise ValueError('Duplicate calibration case')
    for case in cases:
        receipt = case.get('receipt', {})
        identity = receipt.get('identity', {})
        response = receipt.get('raw_response', {})
        expected = case.get('expected', {})
        result = receipt.get('result', {})
        if case.get('passed') is not True or receipt.get('kind') != 'actual_local_model_inference':
            raise ValueError('Missing actual independent inference')
        if identity.get('digest') != MODEL_DIGEST or identity.get('version') != '0.33.3':
            raise ValueError('Model/runtime identity changed')
        if response.get('done') is not True or response.get('done_reason') == 'length':
            raise ValueError('Truncated or unfinished inference')
        if not receipt.get('image_sha256') or not receipt.get('request_sha256'):
            raise ValueError('Inference input provenance missing')
        if not expected or any(type(v) is not bool or result.get(k) is not v for k,v in expected.items()):
            raise ValueError('Raw inference does not match case ground truth')
    return {'passed': True, 'cases': required, 'sha256': digest(path),
            'scope': 'synthetic calibration only; not real-card qualification'}

def report(home: Path = HERE) -> dict:
    checks = {}
    try:
        checks['original_sources'] = source_check(home)
    except Exception as error:
        checks['original_sources'] = {'passed': False, 'reason': str(error)}
    local = home / 'evidence/build-audit-local.json'
    try:
        audit = read_json(local)
        passed = type(audit.get('tests_run')) is int and audit['tests_run'] > 0
        passed = passed and all(audit.get(k) == 0 for k in ('failures', 'errors', 'skipped'))
        checks['recorded_software_tests'] = {'passed': bool(passed), 'evidence': str(local),
                                           'tests_run': audit.get('tests_run'), 'sha256': digest(local),
                                           'scope': 'recorded test run, not proof of later edits'}
    except Exception as error:
        checks['recorded_software_tests'] = {'passed': False, 'reason': str(error)}
    calibrations = []
    for path in sorted((home/'evidence').glob('systematic-*.json')):
        try:
            calibrations.append({'file': path.name, **calibration_check(path)})
        except Exception as error:
            calibrations.append({'file': path.name, 'passed': False, 'reason': str(error)})
    checks['synthetic_calibrations'] = calibrations
    # This is a requirements report, deliberately not a second release-gate implementation.
    # The original geographic and screenshot-evidence gates remain mandatory.
    pending = [
        'Read back the complete deployed branch and its hosted regression results.',
        'Qualify the critic on retained accepted and rejected real territory cards.',
        'Demonstrate a real encrypted input/output run, including recovery after interruption.',
        'Integrate the independent review/repair/retest/release cycle with every original gate.',
        'Run those original gates against the exact final PDF and current source evidence.'
    ]
    return {'kind': 'internal_evidence_inventory', 'checks': checks,
            'unattended_card_release_ready': False, 'real_cards_released': 0,
            'mandatory_unverified': pending, 'approval': 'NOT APPROVED'}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--inventory-only', action='store_true', help='Print inventory without representing a release check')
    args = parser.parse_args()
    value = report()
    text = json.dumps(value, indent=2, allow_nan=False) + '\n'
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding='utf-8')
    print(text, end='')
    return 0 if args.inventory_only else 2

if __name__ == '__main__':
    raise SystemExit(main())
