# M4 V10 — private source-byte custody acceptance scope

Status: engineering work in progress, not a passed gate or production approval.

Baseline: V9 source-media grounding (1,044/1,044 synthetic tests on prior checkpoint). Existing V8/V9 thresholds and signed review workflow stay unchanged. Keep `main`, `PAUSE_AUTONOMY`, customer release and real data outside Git untouched.

Implementation target: private outside-Git source locators; real SHA-256 rehash; image decode and bounds; original-video probe; replay frame pixels and timestamp from parent video; explicit failure on missing or mismatched bytes; offline tests including tampering and file path attacks.

Remaining external M4 blockers: genuine independent custodian and pins; professionally authenticated inspector qualifications and labels; consented real holdout of at least 100 cases, at least 30 critical defects, 13 systems, residential/commercial, zero serious misses and 95% precision; effective insurance, liability and release procedures.

Milestone 5 is to begin as pilot-readiness engineering only after V10 code-level gates are checked. Never call synthetic code checks real inspection competence.
