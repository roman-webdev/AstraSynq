import {chromium} from 'playwright';
import fs from 'node:fs';
const output='../previews/core-scroll';fs.mkdirSync(output,{recursive:true});
const browser=await chromium.launch({channel:'chrome',headless:true});
try{
 const ctx=await browser.newContext({viewport:{width:1440,height:1000},recordVideo:{dir:output+'/capture',size:{width:1280,height:800}}});
 await ctx.addInitScript(()=>localStorage.setItem('astrasynq.language','ru'));
 await ctx.route('**/api/v1/auth/me',r=>r.fulfill({status:401,json:{detail:{code:'auth_required'}}}));
 const p=await ctx.newPage();await p.goto('http://127.0.0.1:4191/?scene=blender');await p.locator('.core-visual[data-state="webgl"]').waitFor();await p.waitForTimeout(900);
 await p.screenshot({path:output+'/hero-ru-1440.png'});
 const c=p.locator('canvas'),b=await c.boundingBox();await p.mouse.move(b.x+Number(await c.getAttribute('data-chip-x')),b.y+Number(await c.getAttribute('data-chip-y')),{steps:16});await p.waitForTimeout(1000);await p.screenshot({path:output+'/hero-hover-ru.png'});await p.mouse.move(10,10);
 for(const key of ['input','validation','deduplication','persistence','event','delivery','workspace']){
  await p.locator('#core-'+key).evaluate(el=>el.scrollIntoView({block:'center'}));await p.waitForTimeout(1100);
  if(['validation','delivery','workspace'].includes(key))await p.screenshot({path:output+'/'+key+'-ru.png'});
 }
 await p.locator('.core-workspace-bridge').evaluate(el=>el.scrollIntoView({block:'start'}));await p.waitForTimeout(600);await p.screenshot({path:output+'/workspace-bridge-ru.png'});const video=p.video();await ctx.close();await video.saveAs(output+'/astra-core-scroll.webm');
}finally{await browser.close();}

