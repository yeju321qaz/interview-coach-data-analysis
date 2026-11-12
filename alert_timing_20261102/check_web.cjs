const {chromium}=require('C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('node:fs');const path=require('node:path');
const {pathToFileURL}=require('node:url');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
 const errors=[],checks=[];
 const page=await browser.newPage();page.on('pageerror',e=>errors.push(String(e)));
 for(const scheme of ['light','dark'])for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000});await page.emulateMedia({colorScheme:scheme});
  await page.goto(pathToFileURL(path.join(__dirname,'../public_interview_report/dist/alert-timing/index.html')).href);
  await page.locator('img').evaluateAll(imgs=>Promise.all(imgs.map(i=>{i.loading='eager';return i.decode()})));
  const state=await page.evaluate(()=>({title:document.title,width:document.documentElement.scrollWidth,viewport:innerWidth,
   tables:document.querySelectorAll('table').length,images:[...document.images].map(i=>({src:i.getAttribute('src'),loaded:i.complete&&i.naturalWidth>0})),
   nan:document.body.innerText.includes('NaN'),replacementChar:document.body.innerText.includes('\ufffd')}));
  checks.push({scheme,...state});if(state.width>width||state.nan||state.replacementChar||state.images.some(i=>!i.loaded))throw Error(JSON.stringify(state));
  await page.screenshot({path:path.join(__dirname,`web_${scheme}_${width}.png`)});
  if(width===1440){await page.locator('figure').first().scrollIntoViewIfNeeded();await page.screenshot({path:path.join(__dirname,`figure_${scheme}.png`)});}
 }
 for(const file of ['../public_interview_report/dist/index.html','../public_interview_report/dist/details.html','../report/index.html','../report/integrated_standalone.html']){
  await page.goto(pathToFileURL(path.join(__dirname,file)).href);
  const n=await page.locator('#alert-timing-20261102').count();if(n!==1)throw Error('missing section '+file);
 }
 await browser.close();if(errors.length)throw Error(errors.join('\n'));
 fs.writeFileSync(path.join(__dirname,'web_checks.json'),JSON.stringify({checks,pageErrors:errors,passed:true},null,2));console.log('responsive checks passed');
})().catch(e=>{console.error(e);process.exitCode=1});
