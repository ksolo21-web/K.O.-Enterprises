# Milestone 4 V7 — Witnessed governance enrollment and revocation history

**Checkpoint date:** 2026-11-03  
**Repository:** `ksolo21-web/K.O.-Enterprises`  
**Only development branch:** `home-inspection-development`  
**Scope:** Offline security engineering with synthetic fixtures. **Customer release: DISABLED**.

## Scope preserved from previous V2–V6 checkpoints

Do not change the M4 source-bound private case pipeline, Q01/Q02/Q03 specialist independence, two source-bound human Ed25519 reviews, Option 2 navy/white photographic PDF, original evidence custody, protected case workspaces, revocation preflight, issuer source receipts, or previously approved milestones. Never touch `main` or root `PAUSE_AUTONOMY`. The user-supplied DeepSeek/Qwen3.5 GGUF remains research-only; **no model downloaded, installed, replaced or benchmarked** in V7.

V6 milestone and evidence: [CHECKPOINT_M4_ISSUER_EVIDENCE_V6.md](CHECKPOINT_M4_ISSUER_EVIDENCE_V6.md), 936/936 offline tests passed at commit `856139e785ee849e8f2e1b95a7c138898fe4b35f`.

## V7 implementation

1. `inspection_engine/m4_governance_history.py` adds **read-only** `verify_governance_history`. A governance root (genesis) declares exactly two separate trustee IDs, Ed25519 public keys and organizations in the Michigan private-residential-inspection trust domain. The root is hash-pinned by a separately controlled trust source, not assumed valid because it exists locally.
2. A bounded chronological **hash-linked** history (up to 4096 events/3 MB file) contains only explicit `enroll_issuer_verifier` and `revoke_issuer_verifier` actions. Each event includes canonical sequence, previous signed-event SHA256, separate nonce, evidence receipt digest, effective date, exact verifier ID/key/organization/registry fingerprint and `customer_release_allowed=false`. **Both trustees sign every event**. Duplicate identities, keys, organizations and challenge nonces fail closed; revoked IDs cannot be re-enrolled. The V7 parser also **rejects duplicate JSON keys and nonstandard `NaN` / `Infinity` numeric constants** in governance history and independent witness files, avoiding conflicting interpretations by different JSON readers.
3. Latest head SHA256, genesis SHA256, minimum event sequence and witness Ed25519 public key must be provided as **out-of-band independently pinned inputs**. A third independent witness signs a fresh (<2-day validity and <=1-day age) checkpoint binding the exact genesis, latest event SHA256, event count and latest event date. Missing/reordered/replaced entries, old histories, forged signatures and stale witnesses fail.
4. `governed_issuer_evidence_preflight` composes V5 + V6 + witnessed V7. It requires the active issuer verifier's exact key, ID, declared organization and registry SHA256 to match the enrolled record, and checks the two trustees and witness are disjoint from the two human reviewers, two qualification/revocation officers and the issuer verifier. **Revocation of a previously active issuer verifier blocks the case**, even if the older V6 signed issuer receipts still appear valid.
5. `scripts/m4_governance_cli.py` provides explicit local `history` and `case` subcommands. No key enrollment/account creation, network search, implicit model inference, PDF publishing or customer delivery action exists.
6. `tests/test_m4_governance_history.py`: **32 synthetic** tests built on the exact V2–V6 synthetic case pipeline. Tests cover legitimate local signatures, two-governor threshold, forged signatures, missing trustee, malformed replay, sequence/prev-hash mismatch, external head/genesis/witness pin disagreement, truncation, expiration, same-org/same-role conflicts, revocation, forbidden re-enrollment, signed-but-unsupported release claim, evidence/case location restrictions, exact registry SHA binding and V5/V6 composition.

## Deliberate limits and threat model

- A local operator may type arbitrary genesis/head/witness pins; this code **cannot independently determine** whether those pins were really controlled by a separate organization. All return contracts explicitly keep `external_pin_origin_independently_authenticated=false`, `real_world_governance_independence_verified=false`, `professional_release_authorized=false` and `customer_release_allowed=false`.
- Ed25519 proves signing key possession, not a real human's identity, qualification, legally independent organization, on-site inspection or official ASHI/InterNACHI/CPI status. There were **no real verifier enrollments or licensed/certified professional validations**.
- A local hash chain alone is **not append-only storage**. The independently maintained latest head, witness key and witness checkpoint are mandatory to detect truncation, forked histories or local alteration. Challenge nonces are checked for uniqueness **within the checked history**; a separately issued unpredictable challenge and immutable trust log are still missing.
- A current signed local witness attestation cannot prove that an independent witness organization exists or controlled its keys. Genuine legal identity proofing, external pin governance, key rotation/recovery and tamper-evident external retention must be implemented and externally corroborated.
- The preflight intentionally has no `release_allowed=true` branch. All Q03/report holds, real field-case accuracy, professional authorization and data privacy restrictions remain.
- Michigan home inspector licenses are **not generally issued** for private visual residential home inspections; do not invent a state-specific license. Jurisdiction-specific specialty and code-official requirements need separate verified policy.

## Private CLI usage — examples only

```bash
# Only after separately enrolling trustees/witness and independently
# authenticating AND pinning genesis, latest head and witness public key:
python -m scripts.m4_governance_cli history \
  --governance-history /private/trust/history.json \
  --independent-witness /private/trust/witness.json \
  --pinned-genesis-sha256 <independently-pinned-64-hex> \
  --pinned-head-sha256 <independently-pinned-64-hex> \
  --pinned-witness-public-key-hex <externally-pinned-64-hex> \
  --minimum-event-sequence <externally-anchored-positive-count>
```

The case subcommand additionally requires the existing V5/V6 private file paths and `--minimum-revocation-sequence` from a separate monotonic revocation source. Never commit any actual private case evidence, reviewer identification records, original photos, credentials, PEM signing keys or issuer replies to this public repository.

## Acceptance / evidence / resumption

- [x] Code committed on `home-inspection-development` with 32 added synthetic tests.
- [x] Original V6 936-test baseline preserved in existing branch history.
- [x] First complete V7 CI run [41673782881](https://github.com/ksolo21-web/K.O.-Enterprises/actions/runs/41673782881) executed 965 tests; **964/965 passed**. The only failure was an assertion expecting lower-case wording whereas the correct rejection message began with capitalized “Independent”. This **test-only** assertion was corrected in `tests/test_m4_governance_history.py` at `652849f245151916b2ad4b00959c7642b778322d`. No release guard, validation rule or trust requirement was relaxed.
- [ ] Full HEAD CI must be observed SUCCESS for the revised trustee test plus three JSON ambiguity tests, now **968 total offline tests**, before V7 synthetic implementation is considered accepted. **Do not mark complete merely because this checkpoint file exists**.
- [ ] Independently governed real-world verifier enrollment, sustained external immutable head publication, authenticated witness organization, issuer-authoritative credential corroboration, professionally labelled serious-defect benchmarking and customer-release legal safeguards remain **BLOCKED**.
- [ ] Independent critic **not executed**; internal review only. Production milestone 4 approval requires strictly above 9/10 with every mandatory real-world validation passed. Current overall readiness is **below acceptance threshold**.

**Next action on “continue”:** verify latest CI after the revised V7 test, fix and retest any remaining failures, then implement an external trust checkpoint store with verifiable origin and controlled key enrollment/revocation without using new accounts or compromising private property data. Larger report and accessibility suites and the professional serious-defect benchmark remain parallel required work.
