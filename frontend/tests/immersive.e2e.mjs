import {test,before,after,afterEach} from 'node:test';
import assert from 'node:assert/strict';
import {chromium} from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
const base=process.env.ASTRASYNQ_IMMERSIVE_URL||'http://127.0.0.1:4191';
const output=process.env.ASTRASYNQ_IMMERSIVE_OUTPUT||path.resolve('..','.clearance','immersive');fs.mkdirSync(output,{recursive:true});
let browser;
before(async()=>{browser=await chromium.launch({channel:process.env.PLAYWRIGHT_CHANNEL||'chrome',headless:true});});
after(async()=>{await browser?.close();});
afterEach(async()=>{for(const ctx of browser.contexts())await ctx.close();});
async function context(options={}) {const ctx=await browser.newContext({viewport:{width:1440,height:1000},...options});await ctx.route('**/api/v1/auth/me',route=>route.fulfill({status:401,json:{detail:{code:'auth_required'}}}));return ctx;}
for(const lang of ['en','uk','ru'])test(`${lang}: responsive semantic story and language persistence`,async()=>{
 const ctx=await context();await ctx.addInitScript(l=>localStorage.setItem('astrasynq.language',l),lang);const p=await ctx.newPage();const errors=[];p.on('pageerror',e=>errors.push(e.message));await p.goto(base);await p.locator('.core-visual[data-state="webgl"]').waitFor({timeout:20000});
 assert.equal(await p.locator('[data-story-stage]').count(),7);const text=await p.locator('#core-input p').innerText();assert(!text.includes('core.input'));assert.equal(await p.locator('html').getAttribute('lang'),lang);
 for(const width of [1440,1024,768,390]) {await p.setViewportSize({width,height:1000});await p.evaluate(()=>window.scrollTo(0,0));await p.waitForTimeout(250);assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`${lang} ${width} overflow`);await p.screenshot({path:path.join(output,`hero-${lang}-${width}.png`)});for(const stage of ['validation','deduplication','delivery']) {await p.locator('#core-'+stage).scrollIntoViewIfNeeded();await p.waitForTimeout(600);assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));}await p.locator('.core-workspace-bridge').scrollIntoViewIfNeeded();assert.equal(await p.locator('.bridge-arrival,.bridge-arrival-line').count(),0);await p.screenshot({path:path.join(output,`workspace-${lang}-${width}.png`)});}
 await p.reload();assert.equal(await p.locator('html').getAttribute('lang'),lang);assert.equal(await p.locator('#core-input p').innerText(),text);assert.deepEqual(errors,[]);await ctx.close();
});
test('reduced motion: static visual, no WebGL/Lenis downloads, semantic content and live preference changes',async()=>{
 const ctx=await context({reducedMotion:'reduce'});const p=await ctx.newPage();const files=[];p.on('request',r=>files.push(r.url()));await p.goto(base);await p.locator('[data-testid="core-fallback"]').waitFor();assert.equal(await p.locator('.core-visual canvas').count(),0);assert.equal(await p.locator('[data-story-stage]').count(),7);assert(!files.some(x=>/CoreScene-|lenis-/.test(x)));await p.screenshot({path:path.join(output,'reduced-motion-1440.png')});if(process.env.ASTRASYNQ_PORTABLE_SMOKE!=='1'){await p.emulateMedia({reducedMotion:'no-preference'});await p.locator('.core-visual[data-state="webgl"]').waitFor({timeout:20000});await p.emulateMedia({reducedMotion:'reduce'});await p.locator('[data-testid="core-fallback"]').waitFor();assert.equal(await p.locator('canvas').count(),0);}await ctx.close();
});
test('WebGL unavailable: graceful image fallback and working CTA',async()=>{
 const ctx=await context();await ctx.addInitScript(()=>{const original=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(type,...args){return String(type).startsWith('webgl')?null:original.call(this,type,...args);};});const p=await ctx.newPage();await p.goto(base);await p.locator('[data-testid="core-fallback"]').waitFor();await p.waitForTimeout(300);assert.equal(await p.locator('canvas').count(),0);assert.equal(await p.locator('[data-story-stage]').count(),7);await p.getByRole('link',{name:'Explore the workspace',exact:true}).click();assert(p.url().endsWith('#/overview'));await ctx.close();
});
test('save-data preference uses static geometry without downloading the renderer',async()=>{
 const ctx=await context();await ctx.addInitScript(()=>Object.defineProperty(navigator,'connection',{get:()=>({saveData:true})}));const p=await ctx.newPage();const files=[];p.on('request',r=>files.push(r.url()));await p.goto(base);await p.locator('[data-testid="core-fallback"]').waitFor();await p.waitForTimeout(350);assert.equal(await p.locator('canvas').count(),0);assert(!files.some(x=>/CoreScene-|lenis-/.test(x)));assert.equal(await p.locator('[data-story-stage]').count(),7);await ctx.close();
});
test('GPU context loss automatically falls back and reload restores WebGL',async()=>{
 const ctx=await context();const p=await ctx.newPage();await p.goto(base);await p.locator('.core-visual[data-state="webgl"]').waitFor({timeout:20000});await p.locator('canvas').evaluate(canvas=>canvas.dispatchEvent(new Event('webglcontextlost',{cancelable:true})));await p.locator('[data-testid="core-fallback"]').waitFor();assert.equal(await p.locator('canvas').count(),0);await p.reload();await p.locator('.core-visual[data-state="webgl"]').waitFor();await ctx.close();
});
test('processor rotates with scroll; hover responds and offscreen rendering stops',async()=>{
 const ctx=await context();const p=await ctx.newPage();await p.goto(base);await p.locator('.core-visual[data-state="webgl"]').waitFor();await p.waitForTimeout(200);
 const canvas=p.locator('canvas'),box=await canvas.boundingBox(),pose=await canvas.getAttribute('data-pose'),time=Number(await canvas.getAttribute('data-pulse-time'));
 await p.mouse.move(box.x+box.width*.15,box.y+box.height*.25);await p.waitForTimeout(250);assert(Number(await canvas.getAttribute('data-hover'))<.1,'hover outside the processor stays inactive');const cx=Number(await canvas.getAttribute('data-chip-x')),cy=Number(await canvas.getAttribute('data-chip-y'));await p.mouse.move(box.x+cx,box.y+cy);await p.mouse.down();await p.mouse.move(box.x+cx+8,box.y+cy+8,{steps:5});await p.mouse.up();await p.waitForTimeout(400);
 assert.equal(await canvas.getAttribute('data-chip-local-pose'),'0,0,0');assert(Number(await canvas.getAttribute('data-hover'))>.5);await p.mouse.move(5,5);await p.waitForFunction(()=>Number(document.querySelector('canvas')?.dataset.hover)<.1,null,{timeout:3000});assert(Number(await canvas.getAttribute('data-hover'))<.1);assert(Number(await canvas.getAttribute('data-pulse-time'))>time);
 await p.locator('#core-validation').scrollIntoViewIfNeeded();await p.waitForTimeout(1000);assert.notEqual(await canvas.getAttribute('data-pose'),pose);
 await p.evaluate(()=>window.scrollTo(0,0));await p.waitForTimeout(1000);assert(Number(await canvas.getAttribute('data-rotation-progress'))<.001);
 assert.equal(await p.locator('.core-controls button').count(),0);assert.equal(await p.locator('.core-object').evaluate(el=>Math.round(el.getBoundingClientRect().height)),await p.locator('.core-visual').evaluate(el=>Math.round(el.getBoundingClientRect().height)));
 await p.locator('.closing-section').scrollIntoViewIfNeeded();await p.waitForTimeout(1200);const stopped=await canvas.getAttribute('data-frame-count');await p.waitForTimeout(400);assert.equal(await canvas.getAttribute('data-frame-count'),stopped);await ctx.close();
});
test('scroll story reverses; anchors, keyboard, back and workspace navigation work',async()=>{
 const ctx=await context();const p=await ctx.newPage();await p.goto(base);await p.locator('.core-visual[data-state="webgl"]').waitFor();await p.locator('#core-delivery').scrollIntoViewIfNeeded();await p.waitForFunction(()=>Number(document.querySelector('.immersive-shell').dataset.stage)>=4,null,{timeout:5000});assert(Number(await p.locator('.immersive-shell').getAttribute('data-stage'))>=4);await p.screenshot({path:path.join(output,'delivery-1440.png')});await p.locator('#core-validation').scrollIntoViewIfNeeded();await p.waitForFunction(()=>Number(document.querySelector('.immersive-shell').dataset.stage)<=2,null,{timeout:5000});assert(Number(await p.locator('.immersive-shell').getAttribute('data-stage'))<=2);await p.screenshot({path:path.join(output,'validation-1440.png')});await p.evaluate(()=>window.scrollTo(0,0));await p.getByRole('link',{name:'See how it flows',exact:true}).click();await p.waitForTimeout(350);assert(p.url().endsWith('#core-story'));assert(await p.evaluate(()=>scrollY>300));await p.keyboard.press('PageDown');await p.waitForTimeout(300);assert(await p.evaluate(()=>scrollY>500));await p.evaluate(()=>scrollTo(0,0));await p.locator('.landing-nav[data-visible="true"]').waitFor();await p.getByRole('banner').getByRole('link',{name:'Open workspace',exact:true}).click();await p.locator('.core-visual').waitFor({state:'detached'});assert.equal(await p.locator('canvas').count(),0);await p.goBack();await p.locator('[data-story-stage]').first().waitFor();await ctx.close();
});

