"""M5 V5 — synthetic-only inspection QA archive and verified restore.

Creates a temporary synthetic Option 2 PDF from pinned source fixtures and
bundles it with bounded provenance receipts. Does NOT read any customer data,
provide independent custody, approve a model or permit customer delivery.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import zipfile

from inspection_engine.core import load_project
from inspection_engine.report import build_pdf
from scripts.generate_public_fixtures import generate
from scripts.m5_release_quality_gate import (
    ROOT, MANIFEST, BASELINE_FILE, _pdf_signature, verify_reproducible_report,
)
from scripts.m5_safety_change_gate import (
    MANIFEST as GOVERNANCE_FILE, verify_safety_change_registry,
)

MEMBERS = (
    "proof/receipt.json",
    "proof/option2_synthetic.pdf",
    "proof/source_manifest.json",
    "proof/render_baseline.json",
    "proof/safety_source_registry.json",
)
SOURCES = {
    "proof/source_manifest.json": MANIFEST,
    "proof/render_baseline.json": BASELINE_FILE,
    "proof/safety_source_registry.json": GOVERNANCE_FILE,
}
MAX_ARCHIVE = 24_000_000
MAX_MEMBER = 12_000_000


class RecoveryBlock(ValueError):
    pass


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json(data: bytes):
    def unique(pairs):
        obj = {}
        for k, v in pairs:
            if k in obj:
                raise RecoveryBlock("Duplicate recovery evidence JSON field")
            obj[k] = v
        return obj
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=unique,
                          parse_constant=lambda value: (_ for _ in ()).throw(
                              RecoveryBlock("Noncanonical recovery JSON")))
    except RecoveryBlock:
        raise
    except (UnicodeError, ValueError) as exc:
        raise RecoveryBlock("Invalid recovery JSON") from exc


def _encode(obj: dict) -> bytes:
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def _outside_checkout(path: Path) -> Path:
    """Reject anything under an actual Git checkout or with symlink ancestry."""
    path = Path(path).expanduser().absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise RecoveryBlock("Recovery path uses symlink")
    if any((p / ".git").exists() for p in (path, *path.parents)):
        raise RecoveryBlock("Synthetic evidence artifact must remain outside Git")
    return path


def _info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | 0o600) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    return info


def _pdf_fingerprint(raw: bytes) -> tuple[int, str]:
    with tempfile.TemporaryDirectory(prefix="m5_pdf_restore_") as folder:
        file = Path(folder) / "synthetic.pdf"
        file.write_bytes(raw)
        try:
            rows = _pdf_signature(file)
        except Exception as exc:
            raise RecoveryBlock("Archived synthetic PDF could not be audited") from exc
    payload = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    return len(rows), _hash(payload)


def _read_bundle(path: Path) -> dict[str, bytes]:
    path = _outside_checkout(path)
    if path.is_symlink() or not path.is_file() or not 1 <= path.stat().st_size <= MAX_ARCHIVE:
        raise RecoveryBlock("Missing or oversized synthetic archive")
    try:
        with zipfile.ZipFile(path, "r") as archive:
            infos = archive.infolist()
            if len(infos) != len(MEMBERS) or [i.filename for i in infos] != list(MEMBERS):
                raise RecoveryBlock("Missing, duplicate, reordered or unexpected archive members")
            if sum(info.file_size for info in infos) > MAX_ARCHIVE:
                raise RecoveryBlock("Expanded recovery evidence exceeds size budget")
            for info in infos:
                mode = info.external_attr >> 16
                if (not 1 <= info.file_size <= MAX_MEMBER or
                        info.compress_size == 0 or
                        info.file_size > 200 * max(info.compress_size, 1) or
                        not stat.S_ISREG(mode) or info.filename.startswith("/") or
                        ".." in Path(info.filename).parts):
                    raise RecoveryBlock("Unsafe or unsupported synthetic archive entry")
            return {item.filename: archive.read(item) for item in infos}
    except RecoveryBlock:
        raise
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError) as exc:
        raise RecoveryBlock("Synthetic recovery evidence archive is unreadable") from exc


def verify_synthetic_bundle(path: Path, *, root: Path = ROOT) -> dict:
    """Verify bytes, exact source pins and PDF raster/text baseline; no extraction."""
    files = _read_bundle(path)
    receipt = _json(files["proof/receipt.json"])
    required = {"schema_version", "status", "customer_release_allowed",
                "page_count", "page_visual_and_text_fingerprint",
                "members_sha256", "synthetic_only"}
    if (not isinstance(receipt, dict) or set(receipt) != required
            or type(receipt["schema_version"]) is not int
            or receipt["schema_version"] != 1
            or receipt["status"] != "M5_SYNTHETIC_TEST_RECOVERY_ONLY"
            or receipt["customer_release_allowed"] is not False
            or receipt["synthetic_only"] is not True
            or type(receipt["page_count"]) is not int
            or not isinstance(receipt["page_visual_and_text_fingerprint"], str)):
        raise RecoveryBlock("Unapproved recovery receipt or customer-release claim")
    declared = receipt["members_sha256"]
    if not isinstance(declared, dict) or set(declared) != set(MEMBERS[1:]):
        raise RecoveryBlock("Recovery receipt excludes source evidence members")
    for key in MEMBERS[1:]:
        if declared[key] != _hash(files[key]):
            raise RecoveryBlock("Archived synthetic evidence member hash mismatch")
    for bundle_name, source in SOURCES.items():
        expected = (Path(root) / source).read_bytes()
        if files[bundle_name] != expected:
            raise RecoveryBlock("Recovery registry or baseline differs from approved source")
    pages, visual_hash = _pdf_fingerprint(files["proof/option2_synthetic.pdf"])
    if pages != receipt["page_count"] or visual_hash != receipt["page_visual_and_text_fingerprint"]:
        raise RecoveryBlock("Recovery PDF differs from sealed page/text evidence")
    baseline = _json(files["proof/render_baseline.json"])
    if (pages != baseline.get("expected_pages") or
            visual_hash != baseline.get("expected_visual_and_text_fingerprint") or
            baseline.get("customer_release_allowed") is not False):
        raise RecoveryBlock("Restored PDF differs from pinned Option 2 golden baseline")
    return {
        "status": "VERIFIED_SYNTHETIC_RECOVERY_ONLY",
        "archive_members_checked": len(MEMBERS),
        "rendered_pages_reverified": pages,
        "page_fingerprint_matches_pinned_baseline": True,
        "customer_data_recovered": False,
        "independent_custody_authenticated": False,
        "customer_release_allowed": False,
    }


def create_synthetic_bundle(destination: Path) -> dict:
    destination = _outside_checkout(destination)
    if destination.exists() or not destination.parent.is_dir():
        raise RecoveryBlock("Recovery destination must be new in an existing private directory")
    verify_safety_change_registry()
    verified = verify_reproducible_report()
    with tempfile.TemporaryDirectory(prefix="m5_bundle_source_") as folder:
        workspace = Path(folder)
        generate(workspace, video=False)
        fixture = workspace / "examples" / "editorial_demo_project.json"
        fixture.write_bytes((ROOT / "examples" / "editorial_demo_project.json").read_bytes())
        project = load_project(fixture)
        pdf_file = workspace / "synthetic.pdf"
        build_pdf(project, workspace / "examples", pdf_file)
        pdf_bytes = pdf_file.read_bytes()
    if len(pdf_bytes) > MAX_MEMBER:
        raise RecoveryBlock("Synthetic report exceeds archive budget")
    pages, fingerprint = _pdf_fingerprint(pdf_bytes)
    if (pages != verified["rendered_page_count"] or
            fingerprint != verified["page_visual_and_text_fingerprint"]):
        raise RecoveryBlock("Synthetic archive report differs from independently replayed baseline")
    members = {"proof/option2_synthetic.pdf": pdf_bytes}
    for bundle_name, source in SOURCES.items():
        members[bundle_name] = (ROOT / source).read_bytes()
    receipt = {
        "schema_version": 1, "status": "M5_SYNTHETIC_TEST_RECOVERY_ONLY",
        "synthetic_only": True, "customer_release_allowed": False,
        "page_count": pages,
        "page_visual_and_text_fingerprint": fingerprint,
        "members_sha256": {key: _hash(members[key]) for key in MEMBERS[1:]},
    }
    members["proof/receipt.json"] = _encode(receipt)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent,
                                         prefix=".m5_bundle_", suffix=".zip",
                                         delete=False) as handle:
            temporary = Path(handle.name)
        with zipfile.ZipFile(temporary, "w") as zipped:
            for name in MEMBERS:
                zipped.writestr(_info(name), members[name], compresslevel=6)
        verify_synthetic_bundle(temporary)
        if destination.exists():
            raise RecoveryBlock("Refusing to replace existing synthetic archive")
        os.replace(temporary, destination)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return verify_synthetic_bundle(destination)


def restore_synthetic_bundle(archive: Path, destination: Path) -> dict:
    result = verify_synthetic_bundle(archive)
    files = _read_bundle(archive)
    dest = _outside_checkout(destination)
    if dest.exists() or not dest.parent.is_dir():
        raise RecoveryBlock("Restore target must be a new, separate directory")
    try:
        dest.mkdir(mode=0o700)
        for name in MEMBERS:
            target = dest / Path(name).name
            target.write_bytes(files[name])
            if _hash(target.read_bytes()) != _hash(files[name]):
                raise RecoveryBlock("Restored synthetic evidence bytes do not match archive")
        # A restored copy is a read-only QC demonstration, not a customer report.
        return dict(result, restored_synthetic_files=len(MEMBERS),
                    restored_pdf_sha256=_hash((dest / "option2_synthetic.pdf").read_bytes()))
    except Exception:
        for name in MEMBERS:
            (dest / Path(name).name).unlink(missing_ok=True)
        dest.rmdir()
        raise


def main(argv=None):
    p = argparse.ArgumentParser(description="M5 synthetic-only archive, verification and recovery")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--create", type=Path)
    mode.add_argument("--verify", type=Path)
    mode.add_argument("--restore", nargs=2, metavar=("ARCHIVE", "NEW_DESTINATION"))
    args = p.parse_args(argv)
    try:
        if args.create is not None:
            result = create_synthetic_bundle(args.create)
        elif args.verify is not None:
            result = verify_synthetic_bundle(args.verify)
        else:
            result = restore_synthetic_bundle(Path(args.restore[0]),
                                             Path(args.restore[1]))
    except (RecoveryBlock, OSError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "SYNTHETIC_RECOVERY_BLOCKED",
                          "reason": str(exc), "customer_release_allowed": False}))
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
