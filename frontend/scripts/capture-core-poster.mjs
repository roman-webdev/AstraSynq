import {chromium} from 'playwright';
const browser=await chromium.launch({channel:'chrome',headless:true});
try{
 for(const [width,height,suffix] of [[1440,1000,'desktop'],[390,1000,'mobile']]){
  const page=await browser.newPage({viewport:{width,height}});await page.goto('http://127.0.0.1:4191');await page.locator('.core-visual[data-state="webgl"]').waitFor();
  await page.addStyleTag({content:'.immersive-content,.landing-nav,.hero-copy,.hero-foot,.core-story,.core-explainer{visibility:hidden!important}'});
  await page.locator('canvas').screenshot({path:'../work/immersive/core-poster-'+suffix+'.png'});await page.close();
 }
}finally{await browser.close();}

