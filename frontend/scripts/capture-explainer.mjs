import {chromium} from 'playwright';
import fs from 'node:fs';
const browser=await chromium.launch({channel:'chrome',headless:true});
try{const page=await browser.newPage({viewport:{width:1440,height:1000}});await page.addInitScript(()=>localStorage.setItem('astrasynq.language','ru'));await page.route('**/api/v1/auth/me',r=>r.fulfill({status:401,json:{detail:{code:'auth_required'}}}));await page.goto('http://127.0.0.1:4191');await page.locator('.core-visual[data-state="webgl"]').waitFor();await page.locator('#core-validation').evaluate(el=>el.scrollIntoView({block:'center'}));await page.waitForTimeout(1100);fs.mkdirSync('../previews/core-fast',{recursive:true});await page.screenshot({path:'../previews/core-fast/explainer-validation-ru.png'});}finally{await browser.close();}
