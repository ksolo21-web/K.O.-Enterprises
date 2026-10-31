# Home Inspection — v1.3.1 pinned runtime proposal and recovery checkpoint

**Status: SOURCE AND OFFLINE TESTS PASSED; REAL INFERENCE / EXTERNAL COMPUTE NOT RUN.**

- Parent repository: `ksolo21-web/K.O.-Enterprises`, branch `home-inspection-development`.
- Existing root `main` branch must remain unchanged. The proposal exists only in the development branch.
- Previous v1.3 base: 165/165 unit tests passed. New v1.3.1 local suite: 172/172 passed after generating only synthetic fixtures.
- Fix: official Ollama v0.40.13 Linux amd64 archive, 1,525,346,571 bytes, SHA-256 `c9490e0f520be21271d969e6703f012268b1d39f8b70dd58854e5bfef7a75bb6`. Metadata retrieved from `https://api.github.com/repos/ollama/ollama/releases/tags/v0.40.13` on 2026-10-30.
- Added fail-closed local verification before decompression; no runtime execution of downloaded install.sh; no checksum operator input.
- Added SSD space preflight and removed the compressed archive after verified extraction. No assumptions that 16 GB RAM means unlimited disk; runner lists only 14 GB SSD.
- Repo remains public; any activation may use ONLY rights-cleared synthetic fixtures; no customer files, identifying data, addresses, paid services, accounts or deployment.
- Root `PAUSE_AUTONOMY` still blocks external/scheduled operations. `workflow_dispatch` remains unregistered on default branch. Approval and workflow activation remain owner-reserved.
- No actual Ollama release binary was downloaded, verified or executed by this task. No model weights or live vision results exist here.
- This is an **internal review**, not a separate critic agent; no autonomous inspection or real defect accuracy pass is claimed. No customer release.

## Resume next

1. Check branch and main heads, reread this checkpoint and `docs/GITHUB_CPU_VISION_TRIAL_v1.3.md`.
2. Revalidate release asset metadata/checksum if altering version; keep exact checksum and size checked before any extraction.
3. Run offline suite, YAML/schema and bash syntax tests after any edits.
4. Obtain explicit CEO authorization for a narrowly scoped synthetic-only GitHub run and any default-branch registration / paused-state governance exception **before** dispatch. Do not infer consent from generic 'continue'.
5. Only after authorized activation, gather timestamped full test logs and model digests, and independently assess actual zoom/video tool requests. Synthetic success is not professional home-inspection accuracy.
