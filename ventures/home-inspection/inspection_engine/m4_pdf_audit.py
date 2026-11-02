"""Render and audit every private M4 Option 2 PDF page without cloud services.

Produces private PNG pages, a compact contact sheet, and immutable hashes.
Automated checks find blank pages, corrupt files and missing source IDs. They do
not certify layout, accessibility or medical/building inspection accuracy.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps, ImageStat
from pypdf import PdfReader
import pypdfium2 as pdfium

from .core import DataError, sha256
from .m4_pipeline import _get_case, _load_json, _atomic_json

def audit_private_pdf(workspace: str | Path, *, max_pages: int = 250) -> dict:
    if not isinstance(max_pages, int) or not 6 <= max_pages <= 250:
        raise DataError("Private PDF raster audit page budget must be 6–250")
    work, state, _, _ = _get_case(workspace)
    if "report" not in state["completed"]:
        raise DataError("Private PDF audit requires a completed report stage")
    summary = _load_json(work / "report_receipt.json")
    pdf_path = work / summary["draft_pdf_relative_path"]
    receipt = _load_json(work / summary["draft_receipt_relative_path"])
    if sha256(pdf_path) != summary["draft_pdf_sha256"] or receipt.get("pdf_sha256") != summary["draft_pdf_sha256"]:
        raise DataError("Private PDF digest or receipt does not match")
    try:
        pages_text = PdfReader(str(pdf_path)).pages
        rendered_pdf = pdfium.PdfDocument(str(pdf_path))
    except Exception as exc:
        raise DataError("Cannot parse Option 2 PDF") from exc
    count = len(pages_text)
    if count < 6 or count > max_pages or len(rendered_pdf) != count:
        raise DataError("PDF page count outside audit budget or renderer mismatch")
    text = [page.extract_text() or "" for page in pages_text]
    if "NOT RELEASED" not in text[0]:
        raise DataError("Private report cover lacks NOT RELEASED notice")
    all_text = "\n".join(text)
    if "SOURCE EVIDENCE" not in all_text:
        raise DataError("Private Option 2 report lacks complete media register")
    media = receipt["evidence"]["media"]
    for row in media:
        if row["id"] not in all_text:
            raise DataError(f"Source evidence {row['id']} not disclosed on PDF pages")
    folder = work / "page_raster_audit"
    if folder.exists():
        raise DataError("PDF raster audit already exists; use existing immutable evidence")
    folder.mkdir(mode=0o700)
    os.chmod(folder, 0o700)
    results = []
    gallery = []
    for n, page in enumerate(rendered_pdf):
        try:
            bitmap = page.render(scale=1.2).to_pil().convert("RGB")
        except Exception as exc:
            raise DataError(f"Could not rasterize Option 2 page {n+1}") from exc
        std = tuple(round(float(x), 3) for x in ImageStat.Stat(bitmap.resize((80, 100))).stddev)
        if max(std) < 3.0:
            raise DataError(f"PDF page {n+1} appears blank or visually uniform")
        png = folder / f"page_{n+1:04}.png"
        bitmap.save(png, "PNG", optimize=True)
        os.chmod(png, 0o600)
        results.append({"page_number": n+1, "image_sha256": sha256(png),
                        "dimensions": list(bitmap.size),
                        "rgb_standard_deviation": list(std),
                        "text_characters": len(text[n])})
        thumb = bitmap.copy()
        thumb.thumbnail((280, 350), Image.Resampling.LANCZOS)
        gallery.append(thumb)
    cols = 3
    cell_w, cell_h = 304, 392
    rows = (len(gallery)+cols-1)//cols
    if rows > 84:
        raise DataError("Contact sheet exceeds page budget")
    contact = Image.new("RGB", (cols*cell_w, rows*cell_h), "#e8edf2")
    draw = ImageDraw.Draw(contact)
    for n, img in enumerate(gallery):
        x=(n%cols)*cell_w+12
        y=(n//cols)*cell_h+20
        contact.paste(img,(x,y))
        draw.text((x,y+355),f"Page {n+1:03}",fill="#152a3c")
    sheet = folder / "all_pages_contact_sheet.png"
    contact.save(sheet, "PNG", optimize=True)
    os.chmod(sheet, 0o600)
    audit = {
        "schema_version": 1, "milestone": "M4",
        "stage": "PRIVATE_PDF_VISUAL_AUDIT",
        "pdf_sha256": summary["draft_pdf_sha256"],
        "total_pages": count, "source_media_ids": [x["id"] for x in media],
        "pages": results, "contact_sheet_sha256": sha256(sheet),
        "source_register_included": True,
        "every_page_rasterized": True,
        "blank_pages_detected": False,
        "qualified_visual_layout_review_completed": False,
        "readability_and_accessibility_verified": False,
        "customer_release_allowed": False,
    }
    _atomic_json(folder / "audit.json", audit)
    return {"audit_json": str(folder / "audit.json"), "contact_sheet": str(sheet),
            "raster_pages": count, "customer_release_allowed": False}
