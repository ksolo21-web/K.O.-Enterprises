# Michigan-first governed expert knowledge v5 — implementation and required evidence

**Reviewed 2026-10-31. Scope: residential visual home inspections; commercial PCA is a separate service/contract framework.**

## What is implemented

- A machine-checkable *source index* containing 17 primary-source pointers, publisher/domain checks, scope, and rights status. These are **references, not full authoritative texts**, provision-by-provision legal opinions, or endorsements.
- A Michigan case research packet that requires county, municipality, building type and inspection date. It creates separate AHJ-verification tasks for building, electrical, mechanical and plumbing; it never presumes a local official or statewide enforcement responsibility.
- A case-specific provision receipt tying a specific code edition/section to an exact original evidence SHA-256 and AHJ receipt. Receipts are strictly **traceable, not a confirmed code violation**. For Michigan residential/commercial code indexes, the referenced edition must match the indexed edition. Historical construction/permit work and approved local amendments require separate confirmation.
- Manufacturer-manual and recall receipts that require an exact model match; a brand warranty portal or photographed appliance alone proves neither installation date nor recall eligibility. Serial/lot range and official current recall findings require human verification. No customer product serial is sent to public services by this module.
- A private local document-rights adapter that refuses files outside the dedicated private directory, group/world-accessible folders, expired permissions, and rights that do not explicitly cover machine indexing. **The adapter only registers metadata; it does not extract text or independently verify the publisher's license**. Restricted documents must never be put in GitHub.
- A SOP coverage-crosswalk with **18 topics** and unresolved fireplace/hearth, garage-door, life safety, combustion/gas, supplemental pool/spa and commercial-specialty coverage. Mapping to a system is not proof of a completed inspection.
- A separate **real-case benchmark** requiring opt-in, original media hashes, locked holdouts, no known training overlap, adjudicated finding labels, independently named expert reviewers and human matching decisions. Critical misses, major misses, false-positive predictions and unmapped building systems are reported individually. A pilot minimum of 100 cases, 30 critical defects, 13 covered systems and both residential/commercial scopes is a *proposed engineering floor*, **not an externally validated scientific threshold**. No such corpus currently exists in this repository.
- Read-only knowledge audit commands and source-digest change queue to **identify** updates. These are not a continuous monitor or a substitute for human legal adoption review.

## Rights and access — hard rules

ICC, NFPA and ASTM texts carry separate licenses and permission conditions. Access to online reading or purchase of a book is **not proof** that machine ingestion, bulk indexing, AI training or redistribution is permitted. Obtain written permission describing the exact titles/editions and authorized computational use. Preserve the rights receipt, verify it with the rightsholder, and store licensed files only in a private controlled environment. Do not download entire protected libraries by scraping, copy them into a public repository, or assert blanket permission. The code records rights claims but deliberately declines automatic full-text indexing until the contractual review and private infrastructure exist.

Primary references (verify links and access conditions again before a real case):
- ICC: https://www.iccsafe.org/about/terms-of-use/ and https://www.iccsafe.org/about/periodicals-and-newsroom/icc-logo-license/
- NFPA: https://www.nfpa.org/en/Customer-Support/Terms-of-Use
- ASTM: https://store.astm.org/restricted_copyright-and-permissions
- Michigan LARA rules: https://www.michigan.gov/lara/bureau-list/bcc/rules-acts/rules/currently-open
- Michigan LARA statewide jurisdiction list, revision 2026-10-06: https://www.michigan.gov/lara/-/media/Project/Websites/lara/bcc-media/ASD/StatewideJurisdictionList.pdf?hash=337442F1456C02A63BAAC230297C59FC&rev=fb9cb0fecd4342e4a084b1230a5ae28d
- CPSC recalls API: https://www.cpsc.gov/Recalls/CPSC-Recalls-Application-Program-Interface-API-Information
- Commercial PCA standard metadata: https://store.astm.org/e2018-24.html
- InterNACHI SOP: https://www.nachi.org/sop.htm
- ASHI SOP: https://www.homeinspector.org/resources/standard-of-practice/

## Source refresh workflow (not running autonomously)

1. Intake an official source revision as a **human-authorized** archival action; record URL, accessed date, exact downloaded document SHA-256, edition, legal effective date and rightsholder permission. No automatic scraping.
2. Compare the prior and new approved source hashes. Every change becomes `CHANGED_REVERIFY_BEFORE_USE` until reviewed. A broken or missing source remains unresolved.
3. For Michigan, verify the legal rule's current status and any injunction; record historical permits and work dates separately. Check the **statewide jurisdiction directory for each discipline**, then review that jurisdiction's official locally enacted ordinances, amendments and fire/zoning authorities. An unknown AHJ blocks compliance conclusions.
4. For equipment, tie the rating-plate photo, exact model, product variant and manual revision to official manufacturer sources; verify safety notices and recalls via product/serial/lot match with current CPSC/manufacturer documentation.
5. Qualified independent technical reviewers approve specific factual evidence links, not an entire page based on resemblance. Changes must pass regression, adversarial, legal/rights and real-case blind holdout review.
6. Only release **clear material observations, why they matter, recommended specialist when indicated, and material access/testing limitations** after authenticated qualified human inspection and contractual review. Root-cause hypotheses and code research remain internal unless independently established and appropriate to report scope.

## Immediate coverage blockers

| Gate | Evidence currently present | Status |
|---|---|---|
| Full ICC/NFPA/ASTM machine-licensed text | No verified publisher grant or private authorized corpus | **BLOCKED** |
| All Michigan municipal amendments | Official statewide index pointer only; no municipality-by-municipality verified amendments | **BLOCKED** |
| All manufacturer exact-model manuals | A few manufacturer official lookup links; zero exhaustive licensed model collections | **BLOCKED** |
| Current recalls against individual case equipment | CPSC public API pointer, no authorized customer-device lookup | **BLOCKED** |
| SOP scope completeness | 18-topic gap map; dedicated hearth/garage coverage pending | **BLOCKED** |
| Every possible defect recognized | Not a scientifically verifiable guarantee; no real-case benchmark | **NOT CLAIMABLE** |
| Serious defect benchmark | 0 opt-in independent professional-labeled real cases in repo | **BLOCKED** |
| Michigan-specific legal/code assertions | Exact AHJ, permit era, edition, amendments and section receipts needed per case | **BLOCKED UNTIL VERIFIED** |

## Local use

```bash
python -m unittest tests.test_knowledge_governance_v5 -q
python -m scripts.knowledge_governance_v5
python -m scripts.knowledge_governance_v5 --case private_case/case_context.json
python -m scripts.knowledge_governance_v5 --human-holdout private_cases/approved_labeled_holdout.json --detections private_cases/model_predictions.json
```

The audit exits nonzero while the enterprise-wide knowledge completeness gates remain open. Case photos/labels must stay out of the public repository. Python scorecards do not establish a credential or confirm that human signoffs are genuine: qualification verification and an independent evidence ledger must be implemented before any production acceptance.

## Objective vs reality

Find as many significant visual issues as reasonably possible. Educate the client, flag material risk promptly, provide sensible referral advice and retain uncertainty and inaccessible areas. Do **not** make a “no issue missed”, “fully code-compliant”, “cause definitively proven”, legal immunity, or exhaustive manufacturer knowledge claim. Insurance, lawyer-reviewed engagement agreements, consistent field practice and qualified inspector responsibility remain necessary.
