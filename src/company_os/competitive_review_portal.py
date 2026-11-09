"""CE-1P: private, offline visual reviewer interface over exact CE-1N pages.

Revalidates the private sealed source-room and CE-1O pending worklist, then
writes ONE self-contained read-only HTML viewer with actual PNG pixels and
full claim/counterevidence context. No HTTP service, network requests,
external assets, remote storage, signing, approval, or business action.

An authorized OS provisioner MUST separately grant the legitimate reviewer
read-only file access. Merely viewing or exporting notes does NOT establish a
qualified independent critic or permission to publish.
"""
from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import re
import stat
from pathlib import Path
from typing import Any, Mapping

from .competitive_critic_observations import (
    _get_room_packet, build_pending_observation_worklist,
)
from .competitive_critic_room import (
    MAX_SINGLE_IMAGE_BYTES, _check_metadata_file, _safe_create, _sha,
)
from .source_provenance import EvidenceError

PORTAL_FORMAT = "CE1P_OFFLINE_VIEWER_V1"
MAX_HTML_BYTES = 98 * 1024 * 1024
_PORTAL_ID = re.compile(r"^[a-z][a-z0-9_-]{2,63}$")

_CSS = r"""
:root { color-scheme:dark; --bg:#0c1220; --panel:#171f30; --panel2:#222c41; --text:#edf1fc; --sub:#b9c6d9; --line:#44516b; --accent:#bd9bff; --focus:#a3d8ff; }
* { box-sizing:border-box; }
body { margin:0; font-family:system-ui,-apple-system,"Segoe UI",sans-serif; background:var(--bg); color:var(--text); line-height:1.48; }
a { color:var(--focus); }
a:focus-visible,button:focus-visible,select:focus-visible,textarea:focus-visible,input:focus-visible,summary:focus-visible { outline:3px solid var(--focus);outline-offset:3px; }
header { padding:28px max(18px,calc((100vw - 1280px)/2)); background:linear-gradient(120deg,#182039,#12192a); border-bottom:1px solid var(--line); }
main { max-width:1280px; margin:auto; padding:24px 18px 90px; }
h1 { font-size:clamp(24px,4vw,37px);margin:9px 0;line-height:1.12;letter-spacing:-.02em; }
h2 { font-size:25px;margin:45px 0 7px;letter-spacing:-.01em; }
h3 { font-size:19px;margin:0 0 7px; }
p { margin:7px 0 13px; }
small,.muted {color:var(--sub);}
.eyebrow { color:#dbceff; text-transform:uppercase; letter-spacing:.13em; font-size:12px; font-weight:750; }
.warning { max-width:1080px;color:#ffd7a3;font-size:14px; }
.topline { display:flex;align-items:center;gap:13px;flex-wrap:wrap;}
.stamp { border:1px solid #ceaa6c;border-radius:999px;padding:5px 11px;color:#ffe4ac;font-size:12px;font-weight:750;letter-spacing:.04em; }
.counts { display:flex;gap:22px;flex-wrap:wrap;color:var(--sub);font-size:13px; }
.toolbar {position:sticky;top:0;z-index:2;display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;background:#101929f7;border:1px solid var(--line);border-radius:14px;padding:12px 15px;box-shadow:0 9px 30px #0005;}
.toolbar nav {display:flex;gap:16px;flex-wrap:wrap;font-size:14px;}
.progress {color:var(--focus);font-size:13px;font-weight:600;}
.stack {display:grid;gap:24px;margin-top:17px;}
.panel {background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:22px;overflow-wrap:anywhere;box-shadow:0 3px 20px #0002;}
.page-grid {display:grid;grid-template-columns:minmax(0,1.65fr) minmax(250px,1fr);gap:20px;align-items:start;margin-top:16px;}
figure {background:#e8e9ea;border-radius:10px;padding:10px;margin:0;overflow:auto;min-height:140px;}
figure img {display:block;max-width:100%;height:auto;object-fit:contain;margin:auto;}
figcaption {padding:7px;color:#273246;font-size:12px;text-align:center;overflow-wrap:anywhere;}
.fieldset {padding:0;border:0;margin:0;display:grid;gap:12px;}
.field {display:grid;gap:7px;}
label {font-weight:650;font-size:14px;color:#e3ebfb;}
select,textarea {width:100%;background:#0e1727;color:var(--text);border:1px solid #677590;border-radius:8px;padding:10px 12px;font:inherit;}
textarea {min-height:120px;resize:vertical;line-height:1.5;}
select {min-height:45px;}
button {border:1px solid #9cb1d3;background:#243453;color:#eef3ff;border-radius:9px;font-weight:650;padding:10px 15px;font:inherit;cursor:pointer;}
button.primary {background:#8456db;border-color:#b69af7;color:#fff;}
button:hover {filter:brightness(1.15);}
.badge {display:inline-block;color:#d9e8ff;background:#293950;border:1px solid #486181;border-radius:5px;padding:2px 7px;font-size:12px;}
.badge.absent {color:#ffd8ad;background:#422d25;border-color:#8d593a;}
.source-list {display:grid;gap:9px;margin:14px 0 17px;}
details {background:var(--panel2);border:1px solid var(--line);border-radius:9px;padding:12px 13px;font-size:13px;}
summary {cursor:pointer;font-weight:680;color:#e2ecff;}
.excerpt {white-space:pre-wrap;background:#0d1625;padding:11px;border-radius:6px;color:#dfe7f7;}
.hash {font-family:ui-monospace,monospace;font-size:11px;word-break:break-all;color:#c6d2e4;}
.summary-box {margin-top:28px;display:grid;gap:12px;}
.actions {display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin:16px 0;}
.hidden-file {width:0;height:0;opacity:0;position:absolute;}
.status {font-size:14px;color:#d5e3f7;min-height:35px;}
.status.error {color:#ffd0cb;}
.state-note {color:#ffc6ae;font-size:13px;}
@media (max-width:810px) { .page-grid {grid-template-columns:1fr;} .panel{padding:15px;} header{padding:20px 18px;} .toolbar{position:static;} }
@media print { body{background:#fff;color:#111;} .toolbar,.actions,.fieldset{display:none;} .panel{break-inside:avoid;} }
""".strip()