test('integrated footer leaves the processor visible and removes cursor instructions',async()=>{
 const ctx=await context();const p=await ctx.newPage();await p.goto(base);await p.locator('.core-visual[data-state="webgl"]').waitFor();
 for(const width of [1440,1024,768,390]){
  await p.setViewportSize({width,height:900});await p.locator('.hero-foot').evaluate(el=>el.scrollIntoView({block:'center'}));await p.waitForTimeout(600);
  const result=await p.evaluate(()=>{const layer=document.querySelector('.core-visual'),band=document.querySelector('.hero-foot'),a=layer.getBoundingClientRect(),b=band.getBoundingClientRect(),canvas=layer.querySelector('canvas'),top=a.top+Number(canvas.dataset.chipTop),bottom=a.top+Number(canvas.dataset.chipBottom);return {overlap:b.top<bottom&&b.bottom>top,opacity:Number(getComputedStyle(layer).opacity),clip:getComputedStyle(layer).clipPath,height:layer.style.height,controls:document.querySelectorAll('.core-controls button').length};});
  assert.equal(result.controls,0);assert.equal(result.clip,'none');assert.equal(result.height,'');assert.equal(result.opacity,1);assert.equal(await p.locator('.core-caption,.core-signal').count(),0);assert.equal(await p.locator('.hero-foot').evaluate(el=>getComputedStyle(el).backgroundColor),'rgba(0, 0, 0, 0)');
  await p.screenshot({path:path.join(output,`footer-${width}.png`)});
 }await ctx.close();
});

