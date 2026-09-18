# R48 Territory Identity & Filename Contract — 2026-09-12

## Purpose
R48 separates **master-map/source labels** from the congregation territory-card identity. Labels such as `R-263-A`, `T-247-N`, `R-240-C`, or `A-262` may identify a polygon/source record on a master map, but they are **not automatically the visible card ID and are never the canonical release filename**.

This contract is a hard release gate for every new card, conversion, rebuild, rename, export, and identity correction.

## Three separate identity fields
Every territory project must carry all three concepts separately:

1. `source_master_label` — source/GIS/master-map alias, e.g. `R-263-A`. Source evidence only. It may contain `R-`, `A-`, `T-`, directional suffixes, or other source notation.
2. `card_identity` — audited congregation-card identity object: base number, card class, and optional lowercase subterritory suffix.
3. `canonical_filename` — derived from `card_identity`; never typed independently for release.

A source/master label must never be copied directly into the card face or filename merely because it exists on the BIG Map.

## Canonical card classes
`card_class` is one of:

- `""` — default/residential card. **No `R` appears on the card or filename.**
- `"A"` — Apartment classification.
- `"T"` — Telephone classification.
- `"TA"` — Telephone/Apartment classification.

`R` is a master-map/source classification only and is prohibited as a rendered card-class prefix/suffix.

## Visible card ID grammar
Let:
- `N` = territory base number as an integer/non-zero-padded display number;
- `C` = card class (``, `A`, `T`, or `TA`);
- `s` = optional lowercase subterritory suffix (`a`, `b`, `c`, ...).

Visible card ID:

`C + N + s`

Examples:
- residential/default 263 subdivision a → `263a`
- Apartment 263 subdivision a → `A263a`
- Telephone 263 subdivision a → `T263a`
- Telephone/Apartment 263 subdivision a → `TA263a`
- Apartment 33 → `A33`
- Telephone 40 → `T40`
- Telephone/Apartment 45 → `TA45`

Never render `R-263-A`, `R263a`, `263R`, `A-263-A`, or other master-map formatting on the card face.

## Canonical PDF filename grammar
For the filename only, pad the base number to **at least three digits** and move the card class **after the number**, before the lowercase suffix:

`Territory - NNN + C + s + .pdf`

Examples:
- `263a` → `Territory - 263a.pdf`
- `A263a` → `Territory - 263Aa.pdf`
- `T263a` → `Territory - 263Ta.pdf`
- `TA263a` → `Territory - 263TAa.pdf`
- `TA263b` → `Territory - 263TAb.pdf`
- `A33` → `Territory - 033A.pdf`
- `T40` → `Territory - 040T.pdf`
- `TA45` → `Territory - 045TA.pdf`
- `31a` → `Territory - 031a.pdf`

The space-hyphen-space form `Territory - ` is canonical. Do not release `Territory-A263a.pdf`, `Territory - A263a.pdf`, `Territory - R-263-A.pdf`, or `Territory - 263-A.pdf`.

## Suffix rules
- The subterritory suffix is separate from the class and is lowercase on both the card face and canonical filename.
- Do not convert a directional/source marker (`N`, `S`, etc.) into a card suffix unless the territory identity audit explicitly establishes that this is the card's subterritory suffix.
- Do not infer `TA` from `T` or `A` source notation. The actual card class must be resolved from the congregation assignment/classification evidence.

## Identity resolution before build
Before rendering a production card, record:

```json
{
  "source_master_label": "R-263-A",
  "card_identity": {
    "base_number": 263,
    "card_class": "",
    "suffix": "a",
    "display_id": "263a",
    "canonical_filename": "Territory - 263a.pdf",
    "identity_status": "verified"
  }
}
```

`display_id` and `canonical_filename` must be recomputed by the R48 identity helper/validator and match exactly. `identity_status` must be `verified` for field-use release.

When source geography is known but the congregation card identity is not yet resolved, keep `identity_status: "unresolved"` and block field-use release. A template-fit fixture may use a clearly marked `fixture_only` identity, but it cannot establish the production identity.

## Release vetoes
Release fails when any of these is true:
- master-map/GIS notation is visible as the card ID;
- `R` is used as a card class;
- visible card ID and canonical filename do not derive from the same identity object;
- class letters are in the wrong position;
- suffix case/order is wrong;
- base number is not minimum-three-digit padded in the filename;
- production filename differs from the derived canonical filename;
- production identity is unresolved or inferred only from the BIG Map prefix;
- hidden/extracted PDF identity conflicts with the visible identity or filename.

## Existing approved examples used as regressions
The current collection already proves the grammar:
- visible `A33` → `Territory - 033A.pdf`;
- visible `A60b` → `Territory - 060Ab.pdf`;
- visible `T40` → `Territory - 040T.pdf`;
- visible `T72` → `Territory - 072T.pdf`;
- visible `TA45` → `Territory - 045TA.pdf`;
- visible `A53a` → `Territory - 053Aa.pdf`;
- visible `31a` uses no residential `R` prefix.

These are naming regressions; they do not by themselves establish geography for another territory.

## Mandatory `territory_identity_review` — exact-artifact critic evidence
Every builder release record and every critic/internal-review report for a production card must carry a `territory_identity_review` bound to the exact reviewed PDF. A count-only or prose-only identity assertion does not pass.

```json
{
  "artifact_sha256": "64-hex SHA-256 of the exact reviewed PDF",
  "source_master_label": "R-263-A",
  "card_identity": {
    "base_number": 263,
    "card_class": "",
    "suffix": "a",
    "display_id": "263a",
    "canonical_filename": "Territory - 263a.pdf",
    "identity_status": "verified"
  },
  "derived_display_id_match": true,
  "derived_filename_match": true,
  "visible_identity_match": true,
  "extracted_text_identity_match": true,
  "pdf_metadata_identity_match": true,
  "source_alias_not_rendered_as_card_identity": true,
  "actual_filename_match": true,
  "hidden_stale_identity_count": 0,
  "identity_validator_passed": true,
  "pdf_identity_validator_passed": true,
  "evidence": ["exact final PDF", "identity validator report", "PDF identity validator report"]
}
```

Rules:
- `artifact_sha256` must equal the exact PDF hash used by the rest of the critic report.
- The reviewer must independently recompute the expected `display_id` and `canonical_filename` from `base_number`, `card_class`, and `suffix`; copying builder-provided derived strings is not review.
- `visible_identity_match`, extracted-text identity, metadata identity, actual filename, and source-alias non-rendering must all be checked on the exact saved/delivered PDF, not only the working candidate.
- `hidden_stale_identity_count` must be zero. An opaque overlay hiding an old ID visually does not pass when the stale ID remains in extractable text or metadata.
- A production review requires `identity_status: verified`; `fixture_only` is limited to explicitly watermarked non-field-use regression fixtures and cannot authorize release.
- Both identity validators must pass. Their PASS validates measurable identity facts only; the critic still checks whether the selected congregation identity itself is supported by assignment/reclassification evidence.

Missing, false, stale-hash, unresolved, or contradictory `territory_identity_review` evidence is a hard release failure. Cap identity/template/export/overall at 8 until repaired.
