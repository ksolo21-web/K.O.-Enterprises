"""CE-1C offline PDF extraction in a bounded subprocess.

This is a *preflight*, not a certified security sandbox, OCR solution, or
independent inspection of an issuer's authentic PDF. The calling platform
needs a separately isolated worker for hostile real-world attachments.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys
from typing import Any

from .source_provenance import EvidenceError

MAX_PDF_BYTES = 4 * 1024 * 1024
MAX_PAGES = 60
MAX_PAGE_TEXT = 16_000
MAX_TOTAL_TEXT = 180_000
EXTRACT_TIMEOUT = 8

def _parse_pdf_in_child(raw: bytes) -> dict[str, Any]:
    """Executed only in a resource-capped child process."""
    from pypdf import PdfReader

    if len(raw) > MAX_PDF_BYTES or not raw.startswith(b"%PDF-"):
        raise EvidenceError("PDF header or size unacceptable")
    reader = PdfReader(io.BytesIO(raw), strict=True)
    if reader.is_encrypted:
        raise EvidenceError("encrypted PDF not accessible for full review")
    pages_count = len(reader.pages)
    if not 1 <= pages_count <= MAX_PAGES:
        raise EvidenceError("PDF page count outside reviewed bounds")
    trailer = reader.trailer
    root = trailer.get("/Root")
    if root is None:
        raise EvidenceError("PDF catalog missing")
    if hasattr(root, "get_object"):
        root = root.get_object()
    if root.get("/OpenAction") is not None or root.get("/AA") is not None:
        raise EvidenceError("interactive PDF document actions not allowed")
    if root.get("/AcroForm") is not None:
        raise EvidenceError("interactive PDF forms require separate review")
    names = root.get("/Names")
    if names is not None:
        names = names.get_object() if hasattr(names, "get_object") else names
        if names.get("/JavaScript") is not None or names.get("/EmbeddedFiles") is not None:
            raise EvidenceError("PDF scripts or embedded files not allowed")
    if root.get("/Collection") is not None:
        raise EvidenceError("PDF portfolios require separate review")

    page_text: list[str] = []
    total = 0
    for page in reader.pages:
        if page.get("/AA") is not None:
            raise EvidenceError("PDF page additional actions not allowed")
        # Untrusted annotations can refer to external actions or file attachments.
        # Retain an explicit hold instead of trying to sanitize in this preflight.
        if page.get("/Annots"):
            raise EvidenceError("annotated PDF requires separate inspection")
        extracted = page.extract_text()
        if not isinstance(extracted, str):
            raise EvidenceError("PDF text extraction failed")
        visible = " ".join(extracted.split())
        if len(visible) < 24:
            raise EvidenceError("PDF page blank, scanned, or unreadable without OCR")
        if len(visible) > MAX_PAGE_TEXT:
            raise EvidenceError("PDF page text exceeds review cap")
        total += len(visible)
        if total > MAX_TOTAL_TEXT:
            raise EvidenceError("PDF text exceeds package review cap")
        page_text.append(visible)
    return {
        "page_count": pages_count,
        "pages": page_text,
        "pdf_sha256": hashlib.sha256(raw).hexdigest(),
        "text_sha256": hashlib.sha256("\n".join(page_text).encode()).hexdigest(),
        "ocr_needed": False,
        "review_status": "HOLD_FOR_INDEPENDENT_REVIEW",
    }


def _child_main() -> int:
    data = sys.stdin.buffer.read(MAX_PDF_BYTES + 1)
    try:
        result = _parse_pdf_in_child(data)
        sys.stdout.write(json.dumps({"ok": True, "result": result}))
        return 0
    except Exception as exc:
        # Avoid leaking PDF contents / stack traces through CI or logs.
        sys.stdout.write(json.dumps({
            "ok": False, "error": exc.__class__.__name__,
        }))
        return 2


def _set_process_limits() -> None:
    """Best-effort POSIX limits; external host sandbox still required."""
    import resource
    resource.setrlimit(resource.RLIMIT_CPU, (5, 6))
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))


def inspect_pdf_bytes(raw: bytes) -> dict[str, Any]:
    """Inspect one bounded PDF in a separate process, fail-closed on any error."""
    if not isinstance(raw, bytes) or not 100 <= len(raw) <= MAX_PDF_BYTES:
        raise EvidenceError("PDF bytes missing or oversized")
    if not raw.startswith(b"%PDF-"):
        raise EvidenceError("unrecognized PDF header")
    args = [sys.executable, "-m", "company_os.pdf_evidence", "--extract-child"]
    env = {
        key: os.environ[key] for key in ("PATH", "PYTHONPATH", "VIRTUAL_ENV", "PYTHONHOME")
        if key in os.environ
    }
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        p = subprocess.run(
            args, input=raw, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=EXTRACT_TIMEOUT, check=False, env=env,
            preexec_fn=_set_process_limits if os.name == "posix" else None,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise EvidenceError("PDF worker unavailable, timed out or resource-limited") from exc
    if p.returncode != 0 or len(p.stdout) > MAX_TOTAL_TEXT * 5:
        raise EvidenceError("PDF extraction worker refused or failed")
    try:
        obj = json.loads(p.stdout)
    except (ValueError, UnicodeError) as exc:
        raise EvidenceError("PDF extractor output invalid") from exc
    if not isinstance(obj, dict) or obj.get("ok") is not True:
        raise EvidenceError("PDF extractor could not verify complete readable text")
    result = obj.get("result")
    if (not isinstance(result, dict)
            or result.get("pdf_sha256") != hashlib.sha256(raw).hexdigest()
            or result.get("review_status") != "HOLD_FOR_INDEPENDENT_REVIEW"):
        raise EvidenceError("PDF extraction integrity mismatch")
    pages = result.get("pages")
    if (not isinstance(pages, list) or not pages
            or len(pages) != result.get("page_count")
            or any(not isinstance(page, str) or len(page) > MAX_PAGE_TEXT for page in pages)):
        raise EvidenceError("PDF extraction structure invalid")
    return result


if __name__ == "__main__" and sys.argv[1:] == ["--extract-child"]:
    raise SystemExit(_child_main())
