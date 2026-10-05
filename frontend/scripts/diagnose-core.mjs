import {chromium} from 'playwright';
const b=await chromium.launch({channel:'chrome',headless:true}),p=await b.newPage();
p.on('pageerror',e=>console.log('pageerror:',e.message));p.on('console',m=>{if(m.type()==='error')console.log('console:',m.text().slice(0,1000));});p.on('response',r=>{if(r.status()>=400)console.log('HTTP',r.status(),r.url());});
await p.goto('http://127.0.0.1:4191');await p.waitForTimeout(3000);console.log(await p.locator('.core-visual').getAttribute('data-state'));await b.close();
