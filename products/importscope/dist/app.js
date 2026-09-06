(function(){
 'use strict';const E=window.ImportScope,$=id=>document.getElementById(id),e=E.escape;
 let files={before:E.SAMPLE_BEFORE,after:E.SAMPLE_AFTER},names={before:'Example current catalog',after:'Example proposed update'},sample=true,result=null,filter='all',findingLimit=50,changeLimit=100,toastTimer;
 const versions={before:0,after:0};
 function toast(s){$('toast').textContent=s;$('toast').classList.add('visible');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').classList.remove('visible'),5000);}
 function fail(s){$('error').textContent=s;$('error').hidden=false;}
 function refresh(){
  $('error').hidden=true;$('before-name').textContent=names.before||'No file selected';$('after-name').textContent=names.after||'No file selected';$('sample-tag').hidden=!sample;
  result=null;if(!files.before||!files.after){$('results').hidden=true;$('empty').hidden=false;return;}
  try{result=E.compare(files.before,files.after,{threshold:Number($('threshold').value),locations:$('locations').value});$('results').hidden=false;$('empty').hidden=true;
   for(const [id,value]of Object.entries({'stat-high':result.stats.priority,'stat-changes':result.stats.changes,'stat-absent':result.stats.absent,'stat-products':result.stats.products}))$(id).textContent=value;
   $('count-all').textContent=result.findings.length;for(const severity of ['high','medium','info'])$('count-'+severity).textContent=result.findings.filter(x=>x.severity===severity).length;
   $('scope-coverage').textContent=result.stats.beforeRows.toLocaleString()+' current rows and '+result.stats.afterRows.toLocaleString()+' proposed rows reviewed. '+result.coverage.uncheckedColumns.length+' additional columns outside the supported checks.';
   findingLimit=50;changeLimit=100;renderFindings();renderChanges();
  }catch(err){$('results').hidden=true;$('empty').hidden=true;fail(err.message);}
 }
 function renderFindings(){if(!result)return;const list=result.findings.filter(x=>filter==='all'||x.severity===filter);$('findings-list').innerHTML=list.slice(0,findingLimit).map(x=>'<article class="finding"><span class="severity '+x.severity+'">'+({high:'PRIORITY',medium:'REVIEW',info:'INFO'}[x.severity])+'</span><div><h4>'+e(x.title)+'</h4><p>'+e(x.detail)+'</p>'+(x.oldValue!==null||x.newValue!==null?'<div class="diff"><span class="old">'+e(x.oldValue)+'</span><span aria-hidden="true">→</span><span class="new">'+e(x.newValue)+'</span></div>':'')+'<p class="location">'+e([x.handle,x.sku,x.line?x.side+' · line '+x.line:'File-level check'].filter(Boolean).join(' / '))+'</p></div></article>').join('')||'<p class="no-findings">No findings in this view. The report only covers the documented checks; it does not certify an import.</p>';$('more-findings').hidden=list.length<=findingLimit;}
 function renderChanges(){if(!result)return;const query=$('change-search').value.toLowerCase();const list=result.changes.filter(x=>[x.handle,x.sku,x.field,x.variant].some(v=>v.toLowerCase().includes(query)));$('changes-body').innerHTML=list.slice(0,changeLimit).map(x=>'<tr><td><strong>'+e(x.handle)+'</strong><small>'+e(x.variant)+(x.sku?' · '+e(x.sku):'')+'</small></td><td>'+e(x.field)+'</td><td>'+(x.before?e(x.before):'<span class="blank">(blank)</span>')+'</td><td>'+(x.after?e(x.after):'<span class="blank">(blank)</span>')+'</td></tr>').join('')||'<tr><td colspan="4">No matching field changes.</td></tr>';$('changes-count').textContent='Showing '+Math.min(list.length,changeLimit)+' of '+list.length+' matching changes. Full downloads include all findings and changes.';$('more-changes').hidden=list.length<=changeLimit;}
 function download(content,type,name){const blob=new Blob([content],{type}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),10000);}
 for(const side of ['before','after']){
  $('choose-'+side).addEventListener('click',()=>$(side+'-file').click());
  $(side+'-file').addEventListener('change',async event=>{
   const file=event.target.files[0];event.target.value='';if(!file)return;const version=++versions[side];
   if(sample){files={before:null,after:null};names={before:null,after:null};sample=false;}
   files[side]=null;names[side]=null;refresh();
   try{if(file.size>E.MAX_CHARS)throw new Error('Use a UTF-8 CSV no larger than 8 MB.');const bytes=await file.arrayBuffer();if(versions[side]!==version)return;let text;try{text=new TextDecoder('utf-8',{fatal:true}).decode(bytes);}catch{throw new Error('This file is not valid UTF-8. Export it again as UTF-8 CSV.');}E.parseCSV(text);files[side]=text;names[side]=file.name;refresh();toast(side==='before'?'Current catalog loaded.':'Proposed import loaded.');}catch(err){if(versions[side]!==version)return;refresh();fail((side==='before'?'Current catalog: ':'Proposed import: ')+err.message);}
  });
 }
 $('use-sample').addEventListener('click',()=>{if((files.before||files.after)&&!sample&&!confirm('Replace the loaded files with the example comparison?'))return;versions.before++;versions.after++;files={before:E.SAMPLE_BEFORE,after:E.SAMPLE_AFTER};names={before:'Example current catalog',after:'Example proposed update'};sample=true;refresh();toast('Example comparison loaded. No real store data.');});
 $('clear-files').addEventListener('click',()=>{versions.before++;versions.after++;files={before:null,after:null};names={before:null,after:null};sample=false;refresh();toast('Both files cleared from this page.');});
 $('threshold').addEventListener('change',refresh);$('locations').addEventListener('change',refresh);
 document.querySelectorAll('[data-filter]').forEach(button=>button.addEventListener('click',()=>{filter=button.dataset.filter;findingLimit=50;document.querySelectorAll('[data-filter]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));renderFindings();}));
 $('more-findings').addEventListener('click',()=>{findingLimit+=50;renderFindings();});$('more-changes').addEventListener('click',()=>{changeLimit+=100;renderChanges();});$('change-search').addEventListener('input',()=>{changeLimit=100;renderChanges();});
 $('export-csv').addEventListener('click',()=>{if(result){download(E.reviewCSV(result),'text/csv;charset=utf-8','importscope-findings.csv');toast('Findings downloaded. This is a review file, not a Shopify import file.');}});
 $('export-report').addEventListener('click',()=>{if(result){download(E.reportHTML(result,{...names,sample}),'text/html;charset=utf-8','importscope-review.html');toast('Full report downloaded. Open it in a browser to read or print.');}});
 refresh();
})();