test('native board animates; removed captions and matching reduced-motion image are preserved',async()=>{
 const ctx=await context(),p=await ctx.newPage();await p.goto(base);await p.locator('.core-visual[data-state="webgl"]').waitFor({timeout:20000});
 assert.equal(await p.locator('.core-caption,.core-signal,.board-pointer-light').count(),0);
 const time=Number(await p.locator('canvas').getAttribute('data-pulse-time'));await p.waitForFunction(t=>Number(document.querySelector('canvas').dataset.pulseTime)>t,time,{timeout:5000});assert(Number(await p.locator('canvas').getAttribute('data-pulse-time'))>time);
 await p.emulateMedia({reducedMotion:'reduce'});await p.locator('[data-testid="core-fallback"]').waitFor();assert.equal(await p.locator('canvas').count(),0);assert((await p.locator('[data-testid="core-fallback"] img').getAttribute('src')).includes('core-poster-desktop.webp'));await p.waitForFunction(()=>document.querySelector('[data-testid="core-fallback"] img').naturalWidth>0);await ctx.close();
});

test('normal WebGL loading keeps neutral background and DOM until the live first frame',async()=>{
 const ctx=await context();let release;const gate=new Promise(resolve=>release=resolve);await ctx.route('**/CoreScene-*.js',async route=>{await gate;await route.continue();});
 const p=await ctx.newPage();await p.goto(base,{waitUntil:'domcontentloaded'});await p.locator('.core-visual[data-state="loading"]').waitFor();await p.waitForTimeout(400);
 assert.equal(await p.locator('[data-testid="core-fallback"]').count(),1);assert(await p.locator('.core-fallback img').evaluate(i=>i.complete&&i.naturalWidth>0));assert.equal(await p.locator('[data-testid="core-loading"]').count(),0);assert.equal(await p.locator('.core-fallback').evaluate(e=>getComputedStyle(e).opacity),'0');assert(await p.locator('h1').isVisible());release();await p.locator('.core-visual[data-state="webgl"]').waitFor({timeout:20000});await p.locator('[data-testid="core-fallback"]').waitFor({state:'detached'});assert.equal(await p.locator('[data-testid="core-fallback"]').count(),0);await ctx.close();
});

