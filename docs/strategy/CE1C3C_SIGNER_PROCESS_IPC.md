# CE-1C3c — One-Request Local Signer Process and Peer-Verified IPC

**Date:** 2026-11-05  
**Status:** Offline Linux process-boundary engineering prototype, not a deployed protected signer or authenticated issuer service.  
**Code:** `src/company_os/capture_signer_ipc.py`  
**Tests:** `tests/test_capture_signer_ipc.py` using actual Linux forked child processes and synthetic PDF bytes; no live sources, protected keys or external data.  
**Previous:** [CE-1C3b root-governed capture trust](CE1C3B_CAPTURE_TRUST.md).  
**Production release:** Blocked by `PAUSE_AUTONOMY` and `PRODUCTION_RELEASE_CONTROLLER_CERTIFIED=False`.

## What was implemented

A single-request local Unix-domain-socket protocol provides an **explicitly separate OS process** capable of signing and recording a staging-only, Ed25519-attested local file record. It has no TCP listener, source-fetch action, queue, publishing command, or business activation function.

- Uses Linux `SO_PEERCRED` to authenticate the client UID. The IPC client also inspects the signer server's kernel UID. Normal mode **refuses same-UID client and signer**. A clearly named `test_only_same_uid` option supports Linux CI and must never be enabled in production.
- The signer process must possess an *injected* private key matching a key in the independently root-signed, valid, nonrevoked governance policy. Its key stays out of the source-fetch and IPC-client modules. It fails closed on revocation, wrong key, invalid/expired policy, incompatible source host or malformed file metadata.
- The framed JSON protocol has a strict maximum message size (8KiB), required-field schema, duplicate JSON-key rejection, and a short socket timeout. Only one `attest_staged` request is supported. The socket is removed after the operation; there is no persistent daemon or implicit scheduler.
- Signer re-reads actual staged bytes, checks their digest, size, approved host, file path, policy and signer roles. It signs only `local_staged_bytes_unverified` with `original_issuer_authenticated=false` and `publication_authorized=false`. The local replay ledger must accept the new receipt before any response is returned.
- The client checks server OS UID, Ed25519 receipt signature, root policy/revocation state, and exact requested file metadata, rather than trusting an IPC response marked successful. Forged sockets cannot simply return unsigned claims.
- The company emergency pause is rechecked at startup, on incoming requests, and immediately before the record is committed.

## Tested scope vs real security isolation

The tests use two actual Linux processes **under the same CI OS user**, and therefore do **not** establish a separate privileged security domain or key custody. A production design requires separately restricted OS users, protected secret provisioning/HSM or KMS, a shared read-only staging mount, an IPC socket accessible by a specifically authorized client via owner/group/ACL, and monitoring/restart semantics. The current private `state/` path uses 0700 permissions and is **not** a working cross-user production deployment configuration. A privileged insider with control over both processes could still mint misleading local staging records. This does not justify production acceptance.

The local audit hash chain is not externally anchored, cannot independently prove true issuer authenticity, and is not a real-time permissioned issuer portal collector. Only the pre-existing CE-1C2 *offline* original package checker can assess PDF inventory, and it cannot guarantee hidden bid portal addenda are complete. Nothing here issues CE-1C2 authenticated-live-original receipts.

## Acceptance evidence / blockers

- Verify full repo Python and Node tests, including child-process signing, wrong signer/peer UID, forged local socket, changed PDF, malformed/truncated/oversized IPC, no-repeat socket, pause enforcement and no publication.
- Verify original production signing/release/financial logic and company-wide emergency controls unchanged.
- **Independent critic not executed.** Only internal review plus automated CI, not external signoff.
- Next: CE-1C3d protected *deployed* signer identity, ACL and key custody; authenticated original issuer transport receipts, audit anchoring and issuer change inventory. Then CE-1D independent critical review and company-wide monitored release controller.

No production deployment, real client delivery, source scraping, spending or venture launch is authorized by this checkpoint.
