"""Editorial, customer-format SIMULATION of a whole-house 1970s inspection.

13 real, externally credited reference images from unrelated buildings plus a
public-domain period-appropriate front facade photograph. All conditions are
HYPOTHETICAL and every section carries an explicit simulation notice.
Not a real inspection, no legal/professional approval and no customer release.
"""
from __future__ import annotations
import argparse, hashlib, io, json, os
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image, ImageOps
from pypdf import PdfReader
from scripts.run_1970s_real_photos import _fetch_real_photo

DATA=json.loads("{\"systems\":[[\"Site & drainage\",\"The lot, surface grading, paths and stormwater pathways affect how water approaches the house.\",[[\"Routine\",\"Walkways, access and vegetation\",\"The scenario includes a usable front approach and typical planted areas; their dimensions, trip conditions and tree clearance have not been measured.\",\"Document settling, low spots, encroaching roots and vegetation touching siding.\"],[\"Repair\",\"Runoff directed toward the house\",\"Deferred landscape upkeep creates a plausible concern for soil sloping toward a basement wall, short downspout extensions and ponding after rain.\",\"Verify slopes and actual discharge points; a drainage contractor may evaluate corrections after the cause is documented.\"],[\"Maintenance\",\"Driveway and exterior hardscape\",\"Aging paving may have hairline cracking and open joints without necessarily indicating foundation movement.\",\"Maintain joints and document any material displacement or trip points.\"]],\"Actual grading, precipitation conditions, drainage ownership and foundation moisture paths were not tested.\"],[\"Exterior envelope\",\"Cladding, trim, windows, doors, sealants and penetrations help separate indoor space from weather.\",[[\"Information\",\"Exterior materials\",\"The representative ranch form suggests a modest single-story exterior, but the fictional home's siding type and window age have not been established.\",\"Record cladding type, repair history, window model and dates.\"],[\"Repair\",\"Weathered trim and failed caulking\",\"On a poorly maintained 1970s house, peeling paint, split trim joints and separated sealant at openings are realistic sample concerns.\",\"Check underlying wood for softening; repair weather barriers and seal according to product guidance.\"],[\"Routine\",\"Window and door operation\",\"Doors and accessible windows should be assessed for fit, glazing damage, locks, weatherstripping and operation, not only for visible defects.\",\"Verify representative operation and emergency-egress dimensions where applicable.\"]],\"Lead-based paint may be present in pre-1978 housing; the report does not contain lead test results.\"],[\"Roof & drainage\",\"Roof coverings, flashing and rainwater controls are important for keeping the structure dry.\",[[\"Information\",\"Roof configuration and age\",\"The house is described as a 1970s home; that does not establish the roof replacement date, covering material or number of roof layers.\",\"Obtain permits, replacement records and roof covering details.\"],[\"Repair\",\"Worn roof covering and flashing\",\"A credible neglected-property scenario includes uneven shingle wear, vulnerable penetrations and loose metal details that warrant close evaluation.\",\"A qualified roofer may document scope, accessible deck condition and whether repair or replacement is appropriate.\"],[\"Maintenance\",\"Gutter and downspout upkeep\",\"Leaf accumulation and disconnected discharge extensions are ordinary maintenance issues that can become moisture problems.\",\"Clean and secure as needed after onsite verification; recheck flow after rain.\"]],\"No roof walk, attic leak tracing or water testing was performed. A separate street-drain photo is not proof of a house gutter defect.\"],[\"Attic & insulation\",\"An accessible attic provides a view of roof framing, ventilation, insulation and penetrations.\",[[\"Information\",\"Attic access\",\"An attic is described as accessible. Hatch size, safe walkway, headroom and visibility are still unknown.\",\"Document the access method and accessible areas at inspection.\"],[\"Maintenance\",\"Uneven insulation coverage\",\"A plausible period-house condition is compressed or uneven insulation around an access hatch or storage area.\",\"Confirm insulation type, approximate depth and coverage without disturbing suspect materials.\"],[\"Further review\",\"Ventilation and exhaust routing\",\"Bathroom fans or dryer ductwork terminating within an attic can contribute to moisture, but no route has been verified in this scenario.\",\"Trace penetrations and discharge points safely; evaluate moisture staining and airflow.\"]],\"No thermal-performance claims, asbestos identification, concealed wiring evaluation or roof sheathing moisture readings are provided.\"],[\"Foundation & basement walls\",\"Visible foundation surfaces, support conditions and signs of water entry help inform further evaluation.\",[[\"Information\",\"Foundation type\",\"The home has a basement. Block, poured concrete, stone or other construction cannot be identified without site views.\",\"Record wall materials, floor slab and visible supports.\"],[\"Repair\",\"Cracks and damp perimeter finish\",\"A poorly maintained basement might show patched cracks, mineral deposits and localized damp finishes, but severity requires inspection of width, displacement and active water.\",\"Map and photograph crack geometry, moisture, grading and any past repairs; consult a structural specialist when evidence indicates movement.\"],[\"Routine\",\"Accessible foundation areas\",\"Unfinished wall surfaces, where exposed, improve the opportunity to check condition without destructive openings.\",\"Record concealed areas and any obstructed perimeter.\"]],\"No structural adequacy determination, settlement measurement, waterproofing test or below-grade excavation was performed.\"],[\"Floor platform & subfloor\",\"Where the basement ceiling is open, portions of joists, subfloor and connections may be visible.\",[[\"Information\",\"Construction materials\",\"Framing species, joist dimensions, span and sheathing remain unknown; the basement description alone does not answer those questions.\",\"Record actual framing members, supports and modifications where safely visible.\"],[\"Further review\",\"Stains below wet rooms\",\"Staining below a bathroom or kitchen may represent historic wetting rather than an active leak.\",\"Compare with current fixture use and moisture readings; distinguish old discoloration from deteriorated wood.\"],[\"Maintenance\",\"Penetrations and alterations\",\"Older additions to utilities sometimes create rough penetrations or unsupported pipes near framing.\",\"Document enlarged openings, unusual notches and loose supports for qualified evaluation if material.\"]],\"No concealed subfloor, structural calculations or floor-load assessment is implied.\"],[\"Structural framing\",\"Visible beams, posts, joists, wall interfaces and modifications inform the structure overview.\",[[\"Information\",\"Single-story configuration\",\"The reported living area has three bedrooms, two baths and an attached garage; exact interior bearing-wall locations are not supplied.\",\"Obtain floor plans and record exposed support elements.\"],[\"Further review\",\"Altered or damaged supports\",\"A deteriorated-home scenario may include improvised supports, older repairs or localized wood deterioration in the basement.\",\"Photograph connections, bearing and deformation; request professional structural review where warranted.\"],[\"Routine\",\"Accessible framing condition\",\"Clean, dry, undisturbed framing would be a favorable condition worth reporting where actually verified.\",\"Record both normal material and adverse conditions, not only deficiencies.\"]],\"Finishes conceal most framing; no engineering certification is being represented.\"],[\"Interior finishes\",\"Walls, ceilings, floors, stairs and doors provide context for everyday living and visible maintenance needs.\",[[\"Information\",\"Room arrangement\",\"Three bedrooms and two full baths, with the second bath inside the primary bedroom, are part of the scenario.\",\"Verify room labels, door swings and accessible circulation.\"],[\"Repair\",\"Ceiling discoloration and damaged finishes\",\"A sample bedroom may have a stain at a ceiling joint and patched drywall from past water entry; no active leak is proved without testing.\",\"Identify the source and whether material is dry and sound before redecorating.\"],[\"Maintenance\",\"Flooring, doors and stairways\",\"Worn carpets, loose thresholds and sticky doors are common in deferred-maintenance houses and vary in impact.\",\"Record locations, operations and potential fall hazards; prioritize stair and handrail safety.\"]],\"No indoor-air assessment, concealed pest evaluation or verified flooring condition is claimed.\"],[\"Electrical\",\"The service, panel, distribution, outlets, lights and protective devices affect daily function and life safety.\",[[\"Information\",\"Electrical system inventory\",\"Service amperage, panel manufacturer, grounding and wiring methods have not been established by the house's construction decade.\",\"Record panel label, accessible equipment markings and applicable test results.\"],[\"Urgent example\",\"Exposed conductors and unsafe panel access\",\"The reference image illustrates exposed wiring near an enclosure. Comparable actual conditions would call for prompt qualified electrical attention.\",\"Avoid contact with suspect energized equipment; a licensed electrician can assess guarding and safe repairs.\"],[\"Further review\",\"Outlet and alarm coverage\",\"The scenario includes older bedrooms and bathrooms where outlet protection and smoke/CO alarm placement deserve detailed documentation.\",\"Test accessible devices within inspection scope; document locations and any limitations.\"]],\"No cover removal, energized probing or circuit capacity analysis was conducted.\"],[\"Supply & waste plumbing\",\"Fixtures, pipes, traps, vents and drainage should be documented for both function and condition.\",[[\"Information\",\"Two full bathrooms and kitchen\",\"The home has a primary en-suite full bath and one other full bath; actual fixture types and water source are unverified.\",\"Record visible fixture inventory, accessible shutoffs and drainage behavior.\"],[\"Repair\",\"Corroded supply pipe or waste connection\",\"The reference photograph illustrates a leak at a corroded pipe; for this scenario it is a realistic example, not a demonstrated house leak.\",\"Check pipe material, joint condition and active wetness; a qualified plumber may determine repair scope.\"],[\"Maintenance\",\"Bath caulking and moisture control\",\"Aged sealants, stained grout and poor ventilation can be present even when plumbing is not leaking.\",\"Assess wet-area finish integrity and fan discharge; maintain seals and resolve moisture sources.\"]],\"No water pressure, flow, drain, sewer lateral, potable-water quality or concealed leak testing was performed.\"],[\"Water heating\",\"Water heating equipment is a key component of daily comfort and potentially of combustion or water safety.\",[[\"Information\",\"Equipment identity\",\"Manufacturer, model, fuel type, capacity, installation year and service history are unknown.\",\"Photograph the rating plate and document relevant installation and maintenance information.\"],[\"Further review\",\"Corrosion and access\",\"An older or poorly maintained heater may show corrosion at fittings or restricted service clearance; the gallery photo is an unrelated example.\",\"Check visible joints, tank base, venting if applicable and discharge piping without manipulating safety devices.\"],[\"Maintenance\",\"Ownership records and upkeep\",\"Routine checks and manufacturer-specified service can help clarify remaining life and support decisions.\",\"Obtain installation invoice and manual; use a qualified service provider for safety-device concerns.\"]],\"Age cannot be inferred from the photo; no combustion or relief-valve functional test occurred.\"],[\"Heating, cooling & ventilation\",\"Condition, operation, filters, distribution and ventilation influence indoor comfort and energy use.\",[[\"Information\",\"Actual HVAC configuration\",\"The property may have forced air or another system, but type, number of units, cooling presence and capacity are unverified.\",\"Document each system's fuel, model, serial, access and operating modes.\"],[\"Maintenance\",\"Dirty filters or disconnected ducts\",\"A neglected home plausibly has restricted filters, loose duct insulation and leaking joints in visible utility spaces.\",\"Check accessible distribution and service history; qualified HVAC contractors may inspect combustion or refrigerant concerns.\"],[\"Further review\",\"Exhaust and ventilation\",\"Bathrooms, laundry and basement can require investigation of moisture and exhaust routing.\",\"Verify any visible bath and dryer exhaust termination and moisture history.\"]],\"No measured HVAC performance, carbon-monoxide screening or equipment safety certification is included.\"],[\"Garage & attached spaces\",\"The attached garage is a distinct area with vehicle access, storage, equipment and a separation from living space.\",[[\"Information\",\"Attached garage\",\"The house includes an attached garage; door dimensions, opener model and interior connection are not confirmed.\",\"Document door type, operator, safety sensors and separation details.\"],[\"Urgent example\",\"Door spring containment\",\"A real reference photograph shows an extension spring without an obvious safety cable; a comparable defect could create injury risk.\",\"A qualified door technician should assess spring containment and reversal; residents should not service tensioned parts.\"],[\"Further review\",\"Separation and stored materials\",\"Damage at the door between house and garage, unsealed openings and combustible storage can warrant attention.\",\"Record observable door condition, penetrations and applicable safety features.\"]],\"No opener-force test, stored-fuel inventory or fire-resistance certification was completed.\"]],\"rooms\":[[\"Exterior approach & entry\",\"Front steps, access path, entrance door, grade at the stoop and drainage are part of a complete exterior walkthrough.\",\"Favorable example: entry path remains accessible. Watch for cracked paving, damaged trim and water pooling at the threshold.\"],[\"Living / dining areas\",\"Record room layout, window function, visible electrical devices, finishes, heat distribution and floor condition.\",\"Favorable example: functional circulation space. Sample concerns: finish wear, loose transition strip and stained ceiling.\"],[\"Kitchen\",\"Include cabinetry, counters, sink drainage, water supply, accessible outlets, windows, exhaust and installed appliances in scope.\",\"Favorable example: operable storage and plumbing shutoffs. Sample concerns: cabinet damage, slow drain, missing protection and leak history.\"],[\"Primary bedroom\",\"Document doors, closet, wall and ceiling finishes, windows/egress, receptacles, floor finishes, heating and alarms.\",\"Favorable example: accessible window. Sample concerns: weatherstripping, ceiling discoloration and worn carpet.\"],[\"Primary full bath (en-suite)\",\"Record all visible fixtures, supply/drain points, caulking, ventilation, electrical protection, shower/tub finish and floor transitions.\",\"Favorable example: separate full bathroom for the primary bedroom. Sample concerns: humidity staining and tired sealant.\"],[\"Bedroom 2\",\"Document ceiling, walls, flooring, door, window, closet, visible outlets, HVAC supply/return and alarms.\",\"Favorable example: usable secondary room. Sample concerns: damaged outlet cover and patched wall surfaces.\"],[\"Bedroom 3\",\"Include independent documentation of windows, floor slope, closet, ceiling, trim, outlets and alarm coverage.\",\"Favorable example: third enclosed bedroom. Sample concerns: worn flooring and ceiling marks.\"],[\"Hall full bathroom\",\"Record sink, toilet, bath/shower, drainage behavior, ventilation, surfaces, grab/handhold features and electrical protection.\",\"Favorable example: second full bathroom. Sample concerns: grout deterioration and moisture-sensitive finishes.\"],[\"Basement & utility zone\",\"Include exposed foundation, floor slab, visible structure, stairs, drainage, electrical panel, laundry, furnace and water heater if present.\",\"Favorable example: service access and potential visibility of framing. Sample concerns: damp perimeter, basement-water history and equipment corrosion.\"],[\"Attached garage\",\"Document vehicle door, opener, sensors, door springs, interior connections, walls/ceilings and accessible penetrations.\",\"Favorable example: protected off-street parking. Sample concerns: spring containment and damaged house/garage interface.\"],[\"Accessible attic\",\"Record access safety, insulation, sheathing, exposed rafters, ventilation, wiring, penetration sealing and evidence of moisture.\",\"Favorable example: inspection access is described. Sample concerns: compressed insulation and uncertain bathroom-fan termination.\"]],\"photos\":[[\"Roof-covering example\",\"Curling and erosion visible in source photograph; not the sample home's roof.\",\"P01\"],[\"Foundation-material example\",\"Detached historic masonry in reference photo is not proof of a 1970s basement condition.\",\"P02\"],[\"Basement moisture example\",\"Standing water shown at another address; actual source and electrical safety require onsite assessment.\",\"P03\"],[\"Electrical example\",\"Open conductors visible near an electrical enclosure; no onsite circuit test.\",\"P04\"],[\"Plumbing example\",\"Corroded pipe and droplet visible in third-party source.\",\"P05\"],[\"Water heater example\",\"Weathered tank at an unrelated property; equipment age unverified.\",\"P06\"],[\"Primary bath moisture example\",\"Discoloration in bathroom reference; microbial species not diagnosed.\",\"P07\"],[\"Hall bath finish example\",\"Dark marks at a wet-area surface; not laboratory-confirmed mold.\",\"P08\"],[\"Garage spring example\",\"Source depicts extension spring; actual house hardware unknown.\",\"P09\"],[\"Interior ceiling example\",\"Staining in an unrelated room; no proved connection to roof example.\",\"P10\"],[\"Attic reference\",\"Insulation and visible attic construction; this photo alone does not establish a defect.\",\"P11\"],[\"Mechanical reference\",\"Dusty equipment, not identified as a functional HVAC system at this house.\",\"P13\"],[\"Site stormwater reference\",\"Curbside inlet, explicitly not a roof gutter or house defect.\",\"P14\"]]}")
W,H=letter; M=50; CW=W-2*M
NAVY="#162C3C"; DARK="#2A3540"; SLATE="#62717D"; FAINT="#DDE3E5"; TAN="#B79A73"; PALE="#F6F6F4"; RED="#994B3F"
for name,fp in (("Lato","/usr/share/fonts/truetype/lato/Lato-Regular.ttf"),("LatoBold","/usr/share/fonts/truetype/lato/Lato-Bold.ttf"),("LatoLight","/usr/share/fonts/truetype/lato/Lato-Light.ttf")):
    if Path(fp).exists(): pdfmetrics.registerFont(TTFont(name,fp))