test('last stage stays fully opaque and the package cannot enter the light workspace',async()=>{
 const ctx=await context();const p=await ctx.newPage();await p.goto(base);await p.locator('.core-visual[data-state="webgl"]').waitFor();
 for(const width of [1440,1024,768]){
  await p.setViewportSize({width,height:1000});await p.locator('#core-workspace').evaluate(el=>el.scrollIntoView({block:'center'}));await p.waitForTimeout(1000);
  assert.equal(await p.locator('.immersive-shell').getAttribute('data-stage'),'6');
  for(const step of [0,180]){
   if(step)await p.evaluate(n=>scrollBy(0,n),step);await p.waitForTimeout(500);
   const bounds=await p.evaluate(()=>{const visual=document.querySelector('.core-visual'),canvas=visual.querySelector('canvas'),white=document.querySelector('.core-workspace-bridge').getBoundingClientRect();return {opacity:Number(getComputedStyle(visual).opacity),bottom:canvas.getBoundingClientRect().bottom,white:white.top};});
   assert.equal(bounds.opacity,1);assert(Number.isFinite(bounds.bottom));assert(bounds.bottom<=bounds.white,`package crosses the dark boundary at ${width}`);
  }await p.screenshot({path:path.join(output,`last-stage-${width}.png`)});
 }await ctx.close();
});


test('continuous shared assembly rotation reverses and background responds to pointer',async()=>{
 const ctx=await context(),p=await ctx.newPage();await p.goto(base);await p.locator('.core-visual[data-state="webgl"]').waitFor();
 const canvas=p.locator('canvas'),box=await canvas.boundingBox();
 await p.mouse.move(box.x+box.width*.85,box.y+box.height*.2);await p.waitForTimeout(500);
 assert(Number(await canvas.getAttribute('data-board-pointer'))>.3);
 const poses=[];
 for(const stage of ['input','validation','deduplication','persistence','event','delivery','workspace']){
  await p.locator('#core-'+stage).evaluate(el=>el.scrollIntoView({block:'center'}));await p.waitForTimeout(1200);
  assert.equal(await canvas.getAttribute('data-chip-local-pose'),'0,0,0');assert.equal(await canvas.getAttribute('data-board-local-pose'),'0,0,0');assert.equal(await canvas.getAttribute('data-pose'),await canvas.getAttribute('data-assembly-pose'));poses.push(await canvas.getAttribute('data-pose'));await p.screenshot({path:path.join(output,'rotation-'+stage+'.png')});
 }
 assert.equal(new Set(poses).size,7);
 await p.locator('#core-validation').evaluate(el=>el.scrollIntoView({block:'center'}));await p.waitForTimeout(1200);
 assert.equal(await canvas.getAttribute('data-pose'),poses[1]);await ctx.close();
});