_JS = r"""
"use strict";
(() => {
  const ctx = JSON.parse(document.getElementById("review-context").textContent);
  const pageCards = Array.from(document.querySelectorAll(".page-card"));
  const claimCards = Array.from(document.querySelectorAll(".claim-card"));
  const summary = document.getElementById("review-summary");
  const status = document.getElementById("status");
  const progress = document.getElementById("progress");
  const pageValues = new Set(["legible_reported","defect_reported","unassessable"]);
  const claimValues = new Set(["packet_excerpt_located","contradiction_reported","unverified"]);
  const stamp = () => new Date().toISOString();
  const value = (card, query) => card.querySelector(query).value.trim();
  function announce(message, error=false) {
    status.textContent = message;
    status.classList.toggle("error", error);
  }
  function observationData(requireComplete) {
    const time = stamp();
    const pages = ctx.page_tasks.map((task, i) => {
      const card = pageCards[i];
      const finding = value(card, ".page-finding");
      const notes = value(card, ".page-notes");
      if (requireComplete && (!pageValues.has(finding) || notes.length < 36 || notes.length > 1200)) {
        throw Error("Page " + (i+1) + " needs a manually chosen finding and 36–1200 characters of notes.");
      }
      return {
        file: task.file, png_sha256: task.png_sha256,
        observed_at: requireComplete ? time : null,
        visual_finding: finding || null, visual_notes: notes || null
      };
    });
    const claims = ctx.claim_tasks.map((task,i) => {
      const card = claimCards[i];
      const disposition = value(card, ".claim-disposition");
      const reasoning = value(card, ".claim-reasoning");
      if (disposition === "packet_excerpt_located" && !task.issuer_citation_refs.length) {
        throw Error("Claim " + task.claim_id + " has no original issuer page in this packet.");
      }
      if (requireComplete && (!claimValues.has(disposition) || reasoning.length < 48 || reasoning.length > 1500)) {
        throw Error("Claim " + task.claim_id + " needs a finding and 48–1500 characters of reasoning.");
      }
      return {
        claim_id: task.claim_id,
        source_ids_considered: task.source_ids_considered,
        counter_source_ids_considered: task.counter_source_ids_considered,
        issuer_citation_refs: task.issuer_citation_refs,
        assessed_at: requireComplete ? time : null,
        disposition: disposition || null, reasoning: reasoning || null
      };
    });
    const reviewerSummary = summary.value.trim();
    if (requireComplete && (reviewerSummary.length < 60 || reviewerSummary.length > 2000)) {
      throw Error("Overall reviewer summary must contain 60–2000 characters.");
    }
    return {pages,claims,reviewerSummary};
  }
  function download(filename, content) {
    const bytes = new Blob([JSON.stringify(content,null,2)],{type:"application/json"});
    const url = URL.createObjectURL(bytes);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.hidden = true;
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  }
  function refresh() {
    const pages = pageCards.filter(card => pageValues.has(value(card,".page-finding")) && value(card,".page-notes").length>=36).length;
    const claims = claimCards.filter(card => claimValues.has(value(card,".claim-disposition")) && value(card,".claim-reasoning").length>=48).length;
    progress.textContent = pages+"/"+pageCards.length+" pages • "+claims+"/"+claimCards.length+" claims recorded";
  }
  document.getElementById("save-draft").addEventListener("click", () => {
    try {
      const notes=observationData(false);
      download("CE1P-PRIVATE-UNSIGNED-DRAFT.json",{
        schema_version:"CE1P_LOCAL_DRAFT_V1",room_manifest_sha256:ctx.room_manifest_sha256,
        pages:notes.pages.map(x=>({file:x.file,visual_finding:x.visual_finding,visual_notes:x.visual_notes})),
        claims:notes.claims.map(x=>({claim_id:x.claim_id,disposition:x.disposition,reasoning:x.reasoning})),
        reviewer_summary:notes.reviewerSummary,publication_authorized:false
      });
      announce("Private unsigned draft saved. Keep it in an approved secure location; no review was signed.");
    } catch (err) { announce(String(err.message), true); }
  });
  document.getElementById("load-draft").addEventListener("change", async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    try {
      if (file.size > 750000) throw Error("Draft exceeds the 750 KB review limit.");
      const draft = JSON.parse(await file.text());
      if (draft.schema_version!=="CE1P_LOCAL_DRAFT_V1" || draft.publication_authorized!==false ||
          draft.room_manifest_sha256!==ctx.room_manifest_sha256 ||
          !Array.isArray(draft.pages) || draft.pages.length!==pageCards.length ||
          !Array.isArray(draft.claims) || draft.claims.length!==claimCards.length) {
        throw Error("Draft does not belong to this exact sealed room.");
      }
      // Check every task before modifying ANY existing editor field.
      draft.pages.forEach((x,i) => {
        if (x.file!==ctx.page_tasks[i].file ||
            (x.visual_finding!==null && !pageValues.has(x.visual_finding)) ||
            (x.visual_notes!==null && (typeof x.visual_notes!=="string" || x.visual_notes.length>1200))) {
          throw Error("Draft page record is missing or invalid.");
        }
      });
      draft.claims.forEach((x,i) => {
        if (x.claim_id!==ctx.claim_tasks[i].claim_id ||
            (x.disposition!==null && !claimValues.has(x.disposition)) ||
            (x.disposition==="packet_excerpt_located" && !ctx.claim_tasks[i].issuer_citation_refs.length) ||
            (x.reasoning!==null && (typeof x.reasoning!=="string" || x.reasoning.length>1500))) {
          throw Error("Draft claim record is missing or invalid.");
        }
      });
      if (typeof draft.reviewer_summary!=="string" || draft.reviewer_summary.length>2000) {
        throw Error("Draft reviewer summary is invalid.");
      }
      draft.pages.forEach((x,i) => {
        pageCards[i].querySelector(".page-finding").value=x.visual_finding||"";
        pageCards[i].querySelector(".page-notes").value=x.visual_notes||"";
      });
      draft.claims.forEach((x,i) => {
        claimCards[i].querySelector(".claim-disposition").value=x.disposition||"";
        claimCards[i].querySelector(".claim-reasoning").value=x.reasoning||"";
      });
      summary.value=draft.reviewer_summary;
      refresh();
      announce("Room-bound unsigned notes restored. Every page and claim still requires a genuine review.");
    } catch (err) { announce(String(err.message), true); }
    finally {event.target.value="";}
  });
  document.getElementById("review-form").addEventListener("submit", (event) => {
    event.preventDefault();
    try {
      const notes=observationData(true);
      download("CE1P-UNSIGNED-REVIEW-OBSERVATIONS.json",{
        schema_version:"CE1P_UNSIGNED_OBSERVATIONS_V1",
        room_manifest_sha256:ctx.room_manifest_sha256,
        dossier_sha256:ctx.dossier_sha256,
        handoff_sha256:ctx.handoff_sha256,
        issuer_inventory_head_sha256:ctx.issuer_inventory_head_sha256,
        page_observations:notes.pages,claim_assessments:notes.claims,
        reviewer_summary:notes.reviewerSummary,
        independent_critic_approved:false,publication_authorized:false,
        requires_separate_root_governed_review_signing:true
      });
      announce("UNSIGNED observations exported. Separate identity verification, signing, independent checking, and release gates are still required.");
    } catch (err) { announce(String(err.message), true); }
  });
  document.getElementById("review-form").addEventListener("input", refresh);
  document.getElementById("review-form").addEventListener("change", refresh);
  refresh();
})();
""".strip()


