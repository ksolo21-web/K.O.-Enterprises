# CE-1C3d — Restricted Linux Signer Host and Distinct-UID Test

**Checkpoint:** 2026-11-05 · **Status:** Offline deployment-reference engineering only. **No real issuer capture, no production credentials, no authorized launch.**

**Code:** `src/company_os/capture_signer_host.py`, `src/company_os/capture_signer_ipc.py` and `src/company_os/capture_trust.py`.  
**Evidence:** `tests/cross_uid_signer_ci.py` runs as root **only on opted-in disposable GitHub Linux runners** and drops to separate synthetic numeric UIDs. Test secrets and synthetic original PDFs are created only under temporary ignored directories and destroyed with the runner.

## Why this increment exists

CE-1C3c demonstrated a separate process but with the **same OS user** and an owner-only socket path. That cannot establish that a compromised source collector is unable to read its signing key. CE-1C3d adds an opt-in separately provisioned group/ACL layout and a real cross-UID exercise **without enabling any actual continuous service**.

### Strict signer host

The one-shot `python -m company_os.capture_signer_host` entrypoint:

- Requires a **nonroot signer UID** and a **distinct nonroot capture-client UID**.
- Loads exactly one 32-byte Ed25519 private seed from an outside-the-repository file owned by the signer, mode `0400`, within a signer-owned mode `0700` secret directory. Symbolic links, multiple hard links, mismatched file identity, wrong owner/mode/size and in-repo keys block. This is **a file-permission prototype, not an HSM/KMS**.
- Verifies a recent root-signed policy before starting. A source collector cannot change key authorization, sign as governance, or obtain keys through the socket protocol.
- Refuses operation while `PAUSE_AUTONOMY` or the environment emergency pause is active; no background daemon/scheduler, outbound fetch, publication, live client communication or company launch.
- Requires an externally provisioned **private IPC group GID**. It does not create users, groups, change host ACLs or widen permissions by itself.
- Uses strict kernel `SO_PEERCRED` identity enforcement, Ed25519 receipt checks, staged-file byte rehash and append-only local replay history from prior milestones. Output remains `local_staged_bytes_unverified`; original issuer identity and publication authorization remain false.

### Provisioning contract (not a deployed host)

To operate with truly separate OS accounts, a trusted administrator would have to arrange this structure **without altering live company permissions**:

| Path/role | Expected ownership | Permission |
|---|---|---|
| Shared `state/` and `competitive_engine/` parents | Protected installer/root, shared IPC group | `0710` |
| `signer_ipc/` socket directory | Signer UID, shared IPC group | `2710` (setgid plus `0710`) |
| Socket | Signer UID, shared IPC group | `0660` |
| Private signer `trust/` replay directory | Signer UID | `0700` |
| Staged PDF directories | Capture UID, approved shared group | `0750` |
| Staged PDFs | Capture UID, approved shared group | `0640` |
| Signing-secret directory | Signer UID (outside repository) | `0700` |
| Signing seed | Signer UID (outside repository) | `0400`, one hard link |

Every shared parent is checked for exact ownership/group, no world permission and no group write. In the new opt-in shared mode the worker **does not chmod shared parents back to 0700**. The pre-existing owner-only path remains the default for same-UID synthetic tests. A true OS-level installer must create directories and enforce SELinux/AppArmor/capabilities as appropriate.

The signer should be locked to a source-read-only shared mount rather than a writable capture checkout; an admin who controls root can still forge the files. A protected key file read into a Python process is **not hardware-backed key custody**.

### Actual cross-UID offline CI demonstration

The distinct-UID CI script uses numeric users `53011` (signer), `53012` (capture), `53013` (unauthorized) and numeric shared group `53010`. It creates **no external accounts and no `/etc/passwd` records**. On an ephemeral GitHub runner, the root test harness provisions a temporary directory with private permissions, starts signer and capture subprocesses with different effective UIDs using Linux `setuid`/`setgid`, and verifies:

1. The capture identity cannot read the signer-owned key.
2. The capture identity can complete one kernel-credential-authenticated IPC exchange under the approved shared group and validate a staging-only signed receipt.
3. A third UID is rejected even if it belongs to the same group.
4. Making the signer key world-readable prevents startup.
5. The emergency-pause file prevents startup and socket creation.
6. One-request server cleanup and local replay audit remain in effect.

Only the **synthetic temporary project tree**, which has no real company pause marker, has `COMPANY_OS_PAUSED=0` for the exercise. The actual repository marker and release hard stop remain untouched. GitHub CI is a finite disposable test, **not an always-running signer service**.

### Outstanding acceptance blockers

- A genuine protected deployment with named OS users, security policy, key rotation/custody, service supervision, distinct approved client, shared volume boundary, real original-source attestations and external immutable audit must be tested outside a temporary CI fixture.
- Real permit-scoped lawful issuer retrieval, versioned addendum completeness, authenticated transport logs and nonoperator-origin provenance remain unverified.
- There is no independent factual/visual critic, no production monitoring or company-wide ready release controller. The 12 mandatory quality checks and strict **greater than 9.0/10** standard remain unmet.
- No business launches, issuer outreach, live source crawl, publishing, contracts or spending are authorized. Keep `PAUSE_AUTONOMY` and `PRODUCTION_RELEASE_CONTROLLER_CERTIFIED=False`.

**CE-1C3e follows:** [Permit-bound issuer listing and PDF change journal](CE1C3E_ISSUER_INVENTORY_JOURNAL.md) reconciles staged source-file hashes and optional staging-only receipt trust with listing/link snapshots, while maintaining an explicit original-issuer verification hold.

**Next critical path:** CE-1C3e protected capture receipt from actual authorized original-source transport, audit anchoring, then CE-1D independent adversarial evidence critic and CE-2/4/5 durable company-wide release controller. [Tracking issue #38](https://github.com/ksolo21-web/K.O.-Enterprises/issues/38).
