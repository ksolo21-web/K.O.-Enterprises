const fs=require('fs');
const path=require('path');
const {pathToFileURL}=require('url');
// Optional QA tool only; never bundled into the offline viewer.
// Usage: node scripts/review_m3_viewer.cjs VIEWER_HTML NEW_EVIDENCE_DIR [PARTIAL_VIEWER_HTML]
const {chromium}=require(process.env.M3_PLAYWRIGHT_MODULE||'playwright');
const chromiumPath=process.env.M3_CHROMIUM_EXECUTABLE;
const assert=require('assert/strict');
(async()=>{
  const [source,out,partial]=process.argv.slice(2);
  if(!source||!out)throw Error('Require synthetic viewer HTML and a new evidence directory');
  fs.mkdirSync(out,{mode:0o700});
  const browser=await chromium.launch({executablePath:chromiumPath,args:['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'],headless:true});
  const context=await browser.newContext({viewport:{width:1280,height:960}});
  const remote=[];const errors=[];
  await context.route('**/*',route=>{const url=route.request().url();if(!url.startsWith('file:')&&!url.startsWith('data:')){remote.push(url);return route.abort();}return route.continue();});
  const page=await context.newPage();page.on('pageerror',e=>errors.push(String(e)));
  await page.goto(pathToFileURL(path.resolve(source)).href);
  await page.locator('.page-image img').evaluateAll(imgs=>imgs.forEach(img=>img.loading='eager'));
  await page.waitForFunction(()=>Array.from(document.images).every(i=>i.complete&&i.naturalWidth>0));
  assert.equal(await page.locator('.page-image img').count(),3);
  await page.screenshot({path:path.join(out,'desktop-top.png')});
  const metrics=await page.locator('#page-1 .page-image').evaluate(box=>{
    const rect=box.getBoundingClientRect(),img=box.querySelector('img').getBoundingClientRect();
    return {containerWidth:rect.width,imageWidth:img.width,containerHeight:rect.height,imageHeight:img.height};
  });
  assert.ok(Math.abs(metrics.containerWidth-metrics.imageWidth)<1);
  assert.ok(Math.abs(metrics.containerHeight-metrics.imageHeight)<1);
  const candidates=page.locator('#page-1 details').filter({has:page.locator('summary',{hasText:'Candidate table groups'})});
  await candidates.locator('summary').click();assert.equal(await candidates.locator('td').count(),12);
  await candidates.screenshot({path:path.join(out,'table-candidate.png')});
  await page.locator('nav a[href="#page-3"]').click();assert.equal(await page.evaluate(()=>location.hash),'#page-3');
  await page.screenshot({path:path.join(out,'desktop-page-three.png')});
  await page.locator('nav a[href="#boundaries"]').click();
  const boundary=page.locator('#boundaries details').first();await boundary.locator('summary').click();
  assert.equal(await boundary.locator('.boundary-grid>div').count(),2);
  assert.ok((await boundary.innerText()).includes('No extractable PDF text'));
  await boundary.screenshot({path:path.join(out,'boundary-context.png')});
  await page.setViewportSize({width:390,height:844});
  await page.locator('nav a[href="#page-1"]').click();
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.screenshot({path:path.join(out,'mobile-page-one.png')});
  await candidates.screenshot({path:path.join(out,'mobile-table-candidate.png')});
  await page.locator('nav a[href="#boundaries"]').click();
  const columns=await boundary.locator('.boundary-grid').evaluate(el=>getComputedStyle(el).gridTemplateColumns);
  assert.equal(columns.trim().split(/\s+/).length,1);
  await boundary.screenshot({path:path.join(out,'mobile-boundary-context.png')});
  if(partial){
    await page.goto(pathToFileURL(path.resolve(partial)).href);
    assert.ok((await page.locator('header').innerText()).includes('PARTIAL_SOURCE_COVERAGE'));
    await page.locator('a[href="#boundaries"]').click();
    const first=page.locator('#boundaries details').first();await first.locator('summary').click();
    assert.ok((await first.innerText()).includes('MISSING_RENDERED_PAGE'));
    await first.locator('a[href="#page-2"]').click();
    assert.ok((await page.locator('#page-2').innerText()).includes('MISSING_RENDERED_PAGE'));
    await page.screenshot({path:path.join(out,'mobile-missing-page.png')});
  }
  assert.deepEqual(remote,[]);assert.deepEqual(errors,[]);
  const evidence={synthetic_only:true,browser:await browser.version(),desktop:[1280,960],mobile:[390,844],
    original_page_images_loaded:3,table_candidate_cells:12,overlay_container_matches_image:metrics,
    page_navigation_passed:true,details_controls_passed:true,boundary_mobile_single_column:true,
    missing_page_navigation_passed:partial?true:null,
    horizontal_document_overflow:false,remote_requests:remote,page_errors:errors,
    screenshots:fs.readdirSync(out).filter(x=>x.endsWith('.png'))};
  fs.writeFileSync(path.join(out,'browser-evidence.json'),JSON.stringify(evidence,null,2)+'\n',{mode:0o600,flag:'wx'});
  for(const file of evidence.screenshots)fs.chmodSync(path.join(out,file),0o600);
  console.log(JSON.stringify(evidence));await browser.close();
})().catch(error=>{console.error(error);process.exit(1)});
