# Home Inspection M4 — preserved candidate-model research and decision (2026-11-03)

> **DURABLE PROJECT CHECKPOINT / RESTART POINT.** This document records the user-supplied AI model reference and the prior Milestone 4 validated baseline. It is NOT a model activation, license clearance, data sharing authorization, performance claim, or customer release approval.

## User references

- Specific Hugging Face repository supplied: https://huggingface.co/mradermacher/DeepSeek-V4-Pro-Qwen3.5-9B-UNCENSORED-heretic-i1-GGUF
- Related X post supplied earlier: https://x.com/alizeh_ai/status/2117212457693573542?a=7In7QlhPgHlGh5hR5Lg&s=19
- **The contents of the specific X post were NOT independently retrieved.** Do not attribute a detailed claim to it without screenshot/text.
- User instruction on 2026-11-03: **"lets lock all this information in so we dont forget it"**. Preserve project continuity in GitHub; don't rely solely on informal chat summaries.

## Exact identity and verified model card details (as checked 2026-11-03)

- Publisher/quantizer: `mradermacher`; repo as above; **third-party GGUF**, not an official DeepSeek V4 release. The "DeepSeek V4" term in the name does not demonstrate official DeepSeek model architecture or performance.
- Published genealogy in Hugging Face model tree:
  `Qwen/Qwen3.5-9B-Base` → `Qwen/Qwen3.5-9B` → `unsloth/Qwen3.5-9B` → `Jackrong/DeepSeek-V4-Pro-Qwen3.5-9B` → `xtools-at/DeepSeek-V4-Pro-Qwen3.5-9B-UNCENSORED-heretic` → mradermacher's imatrix GGUF. This is *model-card attribution*, not independently audited provenance.
- ~9 billion parameters, `qwen35` architecture. Q4_K_M quantization listing is approximately **5.7 GB** on the imatrix repository. The published listing also includes Q4_K_S ~5.5 GB, Q5_K_M ~6.6 GB, Q6_K ~7.5 GB, and lower-bit alternatives. Quant size is **not** system memory/VRAM requirement. Validate GPU/CPU hardware and context overhead before choosing.
- The publisher labels the model as vision-capable and states `mmproj` files (if any) are in the separate **static GGUF repository**: https://huggingface.co/mradermacher/DeepSeek-V4-Pro-Qwen3.5-9B-UNCENSORED-heretic-GGUF . A real image+text inference round trip **has not been tested**. Confirm the correct architecture/runtime, multimodal projector and actual image input behavior rather than assuming the GGUF alone accepts images.
- Hugging Face displays `apache-2.0` as the repository license. **Do not treat that tag alone as completion of chain-of-title, training-data, upstream licensing, or commercial legal review**.
- The repository documents local `llama.cpp` and `Ollama` execution, including the example `ollama run hf.co/mradermacher/DeepSeek-V4-Pro-Qwen3.5-9B-UNCENSORED-heretic-i1-GGUF:Q4_K_M`. This is documentation only, **not a command that has been executed**.
- "Uncensored"/"heretic" refers to modifications to refusal-related behaviors; it is **not** evidence of improved correctness, reduced hallucinations, professional judgment, safety, or reliability.
- Publisher source card: https://huggingface.co/mradermacher/DeepSeek-V4-Pro-Qwen3.5-9B-UNCENSORED-heretic-i1-GGUF
- Modified upstream card: https://huggingface.co/xtools-at/DeepSeek-V4-Pro-Qwen3.5-9B-UNCENSORED-heretic

## Role decision — preserve as candidate, not deployment

**Decision: EVALUATE AS A THIRD-PARTY, LOCAL, EXPERIMENTAL MODEL CANDIDATE. DO NOT AUTOMATICALLY INTEGRATE OR REPLACE APPROVED PROVIDERS.**

Potential uses: locally analyze source photographs and label/text evidence (ONLY if multimodal proof passes); propose clearly preliminary observations; help specialists request missing evidence; compare textual reasoning on structured photo-grounded reports. It may reduce API costs if compute permits, but total ownership cost/performance is unknown.

