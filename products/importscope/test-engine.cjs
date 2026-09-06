const test=require('node:test');
const assert=require('node:assert/strict');
const E=require('./dist/engine.js');
const h='Handle,Title,Option1 Name,Option1 Value,Variant SKU,Variant Price';
const row=(handle='mug',price='20')=>`${handle},Mug,Color,Blue,MUG,${price}`;
test('example detects decimal price error, empty vendor, status change and missing variant',()=>{
 const r=E.compare(E.SAMPLE_BEFORE,E.SAMPLE_AFTER);
 assert.equal(r.stats.priority,3);assert.equal(r.stats.absent,1);assert.equal(r.stats.products,4);
 assert.deepEqual(r.findings.filter(x=>x.severity==='high').map(x=>x.code),['price_drop','status_change','blanked_field']);
 assert.equal(r.findings.find(x=>x.code==='price_drop').newValue,'8.90');
});
test('quoted commas, escaped quotes, BOM, CRLF and multiline descriptions retain exact cells and line numbers',()=>{
 const p=E.parseCSV('\uFEFFHandle,Title,Description\r\nmug,"Mug, blue","One\r\n""two"""\r\nplate,Plate,Text\r\n');
 assert.equal(p.records[0].values.title,'Mug, blue');assert.equal(p.records[0].values.body,'One\r\n"two"');assert.equal(p.records[1].line,4);
});
test('bad quoting, duplicate aliases, wrong widths and wrong delimiters fail before comparison',()=>{
 for(const s of ['Handle,Title\na,"Unclosed','Handle,URL handle,Title\na,a,A','Handle,Title\na,A,extra','Handle;Title\na;A'])assert.throws(()=>E.parseCSV(s));
});
test('an omitted price column is not interpreted as a blank price',()=>{
 const r=E.compare(h+'\n'+row(),'Handle,Title,Option1 Name,Option1 Value\nmug,Mug,Color,Blue');
 assert.equal(r.changes.length,0);assert.ok(!r.findings.some(x=>x.code==='blank_price'));
});
test('an explicit blank price is high priority',()=>{
 const r=E.compare(h+'\n'+row(),h+'\n'+row('mug',''));
 assert.ok(r.findings.some(x=>x.code==='blank_price'));
});
test('products not present in a partial update are not classified as removed',()=>{
 const r=E.compare(h+'\n'+row()+'\n'+row('other'),h+'\n'+row());assert.equal(r.stats.absent,0);assert.equal(r.stats.products,1);
});
test('image-only continuation rows are not duplicate variants',()=>{
 const head=h+',Image Src';const t=head+'\n'+row()+',https://example.com/1.jpg\nmug,,,,,,https://example.com/2.jpg';
 const r=E.compare(t,t);assert.ok(!r.findings.some(x=>x.code==='duplicate_variant'));assert.equal(r.stats.matchedVariants,1);
});
test('duplicate variant identities suppress unreliable price comparisons',()=>{
 const r=E.compare(h+'\n'+row()+'\n'+row('mug','100'),h+'\n'+row('mug','1'));
 assert.ok(r.findings.some(x=>x.code==='duplicate_variant'));assert.equal(r.changes.length,0);
});
test('changed option with the same SKU is flagged without silently matching by SKU',()=>{
 const r=E.compare(h+'\n'+row(),h+'\n'+row().replace(',Blue,',',Green,'));
 assert.ok(r.findings.some(x=>x.code==='sku_option_change'));assert.equal(r.stats.absent,1);assert.equal(r.stats.matchedVariants,0);
});
test('new schema headers compare with legacy headers',()=>{
 const r=E.compare(h+'\n'+row(),'URL handle,Title,Option1 name,Option1 value,SKU,Price\n'+row('mug','10'));
 assert.ok(r.findings.some(x=>x.code==='price_drop'));
});
test('missing Option1 headers and multiple-location inventory receive explicit warnings',()=>{
 const r=E.compare(h+'\n'+row(),'Handle,Title,Variant Price,Inventory quantity\nmug,Mug,20,10',{locations:'multiple'});
 assert.ok(r.findings.some(x=>x.code==='missing_variant_options'));assert.ok(r.findings.some(x=>x.code==='inventory_locations'));
});
test('report exports escape untrusted markup and defuse spreadsheet formulas',()=>{
 assert.equal(E.csvCell('=HYPERLINK("https://example.com")'),'"\'=HYPERLINK(""https://example.com"")"');
 for(const s of ['+1','-1','@SUM(1)','\t=1','  =1'])assert.ok(E.csvCell(s).startsWith('"\''));
 const r=E.compare(E.SAMPLE_BEFORE,E.SAMPLE_AFTER);const html=E.reportHTML(r,{before:'<img src=x onerror=alert(1)>',sample:true});
 assert.ok(!html.includes('<img'));assert.ok(html.includes('&lt;img'));assert.ok(html.includes('Example data only'));
});
test('input limits and invalid thresholds reject safely',()=>{
 assert.throws(()=>E.compare(h+'\n'+row(),h+'\n'+row(),{threshold:NaN}));
 assert.throws(()=>E.parseCSV('a'.repeat(E.MAX_CHARS+1)));
});