REG="Lato" if "Lato" in pdfmetrics.getRegisteredFontNames() else "Helvetica"
BOLD="LatoBold" if "LatoBold" in pdfmetrics.getRegisteredFontNames() else "Helvetica-Bold"
LIGHT="LatoLight" if "LatoLight" in pdfmetrics.getRegisteredFontNames() else REG
def fill(c,col): c.setFillColor(col)
def text(c,x,y,t,size=10,font=None,col=DARK):
    fill(c,col);c.setFont(font or REG,size);c.drawString(x,y,str(t))
def line(c,x,y,xx,yy,color=FAINT,width=.65):
    c.setStrokeColor(color);c.setLineWidth(width);c.line(x,y,xx,yy)
def wrap(s,width,size=10,font=None):
    font=font or REG
    result=[]
    for para in str(s).split("\n"):
        acc=""
        for word in para.split():
            trial=(acc+" "+word).strip()
            if acc and pdfmetrics.stringWidth(trial,font,size)>width:
                result.append(acc);acc=word
            else:acc=trial
        if acc:result.append(acc)
    return result
def paragraph(c,x,y,s,width=CW,size=10,leading=15,color=DARK,font=None):
    for ln in wrap(s,width,size,font):
        text(c,x,y,ln,size,font,color);y-=leading
    return y
