"""End-to-end SYNTHETIC 1970s 1,500-ft2 home inspection workflow exercise.

Uses the production M4 source-custody / M00 specialist / Q02 / Q03 / Option 2
draft / raster audit path, with distinct deterministic scripted test providers.

This is not AI visual accuracy testing, a physical inspection, a consented
property dataset, a professional inspector, or customer-release permission.
Never place real customer evidence or identifying data in the public artifact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil

from PIL import Image, ImageDraw

from inspection_engine.core import DataError, SYSTEMS, load_project, blockers, sha256
from inspection_engine.m4_workflow import preflight_case
from inspection_engine.m4_pipeline import (
    prepare_case, status_case, run_specialists, run_q02, run_q03,
    render_private_case,
)
from inspection_engine.m4_pdf_audit import audit_private_pdf

PROJECT_ID = "SYNTHETIC-1970S-1500SF-3BR-2BA"
TEST_DATE = "2026-11-04"
# id, delegated inspection area, room / zone, synthetic hypothetical visual
ZONES = (
    ("P01", "site", "Lot, grading and drainage", "Possible negative grading and debris accumulation"),
    ("P02", "exterior", "Front and side exterior", "Possible deteriorated trim and peeling coatings"),
    ("P03", "roof", "Roof edges and gutters", "Possible weathered roof covering and blocked gutters"),
    ("P04", "attic", "Accessible attic", "Possible uneven insulation and old staining"),
    ("P05", "foundation", "Basement foundation walls", "Possible wall cracks and discoloration"),
    ("P06", "subfloor", "Basement floor-platform framing", "Possible stained or uneven subfloor surfaces"),
    ("P07", "framing", "Basement structural framing", "Possible wood deterioration at exposed framing"),
    ("P08", "basement", "Basement interior", "Possible dampness and damaged finishes"),
    ("P09", "interior", "Living and dining area", "Possible damaged flooring and wall finishes"),
    ("P10", "electrical", "Electrical service panel", "Possible open panel gaps or unsecured wiring"),
    ("P11", "plumbing", "Kitchen sink plumbing", "Possible corrosion and seepage at pipe joints"),
    ("P12", "water_heating", "Domestic water heater", "Possible aged fittings and corrosion"),
    ("P13", "hvac", "Furnace and distribution", "Possible dirty filter and compromised duct connections"),
    ("P14", "interior", "Primary bedroom", "Possible damaged trim and window seals"),
    ("P15", "interior", "Bedroom 2", "Possible wall staining and damaged receptacle cover"),
    ("P16", "interior", "Bedroom 3", "Possible worn flooring and ceiling discoloration"),
    ("P17", "plumbing", "Primary bedroom en-suite full bathroom", "Possible moisture at shower and sink"),
    ("P18", "plumbing", "Hallway full bathroom", "Possible tub seal/grout deterioration"),
    ("P19", "garage", "Attached garage", "Possible damage near house separation and door hardware"),
    ("P20", "interior", "Kitchen and laundry", "Possible deteriorated cabinets and appliance connections"),
)
SYSTEM_FOR_AREA = {
    "site": "site", "exterior": "exterior", "roof": "roof",
    "attic": "attic", "foundation": "foundation", "subfloor": "subfloor",
    "framing": "framing", "basement": "crawlspace", "interior": "interior",
    "electrical": "electrical", "plumbing": "plumbing",
    "water_heating": "water_heating", "hvac": "hvac", "garage": "interior",
}
# Only one scripted *hypothesis* for each of the 13 systems. Other source
# images still receive real dispatch + coverage review, never fabricated wins.
HYPOTHESIS_BY_ID = {
    row[0]: row for row in ZONES[:13]
}
COVERED_ROOMS = (
    "Primary bedroom", "Bedroom 2", "Bedroom 3",
    "Primary bedroom en-suite full bathroom", "Hallway full bathroom",
    "Living and dining area", "Kitchen and laundry",
    "Basement interior", "Accessible attic", "Attached garage",
)
EXPECTED_ROLE_IDS = frozenset(f"T{i:02}" for i in range(1, 9))


def _inside_external_directory(folder: Path) -> Path:
    folder = Path(folder).expanduser().absolute()
    for parent in (folder, *folder.parents):
        if parent.is_symlink() or (parent / ".git").exists():
            raise DataError("Synthetic dry-run output must be outside Git and not a symlink")
    if folder.exists():
        raise DataError("Synthetic dry-run output directory already exists; no overwrites")
    if not folder.parent.is_dir():
        raise DataError("Dry-run parent output directory must already exist")
    return folder


def _schematic(path: Path, row: tuple, index: int):
    """Original hand-drawn test schematic. Not an evidence photo."""
    _, area, zone, hint = row
    im = Image.new("RGB", (1060, 660), (237, 243, 248))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 1059, 104), fill=(19, 44, 67))
    d.text((30, 20), "SYNTHETIC / NOT A PROPERTY PHOTO", fill="white")
    d.text((30, 55), f"1970s HOUSE DRY RUN - VIEW {index:02}", fill=(185, 217, 229))
    d.rounded_rectangle((60, 144, 1000, 575), radius=20,
                        fill=(250, 249, 244), outline=(65, 88, 108), width=6)
    d.polygon(((165, 345), (445, 180), (760, 345)), fill=(121, 132, 142),
              outline=(39, 55, 69), width=5)
    d.rectangle((195, 348, 735, 520), fill=(201, 205, 199),
                outline=(58, 68, 77), width=6)
    d.rectangle((265, 395, 405, 505), fill=(172, 207, 218),
                outline=(39, 63, 75), width=4)
    d.rectangle((540, 395, 665, 520), fill=(148, 164, 175),
                outline=(39, 63, 75), width=4)
    # Repeated common diagram with a *different test marker*, not asserted
    # visible damage at any genuine address.
    x = 180 + (index * 31) % 540
    y = 275 + (index * 17) % 170
    d.ellipse((x, y, x + 90, y + 90), outline=(213, 112, 52), width=10)
    d.line((x + 12, y + 12, x + 78, y + 78), fill=(213, 112, 52), width=6)
    d.text((70, 596), f"{area.upper()} | {zone[:77]}", fill=(15, 48, 72))
    d.text((70, 624), "ORANGE MARKER = HYPOTHETICAL REVIEW TARGET", fill=(124, 65, 36))
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, format="PNG", optimize=True)


def build_synthetic_property(root: Path) -> tuple[Path, dict]:
    root.mkdir(parents=True, exist_ok=False)
    media = []
    for i, row in enumerate(ZONES, 1):
        ident, area, room, hint = row
        relative = f"media/{ident.lower()}_{area}.png"
        destination = root / relative
        _schematic(destination, row, i)
        media.append({
            "id": ident, "kind": "photo", "path": relative, "area": area,
            "room_label": room, "sha256": sha256(destination),
            "caption": f"SYNTHETIC schematic for {room}; the illustrative "
                       f"scenario asks about: {hint}. No actual condition confirmed.",
        })
    limitations = [
        ("roof", "Roof material, flashings, leaks and useful life not established by a schematic."),
        ("attic", "Attic is described as accessible, but no human has safely entered or verified it."),
        ("foundation", "Foundation type, wall material and concealed supports not verified on site."),
        ("crawlspace", "Basement floor area and moisture levels have not been measured."),
        ("electrical", "1970s construction may warrant targeted electrical review; do not infer wiring type."),
        ("plumbing", "Concealed water leaks, drain flow, water pressure and fixture operation not tested."),
        ("hvac", "Heating/cooling function, venting, combustion and manufacturer labels not tested."),
        ("water_heating", "Model, age, fuel, venting, temperature and safety devices unverified."),
        ("interior", "Bedrooms, bathrooms, detectors, stairways and windows lack physical testing."),
        ("exterior", "1970s coatings or materials could warrant qualified lead/asbestos testing; not diagnosed."),
        ("site", "Grading elevations, standing water and drainage not measured."),
        ("framing", "Concealed framing condition and load capacity unknown."),
        ("subfloor", "Subfloor material, deflection and moisture not established."),
    ]
    project = {
        "project_id": PROJECT_ID,
        "property": {
            "label": "FICTIONAL 1970s neglected home / 1,500 sq ft / 3BR / 2BA / basement / garage",
            "inspection_date": TEST_DATE,
            "synthetic": True,
            "building_type": "residential",
            "inspection_scope": "residential",
            "construction_period": "1970s",
            "reported_living_area_sqft": 1500,
            "basement_area_sqft": None,
            "bedrooms": 3,
            "full_bathrooms": 2,
            "ensuite_full_bathroom_in_primary_bedroom": True,
            "has_basement": True,
            "attached_garage": True,
            "attic_accessible_by_description": True,
            "maintenance_history": "Poorly maintained (scenario premise only)",
            "qualified_reviewer": None,
            "inspector": "SCRIPTED DRY-RUN PROVIDERS ONLY - NOT A REAL INSPECTOR",
        },
        "media": media, "observations": [], "findings": [],
        "equipment": [
            {"id": "E01", "system": "hvac", "brand": "UNKNOWN",
             "model": "NOT VERIFIED", "serial": "NOT VERIFIED", "evidence_ids": ["P13"]},
            {"id": "E02", "system": "water_heating", "brand": "UNKNOWN",
             "model": "NOT VERIFIED", "serial": "NOT VERIFIED", "evidence_ids": ["P12"]},
        ],
        "limitations": [
            {"id": f"L{i:02}", "system": system, "description": detail,
             "evidence_ids": []}
            for i, (system, detail) in enumerate(limitations, 1)
        ],
    }
    filename = root / "synthetic_project.json"
    filename.write_text(json.dumps(project, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    return filename, project


def _propose_by_script(image, prompt, counter: dict):
    match = re.search(r"evidence ID (P[0-9]{2});", prompt)
    if not match:
        raise DataError("Writer received no source-bound evidence ID")
    ident = match.group(1)
    counter["writer"].append(ident)
    if ident not in HYPOTHESIS_BY_ID:
        return {"candidates": [], "requests": []}
    _, area, room, hint = HYPOTHESIS_BY_ID[ident]
    # An area alias can route a work order, but it cannot by itself support
    # a concealed-system finding. 'basement' routes to the 'crawlspace'
    # system in this application's taxonomy; retain the correct room name,
    # skip the unsupported claim, and leave the coverage task for humans.
    if SYSTEM_FOR_AREA[area] != area:
        return {"candidates": [], "requests": []}
    return {
        "candidates": [{
            "type": "potential_concern",
            "system": SYSTEM_FOR_AREA[area],
            "description": f"Illustrated possible concern: {hint.lower()}. "
                           "Actual condition is unknown until an onsite examination.",
            "location": room[:99],
            "status": "partially_observed",
            "bbox": [0.19, 0.24, 0.85, 0.78],
        }],
        "requests": [],
    }


def _q02_script(image, prompt, counter: dict):
    counter["q02"] += 1
    if "UNTRUSTED HYPOTHESIS" not in prompt and "coverage" not in prompt.lower():
        # Current technical critic may use a separate coverage prompt.
        counter["unfamiliar_q02_prompts"] += 1
    return {
        "decision": "insufficient_evidence",
        "reason": "This illustration is synthetic and cannot authenticate a real physical defect.",
        "missing_evidence": "Original site photos, physical tests and qualified inspector corroboration.",
    }


def _q03_script(prompt, schema, counter: dict):
    counter["q03"] += 1
    if "LEDGER_PACKET_JSON: " not in prompt:
        raise DataError("Q03 missing actual aggregated Q02 source ledger")
    data = json.loads(prompt.split("LEDGER_PACKET_JSON: ", 1)[1])
    decisions = []
    for row in data["queue"]["entries"]:
        coverage = row["type"] == "coverage_task"
        decisions.append({
            "entry_id": row["entry_id"],
            "decision": "needs_evidence" if coverage else "distinct",
            "related_ids": [],
            "reason": "Physical coverage requires qualified follow-up" if coverage
                      else "Retain separate scripted concern with human review hold.",
            "evidence_gap": "Verified onsite inspection and source photos required"
                            if coverage else "",
        })
    return {"decisions": decisions}


def execute_case(out: Path) -> dict:
    out = _inside_external_directory(out)
    out.mkdir(mode=0o700)
    source_dir = out / "source"
    filename, project = build_synthetic_property(source_dir)
    state = out / "private_case"
    preflight = preflight_case(filename)
    if not preflight["ready_for_specialist_execution"]:
        raise DataError("Synthetic 20-area property could not route all photo work orders")
    if preflight["inspector_approved"] or preflight["customer_release_allowed"]:
        raise DataError("Synthetic preflight unexpectedly approved property")
    if len(project["media"]) != 20:
        raise DataError("Room/evidence inventory incomplete")
    if len(preflight["coverage"]) != 13:
        raise DataError("Thirteen system coverage checks missing")
    if {r[2] for r in ZONES}.issuperset(COVERED_ROOMS) is False:
        raise DataError("Bedrooms, both full bathrooms, garage, attic or basement missing")
    if {x["system"] for x in preflight["coverage"]} != {name for name, _ in SYSTEMS}:
        raise DataError("Required building system not covered by inspection register")
    if any(x["status"] == "observed" for x in preflight["coverage"]):
        raise DataError("Synthetic coverage falsely passed as inspected")
    if len(preflight["specialist_plan"]["jobs"]) != 20:
        raise DataError("Expected exactly one routed work order per area image")
    roles = {row["assigned_to"] for row in preflight["specialist_plan"]["jobs"]}
    if roles != EXPECTED_ROLE_IDS:
        raise DataError("Eight specialist role assignments not exercised")
    calls = {"writer": [], "q02": 0, "q03": 0, "unfamiliar_q02_prompts": 0}

    try:
        render_private_case(state)
    except DataError as exc:
        if "requires completed" not in str(exc) and "stage" not in str(exc):
            raise
    else:
        raise DataError("Report rendered without Q01/Q02/Q03 stages")

    prepared = prepare_case(filename, state)
    if prepared["status"] != "PREPARED" or prepared["jobs"] != 20:
        raise DataError("M4 source intake failed")
    run_specialists(
        state, lambda image, prompt: _propose_by_script(image, prompt, calls),
        provider_id="scripted-synthetic-writer-NOT-AI",
    )
    if sorted(calls["writer"]) != sorted(m["id"] for m in project["media"]):
        raise DataError("Specialist stage did not visit every media item")
    staged = json.loads((state / "staged_project.json").read_text())
    if any(f.get("review") == "human_verified" for f in staged["findings"]):
        raise DataError("Scripted proposals must remain unverified")
    if len(staged["findings"]) < 10:
        raise DataError("Dry-run scripted concerns did not reach specialist ledger")

    try:
        run_q02(
            state, lambda image, prompt: _q02_script(image, prompt, calls),
            provider_id="scripted-synthetic-writer-NOT-AI",
        )
    except DataError as exc:
        if "different provider" not in str(exc):
            raise
    else:
        raise DataError("Same writer and reviewer should be rejected")
    run_q02(
        state, lambda image, prompt: _q02_script(image, prompt, calls),
        provider_id="scripted-synthetic-Q02-NOT-AI",
    )
    if calls["q02"] < 13:
        raise DataError("Q02 technical and coverage reviews unexpectedly incomplete")
    try:
        run_q03(
            state, lambda prompt, schema: _q03_script(prompt, schema, calls),
            provider_id="scripted-synthetic-Q02-NOT-AI",
        )
    except DataError as exc:
        if "third distinct" not in str(exc):
            raise
    else:
        raise DataError("Same Q02 and Q03 reviewer should be rejected")
    run_q03(
        state, lambda prompt, schema: _q03_script(prompt, schema, calls),
        provider_id="scripted-synthetic-Q03-NOT-AI",
    )
    if calls["q03"] != 1:
        raise DataError("Q03 invoked more than once or skipped")
    review = json.loads((state / "adjudication.json").read_text())
    if review["status"] != "ADJUDICATION_HOLD" or not review["held_entry_ids"]:
        raise DataError("Unqualified source unexpectedly passed adjudication")

    render_result = render_private_case(state)
    if render_result["customer_release_allowed"]:
        raise DataError("Draft PDF unexpectedly approved release")
    final_status = status_case(state)
    if final_status["completed"] != ["specialists", "q02", "q03", "report"]:
        raise DataError("The production four-stage pipeline was not completed")
    if final_status["customer_release_allowed"] or final_status["human_approved"]:
        raise DataError("Synthetic case cannot be customer-approved")
    audit = audit_private_pdf(state)
    audit_data = json.loads(Path(audit["audit_json"]).read_text())
    pdf = next((state / "option2_draft").glob("*.pdf"))
    receipt = json.loads((state / "report_receipt.json").read_text())
    if not pdf.read_bytes().startswith(b"%PDF"):
        raise DataError("Missing actual rendered draft PDF")
    if audit_data["total_pages"] < 6 or audit_data["total_pages"] != audit["raster_pages"]:
        raise DataError("Page-by-page PDF audit incomplete")
    if set(audit_data["source_media_ids"]) != {m["id"] for m in project["media"]}:
        raise DataError("Report dropped original source media")
    if not audit_data["every_page_rasterized"] or not audit_data["source_register_included"]:
        raise DataError("Source-register or PDF audit did not execute")
    if receipt["customer_release_allowed"] or not receipt["report_holds"]:
        raise DataError("Report failed to retain human-approval holds")

    # Tamper test at end, then restore byte-for-byte. The rechecked case state
    # must reject source mutation even after stages and visual audit completed.
    target = source_dir / project["media"][0]["path"]
    old_bytes = target.read_bytes()
    try:
        target.write_bytes(b"tampered image")
        try:
            status_case(state)
        except (DataError, OSError, ValueError):
            pass
        else:
            raise DataError("Source-photo tampering was not rejected")
    finally:
        target.write_bytes(old_bytes)
    if status_case(state)["completed"] != final_status["completed"]:
        raise DataError("Restored evidence lost its valid source checkpoint")

    summary = {
        "status": "SYNTHETIC_END_TO_END_PRIVATE_DRAFT_COMPLETE_WITH_HOLDS",
        "project_id": PROJECT_ID,
        "synthetic_only": True,
        "source_case": "fictional, no address, no real evidence",
        "property": project["property"],
        "source_images": len(project["media"]),
        "all_images_used_by_specialist_dispatch": True,
        "routed_specialist_jobs": len(preflight["specialist_plan"]["jobs"]),
        "unique_specialist_roles": sorted(roles),
        "inspected_system_scopes": len(preflight["coverage"]),
        "systems_human_verified": 0,
        "required_rooms_covered_by_synthetic_source_labels": list(COVERED_ROOMS),
        "initial_invented_hypothetical_concerns": len(HYPOTHESIS_BY_ID),
        "scripted_pending_findings": len(staged["findings"]),
        "Q02_scripted_calls": calls["q02"],
        "Q03_scripted_calls": calls["q03"],
        "Q03_status": review["status"],
        "Q03_held_entry_count": len(review["held_entry_ids"]),
        "pipeline_stages_completed": final_status["completed"],
        "report_holds_count": len(receipt["report_holds"]),
        "PDF_pages_audited": audit_data["total_pages"],
        "source_image_ids_in_pdf": audit_data["source_media_ids"],
        "all_pdf_pages_rasterized": True,
        "private_option2_pdf_sha256": sha256(pdf),
        "private_option2_report_name": pdf.name,
        "pdf_contact_sheet_name": Path(audit["contact_sheet"]).name,
        "negative_tests": {
            "blocked_early_report": True,
            "blocked_same_writer_Q02": True,
            "blocked_same_Q02_Q03": True,
            "blocked_tampered_image": True,
            "full_case_custody_revalidated_after_restore": True,
        },
        "AI_model_inference_performed": False,
        "independent_visual_accuracy_verified": False,
        "real_inspector_physically_visited": False,
        "professional_reviewer_signed": False,
        "field_safety_tests_performed": False,
        "customer_release_allowed": False,
    }
    output = out / "dry_run_summary.json"
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
    return summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Synthetic 1970s 3BR / 2BA whole-house dry run")
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = execute_case(args.out_dir)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (DataError, ValueError, OSError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "SYNTHETIC_DRY_RUN_BLOCKED",
                          "reason": str(exc), "customer_release_allowed": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