Model-selection guardrails:
1. Keep a fixed held-out, permissioned, professionally labeled evaluation corpus. First dry-run on synthetic and public/licensed nonpersonal data.
2. Compare against the original unmodified `Qwen3.5-9B`, the `Jackrong` fine-tune, the heretic/uncensored version, and the currently approved local provider if hardware supports it. Document prompt parity, hardware, version hashes, quantization and projector.
3. Measure **safety-critical defect recall / false negatives**, false-positive rate, visual grounding with quoted source photo IDs/regions, missed material/equipment details, unsupported claims, uncertainty handling, hallucinations, refusal and privacy behavior, runtime cost, memory footprint and latency.
4. Attempt adversarial and out-of-distribution cases, poor lighting, distant labels, cropped/uncropped source, lookalike components, missing evidence, dangerous electrical and roof conditions.
5. **No model, including this one, may create `human_verified` attestations, resolve Q03 release holds, sign professional review, approve building code compliance, fabricate confidence, or enable customer delivery.**
6. Never upload original inspection photos, addresses or private records to Hugging Face, third-party evaluation tools, external APIs, or this public GitHub repo. Local deployment does not eliminate storage, governance or data-handling risks.
7. **No downloads, installs, API calls or real-model evaluations have been authorized by simply recording this candidate**. Any live benchmark remains a separate deliberate action.
8. Do not promote model on inference speed or "uncensored" claim alone; require an independent quality review based on field-accurate labels and pre-registered thresholds. If evidence is lacking, retain `RESEARCH_ONLY` status.

## Milestone 4 validated source-of-truth / continuity

Repository: `ksolo21-web/K.O.-Enterprises`, branch **`home-inspection-development`**, directory `ventures/home-inspection/`. Do **not** modify `main` or root `PAUSE_AUTONOMY`. Real-case credentials, original photos, home addresses, customer files, private generated PDFs and signing keys belong outside Git.

Latest preceding checkpoint documents:
- `docs/CHECKPOINT_M4_PIPELINE_V2.md` — source-bound Q01→specialists→Q02→Q03→private Option 2 PDF, deterministic hashes, resumable stages and fail-closed interrupted inference.
- `docs/CHECKPOINT_M4_SIGNED_REVIEW_AND_PDF_AUDIT_V3.md` — signed declarations from two registered distinct key holders, exact case/report binding, offline worksheet and no-release policy; **not verified professional identity**.
- `docs/CHECKPOINT_M4_BROWSER_AND_PDF_VISUAL_V4.md` — actual synthetic Chromium desktop/Android portrait/landscape review, 13-page PDF raster/visual review, evidence photo full-frame scaling fix, privacy and synthetic acceptance evidence.
- **V4 code baseline:** Git commit `6af4724d75c867cf1cc4b131da2be0c282332666`. GitHub CI run `41553046723`: 892/892 offline tests passed. Synthetic browser and 13-page PDF run `41553019351` passed on image scaling fix commit `96f8efb6a2744c090f6a6bffe22f7e8d60a2518a`. Documentation-only later commits must not be mistaken for new model benchmark evidence.
- Source of truth uses `m4_pipeline.py`, `m4_assembly.py`, `m4_human_review.py`, `m4_review_ui.py`, `m4_pdf_audit.py`, `report.py`. Customer release remains **FALSE**.

**Persistent unresolved production blockers:**
- Real authenticated/qualified inspector credentials and revocation, legally compliant final review/approval, independent QC; two cryptographic signatures do not prove credentials.
- Professionally labeled real defect-detection benchmark, uncertainty/false-negative evidence, consent and calibration; neither Qwen nor the user-supplied candidate has proven inspection accuracy.
- Larger report and accessibility/real-device testing, secure data lifecycle, professional QA of actual consented cases and private delivery controls.
- Separate critic runtime was not available; past review was internal. Never claim a genuinely independent agent executed.
- The full approved Home Inspection business plan should be preserved in existing project checkpoints and business documentation; this model note **does not supersede or change** the business plan, requirements or approvals.

## Next action when user says "continue"

Proceed with the critical-path **Milestone 4** task already authorized (long-form reporting, professional credential gate, and serious-defect measurement infrastructure), **not** by automatically replacing the current model. When evaluating this candidate, first create a metadata-only candidate registry with exact model/version/quant and SHA256 fields, reproducible synthetic comparison protocol, and a credentialed independent quality gate. Only use paid services, external accounts or real customer material with user authorization. Save test evidence and code checkpoints. Report exact verified tests and remaining blockers; approval requires a score strictly **above 9/10 with all mandatory evidence complete**, not a superficial aggregate.

**This checkpoint is the reference to look up in the next chat if user says "remember the Qwen/DeepSeek model" or "continue Home Inspection M4."**
