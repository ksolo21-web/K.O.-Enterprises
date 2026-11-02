# M3 v9 preflight recovery — unapproved

Continues v8 at `5b3b6a652db8ac766c2be51cdfe1ba0aafbe7db0` on the development branch. Original M3 remains incomplete; this checkpoint is not a substitute for real professional or field evaluation.

## Recovered work

The workspace reverted to an older clean v7 checkpoint during the session. GitHub retained v8, which was restored by a fast-forward. Uncommitted fixture/runtime work was absent after that event. The scripts and three synthetic fixtures were rebuilt; the authoritative replacement oracle is `f091c67e20813e4a904aa2d734beb7b8481c9ea7d428c92fbc6fb8b7a35840b1`. No actual model generation was launched. Prior scratch-only runtime download receipts do not establish an available runtime after recovery.

The proposal schema now requires nonempty source anchors, explicit rows/cells, image regions for figures and blank cells, supported system values, bounded titles/locations and safe IDs. Source validators remain authoritative for source matching, sorted OCR IDs, nonoverlapping cells, rectangle geometry and cross-reference validity. A schema-conforming model answer can still be wrong or fail validation.

An optional audit callback records a copy of the exact request and a filtered raw response envelope before interpretation. It excludes `thinking`, `context` and unknown fields. The callback receives source material and images; callers must choose appropriate storage. Audit failure propagates, with no automatic retry. A request event proves an attempt was about to be made, not that the server completed a response.

## Frozen cases and acceptance

`python -m scripts.m3_source_reading_probe --out-dir NEW_DIRECTORY` creates synthetic A (affirmative), B (negation), and C (image-only scan of B). It imports all three into a locked holdout registry before preparing OCR. Each table has four rows, three columns, a header, an inspection limitation and one deliberate blank. All 36 cells matched printed gold; all three rendered pages were visually inspected internally. Public evidence contains PDFs, rendered PNGs and the oracle; regenerate preparation directories locally, because their receipts include local paths.

Required future gates remain separate: completed transport/source custody; exact cell words/quotes; table positions/spans/roles/blank regions; omissions/extras; actual narrative polarity and inspection scope. Free-form descriptions require direct review. Passing one group cannot offset another group's failure. Three tiny synthetic pages cannot establish professional competence.

## Review and tests

Seven controlled transport/schema tests and four actual synthetic PDF/OCR custody tests pass. The home-inspection full regression passed 839/839 in 159.354 seconds; the four newly added fixture tests passed separately in 3.934 seconds. This is 843 distinct tests across two commands, not a claim that one command discovered 843. No real inference, enrollment, lesson activation, remote workflow or production action occurred.

The separate critic returned a usage-limit error before completing this review. Only an internal review was performed. Independent approval and the >9 acceptance score are withheld.

The corrected company command is `PYTHONPATH=src python -m unittest discover -s tests -v`. It ran 229 tests with one failure, zero errors. The unchanged OANDA fixture uses the current price time and expects eligibility even during the production rule's forbidden UTC hours (20 and 21); this run occurred at 20 UTC. The original wrong invocation's nine import errors and corrected log are both preserved. No trading code or tests were changed.

## Resumption

1. Independently review the recovered recipe, proposal schema/audit hook and an explicitly bounded owned-process local runner.
2. Reacquire and verify the previously pinned Ollama archive and qwen2.5vl:3b blobs; never assume scratch downloads survived.
3. Verify the exact frozen oracle and prepared sources before calls. Maximum three calls, one per case, maximum 180 seconds each; no silent retries, no cloud or remote workflow.
4. Preserve raw filtered replies and failures; score structure and inspect actual polarity independently; stop only owned runtime processes.
5. Retain all deferred professional, field, enrollment and activation gates. Keep `main` and `PAUSE_AUTONOMY` unchanged.
