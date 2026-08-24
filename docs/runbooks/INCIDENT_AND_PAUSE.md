# Incident and Pause Runbook

## Trigger

Use this runbook for suspected unauthorized spend or publication, secret/data exposure, control bypass, false public claim, customer harm, corrupted state, audit failure, or unexpected external behavior.

## Contain

1. Preserve or create the global pause through an authorized repository change.
2. Stop the affected connector or assignment without destroying evidence.
3. Quarantine uncertain idempotency keys, credentials, artifacts, and outputs.
4. Continue only unrelated local inspection, reporting, testing, and remediation.

## Establish facts

Record time, reporter, affected system, confirmed behavior, uncertainty, accounts/data/people involved, last known-good state, relevant correlation IDs, and containment actions. Sanitize secrets and private data.

Do not claim containment, loss, exposure, customer impact, or root cause until evidence supports it.

## Route

Notify the President and applicable control lead. Notify Kaleb promptly when owner action is required for identity, accounts, credentials, money, legal obligations, customer/public notice, irreversible action, or critical risk acceptance.

## Recover

Identify root cause, remediate narrowly, rotate/revoke through the account owner when needed, reconcile external state, verify audit integrity, run regression/recovery tests, and obtain the required approval before resuming. Never delete evidence to make checks pass.

## Learn

Record control changes, tests, delegation or performance action, remaining risk, and the evidence required for closure. Resume only the affected scope and keep broader stops in place where uncertainty remains.
