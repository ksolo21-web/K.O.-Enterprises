# Territory R52 Role Authority Contract

Revision: segment-role-whole-label-2026-09-13-r52

This contract prevents the territory Builder from diagnosing, fixing, scoring, and approving its own work.

## Builder
- Creates or revises a candidate only from approved source evidence and an authorized plan.
- May execute a Fixer Advisor plan exactly as written.
- Cannot score its own artifact, declare a pass, weaken a gate, expand repair scope, or issue release authority.
- A changed PDF invalidates the prior critic/enforcer verdict for that artifact hash.

## Fixer Advisor
- Read-only diagnosis/planning role.
- Starts only from a failed Enforcer Critic verdict bound to the exact candidate SHA-256.
- May propose bounded alternatives inside predeclared correction masks.
- Must include R52 label_id, street, navigation_role, physical segment_id, source evidence, and exact allowed placement alternatives.
- Cannot edit the PDF and cannot mark any card release-ready.

## Internal Territory Card Critic
- Mandatory on every created or changed candidate.
- Uses the saved R52 Territory-Card-Critic contract.
- Reopens source evidence and does not reuse Builder claims as proof.
- Records critic_independent:false when it is the authorized internal reviewer.

## Independent Critic
- Separate local visual-model runtime when available/required.
- Must bind the exact candidate PDF hash.
- Every required visual/coverage check must be strictly greater than 9.0; exact 9.0 fails.
- The minimum applicable score controls. Weighted averages have no release authority.
- Does not edit.

## Enforcer Critic
- Read-only release-gate authority.
- Applies R52 deterministic evidence gates, internal-review parity, exact-PDF label-navigation validation, and required independent critic evidence.
- Cannot repair or suggest implementation details.
- Only an Enforcer verdict with passed=true and release_gate_eligible=true for the exact candidate/review hashes can advance to the final release gate.
- Builder and Fixer Advisor cannot override the Enforcer.

## Required chain

source truth -> Builder candidate -> deterministic gates -> internal critic -> independent critic when required -> Enforcer Critic

On failure:

Enforcer fail -> Fixer Advisor bounded plan -> Builder executes only that plan -> all affected evidence is recaptured -> critics rerun -> Enforcer rerun

There is no Builder self-pass and no blind repair loop.
