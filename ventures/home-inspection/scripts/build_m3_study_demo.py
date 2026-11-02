"""Private synthetic 3-page integration demo; no customer inputs or networking."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.utils import ImageReader

from inspection_engine.report_learning import import_reference
from inspection_engine.study_registry import empty_registry, register_bundle
from inspection_engine.report_review_queue import build_review_queue, _write_new
from inspection_engine.report_page_evidence import render_batch
from inspection_engine.report_ocr_review import ocr_review_batch
from inspection_engine.report_layout_navigation import build_layout_index
from inspection_engine.report_study_viewer import build_study_viewer


def prepare_demo(root: Path, *, with_ocr=True):
    root=Path(root)
    os.mkdir(root,0o700)
    source=root/'synthetic.pdf'
    c=Canvas(str(source),pagesize=(600,800),invariant=1)
    c.setFont('Helvetica-Bold',18)
    c.drawString(45,750,'SYNTHETIC STUDY - NOT A REAL INSPECTION')
    c.setFont('Helvetica',17)
    for y, values in zip((650,600,550,500),
            (('Item','State','Action'),('Roof','Unknown','Review'),
             ('Wall','Unknown','Review'),('Floor','Unknown','Review'))):
        for x, value in zip((50,230,410),values):c.drawString(x,y,value)
    c.drawString(45,80,'Boundary text at the end of source page one.')
    c.showPage()
    scan=Image.new('RGB',(1200,1600),'white')
    draw=ImageDraw.Draw(scan)
    font=ImageFont.truetype('DejaVuSans.ttf',38)
    for y, text in ((100,'SYNTHETIC SCANNED PAGE'),(240,'Original image evidence only.'),
                    (380,'No PDF text is available.'),(520,'Manual review is required.')):
        draw.text((75,y),text,font=font,fill='black')
    c.drawImage(ImageReader(scan),0,0,width=600,height=800)
    c.showPage()
    c.setFont('Helvetica',17)
    c.drawString(45,750,'Source page three starts a separate context.')
    c.drawString(45,710,'<script> synthetic markup </script>')
    for y, values in zip((610,560,510),
            (('Item','State','Action'),('Door','Unknown','Review'),('Window','Unknown','Review'))):
        for x, value in zip((50,230,410),values):c.drawString(x,y,value)
    c.showPage();c.save();source.chmod(0o600)
    bundle=import_reference(source,case_id='SYNTH-M3-V6',partition='locked_holdout',
        authorized_use=True,consented=True)
    registry=register_bundle(bundle,empty_registry())
    queue=build_review_queue(bundle,registry)
    batches=[]
    for i, pages in enumerate(([1,2],[3]),1):
        render_dir=root/f'render-{i}'
        manifest=render_batch(bundle,registry,source,render_dir,pages)
        ocr=ocr_review_batch(manifest,bundle,registry,source,render_dir,pages=pages) if with_ocr else None
        layout=build_layout_index(manifest,bundle,registry,source,render_dir,queue,ocr_record=ocr)
        batches.append({'manifest':manifest,'layout':layout,'render_dir':render_dir,
            **({'ocr_record':ocr} if with_ocr else {})})
        _write_new(root/f'layout-{i}.json',layout)
        if ocr:_write_new(root/f'ocr-{i}.json',ocr)
    for filename, obj in (('reference.json',bundle),('registry.json',registry),('text-queue.json',queue)):
        _write_new(root/filename,obj)
    return bundle,registry,queue,source,batches


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir',type=Path,required=True)
    a=parser.parse_args(argv)
    bundle,registry,queue,source,batches=prepare_demo(a.out_dir)
    receipt=build_study_viewer(bundle,registry,queue,source,batches=batches,out_dir=a.out_dir/'viewer')
    print(json.dumps({'synthetic_only':True,'rendered_pages':receipt['rendered_pages'],
        'missing_pages':receipt['unrendered_pages'],'training_approved':False,'customer_release_allowed':False}))
    return 0


if __name__=='__main__':raise SystemExit(main())
