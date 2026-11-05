"""Real PHOTOGRAPHIC EXAMPLES, composite 1970s house M4 end-to-end rehearsal.

Images are existing freely reusable photographs from DIFFERENT actual places.
They are not documentation of the hypothetical property. Scripted specialist,
Q02 and Q03 providers demonstrate the deployed integration interfaces, not
independent trained model perception or qualified inspector approval.

Fail closed on unavailable image, missing license, corrupted source, missing
physical checks, missing systems, reviewer conflict, or release authorization.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import md5, sha256 as digest256
from io import BytesIO
import json
import os
from pathlib import Path
import re
import time
from urllib.request import Request, urlopen
from urllib.parse import quote

from PIL import Image, ImageOps
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
    Image as RLImage, Table, TableStyle, KeepTogether, PageBreak, HRFlowable
)
from reportlab.lib.utils import ImageReader
from pypdf import PdfReader

from inspection_engine.core import DataError, SYSTEMS, load_project, sha256
from inspection_engine.m4_pipeline import (
    prepare_case, run_specialists, run_q02, run_q03,
    render_private_case, status_case,
)
from inspection_engine.m4_workflow import preflight_case
from inspection_engine.m4_pdf_audit import audit_private_pdf
from scripts.run_1970s_house_dry_run import _q03_script

TITLE = "1500-SQ-FT 1970s HOUSE | REAL-PHOTO COMPOSITE CASE STUDY"
CASE_ID = "COMPOSITE-1970S-1500SF-REAL-PHOTOS-V2"
DATE = "2026-11-04"
UNVERIFIED_SPACES = [
    "Bedroom 2: no source photo; outlets, flooring, windows and alarms not verified",
    "Bedroom 3: no source photo; ceiling, closets, flooring and alarms not verified",
    "Primary bedroom: no source photo establishing full-room condition",
    "Primary en-suite: reference image only; no plumbing operation or moisture readings",
    "Hall full bath: reference image only; drain, waterproofing and ventilation untested",
    "Basement: example water image only; actual foundations, floor system, stairs and utilities not measured",
    "Attic: example insulation image only; no actual safe-entry, moisture, ventilation, framing or electrical inspection",
    "Attached garage: example spring only; no door reversal/force tests, garage separation or fire safety checks",
    "Kitchen/laundry: no sink, drain, supply, appliances or laundry vent physical tests",
    "All mechanical equipment: no rating plates, combustion/venting, operating test or age confirmation",
    "Actual exterior wall finish, exposed framing and subfloor: no verified case-specific photo; remain open",
    "All life safety: smoke/CO alarms, egress openings, GFCI/AFCI and handrails untested",
]
# id, area, zone, Wikimedia file title, photographer, license,
# simulated severity, visual example, professional-style recommendation
PHOTOS = [
("P01","roof","Roof covering","Failure of asphalt shingles allowing roof leakage.JPG","Dale Mahalko / DMahalko","CC BY-SA 3.0","MAJOR","Aged asphalt shingles show severe surface loss, curling and separated layers, with dark substrate visible.","Prompt roof-covering specialist review and documented repair/replacement scope. Check decking and evidence of water entry from safe access; do not walk a compromised roof."),
("P02","foundation","Foundation perimeter","4. Footer Stabilization, Water Infiltration, South Wall. (65e1916b-38b4-47dc-9753-2447c4867d9b).JPG","US National Park Service","Public domain US federal","MAJOR","Photograph documents damaged, detached foundation masonry beside an excavated perimeter.","Refer this example to a structural specialist; determine source of movement, capacity, drainage and repairs. Historic masonry in source is not evidence of this imagined 1970s home's foundation type."),
("P03","crawlspace","Basement floor","Basement Flooded in Uncle's Home.jpg","OakleyOriginals","CC BY 2.0","URGENT SAFETY","Standing water is visible in the photographed basement.","Treat potentially energized wet areas as hazardous; no entry until electrical safety is assessed. Arrange qualified water-intrusion assessment and drying plan; confirm the source before repair."),
("P04","electrical","Electrical panel vicinity","Exposed Wall Wiring and Breaker Box.jpg","Paul The Writer","CC0 1.0","URGENT SAFETY","A wall-mounted electrical installation has exposed conductors adjacent to a distribution enclosure.","Have a licensed electrician assess guarding, enclosures and energized parts promptly. Do not touch or dismantle components; photo does not prove voltage, bonding or circuit safety."),
("P05","plumbing","Utility piping","Leak in rusted pipe side view.jpg","Shamrock Lee","CC BY 4.0","MAJOR","A corroded pipe bend is shown with a visible leaking droplet.","Request a qualified plumber to determine whether the pipe is actively leaking in the actual property and repair the damaged run. Evaluate collateral wetting and corrosion."),
("P06","water_heating","Water-heater area","Hoarders House - Rusty Water Heater (15991797965).jpg","darkday","CC BY 2.0","FURTHER EVALUATION","Photograph illustrates a neglected, weathered water-heater installation.","Have a licensed plumbing/mechanical contractor identify the tank, test safety devices and evaluate corrosion, venting, relief discharge, leaks and replacement need. Manufacturing date and safety cannot be read from this image."),
("P07","plumbing","Primary en-suite full bath","Bathroom-mold.jpg","Milliped","CC BY-SA 3.0","MAJOR","Dark surface growth and discolored finish areas appear in a bathroom setting.","Investigate and correct moisture source; request a qualified moisture/remediation assessment where appropriate. Never identify microbial species or concealed damage from photo alone."),
("P08","plumbing","Hall full bath","Black Indoor Mold.jpg","Couch-scratching-cats","Public domain","FURTHER EVALUATION","Dark discolored surface patches are apparent in a bathroom example.","Verify bath ventilation, plumbing seals and substrate moisture; clean or remediate under an appropriate assessment. Do not assume the marks are laboratory-confirmed mold."),
("P09","garage","Attached garage door hardware","Garage door spring needs a safety cable through it.jpg","Tomwsulcer","CC0 1.0","URGENT SAFETY","An extension-type garage-door spring is shown without an obvious containment/safety cable.","Do not operate or adjust the door until a qualified garage-door technician checks spring containment, cables, safety reversal and hardware. Tensioned springs are hazardous."),
("P10","interior","Bedroom ceiling example","Ceiling water damage.jpg","Atomicdragon136","CC BY 3.0","MAJOR","Ceiling finish shows localized staining/discoloration consistent with prior wetting.","Identify and remedy water source; verify ceiling material stability, moisture readings and any concealed deterioration before cosmetic repairs. No active leak established from this still."),
("P11","attic","Accessible attic reference","AtticInsulation.jpg","Jason Dale","CC BY-SA 3.0","FURTHER EVALUATION","Insulation, ducts and roof-space materials are visible in an attic example.","A qualified onsite inspector must safely assess insulation depth/coverage, ventilation paths, roof sheathing, exhaust routing, wiring and moisture. No deficiency is conclusively established here."),
("P13","hvac","Cooling equipment reference","Hoarders House - Abandoned Cooling (15804516978).jpg","darkday","CC BY 2.0","FURTHER EVALUATION","Photograph records neglected cooling-related equipment; serviceability is not demonstrated.","An HVAC professional should identify equipment and inspect electrical connections, refrigerant-side condition, drainage, ventilation and safe operation. Do not assign age or performance without labels and test data."),
("P14","site","Exterior runoff and gutter drainage","Ida clogged gutter Essex 01.jpg","Destroyeraa","CC BY-SA 4.0","MAJOR","The reference photograph shows a residential roof gutter visibly obstructed by debris after heavy weather.","Arrange safe qualified clearing of blocked gutters and verify drainage, downspout discharge, foundations, and related moisture damage. This is not a measurement of actual grade or a claim about the fictional roof."),
]
SEVERITY_ORDER = {"URGENT SAFETY":0,"MAJOR":1,"FURTHER EVALUATION":2}
ALLOWED_LICENCES = {"CC BY-SA 3.0","CC BY-SA 4.0","Public domain US federal","CC BY 2.0",
                    "CC BY 4.0","Public domain","CC0 1.0","CC BY 3.0"}


def _image_url(filename: str) -> str:
    normalized = filename.replace(" ","_")
    h = md5(normalized.encode("utf-8")).hexdigest()
    return f"https://upload.wikimedia.org/wikipedia/commons/{h[0]}/{h[:2]}/{quote(normalized,safe='()')}"


def _fetch_real_photo(filename: str) -> bytes:
    # Wikimedia original byte URLs (avoid unversioned third-party stocks).
    # Retry transient 429/503; no fabricated or generated fallback.
    primary = _image_url(filename)
    normal = filename.replace(" ","_")
    h = md5(normal.encode("utf-8")).hexdigest()
    thumbnail = f"https://upload.wikimedia.org/wikipedia/commons/thumb/{h[0]}/{h[:2]}/{quote(normal,safe='()')}/960px-{quote(normal,safe='()')}"
    alternate = "https://commons.wikimedia.org/wiki/Special:Redirect/file/" + quote(normal,safe="()") + "?width=960"
    last = None
    for attempt, url in enumerate((thumbnail,alternate,primary)):
        try:
            req=Request(url,headers={"User-Agent":"K-O-Enterprises-ResearchDemo/0.1 (educational, noncommercial; GitHub Actions; attribution)", "Accept":"image/jpeg,image/png,image/*"})
            with urlopen(req,timeout=35) as response:
                raw=response.read(26_000_001)
            if not 10_000<len(raw)<26_000_000:
                raise ValueError("Source image empty/oversized")
            with Image.open(BytesIO(raw)) as im:
                im.verify()
            return raw
        except Exception as exc:
            last=exc
            time.sleep(1+attempt)
    raise DataError(f"Real, licensed source photograph unavailable; blocking case: {filename}: {str(last)[:160]}")


def _no_repo_dir(out:Path):
    out=out.expanduser().absolute()
    if out.exists() or not out.parent.is_dir():
        raise DataError("Output must be new and parent already present")
    for p in (out,*out.parents):
        if p.is_symlink() or (p/".git").exists():
            raise DataError("Public repo cannot contain real-photo dry-run outputs")
    return out


def _make_source(out: Path):
    src=out/"evidence"
    src.mkdir(parents=True)
    images=src/"media"
    images.mkdir()
    media=[]
    for index,(ident,area,zone,title,author,license_,severity,observation,recommendation) in enumerate(PHOTOS):
        if index:
            time.sleep(2.5)  # Respect upstream image-request limits; one active run only.
        if license_ not in ALLOWED_LICENCES:
            raise DataError("Unapproved image license: "+ident)
        raw=_fetch_real_photo(title)
        original_hash=digest256(raw).hexdigest()
        with Image.open(BytesIO(raw)) as im:
            im=ImageOps.exif_transpose(im).convert("RGB")
            if min(im.size)<250:raise DataError("Low resolution photograph: "+ident)
            im.thumbnail((1440,1300),Image.Resampling.LANCZOS)
            p=images/(ident+".jpg")
            # EXIF not forwarded. Original hash and Commons URL remain in manifest.
            im.save(p,"JPEG",quality=85,optimize=True,subsampling=0)
        url="https://commons.wikimedia.org/wiki/File:"+quote(title.replace(" ","_"),safe="()")
        media.append({
            "id":ident,"kind":"photo","path":"media/"+ident+".jpg","area":area,
            "room_label":zone,"sha256":sha256(p),
            "upstream_original_sha256":original_hash,"upstream_source_page":url,
            "photographer":author,"license":license_,
            "photo_origin":"REAL THIRD-PARTY PHOTO FROM ANOTHER PROPERTY",
            "caption":f"{ident}: {zone}. Real reference photo by {author}; {license_}; NOT the fictional inspected house.",
            "scaled_and_exif_removed":True,
        })
    doc={
        "project_id":CASE_ID,
        "property":{
            "label":"Fictional neglected 1970s residential 1500 sq ft / three bedrooms / two full baths / primary en-suite / basement / attached garage / accessible attic",
            "inspection_date":DATE,"synthetic":True,
            "building_type":"residential","inspection_scope":"residential",
            "reported_living_area_sqft":1500,"bedrooms":3,"full_bathrooms":2,
            "ensuite_full_bathroom_in_primary_bedroom":True,
            "has_basement":True,"attached_garage":True,
            "attic_accessible_by_description":True,"year_built":"1970s, exact unknown",
            "maintenance_history":"poor (scenario premise)",
            "qualified_reviewer":None,
            "inspector":"NO INSPECTOR: computer replay with genuine external reference photographs"},
        "media":media,"observations":[],"findings":[],
        "equipment":[
          {"id":"E01","system":"hvac","brand":"UNKNOWN","model":"NOT VERIFIED","serial":"NOT VERIFIED","evidence_ids":["P13"]},
          {"id":"E02","system":"water_heating","brand":"UNKNOWN","model":"NOT VERIFIED","serial":"NOT VERIFIED","evidence_ids":["P06"]},
        ],
        "limitations":[
            {"id":f"L{n:02}","system":system,"description":detail,"evidence_ids":[]}
            for n,(system,detail) in enumerate([
                ("site","No real property grading, downspouts or runoff observation"),
                ("foundation","No verified real foundation type, dimensions, crack measurements or movement history"),
                ("subfloor","No actual floor-platform or subfloor source photo, so this system remains OPEN"),
                ("framing","No physical framing capacity or movement measurements"),
                ("exterior","No actual property's cladding, flashing or lead coating test"),
                ("roof","No onsite roof-access or leak test"),
                ("attic","No onsite safe-access attic, electrical, insulation or ventilation test"),
                ("interior","No room-by-room site photos verifying all three bedrooms, hall and kitchen"),
                ("electrical","No voltage, circuit, outlet, grounding or GFCI/AFCI tests"),
                ("plumbing","No fixtures/water pressure/leak testing on actual property"),
                ("water_heating","No rating plate, relief valve, venting, combustion or fuel verification"),
                ("hvac","No operation test, filter check, condensate or equipment plate verified"),
                ("crawlspace","No onsite basement wetness, radon or structural testing"),
            ],1)],
    }
    f=src/"composite_project.json"
    f.write_text(json.dumps(doc,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    return f,doc


def _writer(image,prompt,calls):
    match=re.search(r"evidence ID (P\d{2});",prompt)
    if not match:raise DataError("Missing actual bound source photo in specialist prompt")
    ident=match.group(1)
    row=next(x for x in PHOTOS if x[0]==ident)
    sys={"basement":"crawlspace","garage":"interior"}.get(row[1],row[1])
    if sys not in dict(SYSTEMS):
        raise DataError("Unexpected building system assignment")
    calls["writer"].append(ident)
    # Actual narrative is human-authored from the photo's source description,
    # not generated by a visual model; never assert real property identity.
    description=row[7]
    if len(description)>320:raise DataError("Proposal exceeds M4 bounded length")
    return {"candidates":[{"type":"potential_concern","system":sys,
                           "description":description,"location":row[2][:95],
                           "status":"partially_observed","bbox":[.08,.08,.93,.90]}],
            "requests":[]}


def _q02(image,prompt,calls):
    calls["q02"]+=1
    # Source-context checks are cross-examined within the real pipeline;
    # independent human accreditation is still absent.
    decision="visually_plausible" if "UNTRUSTED HYPOTHESIS" in prompt else "insufficient_evidence"
    return {
        "decision":decision,
        "reason":"The reference photo can support a localized visible description, NOT a defect in the fictional house." if decision=="visually_plausible" else "Coverage requires authenticated onsite evidence; borrowed photos cannot prove house condition.",
        "missing_evidence":"Consent-bound photographs of the actual property, qualified onsite verification and physical safety tests." if decision=="insufficient_evidence" else "",
    }


def _escape(s:str):
    from xml.sax.saxutils import escape
    return escape(str(s))


def _styles():
    style=getSampleStyleSheet()
    style.add(ParagraphStyle(name="KO_Title",fontName="Helvetica-Bold",fontSize=24,leading=29,textColor=colors.HexColor("#142B40"),spaceAfter=14))
    style.add(ParagraphStyle(name="KO_Head",fontName="Helvetica-Bold",fontSize=15,leading=19,textColor=colors.HexColor("#163C5C"),spaceBefore=8,spaceAfter=7))
    style.add(ParagraphStyle(name="KO_Sub",fontName="Helvetica-Bold",fontSize=10,leading=14,textColor=colors.HexColor("#173D5B"),spaceBefore=6,spaceAfter=3))
    style.add(ParagraphStyle(name="KO_Body",fontName="Helvetica",fontSize=9.1,leading=13.2,spaceAfter=5))
    style.add(ParagraphStyle(name="KO_Tiny",fontName="Helvetica",fontSize=7.8,leading=10.5,spaceAfter=3,textColor=colors.HexColor("#526475")))
    style.add(ParagraphStyle(name="KO_Red",fontName="Helvetica-Bold",fontSize=10,leading=14,textColor=colors.HexColor("#952C28"),spaceAfter=8))
    return style


def _report(out:Path, rows:list[dict], stage:Path, qa:dict, core_pdf:Path):
    styles=_styles()
    target=out/"1970s_composite_REAL_PHOTO_DETAILED_DRY_RUN.pdf"
    def footer(canvas,document):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#CED6DD"))
        canvas.line(47,44,565,44)
        canvas.setFont("Helvetica",7.5)
        canvas.setFillColor(colors.HexColor("#53697D"))
        canvas.drawString(48,31,"COMPOSITE TRAINING CASE - NOT AN ACTUAL INSPECTION OR CLIENT REPORT")
        canvas.drawRightString(564,31,f"{document.page}")
        canvas.restoreState()
    def build_doc():
        doc=BaseDocTemplate(str(target),pagesize=letter,leftMargin=48,rightMargin=48,topMargin=54,bottomMargin=58,
                            title="K.O. Home Inspections | REAL-PHOTO COMPOSITE training report",
                            author="K.O. Home Inspections simulation",subject="Not for customer release")
        frame=Frame(doc.leftMargin,doc.bottomMargin,doc.width,doc.height,id="normal",showBoundary=0)
        doc.addPageTemplates(PageTemplate(id="pages",frames=frame,onPage=footer))
        return doc
    body=[]
    P=lambda s,sty="KO_Body":Paragraph(_escape(s),styles[sty])
    body += [Spacer(1,.65*inch),P("K.O. HOME INSPECTIONS","KO_Sub"),
             P("FULL INSPECTION DRY RUN","KO_Title"),
             P("Real photographs. Evidence-based responses. A fictional 1970s home.","KO_Head"),
             P("NOT A REAL PROPERTY INSPECTION - NO CUSTOMER RELEASE","KO_Red"),
             P("Property premise: 1,500 sq ft; built in the 1970s; 3 bedrooms; 2 full bathrooms (one en-suite in primary bedroom); basement; attached garage; accessible attic; deferred maintenance."),
             P("This is a COMPOSITE: the photographs below are from numerous unrelated genuine places, credited individually. They are not photographs from the fictional home. Findings are training responses to the visible example images. No trained model, licensed inspector or separate human Q02/Q03 professional adjudicator performed an examination."),
             P(f"Internal source-bound pipeline: {', '.join(qa['stages'])}. Q03 status: {qa['q03_status']}; open adjudication holds: {qa['q03_held']}; private PDF pages: {qa['m4_pages']}."),
             P("RELEASE DECISION: BLOCKED. Severity is a triage priority for the training photo, not a diagnosis of the described fictional residence.","KO_Red"),
             Spacer(1,.15*inch),
             P("Priority overview","KO_Head")]
    for sev in ("URGENT SAFETY","MAJOR","FURTHER EVALUATION"):
        bucket=[x for x in rows if x["severity"]==sev]
        body.append(P(f"{sev}: {len(bucket)} photo-based example reviews","KO_Sub"))
        for r in bucket:
            body.append(P(f"{r['id']} | {r['zone']}: {r['observation']}"))
    body.append(PageBreak())
    body += [P("Complete room and system coverage","KO_Title"),
             P("A photo of an example roof does not prove the fictional home's roof condition. Room-by-room site photographs and inspections are required even where these examples depict deterioration."),
             P("All 13 system scopes remain UNVERIFIED for the fictional property. Selected example photographs illustrate diagnostic workflow only.","KO_Red"),
             P("Property areas without authentic case-specific evidence","KO_Head")]
    for line in UNVERIFIED_SPACES:
        body.append(P("OPEN | "+line))
    body.append(PageBreak())
    body += [P("Photo-backed training findings","KO_Title"),
             P("Each record includes the exact public source, licensed author, visible condition, scoped recommendation and two levels of simulated review. Source photos are real; case association is fictional.","KO_Body")]
    for r in rows:
        body.append(PageBreak())
        body.append(P(f"{r['id']} | {r['zone']}","KO_Head"))
        body.append(P(f"TRIAGE: {r['severity']} - REAL REFERENCE PHOTO, NOT CASE EVIDENCE","KO_Red"))
        img=Image.open(r["photo_path"])
        iw,ih=img.size
        targetw=6.8*inch
        targeth=3.3*inch
        scale=min(targetw/iw,targeth/ih)
        body.append(RLImage(r["photo_path"],width=iw*scale,height=ih*scale))
        body += [
            Spacer(1,8),
            P("Visible photo observation","KO_Sub"),P(r["observation"]),
            P("What it means / risk","KO_Sub"),P(r["risk"]),
            P("Recommended professional response","KO_Sub"),P(r["recommendation"]),
            P("Q02 technical challenge - simulated","KO_Sub"),
            P("Image is compatible with this visual description, but neither cause, code compliance, full system function nor condition of the fictional home is proven."),
            P("Q03 reconciliation - simulated","KO_Sub"),
            P("Keep this localized entry distinct. Preserve source link, independent verification and full system coverage holds; no human sign-off or customer release."),
            P("Photo source and reuse terms","KO_Sub"),
            P(f"{r['author']} | {r['license']} | Wikimedia Commons. Resized and EXIF metadata removed; original-photo SHA256 {r['original_sha'][:22]}...","KO_Tiny"),
            P(r["commons_url"],"KO_Tiny"),
        ]
    body.append(PageBreak())
    body += [P("Inspector follow-up / disposition","KO_Title"),
             P("This case is not cleared for occupancy decisions, cost estimates or repair orders on a specific address. Its purpose is to demonstrate how a professional would prioritize verified concerns after collecting real-property evidence."),
             P("Urgent safety escalation","KO_Head"),
             P("If analogous hazards were actually present: keep people away from suspected energized wet areas, damaged structural rooms and high-tension garage-door equipment; engage appropriate licensed contractors or emergency services as conditions require. Do not ask occupants to remove breaker covers, handle springs or access unsafe attic/roof structures."),
             P("Priority 1 - further onsite verification","KO_Head"),
             P("Inspect roof covering, flashing, attic roof deck, moisture pathways, basement foundation, standing water, electrical installation, plumbing leaks and garage door; document date/time, location, measuring instrument, result and licensed expert when needed."),
             P("Priority 2 - complete the omitted spaces","KO_Head")]
    for s in UNVERIFIED_SPACES:body.append(P("MISSING EVIDENCE: "+s))
    body += [P("Data integrity and release decision","KO_Head"),
             P(f"{len(rows)} separate, licensed real reference photo sources, with image SHA256 values and upstream file URLs, were processed. The existing M4 workflow used {qa['jobs']} routing jobs and saved hashed stage receipts and an internal {qa['m4_pages']}-page Option 2 report. It retained {qa['q03_held']} adjudication holds and {qa['report_holds']} report holds. This supplemental report is also a PRIVATE TRAINING DOCUMENT."),
             P("No legitimate inspector credentials, jurisdiction approval, 100-real-case benchmark, legally consented source media for this fictional home, insured professional signoff or independent visual model precision measurements exist. No customer release.","KO_Red")]
    build_doc().build(body)
    pages=len(PdfReader(str(target)).pages)
    if pages<len(rows)+3:raise DataError("Supplemental detailed report unexpectedly truncated")
    return target,pages


def run(out:Path):
    out=_no_repo_dir(Path(out))
    out.mkdir(mode=0o700)
    project, doc=_make_source(out)
    pf=preflight_case(project)
    if not pf["ready_for_specialist_execution"] or len(pf["specialist_plan"]["jobs"])!=len(PHOTOS):
        raise DataError("Actual M4 photo source preflight did not route all real photographs")
    if len(pf["coverage"])!=13 or any(row["status"]=="observed" for row in pf["coverage"]):
        raise DataError("Photographic composite incorrectly passed physical system coverage")
    work=out/"m4_private_case"
    try:
        render_private_case(work)
    except (DataError,OSError):
        pass
    else:raise DataError("Attempted report with no Q01/Q02/Q03 should fail")

    started=prepare_case(project,work)
    if started["jobs"]!=len(PHOTOS):raise DataError("Case source intake work-order mismatch")
    counts={"writer":[],"q02":0}
    run_specialists(work,lambda im,prompt:_writer(im,prompt,counts),provider_id="COMPOSITE-SCRIPTED-SPECIALISTS-NOT-AI")
    if sorted(counts["writer"])!=sorted(m["id"] for m in doc["media"]):
        raise DataError("Not every real photograph was actually used by a specialist work order")
    run_q02(work,lambda im,prompt:_q02(im,prompt,counts),provider_id="COMPOSITE-SCRIPTED-Q02-NOT-INDEPENDENT")
    q03count={"q03":0}
    run_q03(work,lambda prompt,schema:_q03_script(prompt,schema,q03count),provider_id="COMPOSITE-SCRIPTED-Q03-NOT-INDEPENDENT")
    rendered=render_private_case(work)
    status=status_case(work)
    if status["completed"]!=["specialists","q02","q03","report"] or status["customer_release_allowed"] or status["human_approved"]:
        raise DataError("Incomplete stages or inappropriate release status")
    m4audit=audit_private_pdf(work)
    audit_json=json.loads(Path(m4audit["audit_json"]).read_text())
    adjud=json.loads((work/"adjudication.json").read_text())
    rreceipt=json.loads((work/"report_receipt.json").read_text())
    if adjud["status"]!="ADJUDICATION_HOLD" or not adjud["held_entry_ids"] or not rreceipt["report_holds"]:
        raise DataError("Borrowed reference photos unexpectedly cleared the M4 release gates")
    if set(audit_json["source_media_ids"])!={m["id"] for m in doc["media"]}:
        raise DataError("Final M4 PDF source register dropped reference images")
    if not audit_json["every_page_rasterized"]:
        raise DataError("Source PDF pages were not rasterized")
    if q03count["q03"]!=1 or counts["q02"]<len(PHOTOS):
        raise DataError("Distinct technical reviewer/adjudicator was skipped")

    records=[]
    for row in PHOTOS:
        ident,area,zone,title,author,license_,severity,observation,recommendation=row
        media=next(m for m in doc["media"] if m["id"]==ident)
        risk={
            "URGENT SAFETY":"Potential injury or serious property damage if an equivalent condition is confirmed on site. Do not touch, access or operate the affected assembly until safe.",
            "MAJOR":"Potential water damage, functional loss or costly deterioration. Requires qualified inspection to establish extent and appropriate scope.",
            "FURTHER EVALUATION":"Observed reference details do not establish safe operation or required features of the actual system. Additional source views and physical tests are needed.",
        }[severity]
        records.append({
            "id":ident,"system":area,"zone":zone,"severity":severity,
            "observation":observation,"risk":risk,"recommendation":recommendation,
            "photo_path":str(out/"evidence"/media["path"]),
            "original_sha":media["upstream_original_sha256"],
            "normalized_sha":media["sha256"],
            "commons_url":media["upstream_source_page"],
            "author":author,"license":license_,
            "real_photo":True,
            "belongs_to_fictional_house":False,
            "human_professional_verified":False,
        })
    m4pdf=next((work/"option2_draft").glob("*.pdf"))
    qa={"stages":status["completed"],"q03_status":adjud["status"],
        "q03_held":len(adjud["held_entry_ids"]),"report_holds":len(rreceipt["report_holds"]),
        "m4_pages":audit_json["total_pages"],"jobs":started["jobs"]}
    supplemental,secondpages=_report(out,records,work,qa,m4pdf)
    if sha256(m4pdf)!=rreceipt["draft_pdf_sha256"] or not supplemental.read_bytes().startswith(b"%PDF"):
        raise DataError("Final report hashes missing or invalid")
    report={
        "status":"REAL_PHOTO_COMPOSITE_E2E_EXECUTED_RELEASE_BLOCKED",
        "scenario":TITLE,"project_id":CASE_ID,
        "photo_sources_from_different_real_properties":True,
        "photographs_downloaded":len(PHOTOS),"photographs_all_real_licensed":True,
        "source_image_ids":[x["id"] for x in records],
        "source_original_sha256":[x["original_sha"] for x in records],
        "specialist_work_orders":started["jobs"],"Q02_scripted_calls":counts["q02"],
        "Q03_scripted_calls":q03count["q03"],"Q03_status":adjud["status"],
        "Q03_holds":len(adjud["held_entry_ids"]),"report_holds":len(rreceipt["report_holds"]),
        "pipeline_completed":status["completed"],
        "m4_private_PDF_pages":audit_json["total_pages"],
        "photo_case_study_PDF_pages":secondpages,
        "case_study_PDF_sha256":sha256(supplemental),
        "m4_PDF_sha256":sha256(m4pdf),
        "original_house_photographs":False,"AI_vision_model_inference_performed":False,
        "independent_Q02_Q03_human_review_performed":False,
        "qualified_inspector_signed":False,"human_verified_systems":0,
        "bedrooms":3,"full_bathrooms":2,"primary_ensuite":True,
        "basement":True,"garage_attached":True,"attic_accessible_per_scenario":True,
        "property_size_sqft":1500,"construction_period":"1970s",
        "property_media_consent_obtained":False,"customer_release_allowed":False,
        "missing_real_case_coverage":UNVERIFIED_SPACES,
    }
    (out/"photo_composite_dryrun_summary.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    (out/"photo_sources_and_findings.json").write_text(json.dumps([{k:v for k,v in x.items() if k!="photo_path"} for x in records],indent=2,sort_keys=True)+"\n")
    return report


def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument("--out-dir",type=Path,required=True)
    opts=ap.parse_args(argv)
    try:
        result=run(opts.out_dir)
    except Exception as exc:
        print(json.dumps({"status":"REAL_PHOTO_COMPOSITE_DRY_RUN_BLOCKED","reason":str(exc),"customer_release_allowed":False}))
        return 2
    print(json.dumps(result,sort_keys=True,indent=2))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
