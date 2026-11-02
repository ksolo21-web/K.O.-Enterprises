const fs=require('fs'),assert=require('assert/strict');
// Controlled synthetic proposal-preview QA; this script is not part of the HTML artifact.
// Usage: node scripts/review_m3_proposals.cjs MODEL_PREVIEW_HTML NEW_EVIDENCE_DIR
const {chromium}=require(process.env.M3_PLAYWRIGHT_MODULE||'playwright');
(async()=>{
const [source,out]=process.argv.slice(2);if(!source||!out)throw Error('Require synthetic model-preview HTML and a new evidence directory');fs.mkdirSync(out,{mode:0o700});
const browser=await chromium.launch({executablePath:process.env.M3_CHROMIUM_EXECUTABLE,args:['--no-sandbox','--disable-gpu','--disable-dev-shm-usage'],headless:true});
const context=await browser.newContext({viewport:{width:1280,height:960}}),network=[],errors=[];
await context.route('**/*',r=>{if(!r.request().url().startsWith('file:')){network.push(r.request().url());return r.abort();}return r.continue();});
const page=await context.newPage();page.on('pageerror',e=>errors.push(String(e)));
const url=require('url').pathToFileURL(require('path').resolve(source)).href;await page.goto(url);
assert.ok((await page.locator('body').innerText()).includes('SYNTH-M3-V6'));
assert.ok((await page.locator('.notice').innerText()).startsWith('MODEL-PROPOSED'));
assert.ok(!(await page.locator('.notice').innerText()).includes('HUMAN-DECLARED'));
assert.equal(await page.locator('table td').count(),3);await page.screenshot({path:out+'/desktop-model-origin.png'});
const table=page.locator('article').filter({has:page.getByRole('heading',{name:'Declared table P0001-T',exact:true})});
assert.ok((await table.innerText()).includes('Item'));assert.ok((await table.innerText()).includes('State'));assert.ok((await table.innerText()).includes('Action'));
await table.screenshot({path:out+'/desktop-source-table.png'});
const widths=[];for(const width of [360,390,768,1280]){await page.setViewportSize({width,height:900});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));widths.push(width);}
await page.setViewportSize({width:390,height:844});await page.goto(url);await page.screenshot({path:out+'/mobile-model-origin.png'});await table.screenshot({path:out+'/mobile-source-table.png'});
await page.locator('a[href="source-viewer/index.html#page-1"]').first().click();assert.ok(page.url().endsWith('#page-1'));
await page.waitForFunction(()=>document.querySelector('#page-1 img')?.complete&&document.querySelector('#page-1 img')?.naturalWidth>0);
await page.screenshot({path:out+'/mobile-original-page.png'});await page.goto(url);
const coverage=page.locator('details').filter({has:page.locator('summary',{hasText:'Coverage'})});await coverage.locator('summary').focus();await page.keyboard.press('Enter');
assert.ok(await coverage.evaluate(d=>d.open));assert.equal((await coverage.innerText()).match(/"status": "unresolved"/g).length,3);
assert.deepEqual(network,[]);assert.deepEqual(errors,[]);
const result={synthetic_controlled_provider_only:true,real_model_inference:false,browser:await browser.version(),widths,model_origin_label:true,human_review_never_claimed:true,source_table_cells:3,all_source_pages_unresolved:3,source_navigation:true,keyboard_details:true,document_overflow:false,remote_requests:network,page_errors:errors,screenshots:fs.readdirSync(out).filter(p=>p.endsWith('.png'))};
fs.writeFileSync(out+'/browser-evidence.json',JSON.stringify(result,null,2)+'\n',{mode:0o600});console.log(JSON.stringify(result));await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