def photo(c,path,x,y,w,h):
    with Image.open(path) as im:
        im=ImageOps.exif_transpose(im).convert("RGB")
        pix=ImageOps.fit(im,(round(w*2.5),round(h*2.5)),Image.Resampling.LANCZOS,centering=(.5,.49))
        b=io.BytesIO();pix.save(b,format="JPEG",quality=87,optimize=True)
        c.drawImage(ImageReader(b.getvalue()),x,y,w,h)
def pageframe(c,topic,caption="",number=True):
    text(c,M,753,"K.O.  /  HOME INSPECTIONS",9,BOLD,NAVY)
    text(c,W-M-128,753,"PROPERTY REPORT   |   SAMPLE",8,REG,SLATE)
    line(c,M,736,W-M,736)
    line(c,M,54,W-M,54)
    text(c,M,38,"TRAINING SIMULATION  -  NOT A REAL PROPERTY INSPECTION",7.1,REG,SLATE)
    if number:
        text(c,W-M-21,38,f"{c.getPageNumber():02d}",8,BOLD,NAVY)
def header(c,kicker,title,deck=None):
    pageframe(c,kicker)
    text(c,M,702,kicker.upper(),9,BOLD,TAN)
    yy=661
    for s in wrap(title,CW,25,LIGHT):
        text(c,M,yy,s,25,LIGHT,NAVY);yy-=31
    if deck: yy=paragraph(c,M,yy-3,deck,CW,10.3,16,SLATE)-7
    return min(yy,594)
