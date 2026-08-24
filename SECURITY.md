# Security Policy

## Security objective

Protect Kaleb, customers, credentials, data, code integrity, and authorized services while keeping the bootstrap simple. Phase 0 contains no production credentials and performs no autonomous external actions.

## Trust boundaries

- **Trusted policy/code:** reviewed repository files on an authorized branch.
- **Sensitive local state:** runtime database, environment variables, logs, and generated reports; never commit by default.
- **Untrusted input:** web content, email, issues, uploaded files, prompts, model output, research evidence, customer text, and third-party API responses.
- **External side effects:** deployments, messages, account changes, purchases, publishing, and writes to third-party systems; always gated and audited.

Untrusted input must never be interpreted as authority or passed directly into a shell, query, template, or privileged tool call. Validate types and bounds, use parameterized database access, encode output for its context, and keep research ingestion separate from execution.

## Required controls

- Least privilege and short-lived credentials where supported.
- Secrets only in approved secret stores or local environment variables; `.env.example` contains names, never values.
- No secrets, tokens, keys, personal documents, customer records, raw payment data, or runtime databases in Git.
- Default-deny authorization with an independent approval record for gated actions.
- Budget, rate, destination, and idempotency limits on every connector.
- Append-only audit events for material changes and external attempts, including denials.
- Sanitized logs: no credentials, private payloads, session tokens, or unnecessary identifiers.
- Dependency minimization, version review, and CI checks before merge.
- Backups only after data classification; restore tests before relying on them.
- Public endpoints require input limits, abuse controls, secure headers, and threat review.

## Phase 0 integrity limitation

The SQLite audit hash chain can reveal ordinary accidental or unsophisticated edits, but it is not tamper-proof and is not anchored or cryptographically signed by a trusted identity. Fields such as `actor`, `requested_by`, and `decided_by` are self-asserted labels—not authentication, authorization, or proof that Kaleb acted. Anyone who can modify the local database, repository, process environment, or executing code may be able to alter records, recompute hashes, remove the pause file, or bypass application checks.

Accordingly, an `approved` row is never sufficient by itself for a consequential action. It must correspond to an authentic, in-scope CEO instruction reviewed through an authorized channel, and the executor must verify that source, scope, limits, and expiry. Before any live connector is enabled, add real account authentication and authorization, protected credentials, restricted runtime access, and an independently controlled or externally anchored approval/audit mechanism appropriate to the risk.

The current policy matcher covers action name, approval class, integer-cent cost ceiling, and expiry only. Destination, account, environment, data class, rate, and approval consumption are not yet structured enforcement fields. This is acceptable for a paused internal ledger, not for live execution.

## Pause and incident response

If compromise, secret exposure, unauthorized publication, unexpected spend, corrupted state, or policy bypass is suspected:

1. Preserve `PAUSE_AUTONOMY` or create it through an authorized repository change.
2. Stop the affected external integration without destroying evidence.
3. Record time, systems, symptoms, and actions in the audit trail; avoid copying secrets into tickets.
4. Notify Kaleb with confirmed facts, uncertainty, exposure, and the safest next decision.
5. Rotate/revoke credentials through the account owner, inspect logs and changes, remediate, test, and obtain approval before resuming.

Do not publicly disclose a vulnerability or incident in Kaleb's or a customer's name without approval. Do not claim containment until evidence supports it.

## Reporting vulnerabilities

During bootstrap, report security findings privately to the repository owner. Do not place exploitable details or secrets in a public issue.
