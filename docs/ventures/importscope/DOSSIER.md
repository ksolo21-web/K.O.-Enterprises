# ImportScope — first fresh venture dossier

Date: 2026-09-06. Status: working prototype; willingness to pay unvalidated. External cash spent by this work: $0. Customers, sales, cleared revenue and OANDA gains: no verified activity.

## Buyer and narrow problem

Target user: an independent Shopify catalog operator or ecommerce freelancer preparing a product CSV update. Budget holder: the store owner or freelancer. Current workaround: spreadsheet comparison, careful sample imports, free validators, or a broader paid catalog-management app. Proposed value: a readable before/after review that highlights supported overwrite risks before the import is submitted.

Cost of inaction is **not quantified**. Potential mistakes include unintended price changes, cleared product fields and altered option structures; official importer documentation establishes the mechanisms, not their prevalence or dollar impact.

The smallest coherent product now exists: two local CSV inputs; supported current/legacy header aliases; exact handle + ordered option matching; price-drop, blank-field, status and variant review; search and severity filters; downloadable review CSV and printable HTML; offline package. No remote store access or recurring API expense is needed. It is an advisory comparison, not a reproduction of the entire importer.

## Alternatives investigated

| Candidate | Current evidence | Decision |
| --- | --- | --- |
| Generic Shopify CSV validator | Craftshift offers a free validator | Reject as the primary paid proposition; too little distinction |
| ImportScope before/after review | Official overwrite mechanics plus a visible adjacent paid app category | Build a bounded prototype; require paid-demand evidence next |
| Generic Notion template pack | Notion supports paid templates and self-service distribution | Hold; no differentiated buyer problem was established |
| Generic website audit service | Webflow supplies audit tooling; delivery can require ongoing custom work | Hold; weak distinction and poor fit with low-touch operation |

## Evidence ledger

Every observation below was checked on **2026-09-06**, should be revalidated by **2026-10-06**, and needs earlier revalidation before external commerce or a rule-dependent release.

| Claim | Source | Evidence type / confidence | What it does not establish |
| --- | --- | --- | --- |
| Supplied blank fields and option-dependent updates can change or replace existing catalog data | [Shopify product CSV documentation](https://help.shopify.com/en/manual/products/import-export/using-csv) | Primary technical documentation / high | Frequency, losses, demand for our tool |
| Shopify advises backups; started product imports cannot be canceled | [Shopify importing products](https://help.shopify.com/en/manual/products/import-export/import-products) | Primary technical documentation / high | That our report can certify an import |
| A free generic CSV validator is available | [Craftshift validator](https://craftshift.com/csv-validator/) | Competitor's own published offer / high for existence, untested for quality | Full competitor feature coverage |
| Matrixify advertises a Basic plan at $20 per 30 days | [Matrixify pricing](https://matrixify.app/pricing/) | Competitor's own pricing / high | Its customer counts or willingness to pay for ImportScope |
| Gumroad lists no monthly fee and 10% + $0.50 for direct/profile sales | [Gumroad pricing](https://gumroad.com/pricing) | Provider pricing / high | Seller approval, no other obligations, or zero transaction cost |
| Standard hosted Actions runners are free for public repositories | [GitHub billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions) | Provider documentation / high | Free larger runners, paid services or unlimited storage |
| Notion permits template sales through its marketplace | [Notion seller guide](https://www.notion.com/help/selling-on-marketplace) | Primary distribution documentation / high | A viable niche or validated sales for our templates |
| Webflow has a native site audit panel | [Webflow audit panel](https://help.webflow.com/hc/en-us/articles/33961313088531-Intro-to-the-Audit-panel) | Primary product documentation / high | The quality or completeness of competing services |

## Counter-thesis

The strongest objection is that this could be a feature rather than a business. A spreadsheet diff, a free validator or an existing app may already be sufficient. Public source makes technical access easy to reproduce, and a one-time license creates no natural recurring revenue. Merchants may want an installed store integration instead of exporting two files. False positives and future Shopify changes can create support costs. We have no evidence yet that buyers will pay $29 or that we can reach them efficiently without advertising.

Proceed only as a cheap, reversible demand experiment. Do not use competitor pricing as proof of our demand or claim low competition. Do not add accounts, subscriptions, a backend, paid inference or bespoke consulting before evidence justifies it.

## Commercial hypothesis and economics

Proposed product: a $29 one-time packaged offline catalog-review utility, including the working tool, examples and documentation. The offer is packaging and a usable review workflow; there is no invented server-enforced paywall around public JavaScript. No promise of lifetime updates or guaranteed import safety.

Using Gumroad's currently advertised direct/profile headline fee alone, an illustrative $29 sale leaves $25.60 before refunds, taxes, chargebacks and any other deductions. Five such sales would leave $128 on that same limited basis; twenty would leave $512. These are arithmetic scenarios, **not a sales forecast**. No processor is connected and no fees are authorized or incurred. Selling fees are still costs even if deducted from proceeds; the owner must choose whether that fits the zero-out-of-pocket mandate.

There are no subscriptions, trial-to-paid upgrades, ads, domains, purchased inventory, paid APIs or customer-hosted databases in this prototype. Development used existing session capabilities; their included resource usage is not described as unlimited.

## Demand test and stop conditions

After merchant setup, honest product/limitations review and approval of the exact public offer, propose a 14-day test with a $0 acquisition budget. Draft distribution: one useful technical walkthrough with the two fictional example CSVs, an owned repository README, and a marketplace listing. A relevant community post is only a candidate channel; check its rules and obtain explicit outreach/publication authority before posting. No cold messages, scraping or fake engagement.

Track authentic qualified visits where the selling platform supports them, completed payments, refunds, self-service success and support minutes. Success hypothesis: at least 3 paid purchases and successful independent use without live assistance. Stop expanding if 100 qualified visits yield no sale, or 5 consenting testers prefer the existing free workflow and cannot identify a material benefit. If 14 days bring inadequate traffic, classify distribution as untested; do not falsely conclude demand is absent. Pause distribution immediately on a confirmed dangerous false-negative claim, privacy defect, surprise charge or platform problem. No fabricated activity or hidden free-to-paid conversion.

## Operating fit

No calls or live demos are required by design. Onboarding: obtain both exports, choose files, inspect findings, download report. No custom setup is part of the offer. Initial support assumption: 5–15 asynchronous minutes per buyer, unverified; reduce scope or stop if repeated handholding is required. Documentation covers supported CSV shapes and limitations. Refund and complaint handling remains necessary and must be agreed in the seller configuration. Legal identity, seller terms, payout verification and applicable seller obligations remain owner-bound setup items. No physical work or installation dependency exists.

## Actual validation

The comparison engine has 13 passing meaningful tests covering CSV parsing, aliases, explicit blanks vs absent columns, partial updates, image-only rows, duplicate identities, changed options, inventory scope and export injection safety. Static asset references, JavaScript syntax and offline ZIP integrity pass. This does not constitute browser/print-layout QA, validation against a real Shopify store, independent customer acceptance, or evidence of income.