def check(y,label):
    if y<78: raise ValueError(f"Page overrun {label}: {y}")
def close(c):c.showPage()
def rulehead(c,y,s):
    line(c,M,y+7,W-M,y+7)
    text(c,M,y-11,s.upper(),9,BOLD,NAVY)
    return y-33
def cover(c,front):
    fill(c,"#FFFFFF");c.rect(0,0,W,H,stroke=0,fill=1)
    text(c,M,744,"K.O.  ENTERPRISES",11,BOLD,NAVY)
    text(c,W-M-130,744,"HOME INSPECTIONS",9,REG,SLATE)
    line(c,M,725,W-M,725,NAVY,.8)
    photo(c,front,M,273,CW,418)
    text(c,M,256,"FRONT ELEVATION REFERENCE  /  1974 RANCH PHOTOGRAPH - DIFFERENT PROPERTY",7.4,REG,SLATE)
    text(c,M,195,"A clearer picture",32,LIGHT,NAVY)
    text(c,M,159,"of the whole home.",32,LIGHT,NAVY)
    line(c,M,133,W-M,133,TAN,2)
    text(c,M,111,"Residential property review  |  Illustrative client-format edition",10,REG,DARK)
    text(c,M,87,"1,500 sq ft   ·   3 bedrooms   ·   2 full baths   ·   basement   ·   attached garage",9.4,REG,SLATE)
    text(c,M,49,"November 5, 2026  |  Scenario property constructed in the 1970s",8.7,REG,SLATE)
    text(c,M,26,"SAMPLE ONLY  -  NO HOME WAS INSPECTED AND PHOTOS ARE NOT FROM ONE PROPERTY",7.2,BOLD,RED)
    close(c)
