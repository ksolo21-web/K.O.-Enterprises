# Territory Work-Rule Model

## Canonical classes

| Class | Work rule | Default visual meaning |
|---|---|---|
| interior | both_sides | green |
| perimeter | inside_only | yellow with worked-side indicator |
| excluded | do_not_work | red |
| context | context_only | muted, clearly non-workable |

## Segment rules

- Rules attach to road segments, not merely street names.
- Split a street where the boundary or work rule changes.
- Every perimeter segment must identify the territory-facing side.
- Every interior street should be visible and worked on both sides unless an explicit exception exists.
- Outside streets must never visually appear workable.
- A corner property or divided road may require an exception object with supporting evidence.

## User corrections

Persist corrections with:

- territory ID;
- affected feature ID or coordinates;
- previous value;
- corrected value;
- reason;
- source or user instruction;
- revision number and date.

## Assignment representation and complete inventory

Apply [coverage-model.md](coverage-model.md). Both polygon and explicit road-segment assignments require complete source-bound coverage and current road/property inventory evidence. Segment assignments do not invent a closed polygon, skip immediate edges or waive unresolved candidates. Require the deterministic coverage/inventory gate and independent source review before release.

Require the bidirectional map-versus-housing-instructions gate in `housing-instructions.md`. The marked assignment controls obsolete housing restrictions; preserve all map-side, exclusion and other-territory/access limits. Review actual full-page text, including work notes, and record the user decision.
