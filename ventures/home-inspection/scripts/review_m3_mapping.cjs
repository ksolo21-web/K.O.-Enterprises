const fs=require('fs'),assert=require('assert/strict');
// Synthetic QA fixture driver only; no code from here is included in the viewer.
// Usage: node scripts/review_m3_mapping.cjs MAPPING_HTML NEW_EVIDENCE_DIR
const {chromium}=require(process.env.M3_PLAYWRIGHT_MODULE||'playwright');
(async()=>{
const [source,out]=process.argv.slice(2);if(!source||!out)throw Error('Require synthetic mapping HTML and new evidence directory');fs.mkdirSync(out,{mode:0o700});
const browser=await chromium.launch({executablePath:process.env.M3_CHROMIUM_EXECUTABLE,args:['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'],headless:true});
const context=await browser.newContext({viewport:{width:1280,height:960}});const network=[],errors=[];
await context.route('**/*',r=>{if(!r.request().url().startsWith('file:')){network.push(r.request().url());return r.abort();}return r.continue();});
const page=await context.newPage();page.on('pageerror',e=>errors.push(String(e)));
const url=require('url').pathToFileURL(require('path').resolve(source)).href;
await page.goto(url);assert.ok((await page.locator('body').innerText()).includes('SYNTH-M3-V6'));assert.equal(await page.locator('table td').count(),3);
assert.ok((await page.locator('body').innerText()).includes('LEARNING_FRAMEWORK_REQUIRES_TRUSTED_ENROLLMENT_AND_REAL_EVALUATION'));
await page.screenshot({path:out+'/desktop-acceptance.png'});
await page.locator('article').filter({has:page.getByRole('heading',{name:'Declared table T1',exact:true})}).screenshot({path:out+'/desktop-table.png'});
await page.locator('article').filter({has:page.getByRole('heading',{name:'Declared continuation',exact:true})}).screenshot({path:out+'/desktop-cross-page.png'});
const widths=[];
for(const width of [360,390,768,1280]){await page.setViewportSize({width,height:900});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));widths.push(width);}
await page.setViewportSize({width:390,height:844});await page.screenshot({path:out+'/mobile-acceptance.png'});
await page.locator('article').filter({has:page.getByRole('heading',{name:'Declared table T1',exact:true})}).screenshot({path:out+'/mobile-table.png'});
await page.locator('a[href="source-viewer/index.html#page-2"]').first().click();assert.ok(page.url().endsWith('#page-2'));
await page.locator('#page-2 img').waitFor();assert.ok(await page.locator('#page-2 img').evaluate(i=>i.complete&&i.naturalWidth>0));
await page.screenshot({path:out+'/mobile-original-scan.png'});
await page.goto(url);const summary=page.locator('details summary').first();await summary.focus();await page.keyboard.press('Enter');assert.ok(await summary.evaluate(s=>s.parentElement.open));
assert.deepEqual(network,[]);assert.deepEqual(errors,[]);
const evidence={synthetic_only:true,browser:await browser.version(),widths,typed_table_cells:3,source_page_links_passed:true,keyboard_details_passed:true,original_completion_gate_blocked:true,document_overflow:false,remote_requests:network,page_errors:errors,screenshots:fs.readdirSync(out).filter(p=>p.endsWith('.png'))};
fs.writeFileSync(out+'/browser-evidence.json',JSON.stringify(evidence,null,2)+'\n',{mode:0o600});console.log(JSON.stringify(evidence));await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
