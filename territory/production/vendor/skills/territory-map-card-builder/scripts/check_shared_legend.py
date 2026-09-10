#!/usr/bin/env python3
"""Read-only native and visible-pixel check for Kaleb's shared sidebar palette.

Optional layout JSON: {"page_size_pt": [768, 480.5],
"swatch_boxes_pt": {"Work Inside Only": [28, 198, 48, 218],
"Work Both Sides": [28, 242, 48, 262], "Do Not Work": [28, 286, 48, 306]}}.
Declare an alternate approved layout before measuring; colors are not configurable.
"""

import argparse
import hashlib
import json
from pathlib import Path

import fitz


PALETTE = {
    "Work Inside Only": (255, 220, 24),
    "Work Both Sides": (81, 199, 43),
    "Do Not Work": (255, 20, 53),
}
DEFAULT_LAYOUT = {
    "page_size_pt": [768, 480.5],
    "swatch_boxes_pt": {
        "Work Inside Only": [28, 198, 48, 218],
        "Work Both Sides": [28, 242, 48, 262],
        "Do Not Work": [28, 286, 48, 306],
    },
}
NATIVE_COLOR_TOLERANCE = 1e-5  # PDF decimal serialization only, in 0..1 units.
RENDER_QUANTIZATION_TOLERANCE = 1  # MuPDF can floor an 8-bit color by one level.


def digest(data):
    return hashlib.sha256(data).hexdigest()


def color_matches(actual, expected):
    return actual is not None and len(actual) == 3 and all(
        abs(float(actual[i]) - expected[i] / 255) <= NATIVE_COLOR_TOLERANCE
        for i in range(3)
    )


def validate_layout(layout):
    size = layout.get("page_size_pt", [])
    boxes = layout.get("swatch_boxes_pt", {})
    if len(size) != 2 or any(not isinstance(v, (int, float)) or v <= 0 for v in size):
        raise ValueError("page_size_pt must contain two positive numbers")
    if set(boxes) != set(PALETTE):
        raise ValueError("swatch_boxes_pt must contain exactly the three approved captions")
    for label, box in boxes.items():
        if len(box) != 4 or any(not isinstance(v, (int, float)) for v in box):
            raise ValueError(f"Invalid swatch rectangle for {label}")
        x0, y0, x1, y1 = box
        if not (0 <= x0 < x1 <= size[0] and 0 <= y0 < y1 <= size[1]):
            raise ValueError(f"Swatch rectangle outside the declared page: {label}")
    centers = [(boxes[label][1] + boxes[label][3]) / 2 for label in PALETTE]
    if not centers[0] < centers[1] < centers[2]:
        raise ValueError("Declared swatches must follow yellow, green, red from top to bottom")


def inspect(pdf, layout=DEFAULT_LAYOUT, layout_path=None):
    pdf = Path(pdf)
    validate_layout(layout)
    errors, rows = [], []
    with fitz.open(pdf) as doc:
        if len(doc) != 1:
            errors.append("Expected one front page")
        if not len(doc):
            raise ValueError("PDF has no page")
        page = doc[0]
        if page.rotation != 0:
            errors.append("Expected the approved unrotated front layout")
        actual_size = [page.rect.width, page.rect.height]
        if any(abs(a - b) > 0.02 for a, b in zip(actual_size, layout["page_size_pt"])):
            errors.append("Actual page size differs from the declared approved layout")
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), colorspace=fitz.csRGB, alpha=False)
        drawings = page.get_drawings()
        for label, rgb in PALETTE.items():
            box = layout["swatch_boxes_pt"][label]
            matches = [d for d in drawings if d.get("fill") is not None and all(
                abs(float(a) - float(b)) <= 0.02 for a, b in zip(d["rect"], box)
            )]
            painted = matches[-1] if matches else None
            native_ok = bool(painted) and color_matches(painted["fill"], rgb)
            if painted:
                native_ok = native_ok and abs(painted.get("fill_opacity", 1) - 1) <= 1e-6
                if painted.get("color") is not None:
                    native_ok = native_ok and color_matches(painted["color"], rgb)
                    native_ok = native_ok and abs(painted.get("stroke_opacity", 1) - 1) <= 1e-6
            x0, y0, x1, y1 = box
            samples = []
            for fx in (0.35, 0.5, 0.65):
                for fy in (0.35, 0.5, 0.65):
                    x, y = int((x0 + (x1 - x0) * fx) * 2), int((y0 + (y1 - y0) * fy) * 2)
                    samples.append(list(pix.pixel(x, y)) if 0 <= x < pix.width and 0 <= y < pix.height else None)
            visible_ok = all(s is not None and all(
                abs(a - b) <= RENDER_QUANTIZATION_TOLERANCE for a, b in zip(s, rgb)
            ) for s in samples)
            passed = bool(native_ok and visible_ok)
            rows.append({
                "caption": label, "expected_hex": "#" + "".join(f"{v:02X}" for v in rgb),
                "expected_rgb": list(rgb), "swatch_box_pt": box,
                "native_fill_rgb": list(painted["fill"]) if painted else None,
                "native_stroke_rgb": list(painted["color"]) if painted and painted.get("color") else None,
                "native_drawing_seqno": painted["seqno"] if painted else None,
                "matching_native_drawing_count": len(matches),
                "native_color_and_opacity_match": bool(native_ok),
                "actual_rgb_samples": samples, "visible_color_match": visible_ok, "passed": passed,
            })
            if not passed:
                errors.append(f"{label}: missing native swatch or wrong native/visible sidebar color")
    return {
        "schema_version": "shared-sidebar-palette-1", "artifact": str(pdf.resolve()),
        "artifact_sha256": digest(pdf.read_bytes()), "status": "FAIL" if errors else "PASS",
        "error_count": len(errors), "errors": errors, "swatches": rows,
        "layout": layout, "layout_path": str(layout_path) if layout_path else None,
        "layout_sha256": digest(Path(layout_path).read_bytes()) if layout_path else digest(
            json.dumps(layout, sort_keys=True, separators=(",", ":")).encode()),
        "actual_page_size_pt": actual_size, "render_scale": 2,
        "native_color_serialization_tolerance": NATIVE_COLOR_TOLERANCE,
        "render_quantization_tolerance_per_channel": RENDER_QUANTIZATION_TOLERANCE,
        "checker_sha256": digest(Path(__file__).read_bytes()),
        "scope": "Sidebar palette only. Captions/layout require independent visual review; preserved map colors and all existing map/glyph/entrance gates remain separate. The PDF is never rewritten.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--layout-json", type=Path, help="Previously declared alternate approved layout; palette remains fixed")
    args = parser.parse_args()
    if args.report.resolve() == args.pdf.resolve():
        parser.error("Report path must differ from the PDF")
    layout = json.loads(args.layout_json.read_text()) if args.layout_json else DEFAULT_LAYOUT
    report = inspect(args.pdf, layout, args.layout_json)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "artifact_sha256": report["artifact_sha256"],
                      "error_count": report["error_count"], "errors": report["errors"], "report": str(args.report)}))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