def intro(c):
    y=header(c,"The report","A house is more than its repair list.","This sample is written in the tone and sequence intended for a homeowner, while distinguishing known scenario facts, illustrative observations and information that only a site visit can establish.")
    y=rulehead(c,y-20,"What is included")
    for title,s in [
        ("A complete property profile","Structure, living areas, all three bedrooms, both bathrooms, basement, attic, garage, mechanical systems and surrounding site."),
        ("Balanced condition narrative","Descriptions of useful features and expected upkeep alongside higher-priority examples; a finding is not automatically a defect."),
        ("Practical next steps","Plain-language reasons for follow-up, the appropriate professional discipline and missing documents or test results."),
    ]:
        text(c,M,y,title,13,BOLD,NAVY);y=paragraph(c,M,y-22,s,CW,10.4,16)-25
    y=rulehead(c,y,"Why the evidence labels matter")
    y=paragraph(c,M,y,"The cover shows a real 1974 ranch-house photograph, and the later gallery contains real photographs from thirteen unrelated locations. None portrays this fictional subject property. Condition narratives are explicitly hypothetical, and no inspector, vision model or independent reviewer verified the fictional house.",CW,10.5,16)
    check(y,"introduction");close(c)
def profile(c):
    y=header(c,"Property profile","The home at a glance","This is the starting inventory a customer should recognize before reading any defects.")
    pairs=[
        ("Reported living area","1,500 square feet"),("Era","Built in the 1970s (exact year unverified)"),
        ("Residence","Single-family home; floor levels not established"),("Bedrooms","3, including a primary bedroom"),
        ("Bathrooms","2 full bathrooms; one inside primary bedroom"),("Basement","Present; finished area and moisture history unknown"),
        ("Garage","Attached; door size and equipment unknown"),("Attic","Access described as available; conditions unverified"),
        ("Maintenance history","Scenario assumes significant deferred care"),("Address / parcel","Not supplied; fictional training property"),
        ("Utilities / fuel","Water, sewer, gas, electrical and HVAC types not confirmed"),("Inspection attendance","None - scenario exercise only"),
    ]
    for i,(k,v) in enumerate(pairs):
        yy=y-i*37
        if i%2==0: fill(c,PALE);c.rect(M,yy-27,CW,36,stroke=0,fill=1)
        text(c,M+9,yy-9,k,9.2,BOLD,NAVY)
        xx=M+190
        paragraph(c,xx,yy-9,v,CW-200,9.4,13,SLATE)
    y=y-len(pairs)*37-11
    y=paragraph(c,M,y,"Property information usually confirmed from listing documents, site observations, equipment labels, municipal permits, survey records and owner disclosures. A customer report should never silently fill unknown fields with guesses.",CW,9.5,14.5,SLATE)
    check(y,"profile");close(c)
