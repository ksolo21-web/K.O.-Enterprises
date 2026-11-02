# Milestone 3 V8 — private report-model audit increment

**Branch:** `home-inspection-development`  
**Status:** Engineering addition under test; original Milestone 3 acceptance remains **OPEN**.

V8 is the active engineering baseline. This addition does not constitute a V9/V10 milestone, model-accuracy evaluation, professional signoff or production authorization.

## What changed

`inspection_engine.proposal_evidence.PrivateProposalAudit` is a private, append-only-by-filename journal for model calls. The local report `propose` command now accepts an optional `--audit-dir` (a **new** directory under an existing private parent). When supplied, a complete pre-generation request event and the filtered generation-response envelope are recorded before JSON decoding/source interpretation. Inference failures keep their preceding request events and mark the manifest FAILED. The manifest records event count, per-event file SHA-256, storage byte count and explicit no-release flags.

A missing response event means **no completed response was captured**. A request event does not prove generation reached the server. Even a completed response is unauthenticated model output; semantic accuracy requires independently reviewed source comparison. The journal does **not** certify the model binary, professional credentials or original PDF custody.

```bash
# From ventures/home-inspection, using an already installed digest-pinned local model.
# Explicit operator action only; does NOT override PAUSE_AUTONOMY or enable learning.
python -m inspection_engine.report_study_pipeline propose \
  --reference /private/case/reference.json \
  --registry /private/study/registry.json \
  --source-pdf /private/case/original.pdf \
  --study-dir /private/case/prepared \
  --model YOUR_ALREADY_INSTALLED_MODEL \
  --model-digest VERIFIED_64_HEX_DIGEST \
  --timeout 120 --max-calls 25 \
  --audit-dir /private/case/new-private-inference-audit \
  --out-dir /private/case/new-proposed-report
```

### Verify the captured journal against the model-proposal receipt

Run this **offline**, after a successful `propose` invocation:

```bash
python -m inspection_engine.proposal_evidence \
  --audit-dir /private/case/new-private-inference-audit \
  --proposals /private/case/new-proposed-report/model-proposals.json
```

The verifier checks all recorded event file SHA-256 values and sequence, total recorded bytes, exact prompt bytes, PNG bytes, parsed model-response identity, call counts and the model proposal receipt digest. Missing or substituted evidence blocks the integrity check. It cannot prove the model really ran or that interpretation was correct. Local coherent rewrite of **both** unsigned records remains possible without an external trusted record.

### Privacy boundary

The audit journal contains original page images encoded as base64, report excerpts, model prompts, response text, and possibly sensitive private case information. Keep the directory under authorized local private storage; files use mode 0600 and its directory 0700 on POSIX. **Never commit, publish or upload a journal to this public repository.** OS/user compromise, filesystem rollback, plaintext at rest, and authenticity of the source reports remain outside this software-only control. The app performs no automatic upload from this journal.

A journal can reach its 512 MB total/800 event budget, in which case the operation fails closed rather than dropping data. Event files are limited to 25 MB. A hard crash can leave an incomplete manifest: preserve the event files as incomplete evidence, not as a pass.

### Acceptance checks

- [x] Exact pre-generation request capture is wired to the real V8 propose CLI.
- [x] Filtered raw completion envelope is saved before parsing and source validation.
- [x] Deliberate failed generation retains attempted requests, without forged responses.
- [x] New-only private folder, exclusive file creates and bounded bytes/events.
- [x] Focused class tests, controlled V8 CLI assertion, offline journal-to-proposal verifier and tamper rejection added.
- [ ] New GitHub offline CI run independently confirms focused and full regressions.
- [ ] Real digest-pinned image-conditioned inference, frozen-source comparison and independently reviewed semantic evidence.
- [ ] Authenticated qualified inspector signoff and consent/provenance evidence.
- [ ] Legitimate production key enrollment and owner-authorized activation/rollback field trial.
- [ ] Release approval: **withheld**.

**Non-regression:** `main`, root `PAUSE_AUTONOMY`, live customer release and production lesson activation have not been modified by this increment. A GitHub Actions workflow is dedicated to offline unit tests only; it sets `COMPANY_OS_PAUSED=1` and never pulls or calls local vision models. The separate vision-trial workflow remains gated/blocked by the repository pause.
