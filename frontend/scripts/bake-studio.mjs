import {chromium} from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
const browser=await chromium.launch({channel:'chrome',headless:true});
try{
 const page=await browser.newPage();
 await page.route('**/node_modules/three/**',async route=>{
  const rel=new URL(route.request().url()).pathname.split('/node_modules/three/')[1];
  const folder=path.resolve('node_modules/three'),file=path.resolve(folder,rel);
  if(!file.startsWith(folder+path.sep))throw Error('Unexpected module path');
  await route.fulfill({contentType:'application/javascript',body:fs.readFileSync(file)});
 });
 await page.route('**/studio-bake',route=>route.fulfill({contentType:'text/html',body:`<script type="importmap">{"imports":{"three":"/node_modules/three/build/three.module.js"}}</script><script type="module">
 import * as T from 'three';import {RoomEnvironment} from '/node_modules/three/examples/jsm/environments/RoomEnvironment.js';
 const renderer=new T.WebGLRenderer();const generator=new T.PMREMGenerator(renderer),room=new RoomEnvironment(),target=generator.fromScene(room,.035,.1,100,{size:64});
 const data=new Uint16Array(target.width*target.height*4);renderer.readRenderTargetPixels(target,0,0,target.width,target.height,data);
 window.baked={width:target.width,height:target.height,data:Array.from(data)};target.dispose();room.dispose();generator.dispose();renderer.dispose();
 </script>`}));
 await page.goto('http://127.0.0.1:4191/studio-bake');await page.waitForFunction(()=>window.baked);
 const result=await page.evaluate(()=>window.baked);
 if(!result.data.some(n=>n>0))throw Error('Empty lighting bake');
 const header=Buffer.alloc(8);header.writeUInt32LE(result.width,0);header.writeUInt32LE(result.height,4);
 const pixels=Buffer.from(new Uint16Array(result.data).buffer);
 const binary=Buffer.concat([header,pixels]);const packed=zlib.gzipSync(binary,{level:9});
 fs.writeFileSync('public/visuals/astra-studio.bin',packed);
 console.log(JSON.stringify({width:result.width,height:result.height,raw:binary.length,compressed:packed.length}));
}finally{await browser.close();}