def reading(c):
    y=header(c,"Reader's guide","How to use these pages","The goal is to understand the home, not to be overwhelmed by warning labels.")
    groups=[
      ("Urgent example","A potential injury, fire, electrical or other immediate hazard if actually present. Urgency is conditional until verified."),
      ("Repair","A condition that could require corrective work; cause, extent and cost depend on onsite examination."),
      ("Further review","More evidence or a specialist assessment is needed before characterizing performance or safety."),
      ("Maintenance","Reasonable upkeep or monitoring that helps protect the home over time."),
      ("Information / routine","Useful property facts or favorable features worth documenting; not every item needs a repair."),
    ]
    for title,body in groups:
        text(c,M,y,title,12,BOLD,NAVY)
        y=paragraph(c,M,y-19,body,CW-5,10,15)-31
    y=rulehead(c,y-3,"Evidence boundary")
    y=paragraph(c,M,y,"Every example condition in this edition is a scenario assumption. Reference images support only descriptions of what is visible in those original photographs. Real reports should identify inspected, not inspected, inaccessible and not applicable areas independently and retain source-to-finding traceability.",CW,10.3,15.7)
    check(y,"guide");close(c)
def summary(c):
    y=header(c,"Executive overview","The story of this house","A 1970s, 1,500-square-foot family home with a useful three-bedroom layout, two full bathrooms, basement space, attached garage and an accessible attic - alongside a plausible backlog of maintenance.")
    y=rulehead(c,y-15,"What the house offers")
    for x in ["Separate primary bathroom and second full bath","Basement and attic access for evaluating some concealed systems","Attached garage and clearly defined sleeping spaces"]:
        text(c,M,y,"—  "+x,10.6,REG,DARK);y-=30
    y=rulehead(c,y-5,"Most important hypothetical concerns")
    for title,body in [
        ("Safety and utility risks","Potentially exposed wiring, garage-door spring safeguards and any wet electrical areas would receive first attention if found on site."),
        ("Water and building fabric","Roof wear, drainage, basement moisture, plumbing leakage and stained ceilings require source identification rather than assumptions."),
        ("Deferred maintenance","Finishes, seals, insulation, ventilation and equipment upkeep may create a cumulative repair plan rather than a single large defect."),
    ]:
        text(c,M,y,title,11.5,BOLD,NAVY)
        y=paragraph(c,M,y-19,body,CW,10,15)-21
    y=paragraph(c,M,y,"A thoughtful report also records conditions that appear normal when actually observed. No favorable or deficient condition on these pages has been confirmed at this fictional address.",CW,9.4,14,SLATE)
    check(y,"summary");close(c)
