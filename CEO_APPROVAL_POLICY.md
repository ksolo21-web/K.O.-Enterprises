# CEO Approval Policy

Authority attaches to an exact action, scope, budget, environment, and expiry. Approval for one action is not reusable for a materially different action.

## AUTO_ALLOWED

Reversible, zero-cash, low-risk work inside an authorized repository:

- inspect repository files and approved local state;
- write code, tests, policies, analysis, and unpublished drafts;
- run local tests, static checks, migrations, and fixture-based simulations;
- conduct lawful research from public sources while respecting terms and access controls;
- add sourced evidence, score candidates, and generate internal reports;
- create branches, commits, issues, and pull requests for review;
- create routine truthful technical documentation covered by the authorization to build this public repository.

AUTO_ALLOWED does not permit a product launch, marketing claim, outreach, credential use, or external side effect merely because it can be initiated from a repository.

## POLICY_GATED

Allowed only under a written standing policy that names the environment, account, action, rate/cost ceiling, data class, audit requirements, and expiry:

- deploy to an already approved environment;
- publish through an already approved company-owned channel;
- call an approved API within a fixed usage and cost envelope;
- send a transactional message to an opted-in user;
- process a predefined operational remedy within an approved limit.

Absent every required control, treat the action as CEO_APPROVAL_REQUIRED.

## CEO_APPROVAL_REQUIRED

Explicit approval is required before:

- spending or committing money; changing billing; moving, investing, refunding, or reinvesting funds;
- opening, changing, or connecting bank, merchant, tax, advertising, domain, subscription, or financial accounts;
- accepting terms, signing a contract, filing a legal document, creating an entity, hiring, or making a regulated decision;
- using Kaleb's identity, signature, personal information, credentials, or voice;
- adding secrets, expanding permissions, connecting a new external system, or granting another actor access;
- customer/prospect outreach, marketing distribution, public launch announcements, production deployment, or material public claims;
- collecting personal data beyond low-risk operational telemetry, or collecting any sensitive data;
- setting live prices/payment terms, materially changing existing-customer terms, or enabling a payment rail;
- destructive migration, irreversible deletion, shutdown of a revenue asset, or other hard-to-reverse action;
- an exception to any root policy.

## Required approval packet

Use `docs/company/APPROVAL_PACKET_TEMPLATE.md`. At minimum state:

1. the exact requested action and actor;
2. the evidence-based reason and expected outcome;
3. cash cost and total resource cost, including model/API usage;
4. affected accounts, people, data, and public surfaces;
5. legal, security, privacy, operational, and reputation risks;
6. reversibility, rollback, monitoring, and stop conditions;
7. consequence of approval, rejection, and delay;
8. requested expiry and hard limits.

Approval must be an affirmative written record from an authentic CEO interaction. No response means no approval. Phase 0 database identity labels are self-asserted and do not authenticate Kaleb; an `approved` row cannot create authority by itself. The operating system records the decision for coordination, and the executor rechecks the authentic source, scope, limits, and expiry immediately before acting.

Phase 0's deterministic matcher enforces the canonical action string, approval class, maximum integer-cent cost, and expiry. It does not yet enforce structured destination/account/environment scope, data class, rate limits, one-time consumption, or cryptographic identity. No live connector may rely on the database row alone; those controls must be implemented and tested before Phase 4 execution.