def _escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _json_for_html(value: Any) -> str:
    # JSON within a script[type=application/json] MUST escape < to prevent
    # attacker-provided text from closing the element and injecting markup.
    data = json.dumps(value, ensure_ascii=True, allow_nan=False,
                      sort_keys=True, separators=(",", ":"))
    return (data.replace("<", "\\u003c").replace(">", "\\u003e")
            .replace("&", "\\u0026"))


def _source_cards(claim: Mapping[str, Any], sources: Mapping[str, Any],
                  citations: Mapping[str, Any]) -> str:
    result = []
    for role, entries in (
        ("Supporting source", claim["source_ids"]),
        ("Counterevidence", claim["counter_source_ids"]),
    ):
        for sid in entries:
            item = sources[sid]
            quote = _escape(item.get("excerpt", ""))
            citation = citations.get(sid)
            if citation:
                anchor = "page-" + citation["document_id"] + "-" + str(citation["page_number"])
                evidence = (
                    '<span class="badge">Original excerpt page in this packet</span> '
                    '<a href="#'+_escape(anchor)+'">View cited image</a>'
                )
            else:
                evidence = (
                    '<span class="badge absent">Original not in sealed issuer-PDF packet</span>'
                )
            result.append(
                '<details><summary>'+_escape(role)+': '+_escape(sid)+
                ' — '+_escape(item.get("publisher", ""))+'</summary>'
                '<p>'+evidence+'</p><p class="muted">Type: '+_escape(item.get("kind", ""))+
                ' · Source URL (text only): '+_escape(item.get("url", ""))+'</p>'
                '<p class="excerpt">'+quote+'</p></details>'
            )
    return "".join(result)


