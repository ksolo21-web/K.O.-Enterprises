# Privacy and Data Policy

## Default posture

Collect no personal data in Phase 0. Store portfolio records, public-source evidence metadata, approvals, costs, and experiments locally. Do not copy source material wholesale when a citation, short note, and hash are sufficient.

## Data classes

| Class | Examples | Rule |
|---|---|---|
| Public | public documentation, licensed datasets, published prices | May be referenced with source, date, license/terms, and freshness metadata. |
| Internal | scores, draft strategy, experiment design, cost estimates | Keep in approved state/repositories; share only deliberately. |
| Personal | name, email, IP address, account identifier, interview notes | Collect only for a defined approved purpose and retention period. |
| Sensitive | credentials, financial/health/government data, precise location, minors' data | Prohibited by default; requires explicit CEO approval and reviewed lawful handling design. |
| Secret | tokens, keys, passwords, signing material | Approved secret store only; never Git, reports, prompts, or logs. |

Public availability does not remove privacy, license, or terms obligations. Do not scrape around access controls, create dossiers, infer sensitive traits, buy lead lists, or repurpose data incompatibly.

## Before collecting personal data

Document and approve:

- the precise user benefit and lawful basis;
- fields collected and why each is necessary;
- notice, consent where applicable, access/deletion process, and processor list;
- storage location, encryption, access roles, retention/deletion schedule, backups, and incident plan;
- cross-border, children's-data, biometrics, marketing, and automated-decision implications;
- a data-flow diagram and security review.

If these items are absent, do not collect the data.

## Retention and rights

Use the shortest practical retention period. Deletion must cover active systems and age out backups under a documented schedule. Product repositories must implement applicable access, correction, export, objection, and deletion workflows before collecting customer data.

Model prompts and third-party APIs are disclosures to another processor unless an approved configuration proves otherwise. Do not send personal, confidential, or secret data to a model or API without explicit authorization and a reviewed agreement/configuration.
