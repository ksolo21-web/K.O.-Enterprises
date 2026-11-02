"""No-network private M4 reviewer worksheet.

This is an offline convenience interface for reviewer *draft* choices; it cannot
authenticate a human, sign a decision or authorize customer release. The exported
JSON must be separately signed with the private local Ed25519 signing CLI.
"""
from __future__ import annotations

import base64
from io import BytesIO
import json
import os
from pathlib import Path

from PIL import Image, ImageOps
from .core import DataError, safe_path, sha256
from .m4_pipeline import _get_case, _atomic_json
from .m4_human_review import _get_packet, _digest, ROLES

HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'none'; form-action 'none'; base-uri 'none'">
<title>Private inspection review — NOT RELEASED</title>
<style>
:root{color-scheme:light; font:15px/1.5 system-ui,Arial,sans-serif;color:#17283c;background:#e9eef2}
*{box-sizing:border-box}body{margin:0}header{background:#152a3c;color:white;padding:22px max(18px,calc((100vw - 1050px)/2))}
h1{margin:0 0 6px;font-size:clamp(22px,3.5vw,33px)}h2{font-size:20px;margin:24px 0 12px}
main{max-width:1050px;margin:auto;padding:16px 18px 70px}.warning{border-left:5px solid #b58b52;background:#fff7e8;padding:12px;margin:12px 0}
.card{background:white;border:1px solid #c7d1dc;border-radius:9px;margin:10px 0;padding:14px;overflow-wrap:anywhere}
.row{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}
select,input,textarea{border:1px solid #6f8496;border-radius:5px;padding:9px;font:inherit;max-width:100%;width:100%;background:white}
label{display:block;margin:8px 0 4px;font-weight:650}.meta{font-size:13px;color:#4d6375;white-space:pre-wrap}
img{max-width:400px;width:100%;height:auto;display:block;border:1px solid #dbe0e7;margin:10px 0}
button{background:#152a3c;border:0;color:white;border-radius:5px;padding:12px 18px;font:inherit;cursor:pointer}
button:focus,select:focus,input:focus{outline:3px solid #a68d64}
.note{background:#dfe8ef;padding:12px}#error{color:#8b2319;font-weight:700}
</style></head><body><header><h1>Private inspection review worksheet</h1>
<div>Evidence review for internal use • NOT RELEASED • Offline / no server</div></header>
<main><p class="warning">This worksheet does not verify a professional license, authenticate the person in the browser,
establish observed conditions or approve a customer report. Open and inspect the original media separately.
Thumbnails are previews, not full-resolution source evidence. Every item, media record and system requires a
manual decision. The exported response must be signed by the registered key holder using the separate local CLI.</p>
<div id="intro" class="card"></div>
<div class="row"><div><label for="role">Reviewer role</label><select id="role"><option value="">Choose role</option>
<option value="qualified_inspector">Qualified inspector (claimed; unverified)</option>
<option value="independent_quality_reviewer">Independent quality reviewer (claimed; unverified)</option></select></div>
<div><label for="reviewer">Registered reviewer ID</label><input id="reviewer" autocomplete="off" placeholder="Exact registry identifier"></div></div>
<label for="summary">Reviewer notes / restrictions</label><textarea id="summary" rows="3" placeholder="Summarize open limitations and work needed"></textarea>
<section id="records"><h2>Inspection records</h2></section>
<section id="media"><h2>Source photos, frames and videos</h2></section>
<section id="systems"><h2>All 13 systems and coverage</h2></section>
<p class="note">Key possession and signed responses are checked by the CLI. This worksheet cannot change a report
to human_verified, remove Q03 holds or authorize release.</p>
<button id="export" type="button">Export unsigned reviewer responses</button><p id="error" role="alert"></p>
</main>
<script id="m4-data" type="application/json">__REVIEW_DATA__</script>
<script>
"use strict";
const input = JSON.parse(document.getElementById("m4-data").textContent);
const req = input.packet, thumbs=input.thumbnails;
const make=(tag,text)=>{const e=document.createElement(tag); if(text!==undefined)e.textContent=String(text);return e;};
const div=(cls)=>{const e=make("div");e.className=cls;return e;};
document.getElementById("intro").textContent="Project "+req.project_id+" • PDF SHA256 "+req.pdf_sha256+
" • Q03 held entries "+req.q03_held_entry_ids.length+" • report holds "+req.report_holds.length;
const choices={
 items:[["accepted_for_internal_review","Accept wording for internal review (not release)"],
 ["correction_required","Correction required"],["insufficient_evidence","Insufficient evidence"]],
 media:[["visually_reviewed","Personally reviewed source evidence"],
 ["not_reviewed","Not reviewed"],["inconclusive","Inconclusive"]],
 systems:[["confirmed_partial","Partial documentation confirmed (not full system approval)"],
 ["not_verified","Not verified"],["requires_field_inspection","Field inspection required"]]
};
const grids={};
for(const group of ["items","media","systems"]){
 grids[group]=[];
 for(const item of req[group]){
  const id=group==="systems"?item:group==="items"?item.section+" / "+item.id:item.id;
  const card=div("card");card.appendChild(make("strong",id));
  if(group==="items"){card.appendChild(make("p",item.system+" • "+item.summary));card.appendChild(make("p","Source IDs: "+item.evidence_ids.join(", ")));}
  if(group==="media"){
    card.appendChild(make("p",item.kind+" • "+item.area+" • "+item.path));
    card.appendChild(make("p","SHA256 "+item.sha256));
    if(item.derived_from_id)card.appendChild(make("p","Source video "+item.derived_from_id+" / time "+item.timestamp_seconds+"s"));
    if(thumbs[item.id]){const pic=make("img");pic.src=thumbs[item.id];pic.alt="Preview of source "+item.id+" (not a complete inspection)";card.appendChild(pic);}
  }
  const lab=make("label","Decision for "+id);const select=make("select");
  select.appendChild(new Option("Choose manually", ""));
  for(const [value,title] of choices[group])select.appendChild(new Option(title,value));
  lab.appendChild(select);card.appendChild(lab);
  const nl=make("label","Review note / unresolved work");const note=make("textarea");
  note.rows=2;note.maxLength=1600;note.placeholder="Explain a correction, inconclusive source, or field-inspection requirement";
  nl.appendChild(note);card.appendChild(nl);
  document.getElementById(group==="items"?"records":group).appendChild(card);
  grids[group].push({item,select,note});
 }
}
document.getElementById("export").addEventListener("click",()=>{
 const error=document.getElementById("error");error.textContent="";
 const reviewer=document.getElementById("reviewer").value.trim();
 const role=document.getElementById("role").value;
 if(!role || !/^[A-Za-z0-9][A-Za-z0-9_-]{2,63}$/.test(reviewer)){error.textContent="Select role and enter your registered reviewer ID.";return;}
 const result={request_digest:input.request_digest,role,reviewer_id:reviewer,
   note:document.getElementById("summary").value,items:[],media:[],systems:[]};
 for(const group of ["items","media","systems"]){
  for(const {item,select,note} of grids[group]){
   if(!select.value){error.textContent="Every record, media asset, and system must have a manual disposition.";return;}
   if(["correction_required","insufficient_evidence","inconclusive","requires_field_inspection"].includes(select.value)&&!note.value.trim()){
    error.textContent="Explain each correction, inconclusive record or required inspection.";return;
   }
   const fields=group==="systems"?{system:item}:group==="items"?{section:item.section,id:item.id}:{id:item.id};
   result[group].push({...fields,decision:select.value,note:note.value});
  }
 }
 const file=new Blob([JSON.stringify(result,null,2)+"\n"],{type:"application/json"});
 const url=URL.createObjectURL(file);const a=make("a");a.href=url;a.download="M4_"+role+"_UNSIGNED.json";
 document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(url);
 error.textContent="Unsigned file exported. Sign it separately; it does not authorize release.";
});
</script></body></html>"""


def build_review_worksheet(workspace: str | Path, *, thumbnail_limit: int = 100) -> dict:
    """Create a local restricted HTML worksheet with source-bound preview images."""
    if not 0 <= thumbnail_limit <= 100:
        raise DataError("Thumbnail limit must be 0 through 100")
    work, state, root, _ = _get_case(workspace)
    packet = _get_packet(work, state)
    thumbs = {}
    for m in packet["media"][:thumbnail_limit]:
        if m["kind"] != "photo":
            continue
        path = safe_path(root, m["path"])
        if sha256(path) != m["sha256"]:
            raise DataError("Reviewer thumbnail source evidence changed")
        try:
            with Image.open(path) as original:
                preview = ImageOps.exif_transpose(original).convert("RGB")
                preview.thumbnail((440, 300), Image.Resampling.LANCZOS)
                output = BytesIO()
                preview.save(output, format="JPEG", quality=75, optimize=True)
                if len(output.getvalue()) > 210_000:
                    raise DataError("Reviewer thumbnail exceeds safe size budget")
                thumbs[m["id"]] = "data:image/jpeg;base64," + base64.b64encode(output.getvalue()).decode("ascii")
        except (OSError, ValueError) as exc:
            raise DataError("Cannot decode reviewer evidence thumbnail") from exc
    if len([m for m in packet["media"] if m["kind"] == "photo"]) > thumbnail_limit:
        # An unpreviewed source is retained by ID; no implied visual review.
        pass
    data = json.dumps({"packet": packet, "request_digest": _digest(packet),
                       "thumbnails": thumbs}, ensure_ascii=True, separators=(",", ":"))
    data = data.replace("<", r"\u003c").replace(">", r"\u003e").replace("&", r"\u0026")
    html = HTML.replace("__REVIEW_DATA__", data)
    target = work / "human_review_worksheet_PRIVATE.html"
    if target.exists():
        if target.read_text(encoding="utf-8") != html:
            raise DataError("Existing human review HTML bound to different source or thumbnails")
        return {"status": "REUSED", "worksheet": str(target), "previewed_photos": len(thumbs),
                "customer_release_allowed": False}
    temp = work / ".m4_html_pending"
    try:
        fd = os.open(temp, os.O_WRONLY | os.O_EXCL | os.O_CREAT, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(html)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, target)
    finally:
        temp.unlink(missing_ok=True)
    return {"status": "CREATED", "worksheet": str(target),
            "previewed_photos": len(thumbs), "customer_release_allowed": False}
