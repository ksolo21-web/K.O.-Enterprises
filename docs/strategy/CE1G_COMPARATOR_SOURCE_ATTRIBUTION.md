# CE-1G — Exact competitor/source attribution (offline, internal only)

**Checkpoint:** 2026-11-07
**Status:** Engineering change pending CI and review; no independent source verification, production deployment, customer release or go-live permission.

## Defect addressed

The historical CE-1F dossier schema \`1.0\` has three competitor rows but does not encode **which competitor a claim and its source actually describe**. Therefore one claimed vendor strength, and one purported weakness, could be attached to three different market alternatives. Its structural comparator-count test could not detect that evidence laundering.

Existing \`1.0\` input is deliberately not silently upgraded or represented as source-authenticated: the evaluator adds \`legacy_comparator_attribution_unverified\` to its internal issues and keeps the result **HOLD** (or BLOCK for other defects).

## Additive strict input schema \`1.1\`

The same bounded dossier shape supports \`schema_version: "1.1"\`, with one extra required field on **every** source and claim:

\`\`\`json
"applies_to_alternative_id": "alternative-1"
\`\`\`

- For a source/claim about a specific named alternative, the value is its **exact registered alternative ID**, not the provider's free-text name.
- For generic buyer-value, cost or general market context, use JSON \`null\`. Generic evidence cannot be used to prove a named competitor strength or weakness.
- A \`strength\` or \`weakness\` claim must identify exactly one alternative. All its cited supporting sources and counter-sources must carry the same subject ID.
- A reported competitor **strength** needs at least one subject-matching \`vendor_original\` source, still only **operator-claimed** as original, not certified.
- Every competitor row's \`strength_claim_ids\` and \`weakness_claim_ids\` must refer to claims bound to that exact row's ID. Sharing a strength/weakness claim across multiple competitors, using a rival's page, applying a buyer complaint to the wrong firm, or using a rival counterexample is a **BLOCK**.
- Existing independent-origin, contradiction, stale-source, rights, finite-value, input-limit, positive contribution margin and mandatory counterevidence rules remain in force.
- Unknown, non-string, omitted, or extra subject fields are rejected. \`1.0\` cannot include new fields to spoof an upgrade.

A synthetic three-comparator fixture with dedicated named vendor, buyer, second-source and contrary records per comparator demonstrates the schema. It is **not evidence that those companies exist or that any buyer paid**.

## Acceptance and limitations

- [ ] Run GitHub full Python 3.12 CI and targeted adversarial tests for mixed or cross-attributed sources, missing subjects, rival vendors, reused claims, unsupported original assertions and no-release posture.
- [ ] Run ordinary project tests and security/release-surface audit.
- [ ] Record a review as **internal** unless a separate reviewer actually runs and supplies independent evidence.
- [ ] Do not check CE-1, CE-2, CE-3, CE-4, CE-5 or Market Intelligence M1 as complete from this feature.

**Important:** A matched \`vendor_original\` source is **a statement inside operator-supplied JSON**, not cryptographic evidence that an actual vendor issued the text. A malicious operator could still falsely label a page or forge origin IDs. Genuine issuer authentication, source completeness, legal rights, conflicting offers, paid buyer testimony and operational reviewer independence must be established separately.

**Global controls unchanged:** \`PAUSE_AUTONOMY\` remains active and \`PRODUCTION_RELEASE_CONTROLLER_CERTIFIED=False\`. A structurally valid \`1.1\` dossier can only be held for genuine independent review and is never authorized to publish, quote, contact, charge or deploy.
