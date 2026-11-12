const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),{pathToFileURL}=require('node:url');
const {chromium}=require('C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');let browser;
(async()=>{
 const root=path.dirname(__dirname);const old=fs.readFileSync(path.join(__dirname,'backup/index.html'),'utf8');const current=fs.readFileSync(path.join(root,'report/index.html'),'utf8');
 assert.equal(old.match(/<style>([\s\S]*?)<\/style>/)[1],current.match(/<style>([\s\S]*?)<\/style>/)[1]);
 for(const variable of ['drift','rows','seg','qt','norms']){
  const regex=new RegExp('const '+variable+' = \\[([\\s\\S]*?)\\];');
  const before=old.match(regex)?.[1],after=current.match(regex)?.[1];assert.ok(before&&after,variable);assert.equal(before,after,variable+' graph data changed');
 }
 for(const bad of ['정확도는 AUC 0.77','문장 하나 (실시간 상황)','STAR 네 요소를 다 말하는 답변은 9%','최소 지연은 약 7~11초','STAR 누락 알림 가능 구간'])assert.ok(!current.includes(bad),bad);
 const beforeSections=[...old.matchAll(/<section id="([^"]+)"/g)].map(x=>x[1]);for(const id of beforeSections)assert.ok(current.includes(`id="${id}"`),id);
 browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});const page=await browser.newPage({viewport:{width:1440,height:1100}});const errors=[];page.on('pageerror',e=>errors.push(String(e)));const reports=[];
 for(const file of ['report/index.html','report/integrated_standalone.html','public_interview_report/dist/index.html']){
  await page.goto(pathToFileURL(path.join(root,file)).href,{waitUntil:'load'});assert.equal(await page.locator('svg').count(),4);
  const first=await page.locator('main > section').evaluateAll(a=>a.slice(0,5).map(e=>e.id));assert.deepEqual(first,['integrated','sources','verification-20261029','stt-local','collection-brief']);
  assert.ok(await page.locator('img').evaluateAll(a=>a.every(e=>e.complete&&e.naturalWidth>0)));
  if(file==='public_interview_report/dist/index.html')await page.screenshot({path:path.join(__dirname,'public_desktop.png')});
  await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth),390);
  if(file==='public_interview_report/dist/index.html')await page.screenshot({path:path.join(__dirname,'public_mobile.png')});
  await page.setViewportSize({width:1440,height:1100});reports.push({file,svg:4,mobileWidth:390,firstSections:first});
 }
 assert.equal(errors.length,0);await browser.close();fs.writeFileSync(path.join(__dirname,'checks.json'),JSON.stringify({status:'PASS',new_experiments:false,legacy_graph_arrays_unchanged:true,old_section_ids_preserved:true,original_css_unchanged:true,reports,pageErrors:errors},null,2));console.log('Editorial checks PASS: data arrays unchanged, all graphs preserved, ordering and mobile verified');
})().catch(async e=>{console.error(e);await browser?.close();process.exitCode=1});
