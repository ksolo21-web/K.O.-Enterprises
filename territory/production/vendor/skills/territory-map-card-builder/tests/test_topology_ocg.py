"""Renderer regression: imported OFF guide must stay hidden after reopen."""
import sys
from pathlib import Path
import fitz
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from validate_topology_patch import preserve_probe_optional_content

def test_imported_visibility_and_reopened_render():
    source=fitz.open();page=source.new_page(width=160,height=120)
    guide=source.add_ocg('Guide',on=False)
    page.draw_line((20,60),(140,60),color=(0,1,0),width=3)
    page.draw_rect((5,5,155,115),color=(0,0,0),width=1,oc=guide)
    source=fitz.open(stream=source.tobytes(),filetype='pdf')
    target=fitz.open();page=target.new_page(width=160,height=120)
    page.show_pdf_page(page.rect,source,0)
    broken=fitz.open(stream=target.tobytes(),filetype='pdf')
    preserve_probe_optional_content(source,target)
    correct=fitz.open(stream=target.tobytes(),filetype='pdf')
    for scale in (1,2,4):
        render=lambda doc:doc[0].get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False).samples
        assert render(source)==render(correct)
        assert render(source)!=render(broken)
    assert len(source[0].get_drawings())==len(correct[0].get_drawings())==1
    assert len(broken[0].get_drawings())==2

if __name__=='__main__':
    test_imported_visibility_and_reopened_render()
    print('PASS: source visibility and rendered pixels retained; exposed control differs')
