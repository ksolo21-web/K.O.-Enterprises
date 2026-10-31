# Source-of-Truth v2 — Development checkpoint

Date: October 31, 2026. Repository target: `ksolo21-web/K.O.-Enterprises`, branch `home-inspection-development`, path `ventures/home-inspection/`.

## New requirements and actual evidence

- [x] Versioned official source registry: 13 references across all 13 inspection systems.
- [x] Practical feature ontology: all 46 current engine feature codes, with system-specific visible cues, unknowns, recommended visual documentation and non-invasive constraints.
- [x] No fake local law: DOE model-code information never stands in for jurisdictionally adopted law, amendments or signed code-review conclusions.
- [x] Professional-standard effective-date nuance: January 2026 approved ASHI revision remains pending effective-date verification, not automatically operative.
- [x] Primary manufacturer age lookup guidance with exact brand/source matching and provisional/ambiguous candidate status.
- [x] Safety/recall/specialist-testing sources separated from direct observations and laboratory measurements.
- [x] Strict provenance data: source ID, publisher, purpose, exact HTTPS host, coverage tags, status, release/review date and truthful missing immutable snapshot.
- [x] Offline metadata audit (catalog and guidance SHA-256; status and coverage); no external fetch, customer data, portal scraping or fees.
- [x] Specialist prompt integration tested on synthetic photo, including refusal to make a proposal without observed evidence.
- [x] New focused tests: 47 catalog/policy/audit tests; 2 work-order integration tests tested in a local earlier-engine snapshot.
- [ ] Current GitHub HEAD remote full regression; no new remote suite was run for this KB change at checkpoint creation.
- [ ] Authenticated reviewer source approvals, signed case-specific receipts, adopted-code inventory for all target jurisdictions, archived legal source snapshots, manufacturer model manuals, live CPSC recall synchronization and human-inspector field benchmarks.

## Editorial and safety rules

Reference URLs and curated prose do **not** authorize any unverified defect, code-compliance, operating-safety, warranty, radon/CO/lead/mold diagnosis, automatic release or customer contact. Public source links are not live content mirrors. Inference prompts are supplementary; current claim records do not yet carry enough reference evidence to make `assess_claim()` an automatic gate for every finding. This is foundation work, not a complete production knowledge system.

## Tests and next action

Run `python -m unittest discover -s tests -p 'test_source_of_truth.py' -q`, `test_knowledge_audit.py`, and `test_knowledge_agent_integration.py`; run `python -m scripts.knowledge_audit` to reproduce the registry digest. Compare full engine regression/remote CI separately; resolve any cross-FFmpeg defects without relaxing evidence custody. Next: case-specific immutable reference receipts and a licensed local-jurisdiction adoption index; then adjudicated field accuracy.

**Review:** internal deterministic code review and local tests only; no separate critic agent; Milestone 2 remains unapproved.

**Internal review fix:** The first policy draft accepted an externally asserted custody flag without confirming on-disk bytes and returned mutable cached references. Both defects were fixed before final delivery. Original evidence now requires bounded streaming SHA-256 verification inside the trusted case root.
