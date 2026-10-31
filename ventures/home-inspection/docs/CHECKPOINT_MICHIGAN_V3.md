# Michigan knowledge & case verification v3 — auditable checkpoint

## Purpose and approved requirements
Build a Michigan-first residential/commercial building-science knowledge substrate embedded in the existing T01–T08 specialist prompts. Tie proposed defects to exact case evidence, plausible competing causes, the correct legal source/edition and authority, review decisions, and coverage gaps. Do not promise perfect detection or unlicensed code-compliance certification.

## Implemented (local source)
- 10 official Michigan state legal reference/status records; notably 2015 MRC operative, 2021 residential and energy proposal stayed per Michigan LARA current open rules as of 2026-10-31; 2021 commercial building/rehab/mechanical/plumbing, 2023 NEC with Michigan Part 8, 2021 commercial energy.
- Pure, defensive loaders with source host checks, date/schema validation, copyright-safe index references, and future/blocked-edition exclusion.
- Separate 13-system, 46-feature differential prompts; observable symptoms vs alternatives, proposed verification, urgency referrals, and no inferred hidden cause.
- Case-specific intake metadata: state MI, county, municipality, type, date, work type, evidence manifest; hash-validated files; rejects invented evidence, path escape, tampering, unsupported claims and false approval.
- Case code-claim gate: requires AHJ, permit/alteration history, exact provision references, amendments; even with inputs, qualification and authentication remain pending.
- Offline case audit that reports unresolved features and keeps all output private.
- Specialist prompt integration patch prepared against the latest branch, preserving v2 prompt controls and unrelated later improvements; scope limited to Michigan-labeled cases.

## Actual tests
Local combined v2 reconstructed source + additions: **251/251 unittest checks passed**, including 30 Michigan law/case tests, 11 differential-playbook tests and one case-audit test; 2 earlier knowledge prompt tests passed. This does not establish new capabilities working with the latest GitHub branch until source readback and test parity. No live Michigan photos or qualified inspection cases were available; legal applicability at a specific property is not verified.

## Remaining (mandatory)
1. Source archive and actual adopted provision/paragraph library with license rights and exact hashes; state rules and jurisdiction amendments tracked per date.
2. Verify local AHJ and municipal fire/property/occupancy/regulatory requirements for each case; history of building and work permits.
3. Manufacturer manuals and safety recalls keyed by precise model and serial, with authorized receipts.
4. Professional authenticated Q02/human review, real property benchmarks, field false-negative stress tests; customer release blocked.
5. Latest GitHub full regression and remote CI; review differences due to concurrent developer changes.

## Governance
The root PAUSE_AUTONOMY stays active, main unchanged. Only public-safe code, synthetic tests, and official URLs belong on GitHub. Do not upload real cases, addresses, photos, serials, contracts or inspector credentials. No external compute/workflow launched by these source changes. Internal review only; no separate critic agent was run.
