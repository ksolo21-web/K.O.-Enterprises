# Michigan-first expert inspection knowledge — case-specific verification v3

**State:** implemented as an offline, read-only, fail-closed initial legal registry, evidence gate, failure-mode prompts, and case audit. **Not** a licensed, comprehensive Michigan building-code database, exhaustive diagnostic expert, or inspection substitute. No customer reports are authorized.

## What the owner is building

The engine should behave like a team of inspectors, forensic building scientists, trade specialists and a separate technical reviewer: observe evidence; find and prioritize potentially missed conditions; reason about competing failure mechanisms; identify needed measurements/tests; select the applicable **legal** source; cite actual provision and equipment instructions; solicit qualified judgment; and preserve all disagreements, unknowns, and limitations. LLM memory is never the legal or factual source of truth.

## Primary Michigan references: snapshot 2026-10-31

- Michigan Bureau of Construction Codes current code books: https://www.michigan.gov/lara/bureau-list/bcc/rules-acts/codes/code-books
- Residential and residential-energy court-order / open-rule status: https://www.michigan.gov/lara/bureau-list/bcc/rules-acts/rules/currently-open
- Michigan code-enforcement jurisdiction list (building, electrical, mechanical, plumbing may differ): https://www.michigan.gov/lara/-/media/Project/Websites/lara/bcc-media/ASD/StatewideJurisdictionList.pdf
- Michigan Building Permit Information: https://www.michigan.gov/lara/bureau-list/bcc/sections/permit-section/permits/building-permit-information
- US DOE Michigan energy-code status: https://energycodes.gov/status/states/michigan

Registry `knowledge/michigan_code_authorities_v1.json` contains **10 authoritative code-status/index entries**, including stayed residential code proposals. It is **not** an exhaustive paid/controlled code text archive. It records references and legal status at a point in time. Source content may change; confirm before each case. Never infer a local ordinance from statewide adoption or a permit status from inspection date alone.

**Current LARA listing:** 2015 MRC for one- and two-family residential; 2021 MBC for commercial/general construction; 2021 rehabilitation code; 2021 mechanical and plumbing; 2023 NEC with Michigan Part 8 amendments; 2021 commercial energy. The planned 2021 residential and residential-energy updates have been affected by July 7, 2025 litigation; the state page continues to list the older residential rules as operative. **Verify litigation/effectiveness for every case.** Local fire, accessibility, property-maintenance, land-use, floodplain, historic, accessibility and specialized occupancy requirements require additional research—not automatically included or represented as checked.

**A building's current condition and its original code obligations are different questions.** The governing edition can depend on the actual type/occupancy, construction and permit dates, alteration history, local amendments, exceptions, retroactive safety requirements, and the AHJ for each discipline. A photographed concern is not automatically a code violation, and a code-index link is never a sufficient citation to an exact rule.

## Case-specific technical verification workflow

1. **Intake and scope:** classify one-/two-family residential or commercial/general; record MI county and municipality, occupancy, inspection date, scope/limitations, build/permit/alteration timeline. Unknown class must block code selection.
2. **Find correct authority:** state/county/local AHJ separately for building, electrical, mechanical and plumbing; jurisdiction list is a starting index, not case verification. Record the official enforcing agency, source and verification date. Local fire and property-maintenance ordinances require additional jurisdiction research.
3. **Observe and preserve:** original image/video file ID, SHA-256, source timestamp, original dimensions, room, system, inspector access limitations and tests actually performed. No source pixels = unknown, not 'no defect'.
4. **Diagnose carefully:** recorded visual symptom, possible mechanisms, competing alternatives, confirmatory and discriminatory measurements, independent site history and safety escalation. The 13 playbooks (46 feature codes) are **non-exhaustive prompting aids, not confirmed causes**.
5. **Code or product application:** only after exact construction/permit history and a matched official edition, record the precise section identifier and verified official provision text/location; manufacturer part number/manual revision if relevant. Do not fabricate full code text or redistribute restricted ICC/NFPA materials in a public repo.
6. **Qualified adjudication:** separate Q01 custody/coverage, Q02 independently grounded technical review, AHJ/code reviewer when a legal allegation is made, and qualified human inspector approval. A caller-supplied boolean or name is **not** an authenticated signature. Independent auth and professional release remain separate unimplemented gates.
7. **Coverage audit:** 46 system descriptor codes remain unverified until they are actually documented; visually inaccessible items are specifically listed as limitations. Check for omissions, duplicate findings, area coverage, contradictory evidence and latent hazards requiring instrument testing.

