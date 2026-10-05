import {chromium} from 'playwright';
import fs from 'node:fs';
const browser=await chromium.launch({channel:'chrome',headless:true});
const results=[];
try {
 for(const mobile of [false,true]) {
  const ctx=await browser.newContext({viewport:{width:mobile?390:1440,height:1000},isMobile:mobile,hasTouch:mobile});
  await ctx.route('**/api/v1/auth/me',r=>r.fulfill({status:401,json:{detail:{code:'auth_required'}}}));
  const p=await ctx.newPage(),errors=[],csp=[];p.on('pageerror',e=>errors.push(e.message));
  p.on('console',m=>{if(m.type()==='error'&&/Content Security|couldn.t load/i.test(m.text()))csp.push(m.text());});
  const cdp=await ctx.newCDPSession(p);if(mobile)await cdp.send('Emulation.setCPUThrottlingRate',{rate:4});
  await p.addInitScript(()=>{
   window.coreMeasure={longTasks:[],cls:0,lcp:0};
   new PerformanceObserver(l=>l.getEntries().forEach(e=>window.coreMeasure.longTasks.push(e.duration))).observe({type:'longtask',buffered:true});
   new PerformanceObserver(l=>l.getEntries().forEach(e=>{if(!e.hadRecentInput)window.coreMeasure.cls+=e.value;})).observe({type:'layout-shift',buffered:true});
   new PerformanceObserver(l=>l.getEntries().forEach(e=>window.coreMeasure.lcp=e.startTime)).observe({type:'largest-contentful-paint',buffered:true});
   const arrival=new MutationObserver(()=>{const loading=document.querySelector('[data-testid="core-loading"]');if(loading&&!window.coreMeasure.loading)window.coreMeasure.loading=performance.now();if(document.querySelector('.core-visual[data-state="webgl"]')&&!window.coreMeasure.webgl)window.coreMeasure.webgl=performance.now();});arrival.observe(document,{subtree:true,childList:true,attributes:true});
  });
  await p.goto('http://127.0.0.1:4191/?scene=blender');await p.locator('.core-visual[data-state="webgl"]').waitFor({timeout:20000});await p.waitForTimeout(6000);
  const a=Number(await p.locator('canvas').getAttribute('data-frame-count')),start=Date.now();await p.waitForTimeout(5000);const fps=(Number(await p.locator('canvas').getAttribute('data-frame-count'))-a)*1000/(Date.now()-start);
  const data=await p.evaluate(()=>({ ...window.coreMeasure,visibility:document.visibilityState,drawCalls:document.querySelector('canvas').dataset.drawCalls,triangles:document.querySelector('canvas').dataset.triangles,dpr:document.querySelector('canvas').dataset.dpr,overflow:document.documentElement.scrollWidth>innerWidth,resources:performance.getEntriesByType('resource').filter(e=>e.name.includes('astra-core.model')||e.name.includes('astra-ceramic')||e.name.includes('astra-pcb')).map(e=>({url:e.name.split('/').pop(),bytes:e.encodedBodySize,duration:e.duration}))}));
  results.push({mode:mobile?'390px touch / 4x CPU':'1440px desktop',fps,...data,errors,csp});await ctx.close();
 }
 fs.writeFileSync('../work/immersive/refinement-performance.json',JSON.stringify(results,null,2));console.log(JSON.stringify(results,null,2));
}finally{await browser.close();}
