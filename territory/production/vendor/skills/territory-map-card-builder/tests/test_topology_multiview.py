"""Shared source identity and clipped per-view mask regressions."""
import sys
from pathlib import Path
import fitz,numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from validate_topology_patch import find_form,source_view_wrappers,view_region

def test_shared_form_views_keep_distinct_clips_and_transforms():
    source=fitz.open();p=source.new_page(width=100,height=100);p.draw_line((10,10),(90,90))
    raw=source.xref_stream(p.get_contents()[0])
    target=fitz.open();p=target.new_page(width=250,height=120)
    p.show_pdf_page(fitz.Rect(0,0,100,100),source,0)
    p.show_pdf_page(fitz.Rect(150,0,250,100),source,0,clip=fitz.Rect(10,10,60,60))
    target=fitz.open(stream=target.tobytes(),filetype='pdf')
    assert find_form(target,0,raw)>0
    wrappers=source_view_wrappers(target,0,raw)
    assert len(wrappers)==2
    assert wrappers[0]['BBox']!=wrappers[1]['BBox']
    assert wrappers[0]['Matrix']!=wrappers[1]['Matrix']

def test_mask_is_clipped_before_transform():
    view={'scale':2,'translate_x':20,'translate_y':0,'clip_source':[0,0,10,10]}
    result=view_region([[8,8,15,15]],view,(100,100),guard=0)
    assert result.any()
    assert not result[:,80:].any()
    assert not result[40:,:].any()
    assert not view_region([[20,20,25,25]],view,(100,100)).any()

if __name__=='__main__':
    test_shared_form_views_keep_distinct_clips_and_transforms();test_mask_is_clipped_before_transform()
    print('PASS shared Form identity, per-view wrappers and clipped masks')
