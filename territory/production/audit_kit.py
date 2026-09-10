#!/usr/bin/env python3
"""Re-run the candidate-tooling tests and record exact local code identities.
This internal software audit is not an independent real-card review.
"""
from pathlib import Path
import datetime
import hashlib
import io
import json
import os
import sys
import unittest

HERE=Path(__file__).resolve().parent

def main():
    sys.path.insert(0,str(HERE))
    from verify_originals import verify_installed
    before=verify_installed(HERE)
    log=io.StringIO()
    names=['test_engine','test_sealed','test_repair','test_privacy','test_readiness','test_transport','test_delivery','test_runtime_integration']
    suite=unittest.defaultTestLoader.loadTestsFromNames(names)
    result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    after=verify_installed(HERE)
    records={p.relative_to(HERE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
             for p in HERE.rglob('*.py') if 'vendor' not in p.relative_to(HERE).parts and '__pycache__' not in p.parts}
    report={'kind':'internal_software_review','date_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'source_integrity_before':before,'source_integrity_after':after,
            'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
            'skipped':len(result.skipped),'source_sha256':records,
            'software_tests_passed':result.wasSuccessful() and not result.skipped,
            'mandatory_real_card_checks_passed':False,'card_release_approved':False,
            'limits':['Not a model-review score','No actual territory card approved by this audit',
                      'Does not certify an unobserved remote deployment or private end-to-end run']}
    evidence=HERE/'evidence';evidence.mkdir(exist_ok=True)
    (evidence/'continuation-kit-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    (evidence/'continuation-kit-audit.txt').write_text(log.getvalue())
    print(json.dumps({k:report[k] for k in ['tests_run','failures','errors','skipped','software_tests_passed','card_release_approved']}))
    return 0 if report['software_tests_passed'] else 2

if __name__=='__main__':raise SystemExit(main())
