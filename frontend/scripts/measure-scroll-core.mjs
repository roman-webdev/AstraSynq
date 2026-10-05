import {chromium} from 'playwright';
import fs from 'node:fs';
const browser=await chromium.launch({channel:'chrome',headless:true}),results=[];
try{
 for(const mobile of [false,true]){
  const ctx=await browser.newContext({viewport:{width:mobile?390:1440,height:1000},isMobile:mobile,hasTouch:mobile});
  await ctx.route('**/api/v1/auth/me',r=>r.fulfill({status:401,json:{detail:{code:'auth_required'}}}));
  const p=await ctx.newPage(),errors=[];p.on('pageerror',error=>errors.push(error.message));
  if(mobile){const cdp=await ctx.newCDPSession(p);await cdp.send('Emulation.setCPUThrottlingRate',{rate:4});}
  await p.addInitScript(()=>{
   window.measureCore={longTasks:[],ready:0,cls:0,lcp:0};
   new PerformanceObserver(list=>list.getEntries().forEach(e=>window.measureCore.longTasks.push({start:e.startTime,duration:e.duration}))).observe({type:'longtask',buffered:true});
   new PerformanceObserver(list=>list.getEntries().forEach(e=>{if(!e.hadRecentInput)window.measureCore.cls+=e.value;})).observe({type:'layout-shift',buffered:true});
   new PerformanceObserver(list=>list.getEntries().forEach(e=>window.measureCore.lcp=e.startTime)).observe({type:'largest-contentful-paint',buffered:true});
   new MutationObserver(()=>{if(!window.measureCore.ready&&document.querySelector('.core-visual[data-state="webgl"]'))window.measureCore.ready=performance.now();}).observe(document,{subtree:true,attributes:true,childList:true});
  });
  await p.goto(process.env.ASTRA_GATE_URL||'http://127.0.0.1:4191/');await p.locator('.core-visual[data-state="webgl"]').waitFor({timeout:20000});await p.waitForTimeout(1500);
  const before=Number(await p.locator('canvas').getAttribute('data-frame-count'));const idleStart=Date.now();await p.waitForTimeout(3000);const idleFPS=(Number(await p.locator('canvas').getAttribute('data-frame-count'))-before)*1000/(Date.now()-idleStart);
  if(!mobile){await p.locator('#core-input').evaluate(el=>el.scrollIntoView({block:'start'}));await p.waitForTimeout(650);}
  const initial=await p.evaluate(()=>({frame:Number(document.querySelector('canvas').dataset.frameCount),y:scrollY,dpr:document.querySelector('canvas').dataset.dpr}));
  await p.evaluate(()=>{window.scrollSample={start:performance.now(),intervals:[],last:performance.now(),running:true};const sample=now=>{const data=window.scrollSample;data.intervals.push(now-data.last);data.last=now;if(data.running)requestAnimationFrame(sample);};requestAnimationFrame(sample);});
  const scrollStart=Date.now();
  for(let i=0;i<90;i++){await p.mouse.wheel(0,i<45?60:-60);await p.waitForTimeout(40);}
  await p.waitForTimeout(250);
  const scrollElapsed=Date.now()-scrollStart;
  const sample=await p.evaluate(()=>{window.scrollSample.running=false;const data=window.scrollSample,sorted=data.intervals.slice(1).sort((a,b)=>a-b),canvas=document.querySelector('canvas');return {scrollStart:data.start,frame:Number(canvas.dataset.frameCount),p95:sorted[Math.floor(sorted.length*.95)],rafFPS:1000/(sorted.reduce((a,b)=>a+b,0)/sorted.length),longTasks:window.measureCore.longTasks.filter(t=>t.start>data.start),drawCalls:canvas.dataset.drawCalls,dpr:canvas.dataset.dpr,marks:performance.getEntriesByType('mark').filter(m=>m.name.startsWith('astra:')).map(m=>({name:m.name,time:m.startTime})),diagnostics:{...canvas.dataset},overflow:document.documentElement.scrollWidth>innerWidth,...window.measureCore,resources:performance.getEntriesByType('resource').filter(r=>r.name.includes('/assets/')||r.name.includes('/visuals/')).map(r=>({name:r.name.split('/').pop(),bytes:r.encodedBodySize,start:r.startTime}))};});
  const allTasks=sample.longTasks;const scrollTasks=allTasks.filter(task=>task.start>=sample.scrollStart);
  results.push({mode:mobile?'390px touch / 4x CPU':'1440px desktop',idleFPS,scrollSceneFPS:(sample.frame-initial.frame)*1000/scrollElapsed,scrollRAF:sample?.rafFPS,scrollP95:sample.p95,scrollLongTasks:scrollTasks,initialDpr:initial.dpr,...sample,errors});await ctx.close();
 }
 fs.writeFileSync(process.env.ASTRA_GATE_OUTPUT||'../work/immersive/scroll-performance.json',JSON.stringify(results,null,2));console.log(JSON.stringify(results,null,2));
}finally{await browser.close();}