test('conservative drawing buffer and one attached physical assembly',async()=>{
 const ctx=await context({viewport:{width:1920,height:1080},deviceScaleFactor:2});const p=await ctx.newPage();await p.goto(base);await p.locator('.core-visual[data-state="webgl"]').waitFor();
 const resolution=await p.locator('canvas').evaluate(c=>({width:c.width,height:c.height}));assert(resolution.width>=1920&&resolution.width<=3360);assert(resolution.height>=1080&&resolution.height<=1890);
 assert.equal(await p.locator('canvas').getAttribute('data-chip-local-pose'),'0,0,0');
 await p.screenshot({path:path.join(output,'native-4k.png')});await ctx.close();
});


test('processor explanations follow every stage and translate in EN/UA/RU',async()=>{
 for(const lang of ['en','uk','ru']){
  const ctx=await context(),p=await ctx.newPage();await ctx.addInitScript(l=>localStorage.setItem('astrasynq.language',l),lang);await p.goto(base);await p.locator('.core-visual[data-state="webgl"]').waitFor();
  for(const key of ['input','validation','deduplication','persistence','event','delivery','workspace']){
   await p.locator('#core-'+key).evaluate(el=>el.scrollIntoView({block:'center'}));await p.waitForTimeout(1100);
   const current=await p.locator('.immersive-shell').getAttribute('data-stage');const expected=['input','validation','deduplication','persistence','event','delivery','workspace'][Number(current)];
   const card=p.locator('[data-core-explainer="'+expected+'"]');await card.waitFor();assert((await card.locator('p').innerText()).length>15);assert(!(await card.innerText()).includes('core.'));
  }
  await p.screenshot({path:path.join(output,'explainer-'+lang+'.png')});await ctx.close();
 }
});

test('cinematic assembly keeps real processor bounds inside every desktop viewport',async()=>{
 const ctx=await context(),p=await ctx.newPage();await p.goto(base);await p.locator('.core-visual[data-state="webgl"]').waitFor();
 for(const width of [1440,1024,768]){
  await p.setViewportSize({width,height:1000});
  for(const key of ['input','validation','workspace']){
   await p.locator('#core-'+key).evaluate(el=>el.scrollIntoView({block:'center'}));await p.waitForTimeout(1000);
   const bounds=await p.locator('canvas').evaluate(c=>({top:Number(c.dataset.chipTop),bottom:Number(c.dataset.chipBottom),height:c.getBoundingClientRect().height,revision:c.dataset.sceneRevision,routes:Number(c.dataset.routeCount)}));
   assert.equal(bounds.revision,'blender-physical');assert(bounds.routes>=60);assert(bounds.top>=0);assert(bounds.bottom<=bounds.height,`processor clipped ${width}/${key}`);
  }
 }await ctx.close();
});

test('Blender asset loads under unchanged CSP and material maps reach the renderer',async()=>{
 const ctx=await context(),p=await ctx.newPage(),violations=[];
 p.on('console',m=>{if(/Content Security Policy|Couldn.t load texture/.test(m.text()))violations.push(m.text());});
 await p.goto(base);await p.locator('.core-visual[data-state="webgl"]').waitFor();
 assert.equal(await p.locator('canvas').getAttribute('data-asset-source'),'blender-5.2');
 assert(Number(await p.locator('canvas').getAttribute('data-normal-map-count'))>=2);
 assert.deepEqual(violations,[]);await ctx.close();
});

