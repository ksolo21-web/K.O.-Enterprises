"""M5 GitHub acceptance: pinned synthetic examples and reproducible PDF pixels.

Runs entirely offline with temporary synthetic files. PDF byte hashes are NOT
compared because permitted metadata may vary; decoded page text and RGB pixels
must agree exactly. Does not test real inspection or permit customer release.
"""
from __future__ import annotations
import copy
import hashlib
from importlib.metadata import version as package_version
import sys
import json
from pathlib import Path
import tempfile

from PIL import ImageStat
import pypdfium2 as pdfium
from pypdf import PdfReader

from inspection_engine.core import load_project
from inspection_engine.report import build_pdf
from scripts.generate_public_fixtures import generate

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "examples/versioned_fixture_manifest_v1.json"
EXAMPLE_PATHS = {
    "examples/demo_project.json": "synthetic_inspection_project",
    "examples/editorial_demo_project.json": "synthetic_inspection_project",
    "examples/human_reference.json": "human_authored_synthetic_comparison_only",
    "scripts/generate_public_fixtures.py": "synthetic_source_generator",
}


class QualityGateBlock(ValueError):
    pass


def _blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii")
                        + b"\x00" + raw).hexdigest()


def verify_versioned_examples(root: Path = ROOT) -> dict:
    root = Path(root).resolve(strict=True)
    try:
        data = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise QualityGateBlock("Missing or unreadable synthetic version manifest") from exc
    if (not isinstance(data, dict) or set(data) != {
            "schema_version", "milestone", "status",
            "customer_release_allowed", "examples"}
            or data["schema_version"] != 1 or data["milestone"] != "M5"
            or data["status"] != "VERSIONED_SYNTHETIC_EXAMPLES_ONLY"
            or data["customer_release_allowed"] is not False):
        raise QualityGateBlock("Invalid public synthetic example registry")
    examples = data["examples"]
    if not isinstance(examples, list) or len(examples) != len(EXAMPLE_PATHS):
        raise QualityGateBlock("Incomplete versioned example inventory")
    seen = set()
    for entry in examples:
        if not isinstance(entry, dict) or set(entry) != {
                "path", "git_blob_sha1", "classification"}:
            raise QualityGateBlock("Unrecognized versioned example schema")
        relative = entry["path"]
        if (not isinstance(relative, str) or relative not in EXAMPLE_PATHS
                or relative in seen or
                entry["classification"] != EXAMPLE_PATHS[relative]):
            raise QualityGateBlock("Unknown or duplicated synthetic example")
        seen.add(relative)
        file = root / relative
        if file.is_symlink() or not file.is_file() or file.stat().st_size > 2_000_000:
            raise QualityGateBlock("Nonregular or oversized versioned fixture")
        actual = _blob_sha(file.read_bytes())
        if entry["git_blob_sha1"] != actual:
            raise QualityGateBlock("Versioned synthetic fixture bytes changed")
        if relative.endswith("_project.json"):
            try:
                project = json.loads(file.read_text(encoding="utf-8"))
            except ValueError as exc:
                raise QualityGateBlock("Synthetic project JSON invalid") from exc
            if project.get("property", {}).get("synthetic") is not True:
                raise QualityGateBlock("Versioned example lacks synthetic flag")
    if seen != set(EXAMPLE_PATHS):
        raise QualityGateBlock("Versioned example missing from manifest")
    return {"manifest_version": 1, "pinned_source_files": len(seen)}


def _pdf_signature(path: Path) -> tuple:
    try:
        reader = PdfReader(path)
        raster = pdfium.PdfDocument(str(path))
    except Exception as exc:
        raise QualityGateBlock("Synthetic Option 2 PDF unreadable") from exc
    if len(reader.pages) < 5 or len(reader.pages) != len(raster):
        raise QualityGateBlock("Synthetic Option 2 PDF page count invalid")
    rows = []
    for index, page in enumerate(raster):
        try:
            rgb = page.render(scale=1).to_pil().convert("RGB")
            text = reader.pages[index].extract_text() or ""
        except Exception as exc:
            raise QualityGateBlock("Synthetic PDF page failed raster/text extraction") from exc
        if max(ImageStat.Stat(rgb.resize((80, 80))).stddev) < 2:
            raise QualityGateBlock("Synthetic Option 2 PDF contains blank page")
        rows.append((rgb.size, hashlib.sha256(rgb.tobytes()).hexdigest(),
                     hashlib.sha256(text.encode("utf-8")).hexdigest()))
    return tuple(rows)



