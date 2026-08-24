# Authority Matrix

## Purpose

This matrix makes the corporate chain of command explicit. It governs who may decide, who may execute, which independent reviews can block, and when Kaleb must act as Owner and CEO.

Repository access, a custom agent profile, a task label, an actor string, or possession of a credential is never authority. Where the Company OS cannot enforce a required field, the affected action fails closed.

## Command structure

```text
Kaleb — Owner / CEO
├── Agent President — chief day-to-day operator
│   ├── Strategy & Portfolio
│   ├── Product & Technology
│   ├── Commercial Operations
│   └── Finance & Administration
└── Independent Controls Council
    ├── Legal / Compliance / IP
    ├── Security / Privacy
    ├── Finance Control
    ├── Quality / Reliability
    └── Internal Audit / Agent Operations
```

The President owns ordinary operating integration. Department leads command their own departments. Specialists act only through an assigned work order. Cross-department orders route through the affected leads or the President.

Independent control functions report functionally to the CEO and may block within their domains. For routine administration they coordinate through the President, but the President cannot suppress, edit, or overrule a control finding.

## Decision classes

| Class | Default decider | Scope | Required record |
|---|---|---|---|
| `D0_TASK_EXECUTION` | Assigned specialist | Reversible, internal, zero-cash work inside an accepted task | Task event and material evidence/artifact |
| `D1_DEPARTMENT_OPERATING` | Department lead | Assignments, sequencing, acceptance, and internal capacity inside an approved objective | Department decision or task event |
| `D2_PRESIDENT_OPERATING` | Agent President | Portfolio priority, candidate hold/kill/select recommendations, cross-department allocation, internal build authorization inside the CEO mandate | Structured operating decision with evidence and constraints |
| `D3_STANDING_POLICY_EXECUTION` | Named executor under a standing policy | Repeated external action whose actor, account, destination, environment, data class, rate, cost, monitoring, expiry, and reviews are all pre-authorized | Just-in-time authorization decision, budget reservation, execution receipt, and audit event |
| `D4_OWNER_RESERVED` | Kaleb | The reserved taxonomy below | Authentic CEO decision and exact approval packet |
| `DX_PROHIBITED` | Nobody | Conduct barred by law, constitution, or policy | Denial and incident/risk record when material |

A role may choose a stricter class but may never downgrade a decision. Unknown actions, unknown principals, broken reporting lines, stale grants, missing scope, and conflicting policy default to `D4_OWNER_RESERVED` or denial, whichever is safer.

## Owner-reserved taxonomy

Only Kaleb may decide the following. The President must package them and keep all unrelated work moving.

### Governance and strategy

- amend the constitution, approval policy, owner-reserved taxonomy, or independent-control authority;
- appoint or remove the Agent President, or remove the independence of a control function;
- change the mission, prohibited business categories, risk appetite, maximum active full builds, or owner-attention contract;
- authorize a material strategy outside the current mandate or accept a critical unresolved control risk.

### Identity, legal, and regulated matters

- form, rename, dissolve, or represent a legal entity;
- use Kaleb's name, signature, personal information, likeness, voice, tax identity, or professional credentials;
- accept platform terms, sign a contract, make a filing, hire a legal employee/contractor, or enter regulated activity;
- approve an exception involving legal, tax, employment, investment, lending, insurance, medical, or other regulated exposure.

### Capital and financial authority

- create or raise a corporate cash envelope;
- open, close, connect, or materially alter a bank, merchant, payment, tax, advertising, brokerage, subscription, or financial account;
- borrow, invest, transfer, withdraw, reinvest, or custody funds;
- set live pricing or payment terms for a first launch, or materially change terms for existing customers;
- authorize refunds, purchases, or paid services unless an existing exact standing policy and parent cash limit already cover the execution.

### Access, data, and security

- add a new production credential, secret, external account, trust provider, or materially broader permission;
- authorize collection or use of sensitive personal data, or a materially new personal-data class;
- approve public incident disclosure, credential rotation requiring account-owner action, or resumption after a critical compromise.

### Market and reputation

- approve a first customer-facing launch, first production deployment, first outreach channel, or first payment rail;
- approve a claim in Kaleb's name, a regulated claim, or another materially reputation-affecting public statement;
- approve destructive or difficult-to-reverse closure of a revenue asset or customer obligation.

An owner decision may create a narrow, expiring `D3` standing policy. Routine executions within that policy should not return to Kaleb. Changing the policy's scope, ceiling, account, data class, or expiry requires the authority named in the policy and can never exceed its parent owner decision.

## Prohibited conduct

No approval can authorize:

- unlawful access, fraud, impersonation, fabricated evidence, fabricated revenue, or false claims;
- spam, fake engagement, dark patterns, deceptive billing, or intentional customer harm;
- bypassing authentication, access controls, paywalls, rate limits, licenses, platform terms, the pause mechanism, or a control block;
- committing secrets, private customer data, raw payment data, or personal documents;
- self-approval, approval laundering through another agent label, or undisclosed conflicts of interest;
- gambling, leveraged speculation, day trading, automated securities/crypto trading, or custody of customer funds;
- silently editing or deleting material audit history.

## Authority evaluation

Before any material action, verify all of the following:

1. The actor is an active principal with an active assignment.
2. The work order names the objective, scope, acceptance criteria, owner, and decision class.
3. The issuer is in the actor's reporting line or holds a narrower valid delegation.
4. The action is within the actor's capability, risk ceiling, and department scope.
5. The action fits an active strategic mandate and opportunity stage.
6. A current budget exists and sufficient capacity is reserved.
7. Required independent reviews are fresh, in-scope, and non-blocking.
8. Any standing policy or CEO approval matches actor, account, environment, destination, data class, cost/rate ceiling, expiry, and use count.
9. `PAUSE_AUTONOMY` and subsystem stops permit the action.
10. An idempotency key is unused and an audit intent is written before execution.

Failure of any test is a denial, not a request to guess.

## Separation of duties

For `D3` and `D4` work, proposer, required control reviewer, approver, and executor must be distinct active assignments. Display names do not establish separation. A reviewer may not review work it authored. A control block remains effective until the same control function records a fresh pass or the CEO records a lawful policy amendment or reserved risk decision.

## Emergency authority

Any agent may stop or quarantine work on a credible safety, legal, financial, privacy, security, truth, or audit concern. A stop grants no authority to take other action. Incident command is temporary, scoped to containment, auditable, and cannot spend money, make public claims, destroy evidence, or expand permissions without the normally required authority.
