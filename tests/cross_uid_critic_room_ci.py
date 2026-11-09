"""CE-1N actual separate Linux UID permission exercise, disposable CI ONLY.

Root is a *test provisioner*, not an independent critic. Different numeric
reviewer/capture/signing UIDs demonstrate a kernel-enforced access boundary.
The actual reviewer executes only a read-only hash verifier; no assertion of
visual/factual truth, real independent business review or client suitability.
"""
from __future__ import annotations

import hashlib
import json
import os
import pwd
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

REVIEWER_UID = 53014
CAPTURE_UID = 53012
SIGNER_UID = 53011
UNRELATED_UID = 53013
REVIEWER_GID = 53014


def _user_as(uid: int):
    def drop():
        os.setgroups([])
        os.setgid(uid)
        os.setuid(uid)
    return drop


def _child(uid: int, argv: list[str], *, code_root: Path) -> subprocess.CompletedProcess:
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "PYTHONPATH": str(code_root),
        "PYTHONDONTWRITEBYTECODE": "1",
        "COMPANY_OS_PAUSED": "1",
        "KO_SOURCE_APPROVED_HOSTS": "issuer.example",
    }
    return subprocess.run(
        [sys.executable, *argv],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        timeout=25, env=env, cwd="/", preexec_fn=_user_as(uid), check=False,
    )


def _perm_denied(uid: int, path: Path, code_root: Path, *, mutate: bool = False):
    verb = "write_bytes(b'CHANGED')" if mutate else "read_bytes()"
    code = "from pathlib import Path; import sys; Path(sys.argv[1])." + verb
    result = _child(uid, ["-c", code, str(path)], code_root=code_root)
    assert result.returncode != 0 and "PermissionError" in result.stderr, (
        "UID unexpectedly accessed restricted data", uid, path.name, result.returncode,
    )


def _provision_owned_critic_packet(source: Path, dest: Path):
    """Disposable root provisioner: reviewer GROUP may read; nobody may write."""
    shutil.copytree(source, dest)
    for path in [dest, *dest.rglob("*")]:
        if path.is_symlink():
            raise AssertionError("unexpected symlink in sealed source packet")
        os.chown(path, 0, REVIEWER_GID)
        os.chmod(path, 0o550 if path.is_dir() else 0o440)
    assert dest.stat().st_uid == 0
    assert dest.stat().st_gid == REVIEWER_GID
    assert stat.S_IMODE(dest.stat().st_mode) == 0o550


