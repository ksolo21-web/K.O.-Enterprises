# Delegation Policy

## Rule

Delegation transfers a bounded duty, never ownership, identity, or constitutional authority. The grantor remains accountable and cannot delegate more authority than it holds.

## Required delegation fields

Every material delegation must identify:

- grantor and grantee active assignments;
- originating mandate, objective, and work order;
- exact action codes and affected resources;
- department, repository, product, environment, account, and destination scope;
- maximum decision class, risk, cash, compute, rate, and use count;
- effective time, expiry, review time, and revocation conditions;
- whether subdelegation is permitted; default is no;
- required reviewers and acceptance authority;
- expected output, acceptance criteria, and escalation target.

Free-text job titles, custom agent files, environment variables, and database actor labels are not delegation records.

## Invariants

1. A grant must be narrower than the grantor's current authority.
2. Owner-reserved and prohibited authority cannot be delegated by an agent.
3. Delegation follows the reporting line; cross-functional grants require both affected department leads or the President.
4. A specialist may receive execution authority, not approval of its own output.
5. Delegation never includes secrets, accounts, cash, or external side effects unless those are explicitly scoped by an authentic parent authorization.
6. Expired, revoked, suspended, exhausted, malformed, or ambiguous grants fail closed.
7. Subdelegation requires an explicit depth and scope; every child grant must be narrower.
8. Authority is rechecked at execution time. A valid grant yesterday is not proof of authority now.

## Sub-agent assignments

A manager may create a project-scoped sub-agent assignment for genuinely separable work. Each assignment must have one accountable manager, one work package, a TTL, a capacity ceiling, file or evidence ownership, and acceptance criteria. The child reports results to its manager; it does not issue lateral commands or contact the CEO.

When work finishes, fails, or is cancelled, close the assignment and release capacity. Persistent specialist profiles may be reused, but each run receives a new bounded assignment.

## Revocation and suspension

The grantor, an ancestor in the operating chain, the President, or an applicable control function may suspend a delegation. Revocation is mandatory after role suspension, scope conflict, policy violation, stale authority, incident containment, or repeated failure. Suspension is a safety action and does not authorize destructive cleanup.

## Delegation review

Department leads review active delegations during weekly operations. Internal Audit samples high-impact grants, nested grants, cross-functional grants, and grants close to a ceiling. Unused or stale grants are closed rather than kept as ambient authority.
