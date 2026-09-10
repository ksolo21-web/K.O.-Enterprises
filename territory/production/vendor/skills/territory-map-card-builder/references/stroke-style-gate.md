# Repaired Stroke Style Gate

Use this gate whenever a correction changes any colored street or boundary pixel on an accepted supplied map. Staying inside a correction mask is necessary but not sufficient: a locally redrawn segment still fails when a person can see that its drawing language changed.

## Required comparison

1. Render the approved base and candidate at the same final 2x dimensions.
2. Declare every correction mask and mark each one with `contains_stroke_repair`.
3. For every stroke-repair mask, list every expected status color and run:

```bash
python scripts/validate_stroke_style.py \
  --base APPROVED-2X.png \
  --candidate CANDIDATE-2X.png \
  --config STROKE-STYLE-CONFIG.json \
  --report STROKE-STYLE-REPORT.json
```

4. Store the report path, report hash, and per-mask metrics in `preservation_audit`. The report binds the evidence to SHA-256 hashes of the approved render, candidate render, and configuration and records the palette and analysis parameters.
5. Inspect paired 4x crops of every repaired mask and its nearby untouched reference strokes. Confirm that no repaired section announces itself through a different thickness, color, softness, curvature, texture, seam, or endpoint character.

Run the gate against the raster rendered from the actual final PDF, not only an intermediate working image. Analyze green, yellow, and red independently inside every multistatus mask; never pool their widths, colors, softness, or texture. Width, edge softness, and texture compare against the same-status approved pixels inside the local repair mask. Color compares against a nearby untouched same-status source sample. Add an explicit `reference_boxes` entry for a status when the automatic untouched ring does not contain a representative core sample.

The centerline check compares the combined colored-route geometry with the approved render, because moving a clean status handoff along the same source path must not count as a new bend. It uses only materially changed candidate ridge pixels, which prevents harmless low-level PDF resampling noise on unchanged pixels from becoming a false curvature failure. The fixed resampling floor does not relax the exact zero-change requirement outside declared masks, and the independent same-status width, color, softness, texture, seam, and unexpected-status checks remain in force.

## Fail-closed measurements

At the final 2x render, every repaired mask must satisfy all of these limits against nearby untouched approved strokes:

| Measurement | Maximum |
|---|---:|
| Median stroke-width difference | 1.25 px |
| Median RGB color distance | 18.0 |
| Edge-softness difference | 0.85 px |
| 95th-percentile centerline deviation | 2.00 px |
| Stroke-presence mismatch at mask boundary | 0 px |
| Local stroke-texture difference | 2.50 |
| Added pixels from an unexpected work-status color | 0 px |

These are maximums, not tuning targets. The 2.00 px centerline limit equals one source pixel at the required final 2x render. A project may use stricter values; never loosen them to force a repair through. Keep changed-pixel tolerance at zero, derive the palette from the approved render rather than the candidate, and do not tune sampling parameters around a defect. If the source is not being evaluated at the required final 2x render, render it correctly before running the gate.

## Visual veto

The automated report does not overrule a visible mismatch. If the repaired segment is distinguishable in the 4x comparison—even when the numeric checks pass—set `repaired_stroke_style_mismatches` above zero and reject the card.

Restore the approved base and repair again using its existing path, adjacent stroke pixels, width, palette, antialiasing, and endpoint profile. Do not replace the street with a newly generated line.

## Typed native topology edits

For source-backed authorized native additions/removals only, apply [native-topology-gate.md](native-topology-gate.md). Keep `contains_stroke_repair=true`, distinguish typed topology masks from existing-path repairs, and run every applicable gate. The original repair comparator and numeric cutoffs are unchanged; do not falsely report an old centerline failure as passed or bypass it by omitting colored edits.

For the independently diagnosed disconnected-tip medial-width defect in a strict native-addition then existing terminal-repair chain, use [mixed-native-existing-chain.md](mixed-native-existing-chain.md). Preserve original comparator FAIL evidence; the source-bound maximum paired width estimator keeps every original limit and all other mandatory checks. This is not a source-scale substitution or a topology-removal reclassification.
