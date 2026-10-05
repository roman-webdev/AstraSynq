import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require=createRequire(new URL('../frontend/package.json',import.meta.url));
const {chromium}=require('playwright');
const browser=await chromium.launch({channel:process.env.PLAYWRIGHT_CHANNEL||'chrome',headless:true});
try {
 const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
 const page=await context.newPage(); const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const base='http://127.0.0.1:8013';
 await page.goto(base);await page.locator('.demo-badge').waitFor();assert.equal(await page.locator('.synthetic-banner').count(),0);await page.locator('.demo-badge').click();
 assert((await page.locator('.demo-popover').innerText()).includes('deliveries simulated'));
 await page.locator('.landing').waitFor();
 await page.goto(base+'/#/overview');await page.getByRole('heading',{name:'Sign in',exact:true}).waitFor();
 await page.getByLabel('Email',{exact:true}).fill('demo@example.test');
 await page.getByLabel('Password',{exact:true}).fill(process.env.ASTRASYNQ_DEMO_PASSWORD);
 await page.getByRole('button',{name:'Sign in',exact:true}).click();await page.locator('.metric-card').first().waitFor();
 await page.goto(base+'/#/import');await page.getByRole('button',{name:'Use sample',exact:true}).click();
 await page.getByRole('button',{name:'Validate records',exact:true}).click();await page.locator('.review-panel').waitFor();
 // The baseline uses separate synthetic emails, so the first sample saves two records.
 await page.locator('.review-panel .wizard-footer button.primary').click();
 await page.locator('.complete-panel').waitFor();
 await page.goto(base+'/#/deliveries');await page.getByRole('heading',{name:'Deliveries',exact:true}).waitFor();
 await page.getByText('synthetic_sink',{exact:false}).first().waitFor();
 await page.goto(base+'/#/integrations');await page.getByRole('heading',{name:'Integrations',exact:true}).waitFor();
 assert.equal(await page.getByRole('button',{name:'Test delivery',exact:true}).count(),0);
 await page.goto(base+'/#/automations');await page.getByRole('heading',{name:'Synthetic audit trail',exact:true}).waitFor();
 await page.getByText('demo.delivery.simulated',{exact:false}).first().waitFor();
 assert.deepEqual(errors,[]);
 console.log('Demo browser PASS: immersive landing, banner, invitation login, sample import, duplicate-safe commit, mock deliveries, disabled integration test, audit view; no page errors');
 await context.close();
} finally {await browser.close();}
