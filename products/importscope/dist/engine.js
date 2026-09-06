(function(root){
 'use strict';
 const MAX_ROWS=10000,MAX_CHARS=8*1024*1024;
 const ALIASES={handle:['Handle','URL handle'],title:['Title'],body:['Body (HTML)','Description'],vendor:['Vendor'],type:['Type'],tags:['Tags'],status:['Status'],published:['Published','Published on online store'],sku:['Variant SKU','SKU'],barcode:['Variant Barcode','Barcode'],price:['Variant Price','Price'],compare:['Variant Compare At Price','Compare-at price'],inventory:['Variant Inventory Qty','Inventory quantity'],option1name:['Option1 Name','Option1 name'],option1:['Option1 Value','Option1 value'],option2name:['Option2 Name','Option2 name'],option2:['Option2 Value','Option2 value'],option3name:['Option3 Name','Option3 name'],option3:['Option3 Value','Option3 value'],image:['Image Src','Product image URL'],variantImage:['Variant Image','Variant image URL']};
 const LABELS={handle:'Handle',title:'Title',body:'Description',vendor:'Vendor',type:'Type',tags:'Tags',status:'Status',published:'Published',sku:'SKU',barcode:'Barcode',price:'Price',compare:'Compare-at price',inventory:'Inventory quantity',option1name:'Option 1 name',option2name:'Option 2 name',option3name:'Option 3 name',variantImage:'Variant image URL'};
 const normalize=s=>s.trim().toLowerCase();
 const MAP=new Map();for(const[k,aliases]of Object.entries(ALIASES))for(const a of aliases)MAP.set(normalize(a),k);
 const escape=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 function parseCSV(text){
  if(typeof text!=='string'||text.length>MAX_CHARS)throw new Error('Use a UTF-8 CSV no larger than 8 MB.');
  text=text.replace(/^\uFEFF/,'');if(text.includes('\0'))throw new Error('The file contains null bytes. Export it as UTF-8 comma-separated CSV.');
  const rows=[],rowLines=[];let row=[],cell='',quoted=false,closed=false,line=1,start=1;
  const push=()=>{row.push(cell);cell='';if(row.some(x=>x!=='')){rows.push(row);rowLines.push(start);}row=[];closed=false;if(rows.length>MAX_ROWS+1)throw new Error('Use at most 10,000 data rows per file.');};
  for(let i=0;i<text.length;i++){
   const c=text[i];
   if(quoted){if(c==='"'){if(text[i+1]==='"'){cell+='"';i++;}else{quoted=false;closed=true;}}else{cell+=c;if(c==='\n')line++;else if(c==='\r'&&text[i+1]!=='\n')line++;}continue;}
   if(closed&&c!==','&&c!=='\r'&&c!=='\n')throw new Error('Unexpected text after a quoted field at line '+line+'.');
   if(c==='"'){if(cell!=='')throw new Error('Unexpected quote at line '+line+'.');quoted=true;continue;}
   if(c===','){row.push(cell);cell='';closed=false;continue;}
   if(c==='\n'||c==='\r'){push();if(c==='\r'&&text[i+1]==='\n')i++;line++;start=line;continue;}
   cell+=c;
  }
  if(quoted)throw new Error('Unclosed quoted field beginning at or after line '+start+'.');
  if(cell!==''||row.length||closed)push();
  if(rows.length<2)throw new Error('The CSV needs a header and at least one product row.');
  const headers=rows.shift(),headerLine=rowLines.shift();
  if(headers.length<2)throw new Error('Expected comma-separated product CSV columns, not a tab- or semicolon-separated file.');
  const seen=new Set(),columns={};const unknown=[];
  headers.forEach((h,i)=>{const norm=normalize(h);if(!norm)throw new Error('Column '+(i+1)+' has no header.');if(seen.has(norm))throw new Error('Duplicate header: '+h);seen.add(norm);const k=MAP.get(norm);if(k){if(k in columns)throw new Error('Two headers map to '+LABELS[k]+'. Keep only one.');columns[k]=i;}else unknown.push(h);});
  if(!('handle'in columns)||!('title'in columns))throw new Error('For a reliable comparison, both files must include Handle (or URL handle) and Title.');
  const records=rows.map((cells,i)=>{if(cells.length!==headers.length)throw new Error('Line '+rowLines[i]+' has '+cells.length+' fields; expected '+headers.length+'.');const values={};for(const[k,j]of Object.entries(columns))values[k]=cells[j];return {values,line:rowLines[i],cells};});
  return {headers,columns,unknown,records,headerLine};
 }
 function number(s){if(typeof s!=='string'||!/^\d+(?:\.\d{1,6})?$/.test(s.trim()))return null;const n=Number(s);return Number.isFinite(n)&&n<=1e9?n:null;}
 function key(v){return JSON.stringify([v.handle,v.option1??'',v.option2??'',v.option3??'']);}
 function variantName(v){return [v.option1,v.option2,v.option3].filter(Boolean).join(' / ')||'Default / unspecified';}
 function compare(beforeText,afterText,options={}){
  const before=parseCSV(beforeText),after=parseCSV(afterText),threshold=Number(options.threshold??20),locations=options.locations??'unknown';
  if(!Number.isFinite(threshold)||threshold<1||threshold>100)throw new Error('Price-drop threshold must be 1–100%.');
  if(!['unknown','single','multiple'].includes(locations))throw new Error('Invalid inventory location setting.');
  const findings=[],changes=[];let counter=0;
  function add(severity,code,title,detail,record,side='proposed',oldValue,newValue){findings.push({id:++counter,severity,code,title,detail,handle:record?.values.handle??'',sku:record?.values.sku??'',line:record?.line??null,side,oldValue:oldValue??null,newValue:newValue??null});}
  function index(file,side){
   const products=new Map(),variants=new Map(),ambiguous=new Set(),skuKeys=new Map();let previous='';
   for(const r of file.records){const v=r.values;const handle=v.handle;
    if(!handle){add('high','missing_handle','A row has no handle','Rows without a handle cannot be matched. Specify the intended product.',r,side);continue;}
    if(/\s/.test(handle))add('high','handle_whitespace','Handle contains whitespace','Review the handle; Shopify product handles cannot contain spaces.',r,side);
    let product=products.get(handle);
    if(!product){product={first:r,rows:[],variants:[],images:new Set()};products.set(handle,product);}else if(previous!==handle)add('medium','split_handle','Product rows are separated','Keep each product’s variant and image rows together. A spreadsheet sort may have split this product.',r,side);
    previous=handle;product.rows.push(r);if(v.image)product.images.add(v.image);
    const variantData=['option1','option2','option3','sku','price','barcode','inventory'].some(k=>(v[k]??'')!=='');
    const imageOnly=product.rows.length>1&&v.image&&!variantData;
    if(imageOnly)continue;
    const k=key(v);r.key=k;product.variants.push(r);
    if(variants.has(k)){ambiguous.add(k);add('high','duplicate_variant','Variant identity is duplicated','The same handle and option combination appears more than once. Comparisons for this identity are suppressed until the duplicate is resolved.',r,side);}else variants.set(k,r);
    if(v.sku){const list=skuKeys.get(v.sku)||[];list.push(r);skuKeys.set(v.sku,list);}
    if('price'in file.columns&&v.price!==''&&number(v.price)===null)add('high','invalid_price','Price is not a supported number','Use a non-negative decimal without a currency symbol or thousands separator. Up to six decimal places are checked.',r,side);
    if(v.inventory!==undefined&&v.inventory!==''&&!/^-?\d+$/.test(v.inventory.trim()))add('high','invalid_inventory','Inventory quantity is not an integer','Review this inventory value before import.',r,side);
   }
   for(const list of skuKeys.values())if(list.length>1)add('medium','duplicate_sku','SKU is reused','This SKU belongs to '+list.length+' rows. Shopify may allow duplicate SKUs, but fulfillment and matching can be ambiguous.',list[0],side);
   for(const product of products.values())if(!product.first.values.title.trim())add('high','blank_title','Product title is blank','The first product row needs the intended title. Later variant rows may leave it blank.',product.first,side);
   return {products,variants,ambiguous,skuKeys};
  }
  const b=index(before,'current'),a=index(after,'proposed');
  const variantColumns=['sku','barcode','price','compare','inventory','variantImage'];
  if(variantColumns.some(k=>k in after.columns)&&(!('option1'in after.columns)||!('option1name'in after.columns)))add('high','missing_variant_options','Variant columns have no complete Option1 headers','Shopify documents variant replacement risk when related variant columns are supplied without Option1 name and value. Add both headers and verify the values.');
  if('inventory'in after.columns&&locations!=='single')add('medium','inventory_locations','Inventory scope needs confirmation',locations==='multiple'?'Product CSV inventory quantity applies to single-location stores. Use Shopify’s separate inventory workflow for multiple locations.':'Confirm whether this store has one inventory location. Product CSV quantities are not a multi-location stock audit.');
  let absent=0,newVariants=0,newProducts=0,matchedVariants=0;
  function diff(old,r,field,productField=false){
   if(!(field in after.columns)||!old||!(field in before.columns))return;
   const left=old.values[field]??'',right=r.values[field]??'';
   if(left===right)return;
   changes.push({handle:r.values.handle,sku:r.values.sku??'',variant:productField?'Product':variantName(r.values),field:LABELS[field]||field,before:left,after:right,line:r.line});
   if(field==='price'){
    const oldPrice=number(left),newPrice=right===''?0:number(right);
    if(right==='')add('high','blank_price','A supplied price is blank','Shopify documents a zero-price default for an empty price. Confirm the intended amount.',r,'proposed',left,'(blank → 0)');
    else if(newPrice===0&&oldPrice>0)add('high','zero_price','Price changes to zero','Confirm that this variant is intended to be free.',r,'proposed',left,right);
    else if(oldPrice>0&&newPrice!==null){const drop=100*(oldPrice-newPrice)/oldPrice;if(drop>=threshold)add('high','price_drop','Price drops '+drop.toFixed(1)+'%','This exceeds your '+threshold+'% review threshold. Check for a misplaced decimal or unintended markdown.',r,'proposed',left,right);}
   }else if(right===''&&left!=='')add(field==='compare'?'medium':'high','blanked_field',LABELS[field]+' becomes blank','This column is present in the proposed file with an empty value. Review the intended overwrite.',r,'proposed',left,'(blank)');
   else if(field==='status'&&left==='active'&&right!=='active')add('high','status_change','An active product changes status','Review its intended availability after import.',r,'proposed',left,right);
   else if(field==='published'&&left.toLowerCase()==='true'&&right.toLowerCase()==='false')add('high','unpublish','A product is marked unpublished','Review whether this product should leave the online store sales channel.',r,'proposed',left,right);
   else if(field.startsWith('option'))add('high','option_name_change','An option name changes','Option changes can affect variant identity. Verify third-party dependencies and test this product separately.',r,'proposed',left,right);
  }
  const productFields=['title','body','vendor','type','tags','status','published'];
  for(const[handle,ap]of a.products){const bp=b.products.get(handle);const r=ap.first;
   if(!bp){newProducts++;add('info','new_product','New product handle','This handle is absent from the current export. Confirm that it is new, rather than an accidental handle change.',r);}
   else for(const field of productFields)diff(bp.first,r,field,true);
   const status=r.values.status;
   if('status'in after.columns&&!['active','draft','archived'].includes(status))add('high','invalid_status','Product status needs correction','Use active, draft or archived on the first product row.',r);
   const published=r.values.published;
   if(published!==undefined&&published!==''&&!['true','false'].includes(published.toLowerCase()))add('high','invalid_published','Published value is not true or false','Review the online-store publication field.',r);
   for(const nr of ap.variants){
    const v=nr.values,k=nr.key,old=b.variants.get(k);
    if(a.ambiguous.has(k)||b.ambiguous.has(k))continue;
    if(!old){newVariants++;if(bp)add('medium','new_variant','New option combination','This combination is absent from the current export. A changed option can create a new variant identity.',nr);
     const sameSku=(b.skuKeys.get(v.sku)||[]).filter(x=>x.values.handle===handle&&x.key!==k);
     if(sameSku.length)add('high','sku_option_change','Existing SKU has a different option combination','The SKU appears under another option combination in the current export. Check whether this is an intentional variant replacement.',nr);
     if('price'in after.columns&&(v.price===''||number(v.price)===0))add('high','new_zero_price','New variant has an empty or zero price','Confirm the intended price before adding this variant.',nr);
    }else{matchedVariants++;for(const f of [...variantColumns,'option1name','option2name','option3name'])diff(old,nr,f);}
    if('price'in after.columns&&'compare'in after.columns&&v.compare!==''){const price=number(v.price),comp=number(v.compare);if(comp===null)add('high','invalid_compare','Compare-at price is not a supported number','Use a non-negative decimal value.',nr);else if(price!==null&&comp<=price)add('medium','compare_not_higher','Compare-at price is not above the selling price','Review whether a sale comparison is intended.',nr);}
   }
   if(bp){for(const old of bp.variants){if(!a.variants.has(old.key)){absent++;add('medium','absent_variant','Existing variant is absent from this product’s update','The current export contains '+variantName(old.values)+'. Its absence is not proof of deletion; review the intended variant structure and import behavior.',old,'current');}}
    if('image'in after.columns){const left=[...bp.images],right=[...ap.images];if(JSON.stringify(left)!==JSON.stringify(right))add('medium','image_list_change','Product image list changes','Image URLs or their sequence differ. Availability and Shopify’s merge behavior are not verified.',r);}
   }
  }
  const missingBaseline=Object.keys(after.columns).filter(k=>!(k in before.columns)&&!['image'].includes(k));
  if(missingBaseline.length)add('medium','missing_baseline_columns','Some proposed fields have no baseline','The current export omits: '+missingBaseline.map(x=>LABELS[x]||x).join(', ')+'. Those fields cannot be compared.');
  if(after.unknown.length)add('info','unchecked_columns','Additional columns are outside this review',after.unknown.length+' columns are preserved in your original file but not checked, including: '+after.unknown.slice(0,8).join(', ')+(after.unknown.length>8?'…':''));
  findings.sort((x,y)=>({high:0,medium:1,info:2}[x.severity]-{high:0,medium:1,info:2}[y.severity])||x.id-y.id);
  return {schemaVersion:1,generatedAt:new Date().toISOString(),settings:{threshold,locations,overwriteMatchingHandles:true},stats:{priority:findings.filter(x=>x.severity==='high').length,changes:changes.length,absent,newVariants,newProducts,matchedVariants,products:a.products.size,beforeRows:before.records.length,afterRows:after.records.length},findings,changes,coverage:{checkedFields:Object.keys(after.columns).filter(x=>x!=='handle').map(x=>LABELS[x]||x),uncheckedColumns:after.unknown},limitations:['Assumes overwrite of matching product handles.','This is a file comparison, not a Shopify import approval.','Missing variants do not prove deletion.','Metafields, apps, image availability, market pricing and store rules are not verified.','Only included products and supported supplied columns are compared.']};
 }
 function csvCell(x){let s=String(x??'');if(/^[\s]*[=+\-@]/.test(s)||/^[\t\r\n]/.test(s))s="'"+s;return '"'+s.replace(/"/g,'""')+'"';}
 function reviewCSV(result){const rows=[['Severity','Code','Handle','SKU','Source file','CSV line','Finding','Detail','Before','Proposed'],...result.findings.map(x=>[x.severity,x.code,x.handle,x.sku,x.side,x.line,x.title,x.detail,x.oldValue,x.newValue])];return '\uFEFF'+rows.map(r=>r.map(csvCell).join(',')).join('\r\n')+'\r\n';}
 function reportHTML(result,names={}){
  const e=escape;return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'"><title>ImportScope catalog review</title><style>body{font:16px/1.5 system-ui,sans-serif;color:#162238;max-width:1100px;margin:40px auto;padding:0 24px}h1{letter-spacing:-.04em}.meta{color:#566780}table{border-collapse:collapse;width:100%;font-size:14px;table-layout:fixed}th,td{padding:12px;border:1px solid #d9e0ec;text-align:left;vertical-align:top;overflow-wrap:anywhere;white-space:pre-wrap}th{background:#edf2fa}.finding{border-left:4px solid #becde7;padding:10px 18px;margin:20px 0;break-inside:avoid}.high{border-color:#ce690e}.medium{border-color:#c6a449}.tag{font-size:12px;font-weight:700;text-transform:uppercase}.finding h3{margin:5px 0}.finding p{margin:5px 0}.notice{background:#f0f4fa;padding:20px}h2{margin-top:35px}@media print{@page{margin:15mm}body{margin:0;padding:0;font-size:10pt}table{font-size:9pt}thead{display:table-header-group}h2,h3{break-after:avoid}}</style><h1>ImportScope / Catalog change review</h1><p class="meta">Generated '+e(result.generatedAt)+'<br>Current: '+e(names.before||'Current export')+'<br>Proposed: '+e(names.after||'Proposed import')+'</p>'+(names.sample?'<p class="notice"><strong>Example data only. This report does not describe a real store.</strong></p>':'')+'<p><strong>'+result.stats.priority+' priority flags · '+result.stats.changes+' field changes · '+result.stats.absent+' variants absent · '+result.stats.products+' products in update</strong></p><div class="notice"><strong>Comparison assumptions and limits</strong><ul>'+result.limitations.map(x=>'<li>'+e(x)+'</li>').join('')+'</ul><p>Price-drop threshold: '+e(result.settings.threshold)+'%. Inventory locations: '+e(result.settings.locations)+'. Keep a backup and test a small import.</p></div><h2>Findings</h2>'+result.findings.map(x=>'<section class="finding '+x.severity+'"><span class="tag">'+e(x.severity)+'</span><h3>'+e(x.title)+'</h3><p>'+e(x.detail)+'</p>'+((x.oldValue!==null||x.newValue!==null)?'<p><strong>'+e(x.oldValue)+' → '+e(x.newValue)+'</strong></p>':'')+'<p class="meta">'+e(x.handle)+' · '+e(x.sku)+' · '+e(x.side)+(x.line?' line '+x.line:'')+'</p></section>').join('')+'<h2>Field changes</h2><table><thead><tr><th>Handle / variant</th><th>Field</th><th>Current</th><th>Proposed</th></tr></thead><tbody>'+result.changes.map(x=>'<tr><td>'+e(x.handle)+'<br>'+e(x.variant)+'</td><td>'+e(x.field)+'</td><td>'+e(x.before||'(blank)')+'</td><td>'+e(x.after||'(blank)')+'</td></tr>').join('')+'</tbody></table><p class="meta">Unchecked columns: '+e(result.coverage.uncheckedColumns.join(', ')||'None in this file')+'. Independent tool; no affiliation with Shopify.</p></html>';
 }
 const sampleHeaders='Handle,Title,Option1 Name,Option1 Value,Variant SKU,Variant Price,Variant Compare At Price,Status,Published,Vendor,Tags';
 const SAMPLE_BEFORE=sampleHeaders+'\nlinen-shirt,Linen Shirt,Size,S,LIN-S,89.00,,active,TRUE,North Studio,summer\nlinen-shirt,,Size,M,LIN-M,89.00,,,,,\nlinen-shirt,,Size,L,LIN-L,89.00,,,,,\nceramic-mug,Ceramic Mug,Color,Ink,MUG-INK,24.00,30.00,active,TRUE,Clay House,gifts\ncanvas-tote,Canvas Tote,Title,Default Title,TOTE-01,32.00,,active,TRUE,North Studio,essentials\n';
 const SAMPLE_AFTER=sampleHeaders+'\nlinen-shirt,Linen Shirt,Size,S,LIN-S,8.90,,active,TRUE,North Studio,summer\nlinen-shirt,,Size,M,LIN-M,89.00,,,,,\nceramic-mug,Ceramic Mug,Color,Ink,MUG-INK,24.00,20.00,draft,TRUE,Clay House,gifts\ncanvas-tote,Canvas Tote,Title,Default Title,TOTE-01,32.00,,active,TRUE,,essentials\ntravel-pouch,Travel Pouch,Color,Navy,POUCH-N,18.00,,active,TRUE,North Studio,travel\n';
 const api={parseCSV,compare,escape,csvCell,reviewCSV,reportHTML,number,SAMPLE_BEFORE,SAMPLE_AFTER,MAX_ROWS,MAX_CHARS};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.ImportScope=api;
})(typeof globalThis!=='undefined'?globalThis:this);