def main() -> int:
    if (
        not sys.platform.startswith("linux")
        or os.geteuid() != 0
        or os.environ.get("GITHUB_ACTIONS") != "true"
        or os.environ.get("KO_CE_REVIEWER_ROOM_CI") != "1"
        or os.environ.get("COMPANY_OS_PAUSED") != "1"
    ):
        raise SystemExit("refusing cross-UID reviewer room exercise outside opted-in disposable CI")
    for ident in (REVIEWER_UID, CAPTURE_UID, SIGNER_UID, UNRELATED_UID):
        try:
            pwd.getpwuid(ident)
        except KeyError:
            pass
        else:
            raise AssertionError("synthetic UID collides with host account")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import test_competitive_critic_room as fixture_module
    from company_os.competitive_review_portal import stage_private_visual_portal

    fx = fixture_module.SealedCriticRoomTests(
        "test_complete_actual_PDF_page_packet_stays_reviewer_pending"
    )
    fx.setUp()
    try:
        staged = fx.stage(room="crossuid-review-room")
        portal = stage_private_visual_portal(
            Path(staged["workroom"]), fx.parent,
            "crossuid-private-visual-interface",
            expected_manifest_sha256=staged["manifest_sha256"],
        )
        with tempfile.TemporaryDirectory(prefix="ko-ce1n-crossuid-", dir="/tmp") as temp:
            root = Path(temp)
            os.chmod(root, 0o711)
            code_root = root/"code"
            package_root = code_root/"company_os"
            shutil.copytree(
                Path.cwd()/"src/company_os", package_root,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
            for path in (code_root, *code_root.rglob("*")):
                if path.is_symlink():
                    raise AssertionError("unexpected symlink in reviewer executable")
                os.chown(path, 0, 0)
                os.chmod(path, 0o755 if path.is_dir() else 0o644)

            private_signer = root/"private-signer"
            private_signer.mkdir(mode=0o700)
            os.chown(private_signer, SIGNER_UID, SIGNER_UID)
            key = private_signer/"synthetic-key.bin"
            key.write_bytes(b"synthetic-key-never-real-credential")
            os.chown(key, SIGNER_UID, SIGNER_UID)
            os.chmod(key, 0o400)

            private_capture = root/"private-capture"
            private_capture.mkdir(mode=0o700)
            os.chown(private_capture, CAPTURE_UID, CAPTURE_UID)
            raw_pdf = private_capture/"original-private.pdf"
            # Actual PDF bytes exist, but reviewer only receives reproductions.
            fixture_pdf = fx.root/"state/competitive_engine/capture_staging/pkg-one/notice.pdf"
            original = fixture_pdf.read_bytes()
            raw_pdf.write_bytes(original)
            os.chown(raw_pdf, CAPTURE_UID, CAPTURE_UID)
            os.chmod(raw_pdf, 0o400)

            reviewer_room = root/"review-room"
            _provision_owned_critic_packet(Path(staged["workroom"]), reviewer_room)
            private_viewer = root/"private-review-viewer"
            _provision_owned_critic_packet(Path(portal["portal"]), private_viewer)
            viewer_html = private_viewer/"index.html"
            assert stat.S_IMODE(viewer_html.stat().st_mode) == 0o440

            manifest = reviewer_room/"manifest.json"
            page = next((reviewer_room/"pages").iterdir())
            sha = staged["manifest_sha256"]

            reviewer = _child(
                REVIEWER_UID,
                ["-m", "company_os.competitive_critic_room",
                 "--verify", str(reviewer_room), sha],
                code_root=code_root,
            )
            assert reviewer.returncode == 0, (
                "authorized reader failed", reviewer.stderr[:350], reviewer.stdout[:350],
            )
            verdict = json.loads(reviewer.stdout)
            assert verdict["state"] == "READ_ONLY_SOURCE_PAGE_ROOM_HASHES_VERIFIED_REVIEW_PENDING"
            assert verdict["page_count"] == 2
            assert verdict["original_source_count"] == 1
            assert verdict["publication_authorized"] is False
            assert verdict["reviewer_independence_operationally_verified"] is False
            print("PASS: real separate reviewer UID can ONLY verify exact sealed original PDF-page packet")

            for uid in (CAPTURE_UID, UNRELATED_UID):
                response = _child(
                    uid,
                    ["-m", "company_os.competitive_critic_room",
                     "--verify", str(reviewer_room), sha],
                    code_root=code_root,
                )
                assert response.returncode != 0, "unapproved UID read critic room"
            print("PASS: capture UID and unrelated UID cannot read reviewer room")

            for protected in (key, raw_pdf, private_signer, private_capture):
                _perm_denied(REVIEWER_UID, protected, code_root)
            for readonly in (manifest, page):
                _perm_denied(REVIEWER_UID, readonly, code_root, mutate=True)
                _perm_denied(CAPTURE_UID, readonly, code_root)
            print("PASS: reviewer denied capture originals, signer key and reviewer packet writes")

            # CE-1P: the actual self-contained page images are present in the
            # private HTML. The reviewer can read it, but cannot alter its bytes;
            # other numeric UIDs do not have access to the whole interface.
            viewer_probe = (
                "import hashlib,json,sys; "
                "from pathlib import Path; "
                "raw=Path(sys.argv[1]).read_bytes(); "
                "print(json.dumps({'sha256':hashlib.sha256(raw).hexdigest(),"
                "'page_images':raw.count(b'data:image/png;base64,'),"
                "'offline':b\"connect-src 'none'\" in raw,"
                "'unsigned':b'UNSIGNED-REVIEW-OBSERVATIONS' in raw}))"
            )
            view_result = _child(
                REVIEWER_UID, ["-c", viewer_probe, str(viewer_html)],
                code_root=code_root,
            )
            assert view_result.returncode == 0, view_result.stderr[:200]
            viewer_evidence = json.loads(view_result.stdout)
            assert viewer_evidence["sha256"] == portal["index_sha256"]
            assert viewer_evidence["page_images"] == 2
            assert viewer_evidence["offline"] and viewer_evidence["unsigned"]
            for blocked_uid in (CAPTURE_UID, UNRELATED_UID):
                _perm_denied(blocked_uid, viewer_html, code_root)
            _perm_denied(REVIEWER_UID, viewer_html, code_root, mutate=True)
            _perm_denied(REVIEWER_UID, private_viewer, code_root, mutate=True)
            print("PASS: separate reviewer UID reads exact private offline visual page; other UIDs denied; browser file cannot be modified")

            forged = _child(
                REVIEWER_UID,
                ["-m", "company_os.competitive_critic_room",
                 "--verify", str(reviewer_room), "0" * 64],
                code_root=code_root,
            )
            assert forged.returncode != 0, "reviewer accepted untrusted external manifest digest"
            print("PASS: wrong externally supplied manifest digest fails closed")

        print("CE-1N actual distinct Linux UID review-room isolation checks PASSED; NO independent critic performed")
        return 0
    finally:
        fx.doCleanups()


if __name__ == "__main__":
    raise SystemExit(main())
