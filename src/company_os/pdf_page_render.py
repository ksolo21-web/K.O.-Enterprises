"""CE-1M: reproducible, resource-capped original PDF page rasterization.

Use a single fixed PDFium/Pillow renderer profile. This process validates
source-document bytes *as images*, not independent reviewers or issuer identity.
PDFium is native code and RLIMIT/subprocess isolation is only a best-effort
local preflight, NOT a hardened sandbox for hostile production PDFs.
"""
from __future__ import annotations

import hashlib
import io
import os
import subprocess
import sys
from typing import Any

from .pdf_evidence import MAX_PDF_BYTES, MAX_PAGES
from .source_provenance import EvidenceError

PDFIUM_VERSION = "5.15.1"
PILLOW_VERSION = "12.3.0"
RENDER_PROFILE = "pdfium-5.15.1-pillow-12.3.0-rgb-png-108dpi-v1"
RENDER_SCALE = 1.5
MAX_PAGE_PIXELS = 5_000_000
MAX_PNG_BYTES = 3_000_000
RENDER_TIMEOUT_SECONDS = 12
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _render_page_in_child(raw: bytes, number: int) -> bytes:
    """Runs exclusively in disposable, resource-limited worker process."""
    from importlib import metadata

    if (metadata.version("pypdfium2") != PDFIUM_VERSION
            or metadata.version("Pillow") != PILLOW_VERSION):
        raise EvidenceError("PDF render backend version differs from approved profile")

    import pypdfium2

    pdf = pypdfium2.PdfDocument(raw)
    try:
        pages = len(pdf)
        if not 1 <= pages <= MAX_PAGES or not 1 <= number <= pages:
            raise EvidenceError("PDF page count or requested page outside approved bounds")
        page = pdf[number - 1]
        try:
            width, height = page.get_size()
            pixels_x = round(width * RENDER_SCALE)
            pixels_y = round(height * RENDER_SCALE)
            if (not 64 <= pixels_x <= 4096 or not 64 <= pixels_y <= 4096
                    or pixels_x * pixels_y > MAX_PAGE_PIXELS):
                raise EvidenceError("original PDF page dimensions exceed render budget")
            bitmap = page.render(
                scale=RENDER_SCALE, rotation=0, may_draw_forms=False,
            )
            try:
                image = bitmap.to_pil().convert("RGB")
                if (not 64 <= image.width <= 4096
                        or not 64 <= image.height <= 4096
                        or image.width * image.height > MAX_PAGE_PIXELS):
                    raise EvidenceError("rendered PDF image exceeded pixel budget")
                buffer = io.BytesIO()
                image.save(buffer, format="PNG", compress_level=6, optimize=False)
                result = buffer.getvalue()
                if not 70 <= len(result) <= MAX_PNG_BYTES or not result.startswith(PNG_MAGIC):
                    raise EvidenceError("rendered PDF PNG exceeded evidence capacity")
                return result
            finally:
                bitmap.close()
        finally:
            page.close()
    finally:
        pdf.close()


def _resource_limits() -> None:
    """POSIX best-effort containment; require external sandbox in production."""
    import resource

    resource.setrlimit(resource.RLIMIT_CPU, (9, 10))
    resource.setrlimit(resource.RLIMIT_AS, (768 * 1024**2, 768 * 1024**2))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))


def _child(number: int) -> int:
    raw = sys.stdin.buffer.read(MAX_PDF_BYTES + 1)
    try:
        if len(raw) > MAX_PDF_BYTES or not raw.startswith(b"%PDF-"):
            raise EvidenceError("original PDF render input invalid")
        png = _render_page_in_child(raw, number)
        sys.stdout.buffer.write(png)
        return 0
    except Exception:
        # Don't expose private PDF or tracebacks to the parent/logs.
        return 2


def render_pdf_page(raw: bytes, page_number: int) -> bytes:
    """Re-render exactly one PDF page as a deterministic PNG evidence artifact.

    No file output, no URL and no business action. Use separately verified
    original source bytes; this function doesn't authenticate their origin.
    """
    if (not isinstance(raw, bytes) or not 100 <= len(raw) <= MAX_PDF_BYTES
            or not raw.startswith(b"%PDF-")
            or type(page_number) is not int or not 1 <= page_number <= MAX_PAGES):
        raise EvidenceError("PDF page renderer input or page number invalid")
    env = {
        key: os.environ[key]
        for key in ("PATH", "PYTHONPATH", "VIRTUAL_ENV", "PYTHONHOME")
        if key in os.environ
    }
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    args = [sys.executable, "-m", "company_os.pdf_page_render", "--child", str(page_number)]
    try:
        response = subprocess.run(
            args, input=raw, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=RENDER_TIMEOUT_SECONDS, check=False, env=env,
            preexec_fn=_resource_limits if os.name == "posix" else None,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise EvidenceError("source PDF page rendering timed out or was unavailable") from exc
    png = response.stdout
    if (response.returncode != 0 or not 70 <= len(png) <= MAX_PNG_BYTES
            or not png.startswith(PNG_MAGIC) or png[12:16] != b"IHDR"):
        raise EvidenceError("original PDF page could not be rendered under approved profile")
    return png


def page_image_evidence(raw: bytes, page_number: int) -> dict[str, Any]:
    """Digest-only reproducible rendering evidence for the input PDF page."""
    png = render_pdf_page(raw, page_number)
    return {
        "renderer_profile": RENDER_PROFILE,
        "source_pdf_sha256": hashlib.sha256(raw).hexdigest(),
        "page_number": page_number,
        "rendered_png_sha256": hashlib.sha256(png).hexdigest(),
        "rendered_png_width": int.from_bytes(png[16:20], "big"),
        "rendered_png_height": int.from_bytes(png[20:24], "big"),
        "visual_page_inspection_completed": False,
        "original_issuer_authenticated": False,
        "independent_reviewer_verified": False,
        "publication_authorized": False,
    }


if __name__ == "__main__" and len(sys.argv) == 3 and sys.argv[1] == "--child":
    try:
        requested_page = int(sys.argv[2])
    except (ValueError, OverflowError):
        raise SystemExit(2)
    raise SystemExit(_child(requested_page))
