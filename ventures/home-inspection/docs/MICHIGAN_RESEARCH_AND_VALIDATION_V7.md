# Michigan-first expert inspection — Governed Research and Field Validation v7

**Date:** 2026-10-31. **Scope:** offline, Michigan-first, residential and commercial research support. **Release:** NEVER autonomously releases an inspection report.

## Purpose

The agent needs deeper internal building science than the customer report contains. The internal record retains observations, plausible mechanisms, alternatives, further testing, source/edition applicability, serious-hazard triage, evidence hashes, uninspected areas, and specialist referrals. The report remains an inspector-approved selection of material findings, consequence, action, and material limitations—not an exhaustive codebook or speculative root-cause report.

A visual survey cannot prove that all material defects were found; code compliance is not part of a typical general home inspection simply because code references were consulted. Actual scope follows the pre-inspection agreement and the relevant currently effective residential SOP or separate commercial PCA agreement. The agent and Q02 reviewer make recommendations, not professional determinations.

## Official reading portals — access does not authorize software ingestion

- **International Code Council**, Digital Codes Basic/Public Access: <https://codes.iccsafe.org/>; see the ICC access and restrictions <https://support.iccsafe.org/ht_kb/digital-codes/basic-vs-premium-view/> and copyright terms <https://www.iccsafe.org/about/terms-of-use/>.
- **NFPA** free access to codes and standards: <https://www.nfpa.org/for-professionals/codes-and-standards>. Registration may be required; no account is created by this software.
- **ASTM** federally incorporated standards Reading Room: <https://www.astm.org/standards-and-solutions/standards-and-publications/reading-room>. The publisher warns a federally incorporated edition may NOT be current; free access may require a registered account. Commercial PCA E2018-24 metadata: <https://store.astm.org/standards/e2018>.
- **ANSI** IBR read-only portal <https://ibr.ansi.org/>; this is not proof of Michigan adoption.
- **Michigan LARA** BCC codes and rules <https://www.michigan.gov/lara/bureau-list/bcc/rules-acts>, rulemaking and litigation status <https://www.michigan.gov/lara/bureau-list/bcc/rules-acts/rules/currently-open>, state jurisdiction directory <https://www.michigan.gov/lara/bureau-list/bcc>, official administrative rule viewer <https://ars.apps.lara.state.mi.us/AdminCode/DeptBureauAdminCode?Bureau=Bureau+of+Construction+Codes&Department=Licensing+and+Regulatory+Affairs>.
- **CPSC** public recalls API overview <https://www.cpsc.gov/Recalls/CPSC-Recalls-Application-Program-Interface-API-Information>.

These links are source *locations*, not proof that full code texts or manuals are held locally. The `official_access_v7.json` catalog allows only reviewed URLs and public metadata. Never bypass paywalls, anti-copy systems, site access controls, or portal terms. Library/university access may be personal or limited to reading, and does not by itself authorize commercial AI indexing. Law.Resource.Org/public legal copies may have separate rights and provenance to verify. Full-text machine ingestion remains off until explicit rights and a private audited source receipt are established.

## Michigan rules and locality resolution

The official Statewide Jurisdiction List distinguishes state, county and local enforcement *for each of building, electrical, mechanical, and plumbing*. There can be different authorities, effective dates and temporary assistance. The published directory must be rechecked for the specific case and date; a municipal page or a jurisdiction-list import cannot establish compliance for an existing property.

The 2025 residential and residential-energy code litigation/stay requires tracking what is operative rather than treating a filed draft as effective. Historical requirements need a construction/permit/alteration date and occupancy context. A building code is generally not a retrospective unconditional condition rating.

`statewide_ahj_v7.py` accepts a **human-reviewed CSV transcription** of the current LARA directory with the exact header provided in `knowledge/statewide_ahj_transcription_template_v7.csv`. It retains **a distinct effective date for each of the four trades**, optional unknown dates, and temporary-assistance notes; it rejects unknown enforcement levels, absent trades, duplicate units, invalid/future dates and missing source SHA-256. The state PDF reviewed here shows revision 2026-09-28; recheck before any case. It returns unverified authority *leads*; obtain names and confirmation from the appropriate official AHJ. Not a statewide-data-completeness claim.

