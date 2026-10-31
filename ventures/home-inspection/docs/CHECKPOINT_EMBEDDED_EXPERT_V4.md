# Resumable checkpoint — Embedded SOP + Michigan expert knowledge v4

Date of source review: 2026-10-31. Branch: `home-inspection-development`. This is **internal software engineering, not approved property inspection service**.

## User requirements preserved

- Comprehensive expert-informing knowledge base available internally to M00, specialist roles T01–T08 and independent challenge Q02; Michigan-first residential inspection plus a deliberately separate contract-scoped commercial PCA path.
- Seek and communicate serious, material issues; describe what is seen, possible danger, limitations and qualified specialist follow-up. Never hide a serious unresolved issue merely because its cause is unknown.
- Distinguish symptom, multiple possible causes, alternative explanations, severity, discriminating evidence and knowledge gaps; no remote self-certification of actual root causes or unobserved systems.
- Customer report is concise, observation-led and educational; internal differential reasoning, standard catalogs and technical receipts are preserved as internal work papers and not indiscriminately printed.
- Liability management requires professional competence, accurate scope/contract, original evidence custody, prompt safety communication, documented exclusions, qualified human review, appropriate insurance and legal counsel. No promise of zero missed issues or immunity from claims.
- No external credential/system claims, no live customer media to public GitHub. No claims to possess complete proprietary standards without necessary licenses.

## Implemented in this iteration

1. `knowledge/national_inspection_policy_v4.json`: 14 official source-reference entries with purpose/status/limitations, 13 inspection-system crosswalk cards/46 feature codes, national residential SOP sections, commercial PCA separation, serious-risk cue and referral guidance.
2. `inspection_engine/inspection_policy.py`: bounded defensive loader, source/publisher/HTTPS/edition/scope validator, hash identity, 2026-vs-2027 ASHI transition enforcement, internal role-specific reference brief, fireplace/hearth gap disclosure.
3. `inspection_engine/inspection_triage.py`: evidence-hash-backed internal review and report-candidate separation; serious and unknown-priority issues reach human review, unsupported code/recall claims or altered evidence cannot become customer drafts, causes/standards stay internal; no signatures forged or reports released.
4. `scripts/inspection_knowledge_audit.py`: validates v2+v3+v4 offline and exposes explicit data completeness and verification flags.
5. Additive prompt/policy metadata changes for the existing specialist `agents.py` planner/provider and Q02 `critic.py` reviewer, preserving later GitHub features. ASHI v2 record updated with publisher's now-announced January 1, 2027 effective date.
6. Operational architecture and professional/risk controls in `docs/EMBEDDED_EXPERT_KNOWLEDGE_V4.md`.

## Verified and not verified

- Local combined source: all new targeted checks plus existing case, critical, model, video and reporting tests. **Local full suite 294 tests passed** in the latest staged code run; the full GitHub branch has additional newer functionality and still requires an integrated fresh-checkout regression.
- Direct comparison with latest branch required before committing `agents.py`, `critic.py` and existing tests; use small additive transformation rather than replacing whole older files.
- No new GitHub Actions run and no independent deployed critic worker. Internal code review only.
- NO verified comprehensive legal provision text, county/city authority refresh, all OEM manuals/serial-range recall matching, field inspector-labeled accuracy, authenticated signoff, complete fireplace role or complete commercial building-systems scope.
- `main` and `PAUSE_AUTONOMY` unchanged; customer report release blocked.

## Next executable steps

1. Reconcile latest GitHub `agents.py`, `critic.py`, existing tests with this small addition and commit to development branch only; read back exact new files.
2. Run complete source tests on fresh GitHub checkout and review any failures. Do not claim the old local test count proves new remote integration.
3. Add contracted national SOP acceptance matrix and missing specialist coverage; source-authorized provision data and local authority receipts; approved manufacturer model-specific knowledge, CPSC exact-match workflow and validated hazard protocols.
4. Build professionally labeled real-case gold sets covering serious missed defects and false alarms; have a genuinely qualified independent inspector grade the outputs, set quantitative sensitivity/specificity targets, then retest on holdouts.
5. Obtain licensed standards/standards usage permission, Michigan legal/insurance review, signed inspection workflow and private customer-data storage before commercial release.