test('missing Blender model preserves semantic content and image fallback',async()=>{
 const ctx=await context();await ctx.route('**/astra-core.model.bin',r=>r.fulfill({status:503,body:'unavailable'}));
 const p=await ctx.newPage();await p.goto(base);await p.locator('[data-testid="core-fallback"]').waitFor();
 assert.equal(await p.locator('[data-story-stage]').count(),7);
 assert(await p.locator('[data-testid="core-fallback"] img').evaluate(im=>im.complete&&im.naturalWidth>0));
 await ctx.close();
});


test('luminous core responds to hover and rigid shadows avoid repeat draws',async()=>{
 const ctx=await context(),p=await ctx.newPage();await p.goto(base);await p.locator('.core-visual[data-state="webgl"]').waitFor();const canvas=p.locator('canvas');await p.waitForTimeout(350);const glow=Number(await canvas.getAttribute('data-core-glow')),b=await canvas.boundingBox();await p.mouse.move(b.x+Number(await canvas.getAttribute('data-chip-x')),b.y+Number(await canvas.getAttribute('data-chip-y')));await p.waitForFunction(()=>Number(document.querySelector('canvas').dataset.hover)>.7,null,{timeout:5000});assert(Number(await canvas.getAttribute('data-core-glow'))>glow+.1);assert.equal(await canvas.getAttribute('data-shadow-mode'),'rigid-cached');assert(Number(await canvas.getAttribute('data-draw-calls'))<45);await ctx.close();
});
test('workspace handoff is readable, localized and navigates to authentication',async()=>{
 const ctx=await context({reducedMotion:'reduce'}),p=await ctx.newPage();await p.goto(base);const bridge=p.locator('.core-workspace-bridge');await bridge.waitFor();assert.equal(await bridge.locator('.bridge-features li').count(),3);assert(await bridge.locator('.bridge-demo-tag').innerText());await bridge.getByRole('link',{name:'Open workspace',exact:true}).click();assert(p.url().endsWith('#/overview'));await ctx.close();
});


test('header reveals on upward scroll and the logo smoothly returns to top',async()=>{
 const ctx=await context(),p=await ctx.newPage();await p.goto(base);await p.locator('.core-visual[data-state="webgl"]').waitFor();await p.evaluate(()=>scrollTo(0,1200));await p.waitForFunction(()=>document.querySelector('.landing-nav').dataset.visible==='false');await p.evaluate(()=>scrollTo(0,800));await p.waitForFunction(()=>document.querySelector('.landing-nav').dataset.visible==='true');await p.getByRole('banner').locator('.brand').click();await p.waitForTimeout(80);assert(await p.evaluate(()=>scrollY>0),'logo animates rather than jumping');await p.waitForFunction(()=>scrollY<2,null,{timeout:5000});assert(p.url().endsWith('#/'));await ctx.close();
});
test('reduced-motion logo jumps directly to top; focused header stays reachable',async()=>{
 const ctx=await context({reducedMotion:'reduce'}),p=await ctx.newPage();await p.goto(base);await p.locator('[data-testid="core-fallback"]').waitFor();await p.evaluate(()=>scrollTo(0,900));await p.waitForTimeout(80);await p.evaluate(()=>scrollTo(0,600));await p.locator('.landing-nav[data-visible="true"]').waitFor();await p.getByRole('banner').locator('.brand').focus();await p.keyboard.press('Enter');await p.waitForFunction(()=>scrollY<2);assert.equal(await p.locator('canvas').count(),0);await ctx.close();
});
test('early loading preserves GPU fallback and keeps Dashboard chart off the landing',async()=>{
 const ctx=await context(),p=await ctx.newPage(),requests=[];p.on('request',r=>requests.push(r.url()));await p.goto(base);await p.locator('.core-visual[data-state="webgl"]').waitFor();assert(!requests.some(url=>/\/charts-|DashboardChart-/.test(url)));assert(requests.some(url=>url.includes('astra-board-desktop.bin')));assert(Number(await p.locator('canvas').getAttribute('data-route-count'))===120);await ctx.close();
});

