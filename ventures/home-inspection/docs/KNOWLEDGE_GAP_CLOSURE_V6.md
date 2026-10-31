# Home Inspection — Michigan source verification and safety sweep v6

**Review date:** 2026-10-31. **Status:** ADDITIVE OFFLINE BUILD, technical trial; NOT field-approved.

This enhancement preserves the national residential-SOP, Michigan authority, building-science, case verification, licensed-reference, and serious-defect benchmark layers established in v2–v5. It closes some *functional* gaps but does not assert complete authority coverage, exhaustive manufacturer documentation, licensed copyrighted text, or validated detection of every defect.

## What is operational in v6

1. **Municipality research pilot:** Official portal indexes for Westland, Livonia, and Detroit, plus the statewide LARA enforcement-jurisdiction list. A case needs municipality *type* as well as name/county/state, otherwise a township cannot silently be treated as a city. Every case receives separate building/electrical/mechanical/plumbing and fire/zoning/maintenance verification tasks. Dated case-specific AHJ confirmation and local amendments remain required. Detroit's older pages reference older building code editions; the registry explicitly flags the conflict rather than choosing one.
2. **Offline verification and revision diff:** Private source snapshots must pass file-size, real SHA-256, source URL, retrieval date, and reviewer-ID checks. Same-URL changes produce a human review task. An official landing page or successful hash comparison is not a legal conclusion or authority authentication. These functions do not scrape or schedule anything.
3. **Manufacturer manuals:** A. O. Smith, Carrier, Goodman and Rheem official document portals are indexed. The lookup requires an exact photographed model and the right discipline. A matching private manual receipt binds model, revision, source URL, rating-plate hash and bytes; it remains pending qualified review. No manual contents, installation dates, remaining service life, recall eligibility, or cause findings are invented. PDF access is not automatic machine-indexing permission.
4. **SOP gap tasks:** Original, copyright-safe observations for fireplace/hearth and garage-door safety (residential), plus commercial fire/life safety (separate commercial PCA). These tasks explicitly discuss possible mechanisms, alternatives, accessible evidence, safety urgency, limitations and specialist referrals. They **remain unassigned inspector tasks**, not proof of inspection or permission to certify code compliance.
5. **Hazard sweep:** A separate 13-system differential-hazard checklist requires human coverage status and evidence IDs. Missing photographs always remain unassessed; a recorded inspector review still does not prove that a hazard is absent. The v6 agent packet adds only the relevant system's urgent-cue differential, plus interior/fireplace/garage or commercial-specialty work orders when applicable. The report generator still requires its separate reviewer and human-signoff gates.
6. **Local audit CLI:** `python -m scripts.knowledge_expansion_v6` prints a source-hashed coverage audit and returns `2` because major knowledge gaps remain. Optional `--case /private/case.json --out /private/audit.json` creates a case-specific, non-overwriting, local-only research plan. It must never be committed with customer metadata.

## Verified official references (public entry points, not reproduced books)

- [Michigan LARA code editions](https://www.michigan.gov/lara/bureau-list/bcc/rules-acts/codes/code-books) and [currently open residential/energy rules](https://www.michigan.gov/lara/bureau-list/bcc/rules-acts/rules/currently-open)
- [Michigan statewide jurisdiction list, revised October 6, 2026](https://www.michigan.gov/lara/-/media/Project/Websites/lara/bcc-media/ASD/StatewideJurisdictionList.pdf?hash=337442F1456C02A63BAAC230297C59FC&rev=fb9cb0fecd4342e4a084b1230a5ae28d)
- [Westland Building Division](https://www.cityofwestland.com/194/Building-Division), [Livonia Inspection](https://livonia.gov/241/Inspection-Building-Enforcement), [Detroit BSEED FAQ](https://detroitmi.gov/departments/buildings-safety-engineering-and-environmental-department/frequently-requested-services)
- [InterNACHI residential Standards of Practice](https://www.nachi.org/sop.htm), [ASTM E2018 commercial PCA overview](https://store.astm.org/standards/e2018)
- [A. O. Smith literature](https://www.hotwater.com/find-documents-and-videos), [Carrier documents](https://www.carrier.com/us/en/product-documents/), [Goodman literature](https://www.goodmanmfg.com/support/literature-library), [Rheem commercial documents](https://www.rheem.com/professionals/commercial-water-heating/product-documentation/)
- [CPSC public recall API](https://www.cpsc.gov/Recalls/CPSC-Recalls-Application-Program-Interface-API-Information)

## Non-negotiable constraints

- **No claims of full ICC/NFPA/ASTM text ingestion** without business-approved machine-use rights and secure local document storage. No copyrighted books copied into the public repository.
- **No all-defects-detected claim.** Visual inspection cannot rule out concealed defects or guarantee the future condition of a building.
- **Safety escalation is human directed.** A suspected urgent condition prompts immediate human evaluation and appropriate specialist/emergency advice; LLM-generated causal theories remain explicitly provisional.
- **Commercial assessments must not be mislabeled as residential SOP inspections.** Occupancy, plans, fire/building records, accessibility and specialist scope vary by property and contract.
- **No claim that web portal listings are actual per-property AHJ certifications.** Michigan enforcement responsibilities can change and differ by trade; parcel, permit history, adoption/effective dates and amendments must be established by qualified reviewers.
- **No field benchmark pass without consented expert adjudication.** The existing v5 serious-defect evaluator is prepared, but does not contain a real field cohort; no images/labels were fabricated.
- `PAUSE_AUTONOMY` unchanged; no actions workflows activated, payments, new accounts, or customer report publication.

## Next evidence-dependent milestones

1. Continue statewide jurisdiction coverage **municipality by municipality** with authenticated dated snapshots and independent checks of municipal ordinance amendments. The three-city index does not stand for Michigan-wide coverage.
2. Obtain rights/permission to machine-index applicable ICC, NFPA and ASTM texts, or continue legal reference-only approaches and private professionally authored explanations.
3. Obtain exact installation/operation manuals for **actual observed equipment** and validate any recalls by full model and serial/lot range; avoid hundreds of irrelevant manuals.
4. Add native fireplace/garage/commercial-specialty system routing, field inspection checklists and report templates after confirming applicable SOP and licensed professional roles.
5. Collect consented independent inspector-annotated real property cases across 13 systems plus specialty concerns, run blind holdout evaluation, and independently audit serious misses before controlled releases.
