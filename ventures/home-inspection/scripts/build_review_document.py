"""One-page, photo-led INTERNAL review sheet; expressly not a client report."""
from __future__ import annotations
from pathlib import Path
import json
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'output'/'m2_specialist_demo'
IN=ROOT/'output'/'m2_critic_demo'/'01_separate_technical_review.json'
OUT=ROOT/'output'/'m2_critic_demo'/'M2_Internal_Review_Synthetic.pdf'
NAVY=HexColor('#172a40'); PALE=HexColor('#f1f5f9'); MUTED=HexColor('#536474'); RULE=HexColor('#d7e0e8')


def image_cover(c:canvas.Canvas,filename:Path,x:float,y:float,w:float,h:float):
    # Fit within content image box, avoiding cropping or false attribution.
    with Image.open(filename) as im:
        a,b=im.size
    factor=min(w/a,h/b)
    W,H=a*factor,b*factor
    c.drawImage(ImageReader(str(filename)),x+(w-W)/2,y+(h-H)/2,W,H,mask='auto')


def main():
    review=json.loads(IN.read_text(encoding='utf8'))
    OUT.parent.mkdir(parents=True,exist_ok=True)
    c=canvas.Canvas(str(OUT),pagesize=(612,792))
    c.setFillColor(NAVY);c.rect(0,736,612,56,fill=1,stroke=0)
    c.setFillColor(HexColor('#ffffff'));c.setFont('Helvetica-Bold',10)
    c.drawString(42,767,'HOME INSPECTION INTELLIGENCE')
    c.setFont('Helvetica',8);c.drawRightString(568,767,'INTERNAL QUALITY RECORD  /  v0.7')
    c.setFillColor(NAVY);c.setFont('Helvetica-Bold',22)
    c.drawString(42,702,'Second-pass technical review')
    c.setFont('Helvetica',10);c.setFillColor(MUTED)
    c.drawString(42,682,'Synthetic demonstration  |  Not a customer inspection  |  Human approval required')
    c.setStrokeColor(RULE);c.line(42,670,570,670)
    c.setFillColor(PALE);c.roundRect(42,612,528,47,7,fill=1,stroke=0)
    c.setFillColor(NAVY);c.setFont('Helvetica-Bold',10)
    c.drawString(57,640,'REVIEW OUTCOME')
    c.setFont('Helvetica',10)
    c.drawString(57,625,'2 proposals: insufficient evidence  •  0 confirmed  •  Client release blocked')
    c.setFont('Helvetica-Bold',11);c.drawString(42,586,'Visual source comparison')
    image_cover(c,BASE/'house_synthetic.png',42,381,252,185)
    image_cover(c,BASE/'zoom_views'/'Z0001_P0001.png',312,381,258,185)
    c.setFillColor(MUTED);c.setFont('Helvetica',9)
    c.drawString(42,369,'ORIGINAL CONTEXT  /  P0001')
    c.drawString(312,369,'NATIVE SOURCE CROP  /  Z0001')
    c.setStrokeColor(RULE);c.line(42,352,570,352)
    c.setFillColor(NAVY);c.setFont('Helvetica-Bold',11)
    c.drawString(42,330,'Two evidence-linked findings remain unresolved')
    c.setFont('Helvetica-Bold',10);c.drawString(42,306,'01  Exterior wall finish — P0001 / zoom Z0001')
    c.setFont('Helvetica',9);c.setFillColor(MUTED)
    c.drawString(42,291,'Synthetic image cannot establish material identity or concealed structure.')
    c.drawString(42,277,'Required: inspector verification and closer material-detail photograph.')
    c.setStrokeColor(RULE);c.line(42,263,570,263)
    c.setFillColor(NAVY);c.setFont('Helvetica-Bold',10)
    c.drawString(42,241,'02  Exterior wall finish — video-derived still P0002')
    c.setFillColor(MUTED);c.setFont('Helvetica',9)
    c.drawString(42,226,'Selected native-resolution video photo has preserved source and timestamp.')
    c.drawString(42,212,'Required: independent onsite verification of the surface composition.')
    c.setFillColor(PALE);c.roundRect(42,102,528,89,8,stroke=0,fill=1)
    c.setFont('Helvetica-Bold',10);c.setFillColor(NAVY)
    c.drawString(57,173,'Release boundary')
    c.setFont('Helvetica',9);c.setFillColor(MUTED)
    c.drawString(57,156,'Q01 checked source custody and authority rules; Q02 was a scripted second pass.')
    c.drawString(57,142,'Neither constitutes an independent deployed AI model or professional diagnosis.')
    c.drawString(57,128,'Qualified inspector review, real-image benchmarking, and release controls remain open.')
    c.setStrokeColor(RULE);c.line(42,73,570,73)
    c.setFillColor(MUTED);c.setFont('Helvetica',8)
    c.drawString(42,57,'EVIDENCE FROM GENERATED TEST FIXTURES — NOT A FIELD INSPECTION')
    c.drawRightString(570,57,'01 / 01')
    c.save()
    print(str(OUT))
if __name__=='__main__':main()
