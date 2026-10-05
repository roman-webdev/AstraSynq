import {chromium} from 'playwright';
import fs from 'node:fs';
const browser=await chromium.launch({channel:'chrome',headless:true});
try{
 const page=await browser.newPage({viewport:{width:1440,height:810}});await page.route('**/api/v1/auth/me',r=>r.fulfill({status:401,json:{detail:{code:'auth_required'}}}));await page.goto('http://127.0.0.1:4191');await page.locator('.core-visual[data-state="webgl"]').waitFor();await page.waitForTimeout(1600);
 await page.addStyleTag({content:'.immersive-content,.landing-nav,.core-explainer{visibility:hidden!important}'});
 fs.mkdirSync('../previews/core-cinematic',{recursive:true});await page.locator('canvas').screenshot({path:'../previews/core-cinematic/reference-angle.png'});
}finally{await browser.close();}