`case_research_v7.py` provides a case task list and four discipline checks, plus receipts for operator-reviewed snapshots and change detection. A changed hash means **REVERIFY**, not automatic adoption of an amendment; an unchanged hash does not prove current applicability. Only bounded, human-reviewed metadata may enter the agent prompt. Protected full texts remain outside the public repository.

## Manufacturer and recall practice

`lookup_indexed_model_manual()` from v6 already connects two A. O. Smith published document identifiers to 18 listed model variants. CLI `manual-index` exposes this exact-model **listing**, not the actual installed equipment/manual revision. Proper equipment work requires (a) legible rating plate and source hash, (b) precise brand and full model/serial or lot where relevant, (c) actual dated manufacturer manual and amendments, (d) applicable instructions/installation conditions reviewed by a qualified specialist, and (e) recall match confirmed against *affected ranges*, not product resemblance.

No equipment age derived from a date code is an installation date or warranty finding. A model's visual suggestion cannot prove combustion, wiring, refrigerant, structural, concealed, or other operational failures without relevant testing.

## Serious-defect benchmark: no substitutions

The v5 `serious_defect_benchmark` handles genuine, consented, locked holdout cases, independent labeler/adjudicator identities and counts missed critical/major findings; its pilot minimum is 100 real cases, 30 critical findings, both building scopes and all 13 systems. The new v7 wrapper adds a locked study protocol and an **explicit external credential/consent authentication gate**. Test-only simulated cases never prove field performance. Even a pilot score passing is NOT qualified human release.

**Immediate unresolved evidence:** no customer consented field cohort or separately authenticated professional labels is supplied in this chat; no real-world sensitivity, precision, critical-miss rate or confidence interval can be stated. This is the largest remaining safety blocker.

### Operator-run offline commands

Run from `ventures/home-inspection/` with the proper private case files:

```bash
python -m scripts.knowledge_watch_v7 audit
python -m scripts.knowledge_watch_v7 case --input /private/metadata.json
python -m scripts.knowledge_watch_v7 manual-index --brand 'A. O. Smith' --model 'ATHR-160M 100'
python -m scripts.knowledge_watch_v7 ahj-import --csv /private/verified_transcription.csv --source-sha256 ORIGINAL_DIRECTORY_SHA256 --revision YYYY-MM-DD --operator-id reviewer_id
python -m scripts.knowledge_watch_v7 diff --before /private/source_receipt_1.json --after /private/source_receipt_2.json
python -m scripts.knowledge_watch_v7 benchmark --cases /private/holdout.json --predictions /private/model_detections.json --signed-protocol /private/protocol.json
```

No code performs network crawling, customer media upload, account creation, scheduled tasks, or a paid download. `PAUSE_AUTONOMY` remains in force. Do not commit private evidence, full copyrighted text, source snapshots or identifying case labels to the public repository.

## Mandatory acceptance checklist (do not average over failures)

- [x] Official access restrictions and source URLs encoded; no full copyrighted works embedded
- [x] Michigan four-discipline case research, bulk directory-transcription validator, and manual diff receipts
- [x] Existing v6 exact model-document lookup remains available, and agent v5/v6 packet is extended with v7 legal provenance rules
- [x] Conservative source/provision checks; no silent code violation, defect-free or exact-cause claim
- [x] Independent field-benchmark study protocol and qualification verification blockers
- [ ] Entire Michigan jurisdiction directory imported, effective dates independently checked, ordinances current and contradictions reconciled
- [ ] Every relevant municipality's amendments verified by current AHJ and tied to specific case
- [ ] Full authorized ICC/NFPA/ASTM machine-use licenses or alternate legally permitted public technical provision corpus
- [ ] Broad exact-model manufacturer manual coverage with photographed rating plates and current applicability
- [ ] SOP specialty work orders field-validated (hearth, garage-door safety and separate commercial fire/life-safety PCA)
- [ ] Qualified inspector consents, real holdout cases, double-independent expert labels and serious-hazard performance gate
- [ ] End-to-end GitHub regression and real property safety review; signed professional report release workflow

**No completeness or field-safety certification.**