BASELINE_FILE = "examples/option2_report_baseline_v1.json"
BASELINE_KEYS = {"schema_version", "baseline_id", "fixture_manifest_version",
                 "expected_pages", "expected_visual_and_text_fingerprint",
                 "python_major_minor", "packages", "note", "customer_release_allowed"}
BASELINE_PACKAGES = {"Pillow", "reportlab", "pypdf", "pypdfium2"}


def verify_pinned_render_baseline(reference, page_count: int, fingerprint: str):
    """Cross-run golden baseline: no self-approval if identical builds both drift."""
    if (not isinstance(reference, dict) or set(reference) != BASELINE_KEYS
            or reference["schema_version"] != 1
            or reference["fixture_manifest_version"] != 1
            or reference["customer_release_allowed"] is not False
            or reference["baseline_id"] != "m5-option2-synthetic-ubuntu24-py312-v1"
            or not isinstance(reference["note"], str)):
        raise QualityGateBlock("Unapproved PDF reproducibility baseline schema")
    expected = reference["expected_visual_and_text_fingerprint"]
    if (not isinstance(expected, str) or len(expected) != 64
            or any(c not in "0123456789abcdef" for c in expected)
            or type(reference["expected_pages"]) is not int
            or reference["expected_pages"] < 5):
        raise QualityGateBlock("Malformed golden page fingerprint or page count")
    if reference["expected_pages"] != page_count or expected != fingerprint:
        raise QualityGateBlock("Report pages differ from pinned repository baseline")
    if (reference["python_major_minor"] != f"{sys.version_info.major}.{sys.version_info.minor}"
            or not isinstance(reference["packages"], dict)
            or set(reference["packages"]) != BASELINE_PACKAGES):
        raise QualityGateBlock("Baseline Python or package runtime mismatch")
    for name, pinned in reference["packages"].items():
        if not isinstance(pinned, str) or package_version(name) != pinned:
            raise QualityGateBlock("Synthetic raster runtime dependency changed: " + name)
    return reference["baseline_id"]


def verify_reproducible_report(root: Path = ROOT) -> dict:
    """Generate clean synthetic sources twice; compare EVERY page's pixels and text."""
    base = verify_versioned_examples(root)
    project_path = Path(root) / "examples" / "editorial_demo_project.json"
    signatures = []
    with tempfile.TemporaryDirectory(prefix="m5_synthetic_repro_") as folder:
        for label in ("a", "b"):
            workspace = Path(folder) / label
            workspace.mkdir()
            generate(workspace, video=False)
            # load_project validates media relative to its JSON location.
            # Bundle the *pinned* example manifest with each newly generated,
            # clean-room synthetic image set before validating the project.
            replica = workspace / "examples" / "editorial_demo_project.json"
            replica.write_bytes(project_path.read_bytes())
            source = load_project(replica)
            output = workspace / "draft.pdf"
            build_pdf(copy.deepcopy(source), workspace / "examples", output)
            signatures.append(_pdf_signature(output))
    if signatures[0] != signatures[1]:
        raise QualityGateBlock("Option 2 page text/pixels changed between clean builds")
    raw = json.dumps(signatures[0], sort_keys=True, separators=(",", ":")).encode()
    fingerprint = hashlib.sha256(raw).hexdigest()
    reference_path = Path(root) / BASELINE_FILE
    if reference_path.is_symlink() or not reference_path.is_file():
        raise QualityGateBlock("Missing or symlinked approved report baseline")
    try:
        reference = json.loads(reference_path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise QualityGateBlock("Unreadable approved report baseline") from exc
    reference_id = verify_pinned_render_baseline(
        reference, len(signatures[0]), fingerprint)
    return {
        "schema_version": 1,
        "approved_synthetic_render_baseline": reference_id,
        "status": "SYNTHETIC_RENDER_AND_VERSIONED_EXAMPLES_REPRODUCIBLE_ONLY",
        **base,
        "rendered_page_count": len(signatures[0]),
        "page_visual_and_text_fingerprint": fingerprint,
        "all_pages_raster_and_text_reproducible": True,
        "real_customer_inspection_coverage_verified": False,
        "model_accuracy_verified": False,
        "qualified_human_approval_verified": False,
        "customer_release_allowed": False,
    }


def main() -> int:
    try:
        result = verify_reproducible_report()
    except (QualityGateBlock, OSError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "M5_REPRODUCIBILITY_GATE_BLOCKED",
                          "reason": str(exc), "customer_release_allowed": False}))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
