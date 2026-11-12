const {chromium}=require('C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('node:fs');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
 const page=await browser.newPage({viewport:{width:1440,height:1100}});
 const errors=[];page.on('pageerror',e=>errors.push(String(e)));
 const checks=[];
 for(const file of ['index.html','verification.html']){
   await page.goto(pathToFileURL(path.join(__dirname,'../report',file)).href,{waitUntil:'load'});
   if(file==='index.html'){
     await page.locator('#verification-20261029').scrollIntoViewIfNeeded();
     checks.push({file,existingSvgCount:await page.locator('svg').count(),addedSectionCount:await page.locator('#verification-20261029').count(),imageLoaded:await page.locator('#verification-20261029 img').evaluate(e=>e.complete&&e.naturalWidth>0)});
   }else checks.push({file,title:await page.title(),tableCount:await page.locator('table').count(),h1Count:await page.locator('h1').count()});
   await page.screenshot({path:path.join(__dirname,file.replace('.html','_desktop.png'))});
 }
 await page.setViewportSize({width:390,height:844});
 await page.goto(pathToFileURL(path.join(__dirname,'../report/index.html')).href,{waitUntil:'load'});
 await page.locator('#verification-20261029').scrollIntoViewIfNeeded();
 checks.push({mobileWidth:390,documentWidth:await page.evaluate(()=>document.documentElement.scrollWidth),viewportWidth:390});
 await page.screenshot({path:path.join(__dirname,'index_mobile.png')});
 await browser.close();
 const result={checks,pageErrors:errors};fs.writeFileSync(path.join(__dirname,'web_check.json'),JSON.stringify(result,null,2));console.log(result);
 if(errors.length)process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1});
