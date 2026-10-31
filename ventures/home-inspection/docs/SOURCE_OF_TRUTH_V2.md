# Home Inspection — Source of Truth v2.0

**Status:** versioned primary-source *reference registry* + offline policy engine + auditable lookup. This does **not** verify conditions in a specific property, create local-law applicability, or approve reports. No live website fetch or frozen source-page archive is implemented yet.

## What was wrong with the previous approach

The earlier manufacturer register was a loose list of five brand links, while the 13-system feature taxonomy had no authoritative reference mapping. Without explicit boundaries, model-generated prose could incorrectly promote generic advice into a verified defect, present a manufacturing-code guess as an installation date, or treat any edition of a model code as the law in an unknown jurisdiction.

## v2 data model and design

- `knowledge/source_registry_v2.json`: 13 reviewed official entry points across professional SOPs, federal safety guidance, manufacturer data, recalls, and model-code context. Each entry has stable ID, title, publisher, authority class, applicability, covered systems, purpose, canonical HTTPS link, review date, current/pending status, original-content snapshot status, and *never-a-case-fact* flags. Index covers all 13 inspection systems. No copyrighted full manuals or proprietary standards text is copied into the repository.
- `inspection_engine/source_of_truth.py`: deterministic catalog validation, safe bounded retrieval, prompts that disclose the source's limits, and `assess_claim()` decisions that never silently certify a property, a jurisdictional code rule or a technical finding.
- `scripts/knowledge_audit.py`: offline reproducible report of registry integrity, coverage, pending standards, references needing re-review, and the SHA-256 of the current catalog.
- `tests/test_source_of_truth.py`: positive and adversarial provenance tests. All source documents remain independent of case photographs and videos.

### Source-of-truth priority — *specific to the question*

1. **Case evidence:** originals with SHA-256, visible labels, tested functions, inspected access, the time/room/system and the qualified inspector's signed observation. No public webpage can prove what is present in this house.
2. **Applicable legal authority:** adopted local and state laws/permit requirements with jurisdiction, edition, amendments, date and written authority. The mere existence of ICC/NEC/IECC model documents is not proof of adoption. Professional home inspections are not blanket code-compliance certifications.
3. **Manufacturer primary material:** model-specific manuals, nameplates and authorized serial lookups. A manufacturer's general warranty URL is not a confirmed individual date, status or warranty record. Age codes can repeat.
4. **Inspection SOP / contractual scope:** currently operative, legally applicable professional standard, state SOP and actual signed service scope. Voluntary ASHI/InterNACHI guides are useful comparisons, not substitutes for licensing requirements.
5. **Specialist government guidance:** EPA, CDC and CPSC information for safety or specialist-testing referrals. A photo cannot diagnose radon, lead, carbon-monoxide concentration or mold species. A recall search page without exact model/serial match cannot prove an applicable recall.
6. **Secondary educational materials, community discussion and LLM background:** research clues only, never independent proof of a home defect or legal compliance.

The ranking is **not** a single blanket priority order: local law governs legal obligations, manufacturer documentation governs a product specification, while observed case evidence governs the factual condition of the particular property. Resolve conflict by *claim type*, date, product and jurisdiction, not by source count.

## Non-negotiable claim gates

| Requested statement | Required evidence | Allowed automated status |
| --- | --- | --- |
| Visible characteristic / potential issue | Source photo/video hash and in-scope SOP, with exact system and feature code | Provisional; human review pending |
| Water-heater manufacture month | Legible rating plate, brand-matched official date-code rules, cycle analysis and source receipt | `CODE_ONLY_UNVERIFIED` until manufacturer/professional corroboration |
| Installation date / remaining useful life | Separate installation record or qualified determination; serial alone insufficient | Blocked |
| Code violation or code compliance | Authority having jurisdiction, adopted edition/amendments/effective date, competent inspector review | Blocked in v2; not a home-inspection auto-result |
| Recall applicable to this equipment | Verified exact product identity and government recall match, manufacturer response and human signoff | Blocked in v2 pending case-specific workflow |
| Radon/lead/CO concentration or mold species | Approved instrument/laboratory and qualified specialist as appropriate | Blocked from image-only diagnosis |
| "No problem" based on absent observation | Evidence of the required completed checks and access; missing evidence cannot prove absence | Blocked / not verified |

### Effective-date handling

On October 31, 2026, ASHI's current published SOP was listed as operative, while a January 8, 2026 approved revision had **implementation date to be determined**. These are two separate registry records, with the pending one excluded by default. The source review must be repeated and recorded when the operative version changes; do not silently mark the pending text effective.

## Workflow to expand toward a real knowledge system

1. Gather an official candidate from a manufacturer, regulatory body, inspector board, adopted law, or source owner. **No background scrapers or unauthorized customer serial submissions.**
2. Record content ownership, effective period, geographical/product scope, source webpage/PDF version, retrieval time, rights and an immutable snapshot hash *when actual bytes have been lawfully retained*. `content_snapshot_sha256: null` truthfully means not yet archived.
3. Split into atomic, attributable propositions, each with source excerpt location, permitted claim types, contradictions, exclusions and review priority. Do not ingest a whole page as unconditional "truth."
4. Require technical reviewer, licensing/jurisdiction reviewer when needed, and source QA before promotion; rejected/superseded facts remain historically traceable.
5. Attach the approved propositions to system/feature codes and service-model/serial applicability. Validate source date and apply re-review cadence: recalls before every relevant case, codes and state licensing as of inspection date, product manuals by exact model revision.
6. Test conflict cases, expired SOPs, false recall matches, ambiguous cycle-coded serials, concealed framing, visual-only mold/lead/radon, and adversarial prompt text. Run holdout case benchmarks against independent qualified inspector adjudication. Do not auto-learn from unreviewed human reports.
7. Commit signed review receipts and tests, calculate catalog digest, and keep a rollbackable revision. Customer evidence stays in private storage only; no customer photos/serials in public GitHub.

### Scope honestly not delivered in v2

No locally adopted code database, laws/amendment versioning by municipality, licensed inspector directory, product-manual text archive, automated manufacturer portal verification, active CPSC recall syncing, model-retrieval embeddings, external QA reviewer identity, or verified real-property diagnostic accuracy. The present registry is a **controlled, reference-only foundation**, not a comprehensive professional knowledge repository. A successful model prompt or a list of official URLs cannot substitute for those gates.

## Developer commands

```bash
python -m unittest discover -s tests -p 'test_source_of_truth.py' -q
python -m scripts.knowledge_audit --output local-results/source_of_truth_audit.json
```

Source links are contained in `knowledge/source_registry_v2.json`, independently reviewed via the official websites as of October 31, 2026.

## Observable system knowledge (new)

`knowledge/system_guidance_v2.json` adds a curated 13-system, 46-feature-code vocabulary tied exactly to `inspection_engine.descriptors.REQUIRED_FEATURES`, with (a) visible observation examples, (b) what still photographs cannot establish, (c) safe noninvasive evidence-capture/review guidance and (d) current SOP reference IDs. `build_knowledge_brief(systems)` supplies a bounded, non-diagnostic reference context on each specialist work order; tests compare all 46 codes to the live engine and require that the prompt remains review-pending. This prevents feature taxonomy drift, but **does not** prove the model obeyed its prompt or correctly identified a defect. Human adjudication is required.
