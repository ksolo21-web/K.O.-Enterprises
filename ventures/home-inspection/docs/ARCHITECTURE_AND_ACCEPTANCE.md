# Architecture, agent responsibilities and resumable quality gates

**2026-10-30 | Draft implementation checkpoint | Evidence-based engineering**

```text
Kaleb — Owner / business authority
└── M00 — Inspection Director (workflow, routing, integration)
    ├── Evidence & Knowledge Lead
    │   ├── M01 — Intake/asset tagging and file-integrity agent
    │   ├── M02 — Location and coverage tracking agent
    │   ├── M03 — Property type / feature description agent
    │   └── L01 — Learning and Evaluation Analyst
    ├── Technical Lead
    │   ├── Structural/foundation/subfloor specialist
    │   ├── Exterior/roof/drainage specialist
    │   ├── Electrical specialist
    │   ├── Plumbing and water heater specialist (T07)
    │   ├── Heating/cooling specialist (T08)
    │   ├── Attic/insulation/ventilation specialist
    │   └── Interior/site/safety specialists
    └── Report Lead
        ├── Natural-language narrative and consistency editor
        └── Editorial navy report layout/photography assistant

Independent release and controls (not accountable to M00):
Q01 — Evidence/coverage critic (may block)
Q02 — Technical accuracy/unsupported claim critic (may block)
Qualified human review and signature (must pass before client delivery)
```

An `agent` is a **role specification**, not a running LLM worker. No specialist agent runtime is deployed by this prototype. Labels T07 and T08 are conserved from the approved original design. Technical specialists may propose findings; they may not declare a home condition or evidence coverage fact that their source does not support. Q01/Q02 cannot be overruled by the Report Lead.

## Required report facts

For each system: type of system, material/design where visible, observed components, condition, evidence references, inaccessible/absent view, reviewer confidence, and whether referral is warranted. Do not collapse `not observed` into `no issue`.

## Photo/video protocol

Original file → SHA-256 + system/room provenance → frame or photo reference → agent provisional observation → second-pass critique → inspector's correction → report. For video, an agent must identify the exact reviewed frame/time; this is an unimplemented milestone. Observations with missing original evidence or field-author attribution are not accepted.

## Equipment research protocol

Recorded brand/model/serial + label photo → manufacturer-specific research → official URL + retrieval date + dated evidence → manufacturing month/year candidates → conflict/uncertainty flag → human verification. Installation date is a separate, never-implied field. Bradford White's year code is cyclical, and the sample shows why a 'code-only' date must not be phrased as independently verified.

## Learning and validation

Human reference report → parse structured systems/findings → align to agent result → missed/extra/contradiction ledger → human adjudication → approved labeled examples → holdout regression checks → candidate update → independent review → release. The current comparator handles structured observations only; it does NOT autonomously learn an image model or extract arbitrary scanned report content.

## Acceptance checklist for v0.1

- [x] Document 13 system coverage subjects (all documented or visibly unverified)
- [x] Validate media provenance IDs and local path safety
- [x] Distinguish photo-only, video-only, mixed inventories
- [x] Generate a deterministic editorial navy PDF with embedded user-provided image (sample uses synthetic image)
- [x] Decode Bradford White and one published Rheem water-heater format with source attribution and ambiguity/future-date detection
- [x] Compare structured human-vs-agent observation sets without self-training
- [x] Reject unsupported report release and incomplete review
- [ ] Automatic photo interpretation and finding extraction
- [ ] Real video processing and timestamped evidence extraction
- [ ] Multiple-brand online manufacturing-date verification
- [ ] Human report ingestion from an arbitrary PDF
- [ ] Qualifying human reviewer workflow and electronic sign-off
- [ ] Real property inspection validation, legal/privacy/insurance and QA approval
- [ ] Dedicated GitHub repository and remote commit

`output/` holds generated demonstration artifacts; no customer media or identifiable property information belong in a public repository.
