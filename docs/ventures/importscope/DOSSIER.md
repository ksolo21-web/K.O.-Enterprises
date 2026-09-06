# ImportScope — first fresh venture dossier

Date: 2026-09-06. Status: working prototype; willingness to pay unvalidated. External cash spent by this work: $0. Customers, sales, cleared revenue and OANDA gains: no verified activity.

## Buyer and narrow problem

Target user: first test freelance Shopify catalog operators handling repeated product CSV updates. Budget holder: the store owner or freelancer. Current workaround: spreadsheet comparison, careful sample imports, free validators, or a broader paid catalog-management app. Proposed value: a readable before/after report for reviewing or explaining supported changes before submitting an import. The segment preference is an unvalidated hypothesis from the [five-advisor review](../../advisory/BOARD_DECISION.md).

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
| A free CSV validator advertises local browser processing | [Craftshift validator](https://craftshift.com/csv-validator/) | Competitor's own published offer / high for existence, untested for quality | Privacy as a unique paid advantage or full competitor feature coverage |
| Matrixify advertises a free 10-product demo, Basic at $20 per 30 days, and a documented dry run with limits | [Matrixify pricing](https://matrixify.app/pricing/), [job options](https://matrixify.app/documentation/matrixify-import-export-job-options/) | Competitor's own pricing and documentation / high | Identical before/after reporting, its customer counts or willingness to pay for ImportScope |
| Gumroad lists direct fees of 10% + $0.50 plus 2.9% + $0.30 card processing; account-specific deductions remain unverified | [Gumroad fee details](https://gumroad.com/help/article/66-gumroads-fees) | Current provider article / high for published rates, medium for account applicability | Seller approval, a complete cost model, or zero owner liability |
| Standard hosted Actions runners are free for public repositories | [GitHub billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions) | Provider documentation / high | Free larger runners, paid services or unlimited storage |
| Notion permits template sales through its marketplace | [Notion seller guide](https://www.notion.com/help/selling-on-marketplace) | Primary distribution documentation / high | A viable niche or validated sales for our templates |
| Webflow has a native site audit panel | [Webflow audit panel](https://help.webflow.com/hc/en-us/articles/33961313088531-Intro-to-the-Audit-panel) | Primary product documentation / high | The quality or completeness of competing services |

## Counter-thesis

The strongest objection is that this could be a feature rather than a business. A spreadsheet diff, a free validator or an existing app may already be sufficient. Public source makes technical access easy to reproduce, and a one-time license creates no natural recurring revenue. Merchants may want an installed store integration instead of exporting two files. False positives and future Shopify changes can create support costs. We have no evidence yet that buyers will pay $29 or that we can reach them efficiently without advertising.

Proceed only as a cheap, reversible demand experiment. Do not use competitor pricing as proof of our demand or claim low competition. Do not add accounts, subscriptions, a backend, paid inference or bespoke consulting before evidence justifies it.

## Commercial hypothesis and economics

Proposed product: a $29 one-time packaged offline catalog-review utility, including the working tool, examples and documentation. The offer is packaging and a usable review workflow; there is no invented server-enforced paywall around public JavaScript. No promise of lifetime updates or guaranteed import safety.

The financial rereview on 2026-09-06 supersedes the initial headline-only operating illustration. Assuming the published ordinary direct-card rates apply to a $29 product price, with each fee rounded to cents, the platform fee is $3.40 and card processing $1.14, leaving **$24.46 before other deductions**. Five orders yield $122.30 and twenty $489.20 under those assumptions. Three orders yield $73.38, below the published standard $100 payout threshold. These are arithmetic scenarios, **not forecasts, received cash or profit**. Fee taxes, buyer-tax-related processing, currency conversion, refunds, disputes, withholding and exact account terms are not verified zeros. See the [financial review and executable Decimal calculation](../../advisory/reviews/2026-09-06/financial.md).

The same review found that ordinary refunds return Gumroad's own fee while retaining processing; five fully refunded $29 card orders could leave a $5.70 processing loss. Published terms allow negative-balance bank debits and payout holds. Thus no upfront or monthly fee does not establish compatibility with strict $0 owner exposure. No processor is connected, costs or terms accepted, or refund funding activated. Preserve the financial hold for commerce while internal preparation continues.

There are no subscriptions, trial-to-paid upgrades, ads, domains, purchased inventory, paid APIs or customer-hosted databases in this prototype. Development used existing session capabilities; their included resource usage is not described as unlimited.

## Demand test and stop conditions

The [comparative validation packet](validation/README.md) is prepared from the existing tool. No experiment has started. First establish an observable channel: the growth review specifies a bounded owned-repository reach test with native aggregate evidence. Gumroad Discover has eligibility prerequisites and is not the first-customer plan; community access and rules are unverified for an actual post. No cold messages, scraping or fake engagement. Read the [growth review](../../advisory/reviews/2026-09-06/growth.md) for sources and the exact reach/qualification distinction.

When a permitted qualified audience exists, run the packet's five-evaluator utility test. A separate 14-day paid test at $29 can start only after merchant setup, financial exposure, release/limitations review and the exact commercial authority are resolved. A free evaluation is not evidence of paid demand.

Track authentic qualified evaluations, completed payments, refunds, independent successful use, support minutes and reconciled settlements separately. Paid continuation hypothesis: at least 3 genuine purchases with successful independent use. The 100-qualified-visit/no-sale rule is disabled until qualification is actually observed and checkout works; ordinary page views cannot supply that denominator. Five qualified evaluators preferring the free workflow without material benefit would weaken this offer. Inadequate traffic or missing checkout is insufficient evidence. Pause the affected activity on a material misleading result, privacy defect, surprise charge or platform problem. Keep unmeasured counts null in [EXPERIMENT_STATUS.json](EXPERIMENT_STATUS.json).

## Operating fit

No calls or live demos are required by design. Onboarding: obtain both exports, choose files, inspect findings, download report. No custom setup is part of the offer. Initial support assumption: 5–15 asynchronous minutes per buyer, unverified; reduce scope or stop if repeated handholding is required. Documentation covers supported CSV shapes and limitations. Refund and complaint handling remains necessary and must be agreed in the seller configuration. Legal identity, seller terms, payout verification and applicable seller obligations remain owner-bound setup items. No physical work or installation dependency exists.

## Actual validation

The comparison engine has 13 passing meaningful tests covering CSV parsing, aliases, explicit blanks vs absent columns, partial updates, image-only rows, duplicate identities, changed options, inventory scope and export injection safety. Static asset references, JavaScript syntax and offline ZIP integrity pass. This does not constitute browser/print-layout QA, validation against a real Shopify store, independent customer acceptance, or evidence of income.