def _create_html(room: Path, digest: str) -> bytes:
    # _get_room_packet verifies all page bytes/metadata and manifest digest.
    packet = _get_room_packet(room, digest)
    pending = build_pending_observation_worklist(
        room, expected_manifest_sha256=digest,
    )
    pages = pending["page_tasks"]
    claims = pending["claim_tasks"]
    dossier = packet["dossier"]
    sources = {source["id"]: source for source in dossier["sources"]}
    citation_by_id = {
        row["source_id"]: row
        for row in packet["original_pdf_worklist"]["source_requirements"]
    }

    page_markup = []
    for i, task in enumerate(pages):
        png_path = room / "pages" / task["file"]
        png = _check_metadata_file(png_path, maximum=MAX_SINGLE_IMAGE_BYTES)
        if hashlib.sha256(png).hexdigest() != task["png_sha256"]:
            raise EvidenceError("original PDF viewer image changed after workroom validation")
        img = base64.b64encode(png).decode("ascii")
        stem = task["file"].rsplit("-page-",1)
        doc = stem[0]
        index = int(stem[1][:3])
        anchor = "page-" + doc + "-" + str(index)
        page_markup.append(
            '<article class="panel page-card" id="'+_escape(anchor)+'" data-index="'+str(i)+'">'
            '<div class="topline"><h3>Original PDF page '+str(i+1)+'</h3>'
            '<span class="badge">'+_escape(doc)+' · page '+str(index)+'</span></div>'
            '<div class="page-grid"><figure><img loading="lazy" decoding="async" '
            'alt="Reproducible original PDF page '+str(i+1)+'" '
            'src="data:image/png;base64,'+img+'">'
            '<figcaption>Controlled PDFium render · SHA-256 '+_escape(task["png_sha256"])+'</figcaption>'
            '</figure><fieldset class="fieldset"><legend class="muted">Reviewer observations (start unanswered)</legend>'
            '<div class="field"><label for="page-finding-'+str(i)+'">Visual finding</label>'
            '<select class="page-finding" id="page-finding-'+str(i)+'" required>'
            '<option value="">Select after inspecting</option>'
            '<option value="legible_reported">Legible (reviewer report only)</option>'
            '<option value="defect_reported">Potential defect / discrepancy</option>'
            '<option value="unassessable">Cannot assess this page</option></select></div>'
            '<div class="field"><label for="page-notes-'+str(i)+'">What did you actually see? (36–1200 chars)</label>'
            '<textarea class="page-notes" id="page-notes-'+str(i)+'" maxlength="1200" '
            'placeholder="Describe legibility, visible facts, annotations, attachments, omissions or limits."></textarea></div>'
            '</fieldset></div></article>'
        )
    claim_markup = []
    for i,(task,claim) in enumerate(zip(claims,dossier["claims"],strict=True)):
        refs = task["issuer_citation_refs"]
        choices = '<option value="">Select after evaluating</option>'
        choices += '<option value="unverified">Unverified / additional original needed</option>'
        choices += '<option value="contradiction_reported">Contradiction or adverse evidence reported</option>'
        if refs:
            choices += '<option value="packet_excerpt_located">Original excerpt located in packet (not verified truth)</option>'
        orig = sum(1 for sid in claim["source_ids"]+claim["counter_source_ids"] if sid in citation_by_id)
        claim_markup.append(
            '<article class="panel claim-card" id="claim-'+_escape(task["claim_id"])+'" data-index="'+str(i)+'">'
            '<div class="topline"><h3>Claim '+str(i+1)+': '+_escape(task["claim_id"])+'</h3>'
            '<span class="badge">'+str(orig)+' original PDF citation(s)</span></div>'
            '<p>'+_escape(claim["text"])+'</p>'
            '<p class="muted">Class: '+_escape(claim.get("classification"))+
            ' · Materiality: '+_escape(claim.get("materiality"))+'</p>'
            '<div class="source-list">'+_source_cards(claim,sources,citation_by_id)+'</div>'
            '<fieldset class="fieldset"><legend class="muted">Independent challenge notes (not prefilled)</legend>'
            '<div class="field"><label for="claim-finding-'+str(i)+'">Disposition</label>'
            '<select class="claim-disposition" id="claim-finding-'+str(i)+'" required>'+choices+'</select></div>'
            '<div class="field"><label for="claim-notes-'+str(i)+'">Reasoning, limitations and counterevidence (48–1500 chars)</label>'
            '<textarea class="claim-reasoning" id="claim-notes-'+str(i)+'" maxlength="1500" '
            'placeholder="Explain what the supplied pages do and do not establish; identify contradictions and needed independent evidence."></textarea></div>'
            '</fieldset></article>'
        )
    context = {
        "room_manifest_sha256": digest,
        "dossier_sha256": packet["dossier_sha256"],
        "handoff_sha256": packet["handoff_sha256"],
        "issuer_inventory_head_sha256": packet["issuer_inventory_head_sha256"],
        "page_tasks": pages,
        "claim_tasks": claims,
        "review_completed": False,
        "publication_authorized": False,
    }
    ctx = _json_for_html(context)
    css_hash=base64.b64encode(hashlib.sha256(_CSS.encode()).digest()).decode()
    js_hash=base64.b64encode(hashlib.sha256(_JS.encode()).digest()).decode()
    csp = ("default-src 'none'; img-src data:; style-src 'sha256-"+css_hash+
           "'; script-src 'sha256-"+js_hash+
           "'; connect-src 'none'; form-action 'none'; object-src 'none'; "
           "frame-src 'none'; base-uri 'none'")
    page = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta name="referrer" content="no-referrer">'
        '<meta http-equiv="Content-Security-Policy" content="'+_escape(csp)+'">'
        '<title>CE-1P · Private Source Review</title>'
        '<style>'+_CSS+'</style></head><body>'
        '<header><div class="topline"><span class="eyebrow">K.O. Enterprises · Evidence review</span>'
        '<span class="stamp">HOLD · NO RELEASE AUTHORITY</span></div>'
        '<h1>Private source review</h1>'
        '<p class="warning">This file contains private evidence. Open offline in an approved reviewer account only. '
        'Every page and claim begins unanswered. Signed or exported statements do not prove independence or factual truth.</p>'
        '<div class="counts"><span>'+str(len(pages))+' exact original PDF pages</span>'
        '<span>'+str(len(claims))+' dossier claims</span><span>Issuer inventory: <span class="hash">'+
        _escape(packet["issuer_inventory_head_sha256"])+'</span></span></div></header>'
        '<main><div class="toolbar"><nav aria-label="Review sections">'
        '<a href="#pages">Source pages</a><a href="#claims">Claims & counterevidence</a>'
        '<a href="#complete">Export findings</a></nav><span id="progress" class="progress" aria-live="polite">'
        '0/'+str(len(pages))+' pages · 0/'+str(len(claims))+' claims recorded</span></div>'
        '<form id="review-form" autocomplete="off" novalidate>'
        '<section id="pages" aria-label="Original PDF images"><h2>01 / View every original page</h2>'
        '<p class="muted">Images below contain the actual bytes of the sealed, controlled PDFium renders. '
        'Use the detailed notes to document what you actually observe; a matching PNG hash is not an inspection.</p>'
        '<div class="stack">'+''.join(page_markup)+'</div></section>'
        '<section id="claims" aria-label="Claim and counterevidence analysis"><h2>02 / Challenge every claim</h2>'
        '<p class="muted">All supporting and contrary source IDs remain visible. Vendor, buyer, or secondary '
        'claims without original documents in this packet must not be treated as independently verified.</p>'
        '<div class="stack">'+''.join(claim_markup)+'</div></section>'
        '<section id="complete" class="panel summary-box"><h2>03 / Reviewer summary & private export</h2>'
        '<label for="review-summary">Overall findings and unresolved questions (60–2000 chars)</label>'
        '<textarea id="review-summary" maxlength="2000" placeholder="Describe factual limitations, missing originals, '
        'source conflicts, required follow-up and reasons for any reported findings."></textarea>'
        '<p class="state-note">No signing key is present. Exported observations are UNSIGNED. '
        'They must be verified against this room, reviewed under separate authority and signed through an approved external process.</p>'
        '<div class="actions"><button type="button" id="save-draft">Save private draft</button>'
        '<label for="load-draft" class="badge">Reopen private draft (JSON)</label>'
        '<input class="hidden-file" type="file" id="load-draft" accept=".json,application/json">'
        '<button type="submit" class="primary" id="export-unsigned">Export complete UNSIGNED observations</button></div>'
        '<div class="status" id="status" role="status" aria-live="polite"></div></section></form></main>'
        '<script id="review-context" type="application/json">'+ctx+'</script>'
        '<script>'+_JS+'</script></body></html>'
    )
    raw=page.encode("utf-8")
    if len(raw)>MAX_HTML_BYTES:
        raise EvidenceError("offline visual review page exceeds private bounded capacity; no truncated output")
    return raw


