# ImportScope

A fresh product experiment: compare a Shopify product export with a proposed import before submitting it to Shopify. No relation to Kaleb's existing game, installation, art or app projects.

## What works

- Two local CSV inputs, with strict comma-separated UTF-8 parsing, 8 MB / 10,000-row limits.
- Legacy and current Shopify column aliases, exact handle + ordered option matching.
- Priority findings for large price drops, explicit blank prices, blanked supported fields, availability changes, ambiguous variant identities and option changes.
- Explicit treatment of partial updates, missing columns, image-only rows and unsupported columns.
- Searchable before/after changes, finding filters, CSV findings and a standalone printable HTML review.
- A complete offline ZIP with sample CSVs and no remote runtime dependencies.

The source has no payment rail, store connection, analytics, uploads, paid APIs, network fetches, automatic storage or real customer information. Closing the page discards inputs. Downloaded reviews can contain private catalog data and stay under the user's control.

## Limits

This is an advisory file comparison, not an exact emulation of Shopify's importer or a certification that an import is safe. Overwrite matching handles is assumed. Missing variants are review flags, not asserted deletions. Metafields, apps, media availability, market-specific prices and store rules are outside scope. Baseline fields absent from an export cannot be compared. Inventory-location assumptions are explicit.

The initial commercial hypothesis is a $29 one-time packaged offline edition. This is a proposed test price, not a live offer. No revenue or customer demand has been validated. Public source availability means packaging, workflow and documentation must justify payment; access to public code is not a defensible paywall.

## Run and verify

Open `dist/index.html` in a modern browser, or use the private hosted preview. Run `node --test test-engine.cjs` for the meaningful parser, identity, overwrite-risk and export-safety checks. Run `python package_offline.py` to rebuild the downloadable ZIP after source changes.

No browser or print-layout QA has been performed in this turn. Automated checks do not establish visual quality or actual Shopify import outcomes. Rules last researched 2026-09-06; revalidate before a paid launch or after Shopify CSV changes.

## Sources

- Shopify CSV fields and overwrite behavior: https://help.shopify.com/en/manual/products/import-export/using-csv
- Shopify import cautions: https://help.shopify.com/en/manual/products/import-export/import-products

Source and deployment are retained in this Site's repository. A source snapshot is also submitted on Kaleb's authorized public GitHub branch for review. The unrelated camera draft was shelved following Kaleb's correction and is not part of this product.
