# Territory encrypted-session recovery

This extends the installed territory system. Do not repeat the completed 39-segment source transfer or replace the 138 pinned originals. Transport completion is not a territory-card approval.

## Verified software baseline

Recovery implementation commit: `2a4efbe32459ff630be6ba2b1bb7fe144deb48d2`.
Hosted rerun: `34530217442`, source commit `90f8718190edad2291beef869295f64baebd85e2`.
The saved receipt `evidence/recovery-34530217442.json` records 207 tests, zero failures/errors/skips, and 138 original files verified before and after testing. This is an internal software review with synthetic cryptographic fixtures, not independent visual qualification. The Ubuntu execution is verified; Windows-specific runtime is not.

## Existing authenticated owner workstation

Run with the owner's existing GitHub CLI authorization and the installed production requirements. No paid model API is used.

```sh
python territory/production/client.py /private/job --output /private/result --kind candidates
python territory/production/client.py /private/visual-job --output /private/visual-result --kind visual
```

The client saves `result-client-key.json` or `visual-result-client-key.json` beside the output, outside the input job. The file contains a private decryption key and must remain private. Never commit it, paste it into an issue, or include it in the job archive.

## Resume the same session

```sh
python territory/production/client.py --output /private/result --resume
python territory/production/client.py --output /private/visual-result --resume
```

Repeating the original command also resumes its saved checkpoint. `--once` advances one recovery step; exit code 3 means pending, not failed or approved. Exit code 0 means an authenticated result has been installed and its exact file hashes match the saved delivery record. Read the returned card gates separately.

Requests and exact encrypted inputs are checkpointed before publication. A lost network response does not authorize a second logical job. Existing authenticated results are recovered first, even if the input directory is no longer available. A legacy key-only checkpoint can retrieve an already-published result, but cannot resubmit unbound inputs.

Changed source files, a different output location, a changed worker key, conflicting published inputs, unsafe key-file permissions, or modified returned files stop recovery. Keep the checkpoint; do not delete it to force a pass. An expired worker does not silently start a duplicate session.

## Failure diagnostics

The visual worker publishes only opaque session metadata, a stage and a generic code. Private street names, pixels and model observations remain inside encrypted returns. `protocol_error` at `receive_input` requires generating a new valid envelope through `sealed.seal`; editing authenticated metadata is not a repair. `authentication_error` requires investigating key/session/payload identity. `input_window_expired` means no accepted input arrived in the advertised window.

The old session `28e5c84fbff947208243da2c13221788` used an incompatible suite/ephemeral_public header. The current v1 envelope requires version, session, purpose, sender, receiver, nonce and ciphertext. Its unsuccessful run is historical failure evidence, not a critic result.

## Remaining release requirements

The actual accepted/rejected-card critic suite, full-card and regional readability, geographic completeness, source/work-color preservation, and the original exact-final-file review/repair/retest/release gates remain mandatory. A pair of passing label crops would not qualify the whole card system. No real card release is authorized by this runbook.
