# Sidebar, entrance and stroke evidence

Apply these checks to the exact candidate and again to the actual saved PDF. Keep the existing validators and their thresholds unchanged; these checks supplement them.

## Shared sidebar palette

For Kaleb's approved card template, use this one sidebar palette on every territory:

| Caption | Hex | RGB |
|---|---|---|
| Work Inside Only | `#FFDC18` | 255, 220, 24 |
| Work Both Sides | `#51C72B` | 81, 199, 43 |
| Do Not Work | `#FF1435` | 255, 20, 53 |

Treat sidebar colors independently of preserved map colors. Legacy source streets may have a different approved green, yellow or red. Retain those map colors; neither copy them into the sidebar nor recolor the map to match the sidebar.

Run the standalone actual-PDF check:

```bash
python scripts/check_shared_legend.py CARD.pdf --report SIDEBAR-PALETTE.json
```

The default layout is the approved 768 × 480.5 pt front with 20 pt swatches centered at (38, 208), (38, 252), (38, 296). For another approved layout, declare its page size and three swatch rectangles in `--layout-json` before checking; the palette is fixed. The script checks native fill/stroke colors and visible interior pixels, reports the PDF/config hashes, and never edits the PDF. A missing native swatch, wrong visible color or unexpected layout fails. It does not replace inspection of captions, font size, alignment, spacing, calendar/date or the full sidebar. Keep this report outside the card.

## Source-fixed entrance targets

Declare the source feature, whole relevant unbranched access stem or actual source junction, source-to-page transform, target region and small output-pixel contact radius before placement measurements. Derive the region from source geometry, not from the eventual arrow tip or a tip-centered box. Preserve that declaration and its hash. A known target radius such as 7 or 8 px is not a new universal size requirement.

Inspect the actual saved arrow, including its filled head and entire shaft. It must meet the verified access, remain clear of labels and other leaders, and have no road contact outside the declared local target allowance. Contact with a serving public road is allowed only at a proven shared public/access junction, inside that same small region; it never permits an arrow along the public road or across another road.

If overlap fails, retain the raw result and repair the arrow. Do not enlarge a target radius, shift a target box, omit offending pixels or relabel an unrelated road after measuring to manufacture a pass. If a genuine source or measurement error is discovered, retain both versions and require an independent source-only explanation and fresh measurements; a revised declaration alone is not evidence. Verify separately scaled insets through source identities and matching navigation markers, not a claim of connected pixels across separate views.

## Complete native stroke cross-sections

When a repair affects colored pixels, including antialias pixels during neutral text cleanup, retain the existing style gate, exact correction masks and zero-outside check. Native path reuse alone does not prove the resulting visible stroke is unchanged.

A crop that cuts through a thick native stroke can report its clipped fragment as the stroke width. Before treating a width result as either a defect or an exemption, have an independent reviewer measure complete cross-sections on the original and actual-final renders at the same required scale, perpendicular to a representative straight run. Include both edges and nearby whitespace; use untouched same-status reference strokes and account for native width, uniform scale, caps and joins. Retain the original narrow diagnostics, full measurement-window coordinates/hashes, native operator/style comparison and paired 4x views. Keep broader diagnostic windows separate from the strict edit masks: they cannot authorize extra changed pixels.

Accept a sampling-artifact explanation only when the independent full cross-section, applicable unchanged-limit comparator and exact native/expected-paint evidence all support it, with zero outside the original correction masks and no visible mismatch. Otherwise repair the stroke; do not widen masks, reduce alpha sensitivity, omit border pixels, relabel the edit or loosen a threshold to hide a real mismatch. A legitimate full-cross-section result on one card does not waive another card's failed arrow or stroke measurements.

## Whole street words

Inspect every complete street name at actual output size and in close-up, including its prefix and suffix. A broken-looking word, abruptly rotated final letters, detached suffix or word forced around a tight guide bend blocks release even if glyph-road clearance and collision measurements pass. Move the whole label to a suitable straight or gently curved run beside the same assigned street; preserve ordinary spacing and regular type. Use the opposite side or other clear same-road whitespace when helpful. Do not use ad hoc per-letter rotations, stretched tracking, shrunk text or altered street geometry to force a broken word around a bend. Ordinary glyph rotation along a smooth curved baseline and evidence-backed limited spacing repairs under [label-glyph-review.md](label-glyph-review.md) remain allowed. No arbitrary global angle cutoff is introduced. Check the full word against inset/frame edges as well as other labels.

For dark neutral/black callout heads and mutated shared native Forms, apply the A51 self-occlusion and stale-index regressions in learning-regressions.md. Exclude validated annotation shapes from both road-visibility comparisons while retaining opaque nonannotation overpaint, and bind target paths only after reopening actual serialized final bytes. Preserve real gap/crossing negatives and every existing threshold.