## What this release actually builds

- `inspection_engine/michigan_authority.py`: immutable defensive registry loader; scope/date filters exclude stayed editions; builds safe, bounded MI context for relevant specialist work orders.
- `inspection_engine/failure_modes.py`: validates all 13 symptom/alternative/verification playbooks, mapped to exactly the 46 production feature codes.
- `inspection_engine/case_verification.py`: validates Michigan case metadata and original case media hashes; gate for proposed findings, legal claims, causal language, evidence custody and presumed reviewer signatures. All outcomes remain release-blocked.
- `scripts/case_knowledge_audit.py`: runs a private local JSON audit against a local case and finding file without publishing evidence or calling a remote AI.
- Latest live `inspection_engine/agents.py` integration: Michigan source-status limits only when `property.state` is `MI` or `Michigan` and building type is explicit; all specialists receive differential reasoning prompts. System knowledge v2 remains in place.

### Example, local private records only

Run from `ventures/home-inspection` after preparing actual case JSON with the required fields:

```bash
python -m scripts.case_knowledge_audit private_case/mi_case.json private_case/proposals.json \
  --case-root private_case --out private_case/knowledge_review.json
```

The input case must have `case_id`, `state: MI`, `county`, `municipality`, `building_type`, `inspection_date`, `work_type`, and `media: [{id,path,sha256}]`. Each proposed finding includes `claim_type`, `system`, `feature_code`, `observed_symptom`, `evidence_ids`, and a `cause_assessment` marked `unknown` or `hypotheses_only` (with competing mechanisms and verifying actions where used). Code findings additionally require jurisdiction, permit history, amendments and exact provision receipts, **and still cannot be approved automatically**.

## Mandatory expansion backlog — not falsely claimed finished

1. Permissioned full Michigan amendment/code provision retrieval with legal publisher, exact section history, source snapshot hashes, review date, conflicts, and copyright-safe excerpts; LARA administrative rules must be verified against adopted texts rather than a broad codebook index.
2. County/municipal AHJ locator and separately maintained local fire, property-maintenance, floodplain, zoning, accessibility and related ordinances. Michigan-specific baseline does not make every local ordinance applicable.
3. Commercial building use groups, business occupancies, high-rise, multifamily, mixed-use, special inspections, equipment categories and professional disciplines; separate SOPs and building-code expertise from routine residential visual inspection contracts.
4. Manufacturer manuals **by exact model and revision**, labeled equipment, applicable recalls **by exact product match**, service history, and time-bound interpretation with physical documentation.
5. Physics and causality: moisture movement, hydrostatic load, structural deflection, material aging, fire life safety, ventilation/combustion, electrical hazards, thermal bridges, soil and foundation movement, differential diagnosis with structured tests and measured uncertainty.
6. Independent qualified field benchmark cases including hidden and known defects, negative controls, varied seasons/lighting, original videos, systematic false negatives/false positives and missed-system metrics; oversight for urgent hazards and limitations. No promise of 100% detection.
7. A secure, authenticated professional review/sign-off service; non-public customer storage and redaction/retention policy; full multi-agent independent Q02 infrastructure; audit trails with tamper-evident linked receipts.

## Acceptance evidence and limitations

The local combined baseline (v2 full source plus these additions) passes **251/251 tests**. It is a local reconstructed copy, **not** a complete clean checkout of the most recent development branch and **not** a remote GitHub Actions validation. Code enforcement authority, code-provision text, field defect accuracy, human authentication, and client release remain **OPEN**. The `PAUSE_AUTONOMY` governance file remains unchanged; no new external compute trial is authorized or run here.
