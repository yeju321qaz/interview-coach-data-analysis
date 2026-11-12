const {chromium}=require('C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path'),{pathToFileURL}=require('node:url'),assert=require('node:assert/strict');let browser;
(async()=>{
 browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
 const page=await browser.newPage({viewport:{width:1440,height:1100}});const errors=[];page.on('pageerror',e=>errors.push(String(e)));const checks=[];
 for(const name of ['index.html','integrated_standalone.html']){
  await page.goto(pathToFileURL(path.join(__dirname,'../report',name)).href,{waitUntil:'load'});
  assert.equal(await page.locator('svg').count(),4);for(const id of ['integrated','stt-local','intent-prototype','artifact-sync'])assert.equal(await page.locator('#'+id).count(),1);
  const loaded=await page.locator('img').evaluateAll(imgs=>imgs.every(i=>i.complete&&i.naturalWidth>0));assert.ok(loaded);
  await page.locator('#stt-local').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(__dirname,name.replace('.html','_desktop.png'))});
  await page.setViewportSize({width:390,height:844});await page.locator('#integrated').scrollIntoViewIfNeeded();const width=await page.evaluate(()=>document.documentElement.scrollWidth);assert.equal(width,390);
  await page.screenshot({path:path.join(__dirname,name.replace('.html','_mobile.png'))});
  if(name==='integrated_standalone.html'){
    const images=await page.locator('img').evaluateAll(imgs=>imgs.map(i=>i.getAttribute('src')));assert.ok(images.every(s=>s.startsWith('data:')));
    assert.equal(await page.locator('a[href="verification.html"],a[href="phase2.html"],link').count(),0);
  }
  checks.push({file:name,svg_count:4,images_loaded:true,mobile_width:width});await page.setViewportSize({width:1440,height:1100});
 }
 assert.equal(errors.length,0);await browser.close();
 fs.writeFileSync(path.join(__dirname,'web_checks.json'),JSON.stringify({status:'PASS',checks,pageErrors:errors,standalone_images_embedded:true,remote_upload:false},null,2));console.log('Integrated site and standalone checks PASS');
})().catch(async e=>{console.error(e);await browser?.close();process.exitCode=1});