def stage_private_visual_portal(
    room: Path | str,
    private_parent: Path | str,
    portal_id: str,
    *,
    expected_manifest_sha256: str,
) -> dict[str, Any]:
    """Build read-only fully offline HTML; provision access separately by UID."""
    digest=_sha(expected_manifest_sha256, "out-of-band sealed workroom manifest")
    if not isinstance(portal_id,str) or not _PORTAL_ID.fullmatch(portal_id):
        raise EvidenceError("private portal identifier invalid")
    room_path=Path(room)
    parent=Path(private_parent)
    if (parent.is_symlink() or not parent.is_dir()
            or parent.stat().st_mode&0o077
            or room_path.parent.resolve()!=parent.resolve()):
        raise EvidenceError("visual portal must be staged beside sealed room in private parent")
    if os.name=="posix" and parent.stat().st_uid!=os.geteuid():
        raise EvidenceError("visual portal parent not owned by current provisioner")
    raw=_create_html(room_path,digest)
    dest=parent/portal_id
    if dest.exists() or dest.is_symlink():
        raise EvidenceError("private reviewer portal already exists")
    dest.mkdir(mode=0o700)
    try:
        _safe_create(dest/"index.html",raw)
        os.chmod(dest,0o500)
    except BaseException:
        # A partial private directory has no valid completion receipt.
        raise
    return {
        "state":"PRIVATE_OFFLINE_VISUAL_PORTAL_AWAITING_SEPARATE_REAL_REVIEW",
        "portal":str(dest),
        "index_sha256":hashlib.sha256(raw).hexdigest(),
        "room_manifest_sha256":digest,
        "page_count":len(json.loads((room_path/"manifest.json").read_bytes())["pages"]),
        "claims_assessed":0,
        "pages_observed_by_real_critic":0,
        "independent_critic_approved":False,
        "publication_authorized":False,
    }


def inspect_private_visual_portal(
    portal: Path | str, *, expected_html_sha256: str,
) -> dict[str, Any]:
    """Check privacy modes and out-of-band hash; cannot attest actual viewing."""
    expected=_sha(expected_html_sha256,"visual portal HTML")
    directory=Path(portal)
    page=directory/"index.html"
    if (directory.is_symlink() or not directory.is_dir()
            or directory.stat().st_mode&0o222
            or {x.name for x in directory.iterdir()}!={"index.html"}):
        raise EvidenceError("private visual portal directory missing, changed or writable")
    raw=_check_metadata_file(page,maximum=MAX_HTML_BYTES)
    if not raw.startswith(b"<!doctype html>") or hashlib.sha256(raw).hexdigest()!=expected:
        raise EvidenceError("private visual portal HTML different from supplied digest")
    return {
        "state":"PRIVATE_OFFLINE_VIEWER_BYTES_VALID_REVIEW_NOT_PERFORMED",
        "html_sha256":expected,
        "external_resources_required":False,
        "qualified_reviewer_observed":False,
        "independent_critic_approved":False,
        "publication_authorized":False,
    }
