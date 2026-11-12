const {chromium}=require('C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('node:fs');const path=require('node:path');const {pathToFileURL}=require('node:url');const assert=require('node:assert/strict');let activeBrowser;
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',downloadsPath:path.join(__dirname,'browser_downloads')});
 activeBrowser=browser;
 const context=await browser.newContext({viewport:{width:1440,height:1100},acceptDownloads:true});const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(String(e)));
 const url=pathToFileURL(path.join(__dirname,'../report/review.html')).href;
 await page.goto(url);await page.locator('#reviewer').fill('R_UI_SYNTHETIC_TEST');await page.locator('#reviewer').dispatchEvent('change');
 const actual=JSON.parse(fs.readFileSync(path.join(__dirname,'review/review_subset48.json'),'utf8'));
 const fixture=structuredClone(actual);fixture.rows=fixture.rows.map((r,i)=>({...r,q_text:'UI 합성 시험 질문 '+i,a_text:'합성 시험 답변입니다.',audio_pair_available:'False',answer_audio_path:''}));
 const fp=path.join(__dirname,'ui_fixture.json');fs.writeFileSync(fp,JSON.stringify(fixture));
 await page.locator('#dataset_file').setInputFiles(fp);await page.locator('#workspace').waitFor({state:'visible'});
 assert.match(await page.locator('#progress').innerText(),/완료 0/);
 await page.locator('#save_review').click();assert.match(await page.locator('#message').innerText(),/모두 입력/);assert.match(await page.locator('#progress').innerText(),/완료 0/);
 await page.locator('input[name=human_type]').first().check();await page.locator('#human_star_applicable').selectOption('no');await page.locator('#question_answer_match').selectOption('relevant');await page.locator('#transcript_audio_match').selectOption('not_available');await page.locator('#human_quality_status').selectOption('review');await page.locator('#evidence_notes').fill('합성 UI 시험, "따옴표"\n다음 줄');await page.locator('#save_review').click();assert.match(await page.locator('#progress').innerText(),/완료 1/);
 const downloaded=page.waitForEvent('download');await page.locator('#export').click();const dl=await downloaded;const csv=path.join(__dirname,'ui_fixture_export.csv');await dl.saveAs(csv);
 await page.locator('#results_file').setInputFiles(csv);assert.match(await page.locator('#message').innerText(),/복원/);assert.match(await page.locator('#progress').innerText(),/완료 1/);
 await page.locator('#evidence_notes').fill('합성 시험 수정');assert.match(await page.locator('#progress').innerText(),/완료 0/);
 await context.close();
 // Independent clean context: actual records stay unreviewed.
 const real=await browser.newContext({viewport:{width:1440,height:1100}});const rp=await real.newPage();rp.on('pageerror',e=>errors.push(String(e)));await rp.goto(url);await rp.locator('#dataset_file').setInputFiles(path.join(__dirname,'review/review_subset48.json'));await rp.locator('#workspace').waitFor({state:'visible'});assert.match(await rp.locator('#progress').innerText(),/완료 0/);
 await rp.locator('#audio').evaluate(e=>e.load());await rp.waitForFunction(()=>document.getElementById('audio').readyState>=1,{timeout:15000});
 const audioDuration=await rp.locator('#audio').evaluate(e=>e.duration);assert.ok(audioDuration>0);
 await rp.screenshot({path:path.join(__dirname,'review_desktop.png')});await rp.setViewportSize({width:390,height:844});await rp.screenshot({path:path.join(__dirname,'review_mobile.png')});assert.equal(await rp.evaluate(()=>document.documentElement.scrollWidth),390);
 await rp.goto(pathToFileURL(path.join(__dirname,'../report/index.html')).href);assert.equal(await rp.locator('svg').count(),4);assert.equal(await rp.locator('#phase2').count(),1);
 assert.equal(errors.length,0);await browser.close();
 fs.writeFileSync(path.join(__dirname,'ui_check.json'),JSON.stringify({status:'PASS',synthetic_fixture_only:true,blank_completion_blocked:true,save_export_import_roundtrip:true,editing_invalidates_completion:true,actual_human_review_completed:0,local_audio_duration_s:audioDuration,mobile_width:390,legacy_svg_count:4,pageErrors:errors},null,2));console.log('UI tests PASS; actual review count remains 0');
})().catch(async e=>{console.error(e);await activeBrowser?.close();process.exitCode=1;});
