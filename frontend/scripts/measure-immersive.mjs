// Local synthetic performance smoke, not a field Core Web Vitals certification.
import {chromium} from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
const output=process.env.ASTRASYNQ_IMMERSIVE_OUTPUT||path.resolve('..','previews','core-cinematic');
fs.mkdirSync(output,{recursive:true});
const browser=await chromium.launch({channel:'chrome',headless:true});
const results=[];
try {
 for(const mobile of [false,true]) {
  const ctx=await browser.newContext({viewport:mobile?{width:390,height:844}:{width:1440,height:1000},isMobile:mobile,hasTouch:mobile,reducedMotion:'no-preference'});
  await ctx.route('**/api/v1/auth/me',route=>route.fulfill({status:401,json:{detail:{code:'auth_required'}}}));
  await ctx.addInitScript(()=>{window.__smoke={cls:0,lcp:0,longTasks:[]};window.__arrival={};const observe=()=>{const im=document.querySelector('[data-testid="core-poster"] img'),visual=document.querySelector('.core-visual');if(im?.complete&&im.naturalWidth>0&&window.__arrival.poster===undefined)window.__arrival.poster=performance.now();if(visual?.dataset.state==='webgl'&&window.__arrival.webgl===undefined)window.__arrival.webgl=performance.now();};new MutationObserver(observe).observe(document,{subtree:true,childList:true,attributes:true,attributeFilter:['data-state']});document.addEventListener('load',observe,true);for(const type of ['layout-shift','largest-contentful-paint','longtask'])try{new PerformanceObserver(list=>{for(const entry of list.getEntries()){if(type==='layout-shift'&&!entry.hadRecentInput)window.__smoke.cls+=entry.value;if(type==='largest-contentful-paint')window.__smoke.lcp=entry.startTime;if(type==='longtask')window.__smoke.longTasks.push(entry.duration);}}).observe({type,buffered:true});}catch{}});
  const p=await ctx.newPage();const cdp=await ctx.newCDPSession(p);if(mobile)await cdp.send('Emulation.setCPUThrottlingRate',{rate:4});
  await p.goto(process.env.ASTRASYNQ_IMMERSIVE_URL||'http://127.0.0.1:4191');await p.locator('.core-visual[data-state="webgl"]').waitFor({timeout:30000});
  await p.waitForTimeout(1500);
  const fps=await p.evaluate(()=>new Promise(resolve=>{const deltas=[],canvas=document.querySelector('canvas'),initial=Number(canvas.dataset.frameCount);let start=performance.now(),last=start;function frame(now){deltas.push(now-last);last=now;if(now-start<3000)requestAnimationFrame(frame);else{deltas.sort((a,b)=>a-b);resolve({fps:(Number(canvas.dataset.frameCount)-initial)/((now-start)/1000),rafCadence:deltas.length/((now-start)/1000),p95RafFrameMs:deltas[Math.floor(deltas.length*.95)]});}}requestAnimationFrame(frame);}));
  const metrics=await p.evaluate(()=>({ ...window.__smoke,arrival:window.__arrival,drawCalls:Number(document.querySelector('canvas')?.dataset.drawCalls),triangles:Number(document.querySelector('canvas')?.dataset.triangles),drawingBuffer:[document.querySelector('canvas')?.width,document.querySelector('canvas')?.height],pageOverflow:document.documentElement.scrollWidth>innerWidth,resources:performance.getEntriesByType('resource').filter(e=>e.name.endsWith('.js')).map(e=>({name:e.name.split('/').pop(),bytes:e.decodedBodySize})),heapBytes:performance.memory?.usedJSHeapSize}));
  results.push({mode:mobile?'390px touch + 4x CPU emulation':'1440px desktop',...fps,...metrics});
  if(!mobile){for(const key of ['input','validation','deduplication','persistence','event','delivery','workspace']){await p.locator('#core-'+key).scrollIntoViewIfNeeded();await p.waitForTimeout(850);await p.screenshot({path:path.join(output,`stage-${key}-1440.png`)});}await p.locator('.core-workspace-bridge').scrollIntoViewIfNeeded();await p.waitForTimeout(600);await p.screenshot({path:path.join(output,'workspace-transition-1440.png')});}
  await ctx.close();
 }
 // Capture separately: video encoding must not contaminate the frame-rate measurement.
 const capture=await browser.newContext({viewport:{width:1440,height:1000},recordVideo:{dir:path.join(output,'capture'),size:{width:1280,height:800}}});
 await capture.route('**/api/v1/auth/me',route=>route.fulfill({status:401,json:{detail:{code:'auth_required'}}}));
 const recorded=await capture.newPage();await recorded.goto(process.env.ASTRASYNQ_IMMERSIVE_URL||'http://127.0.0.1:4191');await recorded.locator('.core-visual[data-state="webgl"]').waitFor();await recorded.waitForTimeout(1500);
 const canvas=recorded.locator('canvas'),box=await canvas.boundingBox(),cx=Number(await canvas.getAttribute('data-chip-x')),cy=Number(await canvas.getAttribute('data-chip-y'));await recorded.mouse.move(10,10);await recorded.waitForTimeout(700);await recorded.mouse.move(box.x+cx,box.y+cy,{steps:18});await recorded.waitForTimeout(1600);await recorded.screenshot({path:path.join(output,'hero-hover-1440.png')});await recorded.mouse.move(10,10);await recorded.waitForTimeout(600);
 for(const key of ['input','validation','deduplication','event','delivery','workspace']){await recorded.locator('#core-'+key).scrollIntoViewIfNeeded();await recorded.waitForTimeout(850);}
 const video=recorded.video();await capture.close();await video.saveAs(path.join(output,'astra-core-story.webm'));
 const folder='dist/client/assets';const bundle=fs.readdirSync(folder).filter(x=>/\.(js|css)$/.test(x)).map(file=>{const b=fs.readFileSync(path.join(folder,file));return {file,bytes:b.length,gzip:zlib.gzipSync(b).length};});
 fs.writeFileSync(path.resolve('..','work','immersive','cinematic-performance.json'),JSON.stringify({results,bundle},null,2));
 console.log(JSON.stringify(results.map(({mode,fps,p95FrameMs,drawCalls,triangles,lcp,cls,longTasks,arrival})=>({arrival,mode,fps,p95FrameMs,drawCalls,triangles,lcp,cls,longTasks})),null,2));
} finally {await browser.close();}