test('missing board geometry gracefully preserves the story',async()=>{
 const ctx=await context();await ctx.route('**/astra-board-desktop.bin',r=>r.fulfill({status:503,body:'unavailable'}));const p=await ctx.newPage();await p.goto(base);await p.locator('[data-testid="core-fallback"]').waitFor();assert.equal(await p.locator('[data-story-stage]').count(),7);await ctx.close();
});
test('iPhone touch drag discriminates horizontal processor gestures from native vertical scroll and refreshes landscape',async()=>{
 const ctx=await context({viewport:{width:390,height:844},isMobile:true,hasTouch:true});const p=await ctx.newPage();await p.goto(base);await p.locator('.core-visual[data-state="webgl"]').waitFor();
 await p.locator('canvas').scrollIntoViewIfNeeded();await p.waitForTimeout(500);
 const canvas=p.locator('canvas'),cdp=await ctx.newCDPSession(p);
 const gesture=async(dx,dy)=>{const a=await canvas.evaluate(e=>{const b=e.getBoundingClientRect();return {x:b.left+Number(e.dataset.chipX),y:b.top+Number(e.dataset.chipY)};});await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[a]});for(let i=1;i<=6;i++){await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:a.x+dx*i/6,y:a.y+dy*i/6}]});await p.waitForTimeout(35);}};
 const before=await p.evaluate(()=>scrollY);await gesture(45,4);await p.waitForTimeout(150);assert(Number(await canvas.getAttribute('data-touch-drag'))>.1);assert(Math.abs(await p.evaluate(()=>scrollY)-before)<3);await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});await p.waitForTimeout(500);assert(Math.abs(Number(await canvas.getAttribute('data-touch-drag')))<.03);
 await gesture(3,-100);await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});await p.waitForTimeout(350);assert(await p.evaluate(()=>scrollY)>before+30,'vertical swipe scrolls');
 for(const viewport of [{width:844,height:390},{width:932,height:430},{width:390,height:844}]){
  await p.setViewportSize(viewport);await p.evaluate(()=>dispatchEvent(new Event('orientationchange')));await p.waitForTimeout(650);
  assert(await p.locator('.core-visual-sticky').getAttribute('data-layout-refresh'));
  assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  const b=await p.locator('.immersive-shell').boundingBox();assert.equal(b.x,0);assert.equal(b.width,viewport.width);
  assert.equal(await p.locator('.core-visual-sticky').evaluate(e=>getComputedStyle(e).position),'relative');
  await canvas.scrollIntoViewIfNeeded();await p.waitForTimeout(250);
  assert(await canvas.evaluate(e=>Number(e.dataset.chipTop)>=0&&Number(e.dataset.chipBottom)<=e.clientHeight&&Number(e.dataset.chipLeft)>=0&&Number(e.dataset.chipRight)<=e.clientWidth),'chip inside resized canvas');
  await p.screenshot({path:path.join(output,`iphone-${viewport.width}-${viewport.height}.png`)});
  for(const stage of ['input','delivery','workspace']){await p.locator('#core-'+stage).scrollIntoViewIfNeeded();assert(await p.locator('#core-'+stage+' h2').isVisible());assert(await p.locator('#core-'+stage).evaluate(e=>{const p=e.parentElement.getBoundingClientRect(),b=e.getBoundingClientRect();return b.left>=p.left&&b.right<=p.right&&b.bottom<=p.bottom;}));}
 }
 await ctx.close();
});