def systems_page(c,index,info):
    name,overview,items,limit=info
    y=header(c,f"System {index:02d} of 13",name,overview)
    for j,(label,title,desc,response) in enumerate(items):
        y-=13
        line(c,M,y+5,W-M,y+5,FAINT)
        text(c,M,y-13,f"{index:02d}.{j+1:02d}",9,BOLD,TAN)
        text(c,M+48,y-13,title,12.1,BOLD,NAVY)
        text(c,W-M-91,y-13,label.upper(),7.7,BOLD,SLATE)
        y=paragraph(c,M+48,y-35,desc,CW-52,9.55,14.1)-7
        y=paragraph(c,M+48,y,"Follow-up: "+response,CW-52,9,13.4,SLATE)-17
    y=rulehead(c,y-3,"Not established in this simulation")
    y=paragraph(c,M,y,limit,CW,9.35,14.2,SLATE)
    check(y,f"system {index}");close(c)
def room_page(c,number,rooms):
    y=header(c,f"Rooms & spaces / {number}","Room-by-room view","An effective report documents every accessible space and separates favorable everyday features from work that may be needed.")
    for room,desc,assessment in rooms:
        y-=7
        line(c,M,y+5,W-M,y+5)
        text(c,M,y-14,room,13.2,BOLD,NAVY)
        y=paragraph(c,M,y-34,desc,CW,9.8,14.5)-7
        y=paragraph(c,M,y,assessment,CW,9.6,14.5,SLATE)-21
    check(y,f"room {number}");close(c)
def gallery_page(c,number,entries,paths):
    y=header(c,f"Photo references / {number}","Real photographs, clearly sourced","Images are from unrelated real properties. They are visual examples only and must never be treated as evidence about this scenario house.")
    for title,description,pid in entries:
        path=paths[pid]; y-=5
        with Image.open(path) as im:
            iw,ih=im.size
        h=164 if len(entries)>1 else 238
        photo(c,path,M,y-h,CW,h)
        y-=h+18
        text(c,M,y,title,12,BOLD,NAVY)
        y=paragraph(c,M,y-19,description,CW,9.25,13.7,SLATE)-7
        source="Wikimedia Commons  |  source photograph "+pid+"  |  source credits in photographic index"
        text(c,M,y,source,8,REG,SLATE)
        y-=33
    check(y,f"gallery {number}");close(c)
def plan(c):
    y=header(c,"Ownership planning","A sensible order for follow-up","The sequence below is illustrative and depends on what a qualified onsite inspection actually finds.")
    blocks=[
        ("First: protect occupants","Where an actual immediate shock, uncontrolled water, structural or garage-spring hazard is identified, restrict exposure and obtain appropriate qualified help."),
        ("Next: stop active deterioration","Check roof and surface drainage, moisture entry, plumbing leaks and any ongoing damage to building finishes or framing."),
        ("Then: restore reliable systems","Use equipment inventories and professional assessment to scope electrical, plumbing, heating, ventilation, garage and water-heating work."),
        ("Finally: plan upkeep and comfort","Address finish repairs, sealants, insulation, drainage maintenance, ventilation, manufacturer maintenance and long-range replacement."),
    ]
    for title,body in blocks:
        text(c,M,y,title,13,BOLD,NAVY)
        y=paragraph(c,M,y-22,body,CW,10.1,15.5)-37
    y=rulehead(c,y,"No unsupported price estimates")
    y=paragraph(c,M,y,"Costs, completion times and code obligations depend on local jurisdiction, actual material, access, contractor inspection and permits. This sample does not invent quotes or guarantee remaining useful life.",CW,9.6,14.5,SLATE)
    check(y,"plan");close(c)
def owner_info(c):
    y=header(c,"Property records","The information owners deserve","A completed real report should make it easy to understand and maintain the property after the inspection is over.")
    blocks=[
        ("Materials & construction","Foundation type, visible cladding, roof covering and approximate age, insulation characteristics, accessible framing and visible repairs."),
        ("Equipment register","Heating, cooling, water heating, electrical service and garage equipment: location, make/model/serial when legible, fuel type, capacity if recorded, and maintenance documents."),
        ("Operation & safety","Visible shutoffs, panel and disconnect locations, drainage behavior, accessible protective devices, moisture concerns and alarm observations within scope."),
        ("Room and site index","Bedroom and bathroom coverage, garage and attic access, exterior elevations, basement, kitchen and living areas, plus any inaccessible spaces."),
        ("Follow-up record","Priority, responsible professional discipline, uncertainty and the evidence needed to close each finding; no unconditional repair conclusion."),
    ]
    for title,body in blocks:
        text(c,M,y,title,12.6,BOLD,NAVY)
        y=paragraph(c,M,y-21,body,CW,10,15.1)-30
    check(y,"owner info");close(c)
