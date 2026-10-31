# Embedded inspection expertise and customer reporting — national/Michigan v4

**Status: IMPLEMENTED INTERNAL KNOWLEDGE POLICY; no claims of complete field accuracy or freedom from liability.**

## Operating principle

The company provides careful visual home inspections to locate and communicate material issues, especially serious visible safety and structural concerns. The goal is to educate the customer in plain language and recommend appropriate further evaluation or repair by qualified specialists. The inspector has to document what was actually inspected and what was inaccessible or not tested. An AI photo-review is an aid to that physical inspection, not a substitute for the inspector's decisions or a guarantee that all hazards will be discovered.

### Three different bodies of reference material

1. **Professional home-inspection SOP** (residential). InterNACHI's official visual SOP, last revised October 2022, describes material defects and limitations. ASHI publishes a current SOP and a newly approved January 2026 revision with implementation listed **January 1, 2027**. Select the SOP actually agreed in the customer contract and applicable on the inspection date; do not falsely claim the inspector holds an InterNACHI or ASHI credential.
2. **Building, fire, electrical, energy and other regulations.** Michigan LARA publishes the state code-edition index and identifies stays/proposed editions. A code violation is a separate legal and technical finding that requires the correct historic work, permit edition, actual municipality, amendments, enforcing authority and exact authorized provision text. A general home inspection is **not an exhaustive code-compliance inspection**. Do not use today's codes to brand decades-old construction illegal merely because standards changed.
3. **Commercial property condition assessments**. ASTM E2018-24 is a separate baseline framework, used by agreement for commercial PCA where appropriate. It is not interchangeable with a residential SOP, a licensed engineer's design inspection, an environmental assessment, or a fire-code enforcement inspection. The complete ASTM and ICC/NFPA code texts are NOT bundled without licensing.

Primary official references: https://www.nachi.org/sop.htm ; https://www.homeinspector.org/proposed-ashi-standards-of-practice-public-changes/ ; https://store.astm.org/standards/e2018 ; https://www.michigan.gov/lara/bureau-list/bcc/rules-acts/codes/code-books ; https://www.michigan.gov/lara/bureau-list/bcc/rules-acts/rules/currently-open

## Agent architecture

Existing bundled source registry v2 + Michigan authority and 13-system failure-mode playbooks v3 + national policy v4 are all available offline. Each agent is given only the related systems' reference packet to fit local-model context; the entire available corpus remains on disk for other work orders. M00 records scope/digest; T01–T08 receive source and SOP context plus symptoms, possible causes, alternatives, needed testing and referral; Q02 receives the same knowledge but independently evaluates actual pictured evidence. **These are model-role specifications, not verified independent autonomous hosts.** Sources never override observed pixels, file hashes or a qualified inspector's decision.

The embedded policy crosswalk covers all 46 pre-existing feature codes and the 13 current system roles. It **explicitly flags fireplaces/hearths** (InterNACHI 3.8) for separate inspector triage because no dedicated role exists yet. This is a known completeness gap, not a claim that fireplace coverage is finished. Other extended specialist disciplines (commercial fire systems, accessibility, specialty inspections, environmental tests) require separately scoped workflows and expertise.

## Internal versus customer-facing information

The internal ledger contains observation, original evidence hashes, alternative mechanisms, possible seriousness, code/model source IDs, tests that distinguish causes, missing coverage, qualified referrals, and all review blockers. **None of those hypotheses becomes a confirmed defect because an AI wrote it.**

An inspector-facing report candidate contains only: specific observed condition and location; why the observation matters (calibrated, not a claimed diagnosis); recommended next step (appropriate qualified specialist or corrective evaluation); a material limitation if relevant; evidence IDs. A serious sign is escalated promptly for human assessment even if the cause is unknown. Purely cosmetic/maintenance-only model proposals are retained internally rather than automatically filling the customer report. Qualified inspectors decide report inclusion under the contracted SOP and particular client's needs.

The `case_review_queue` returns internal and inspector-facing **drafts only**; it never authenticates signatures, sends a report, obtains insurance, gives legal opinions, diagnoses concealed defects, or confirms recall/product model applicability.

## Risk and liability controls — required operating practices

- Written pre-inspection agreement defining standard/scope, exclusions, property type, ancillary services, limits, and who receives the report; **obtain Michigan-qualified legal counsel to review contract terms and actual enforceability**.
- Verify credentials/authority for each person offering an inspection or specialty assessment, and professional liability / errors-and-omissions coverage appropriate to the work. Legal compliance/insurance must be assessed case-by-case; software cannot prevent liability.
- Original images and notes with timestamps, SHA-256, access and test limitations, date of inspection, agreements and retained communications; store privately and apply a defensible retention and access policy.
- Document any immediate safety concern and escalate it promptly through an approved communication path. Do not claim a photo proves CO concentration, gas leakage, electrical safety or structural soundness. Do not tell users to undertake unsafe testing.
- Ensure every serious finding and every material limitation is reviewed by a qualified human; inspector must correct false positives, assess missing coverage, and decide whether further specialist referral is necessary.
- Do not issue 'safe', 'no defects', '100% inspected', 'code compliant', 'recall confirmed', remaining-life or guaranteed-root-cause language. Disclaimers do not replace competent work and do not eliminate liability.
- Keep customer documents to the applicable SOP's material findings and communication needs, not a dump of source libraries, speculative root causes, or code paragraphs.

## Reproducible checks

Run from `ventures/home-inspection`:

```bash
python -m scripts.inspection_knowledge_audit --out local-results/policy-audit-v4.json
python -m unittest discover -s tests -q
```

The output explicitly marks source freshness, municipal AHJ review, manufacturer model-manual coverage, field-accuracy benchmarking and final customer release as **NOT VERIFIED**.

## Coverage that still requires substantial work

1. Complete inspection SOP item mapping beyond the 13 current systems, including fireplace/hearth and other specialist or commercial systems, and a legally reviewed company standard of care.
2. Licensed/copyright-permitted exact code-provision text and indexed amendments; property-level municipality and enforcement authority, effective dates and actual permit chronology. **No unaudited bulk copying** of ICC, NFPA or ASTM copyrighted standards.
3. Broader approved manufacturer manual/spec and serial-range database; verified official recall querying with model/serial exact-match and retrieval receipts; no unsupported blanket manufacturer claims.
4. Qualified inspector-labeled real Michigan residential and commercial cases; measurable sensitivity for urgent/material issues, false negatives/false positives, independent challenge and retraining approvals.
5. Authentic signed human review, case/privacy controls, client-report delivery, quality assurance and insurance/legal review. Continuous code/recall updates are not implemented and the public repository cannot contain private customer media.

**Milestone acceptance:** Code/policy regression passing is not defect-recognition performance or permission to provide a signed commercial or residential report. Independent human/field validation remains mandatory.
