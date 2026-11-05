# K.O. Enterprises Client-Document Critic Gate (Pilot v1)

Applies to Market Intelligence, Contractor Operations, and future business lines. The repo is PUBLIC. Do not commit customer data, invoices, secrets, identifying prospect information, or confidential research.

## No client-facing issuance until all checks pass

1. Verify every significant factual claim against accessible, licensed primary or appropriately corroborated sources; retain specific quoted excerpts, observation dates, versioned evidence and explicit uncertainty. A URL does not prove a statement is true.
2. Evaluate opposing evidence and source conflicts. Unsupported or contradicted important claims block release; never make up missing information.
3. Recheck official procurement announcements and amendments within 24 hours, including mandatory meetings, eligibility, capacity, deadlines and status. Unknown client eligibility cannot be presented as a verified go decision.
4. Offer conditional, client-specific options with limitations and tradeoffs; avoid commands or implied guarantees. Mandatory legal requirements must still be reported faithfully. Suggestive language is NOT a liability shield.
5. Review each rendered document page for spelling, layout, legibility, links, citations, tables, chart denominators, arithmetic and professional tone. No generic boilerplate.
6. Have an actually independent reviewer examine the original sources, contrary evidence, legal/regulated-work boundaries, sensitive information and publication quality. A reviewer name written into a JSON file cannot establish independence.
7. Release acceptance requires every mandatory control and an independently supported quality score strictly above 9.0/10. Unverified checks, missing review evidence or an unresolved issue => HOLD; fix and retest. Reopen approval after material changes.
8. Keep CEO authorization separate. The existing PAUSE_AUTONOMY file blocks automated external activity. NEVER automatically email, publish, deploy, sign, invoice or transmit.

## What the present implementation does

The module at src/company_os/document_quality.py checks declared source metadata, source identifiers, issuer freshness, basic corroboration, required narrative sections, conditional options, privacy flags, credential-like strings, and reviewer attestations.

Its READY_FOR_OWNER_APPROVAL status means only that metadata passed the deterministic gate. It does NOT validate source content, independent reviewer identity or actual visual quality. The can_publish field is ALWAYS false.

Run: PYTHONPATH=src python -m unittest tests.test_document_quality -v

Run a public-safe candidate: PYTHONPATH=src python -m company_os.document_quality candidate.json

## Mandatory follow-on work (not finished)

- Authenticated independent reviewers and signed review records.
- Actual source retrieval, excerpt matching, semantic contradiction tests and provenance snapshots.
- Private customer data store with permissions, retention, deletion and audit.
- Real PDF rendering and visual multi-page review evidence.
- Professional compliance review of customer agreements and liability exposure.
- Explicit owner approval before client delivery; audited delivery mechanism.