def credits(c,front_url,source_json):
    y=header(c,"Photographic sources","Image credits & provenance","All photographic source credits are visible here for auditability; the photographs are not of the fictional subject property.")
    y=paragraph(c,M,y,f"Cover: 'SIMPLERANCH1.JPG' by Mcheath. Public domain. {front_url}",CW,8.7,12.8,SLATE)-24
    for row in source_json:
        title=f"{row['id']}  /  {row['photographer']}  /  {row['license']}"
        text(c,M,y,title,8.7,BOLD,NAVY)
        y=paragraph(c,M,y-14,row["upstream_source_page"],CW,7.8,10.5,SLATE)-10
        if y<115:
            close(c);y=header(c,"Photographic sources","Credits, continued")
    check(y,"credits")
    close(c)
def final(c):
    y=header(c,"Scope & conclusion","A report built for understanding","Good reporting should be readable, comprehensive and transparent about what it can and cannot prove.")
    for title,body in [
        ("What is genuinely known","Only the scenario constraints: a neglected 1970s home of approximately 1,500 square feet with three bedrooms, two full bathrooms (one en-suite), a basement, attached garage and described attic access."),
        ("What is demonstrated","The editorial presentation, a balanced inventory of 13 systems, realistic example observations, a room-by-room framework, practical homeowner guidance and 14 real, licensed/public-domain reference photographs."),
        ("What is NOT demonstrated","A single-home inspection, source-backed defect identification for this home, measured utilities, field testing, specialist responses by licensed humans, independent AI accuracy or signed professional approval."),
        ("What still blocks commercial release","Authentic onsite media with consent, inspector credentials and signoff, verified recognition accuracy, municipal/insurance review where needed, full report-generator integration and a professionally witnessed end-to-end pilot."),
    ]:
        text(c,M,y,title,12.7,BOLD,NAVY)
        y=paragraph(c,M,y-23,body,CW,10.2,15.8)-35
    check(y,"conclusion");close(c)
def build(root,out):
    root=Path(root);out=Path(out)
    mdir=root/"evidence"/"media";sources=json.loads((root/"photo_sources_and_findings.json").read_text())
    paths={r["id"]:mdir/(r["id"]+".jpg") for r in sources}
    assert len(sources)==13 and all(x.exists() for x in paths.values())
    cover_image=out.parent/"cover_front_1974_public_domain.jpg"
    raw=_fetch_real_photo("SIMPLERANCH1.JPG")
    with Image.open(io.BytesIO(raw)) as im:
        ImageOps.exif_transpose(im).convert("RGB").save(cover_image,"JPEG",quality=89,optimize=True)
    front_url="https://commons.wikimedia.org/wiki/File:SIMPLERANCH1.JPG"
    c=canvas.Canvas(str(out),pagesize=letter,pageCompression=1)
    c.setTitle("K.O. Home Inspections | Whole-Home Editorial Sample | 1970s Property")
    c.setAuthor("K.O. Enterprises | synthetic editorial test")
    cover(c,cover_image);intro(c);profile(c);reading(c);summary(c)
    for i,s in enumerate(DATA["systems"],1):systems_page(c,i,s)
    chunks=[DATA["rooms"][0:3],DATA["rooms"][3:6],DATA["rooms"][6:9],DATA["rooms"][9:]]
    for i,rs in enumerate(chunks,1):room_page(c,i,rs)
    # Pair images; protect against orphaned final image by dedicating one page.
    for i in range(0,len(DATA["photos"]),2):
        gallery_page(c,i//2+1,DATA["photos"][i:i+2],paths)
    plan(c);owner_info(c);credits(c,front_url,sources);final(c)
    c.save()
    pdf=PdfReader(str(out));n=len(pdf.pages)
    if n<31 or n>35: raise ValueError(f"Page count outside expected range: {n}")
    full="\n".join(p.extract_text() or "" for p in pdf.pages)
    for required in ["A clearer picture","The home at a glance","The story of this house","Primary full bath (en-suite)","Room-by-room view","Garage & attached spaces","Image credits & provenance","NOT A REAL PROPERTY INSPECTION"]:
        if required not in full:raise ValueError("Missing required content: "+required)
    report={"status":"CUSTOMER_FORMAT_SIMULATION_COMPLETE_NOT_APPROVED","pages":n,"photographs":len(sources)+1,"system_sections":len(DATA["systems"]),"room_spaces":len(DATA["rooms"]),"sample_conditions":sum(len(x[2]) for x in DATA["systems"]),"photo_source_links":len(sources)+1,"customer_release_allowed":False,"front_image_public_domain_url":front_url,"pdf_sha256":hashlib.sha256(out.read_bytes()).hexdigest()}
    (out.parent/"editorial_sample_verification.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report))
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--source-dir",required=True);p.add_argument("--out-pdf",required=True)
    a=p.parse_args();build(a.source_dir,a.out_pdf)
