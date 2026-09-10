"""Select a contiguous line run from actual native operators, retaining native state.
This is measurement isolation only: no reconstructed style/coordinate drawing.
"""
import io
import fitz,numpy as np
from pypdf import PdfReader,PdfWriter
from pypdf.generic import ContentStream,NameObject

def require(ok,msg):
 if not ok:raise ValueError(msg)
def isolate_subsegment(actual_isolation,vertex_range,expected_vertices):
 reader=PdfReader(io.BytesIO(actual_isolation));i,j=vertex_range;selected=0;seen=set()
 def process(owner,resources,ispage=False):
  nonlocal selected
  ident=id(owner)
  if ident in seen:return
  seen.add(ident)
  stream=owner.get_contents() if ispage else owner
  cs=ContentStream(stream,reader);ops=list(cs.operations);path=[];replacements={};remove=set()
  for idx,(args,op)in enumerate(ops):
   if op==b'm':path=[idx]
   elif op==b'l':path.append(idx)
   elif op in [b'c',b'v',b'y',b're',b'h']:path.append(idx)
   elif op in [b'S',b's',b'f',b'F',b'f*',b'B',b'B*',b'b',b'b*',b'n']:
    if op!=b'n':
     require(op==b'S' and path and all(ops[k][1]in[b'm',b'l']for k in path),'subsegment requires one open native line stroke')
     require(0<=i<j<=len(path)and j-i>=2,'invalid native subsegment vertex range')
     require(all(ops[k][1]==b'l'for k in path[1:]),'multiple native subpaths unsupported')
     replacements[path[0]]=(ops[path[i]][0],b'm')
     remove.update(path[1:i+1]);remove.update(path[j:]);selected+=1
    path=[]
  cs.operations=[replacements.get(k,v)for k,v in enumerate(ops)if k not in remove]
  if ispage:owner[NameObject('/Contents')]=cs
  else:owner.set_data(cs.get_data())
  invoked=[args[0]for args,op in ops if op==b'Do']
  for name in dict.fromkeys(invoked):
   form=resources['/XObject'][name].get_object()
   if form.get('/Subtype')=='/Form':process(form,form.get('/Resources',resources))
 for page in reader.pages:process(page,page['/Resources'],True)
 require(selected==1,'native subsegment must select exactly one actual stroke')
 writer=PdfWriter();writer.append_pages_from_reader(reader);out=io.BytesIO();writer.write(out);data=out.getvalue()
 doc=fitz.open(stream=data,filetype='pdf');draws=doc[0].get_drawings();require(len(draws)==1,'isolated subsegment produced extra/missing geometry');d=draws[0];require(all(x[0]=='l'for x in d['items']),'isolated subsegment changed native type');actual=np.array([list(d['items'][0][1])]+[list(x[2])for x in d['items']]);expected=np.array(expected_vertices)
 require(actual.shape==expected.shape and np.max(abs(actual-expected))<.001,'actual operator subsegment differs from verified source-bound vertices')
 return data
