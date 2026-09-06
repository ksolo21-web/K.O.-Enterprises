# ImportScope comparative evaluation packet

Prepared 2026-09-06. **Fictional data only; no buyer evaluation has started.** This packet makes the current workflow testable without adding features or accepting money. Review the [complete sample report](sample-review.html) and [machine-recorded fixture results](fixture-results.json). The HTML file can be downloaded and opened locally; its browser and print appearance has not yet been independently checked.

## Ten-minute self-service task

Use the [existing offline evaluation ZIP](../../../../products/importscope/dist/importscope-offline.zip). Download and extract it, then open `index.html` in a desktop browser. Keep the default 20% price-drop threshold. The kit begins with an explicitly labeled fictional example. No store, account or production catalog is needed.

1. Identify the linen-shirt price change from 89.00 to 8.90. Explain whether a 90% reduction deserves review; do not assume it is always an error.
2. Find the mug's active-to-draft status change and the tote's cleared vendor. The sample has three priority flags and four field changes. The fourth field change is the mug's compare-at price from 30.00 to 20.00 while selling price stays 24.00.
3. Explain why the absent large shirt variant is a review flag rather than proof of deletion. Note that the travel pouch is a new handle.
4. Download the full HTML report and open it. Identify at least one limitation: apps, metafields, market pricing, media availability or store-specific rules are outside scope.
5. Load [current-mug.csv](fixtures/current-mug.csv) as the current export and compare each proposed file below. Explain the different outcomes.

| Proposed file | Intended distinction | Expected supported result |
| --- | --- | --- |
| [blank-price.csv](fixtures/blank-price.csv) | The price header exists and its supplied cell is empty | High-priority blank-price finding; do not treat this as an omitted field |
| [omitted-price.csv](fixtures/omitted-price.csv) | The price column is entirely absent | No price-change comparison and no blank-price finding |
| [changed-option.csv](fixtures/changed-option.csv) | Color changes from Blue to Green while SKU stays MUG | Changed option identity warning; do not silently match by SKU or infer variant deletion |

These expected outcomes were checked with the existing comparison engine. They do not establish exact Shopify import behavior. The tool assumes overwrite of matching handles; keep a backup and test a small actual import separately when authorized. See [Shopify's CSV guidance](https://help.shopify.com/en/manual/products/import-export/using-csv), reviewed 2026-09-06 and due for revalidation before commerce or a rule change.

## Compare with the evaluator's normal workflow

Use five consenting freelancers who have actually completed at least two Shopify CSV update jobs in the previous 90 days. This is an experiment selection rule, not a claim about the market. No recruitment, outreach, form or account is activated by this packet. Use only an authorized channel and consented response method; do not collect real catalogs or store credentials.

For each evaluator, record an anonymous internal reference, qualification established or unknown, completion time, tasks completed, live-help minutes, specific useful change, current workaround, preference, and whether an authentic purchase later occurred. Keep private evidence separate from public aggregate results. Unknown is not a failed task or zero support.

Ask: What did your existing workflow already make clear? Which supported change, if any, was easier to identify or explain with this report? What remained confusing? Would you choose the existing workflow for the next real job, and why? A compliment or hypothetical willingness to pay is not a purchase.

**Utility continuation rule:** four of five complete within ten minutes without live help, and three name a concrete useful comparison their ordinary workflow missed or made harder. **Stop this offer/segment:** all five prefer the existing free workflow and identify no material benefit. **Insufficient evidence:** fewer than five qualified participants, missing observations, or only model/owner demonstrations. Thresholds are judgment rules, not statistical validation.

## Keep the paid test separate

The proposed offer remains $29 once for a packaged catalog-change review kit. See [the unpublished listing and terms proposal](../LISTING_DRAFT.md). It does not sell exclusive access to public source or certify imports.

Seller identity, rights, actual merchant terms, cash exposure and release/delivery verification must be resolved before a paid test. Three genuine purchases with successful independent use would justify another bounded test; a cleared payout is a different milestone. The 100-qualified-visit failure rule is disabled while qualification or checkout is unobserved. No date or payment result is promised.

If no reachable qualified audience is established, use the smaller [IS-REACH-01 channel specification](../../../advisory/reviews/2026-09-06/growth.md) first. Do not infer buyer demand from repository views. Current experiment counters are in [EXPERIMENT_STATUS.json](../EXPERIMENT_STATUS.json).

Stop the affected test on a material misleading finding, privacy defect, unexpected cash exposure or platform problem. No further product feature work is justified by this packet alone.
