"""CE-1P offline private visual page in real headless browser, synthetic fixtures.

Disposable CI only: Chrome renders **actual** generated HTML with exact
PDFium source-page images at desktop/mobile and source/claims/export anchors.
Screenshots are inspected for basic load/color/content, then destroyed inside
the temporary fixture. Never run this on actual private issuer/client data in
public GitHub Actions. This is NOT an independent source-review critic.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image


def _browser() -> str:
    for name in ("google-chrome", "chromium", "chromium-browser"):
        command = shutil.which(name)
        if command:
            return command
    raise AssertionError("No headless Chromium/Chrome executable: visual QA BLOCKED")


def main() -> int:
    if (os.environ.get("GITHUB_ACTIONS") != "true"
            or os.environ.get("KO_CE_PORTAL_BROWSER_CI") != "1"
            or os.environ.get("COMPANY_OS_PAUSED") != "1"):
        raise SystemExit("refusing private reviewer browser smoke outside opted-in paused disposable CI")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from company_os.competitive_review_portal import stage_private_visual_portal
    import test_competitive_critic_room as fixture_module

    fx = fixture_module.SealedCriticRoomTests(
        "test_complete_actual_PDF_page_packet_stays_reviewer_pending"
    )
    fx.setUp()
    try:
        source=fx.stage(room="synthetic-private-original-pdf-room")
        viewer=stage_private_visual_portal(
            Path(source["workroom"]),fx.parent,"synthetic-browser-viewer",
            expected_manifest_sha256=source["manifest_sha256"],
        )
        src=Path(viewer["portal"])/"index.html"
        chrome=_browser()
        url=src.resolve().as_uri()
        # View states: original page overview, claim/counterevidence, export.
        views=(
            ("desktop-pages",1365,900,""),
            ("mobile-pages",420,880,""),
            ("desktop-claims",1365,900,"#claims"),
            ("desktop-export",1365,900,"#complete"),
        )
        with tempfile.TemporaryDirectory(prefix="ce1p-browser-synthetic-") as tmp:
            root=Path(tmp)
            for name,width,height,fragment in views:
                shot=root/(name+".png")
                profile=root/("profile-"+name)
                args=[
                    chrome,"--headless=new","--no-sandbox",
                    "--disable-gpu","--disable-background-networking",
                    "--disable-component-update","--disable-extensions",
                    "--disable-default-apps","--disable-sync",
                    "--disable-features=Translate",
                    "--no-first-run","--no-default-browser-check",
                    "--no-proxy-server","--disable-dev-shm-usage",
                    "--hide-scrollbars","--force-device-scale-factor=1",
                    "--virtual-time-budget=1200",
                    "--window-size="+str(width)+","+str(height),
                    "--user-data-dir="+str(profile),
                    "--screenshot="+str(shot),url+fragment,
                ]
                proc=subprocess.run(
                    args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                    timeout=35,check=False,
                    env={**os.environ,"HOME":str(root)},
                )
                if proc.returncode!=0 or not shot.is_file():
                    raise AssertionError("headless browser failed to render "+name+
                                         "; code="+str(proc.returncode)+
                                         "; error="+proc.stderr.decode(errors="replace")[-300:])
                with Image.open(shot) as image:
                    image.load()
                    actual=image.convert("RGB")
                    if (actual.width < 350 or actual.height < 600
                            or max(actual.getpixel((20,20)))>=200):
                        raise AssertionError("offline visual page did not render with expected dark header: "+name)
                    colors=actual.getcolors(maxcolors=1000000)
                    if colors is not None and len(colors)<120:
                        raise AssertionError("offline visual page appears blank/unstyled: "+name)
                print("PASS: "+name+" actual headless browser screenshot rendered, offline private synthetic evidence only")
            # Privacy: no screenshots or generated HTML are uploaded or committed.
        print("CE-1P browser desktop/mobile/pages/claims/export viewport smoke PASS; NO reviewer approval")
        return 0
    finally:
        fx.doCleanups()


if __name__=="__main__":
    raise SystemExit(main())
