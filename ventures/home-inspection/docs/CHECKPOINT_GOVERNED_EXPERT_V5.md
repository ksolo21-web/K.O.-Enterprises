# Resume checkpoint — Michigan governed expert knowledge v5

**Working branch:** `ksolo21-web/K.O.-Enterprises`, `home-inspection-development`; preserve root `PAUSE_AUTONOMY` and do not change `main`.

**Task:** Expand Michigan-first residential and separate commercial knowledge references legally and traceably; support authenticated AHJ/source receipts, licensed manuals, recall verification and critical-defect blind benchmarks. Do not copy ICC/NFPA/ASTM full texts without verified machine-use rights or claim all defects can be detected.

**Delivered in this checkpoint:** `knowledge/governed_sources_v5.json`, `inspection_engine/knowledge_registry.py`, `inspection_engine/licensed_reference.py`, `inspection_engine/sop_scope.py`, `inspection_engine/serious_defect_benchmark.py`, `knowledge/sop_scope_crosswalk_v5.json`, `scripts/knowledge_governance_v5.py`, tests, docs, and additive Michigan specialist prompt integration.

**Validated:** 51/51 v5 targeted tests passed locally, with no real labeled holdout or publisher-rights verification. Rights filters, source authority mapping, edition mismatch, source SHA, reviewer/consent, SOP gap report, private-only access, manual/recall restrictions and critical-defect miss cases are included. Full up-to-date GitHub project regression and real model field benchmark remain pending.

**Priorities next:** (1) Publisher-provided machine-use licenses and legal review, if obtainable; (2) authenticated Michigan AHJ registry ingestion/review, one municipality and discipline at a time; (3) manufacturer official manual and recall connector with exact model match and approved PII controls; (4) expanded SOP feature vocabulary and work-order coverage for fireplace/garage and commercial PCA; (5) signed qualified-inspector holdout samples and separate severity/coverage metrics; (6) release-gate CI and human signoff. Do not lower required evidence to make an automation green.
