import fs from 'node:fs';
const dir='../work/immersive/',median=a=>a.slice().sort((a,b)=>a-b)[Math.floor(a.length/2)],round=x=>Number(x.toFixed(3));
const sets=Object.fromEntries(['baseline','after'].map(name=>[name,[1,2,3].flatMap(i=>JSON.parse(fs.readFileSync(`${dir}gate-${name}-${i}.json`)))]));
const stages=r=>{const m=Object.fromEntries(r.marks.map(x=>[x.name.replace('astra:',''),x.time]));return {importMs:m['import-end']-m['import-start'],modelFetchDecompressMs:m['model-decompressed']-m['model-load-start'],textureParseDecodeMs:m['model-textures-decoded']-m['model-decompressed'],r3fInitializedAtMs:m['r3f-init'],shaderMs:m['shader-end']-m['shader-start'],firstRenderRevealMs:m['first-frame']-m['shader-end']};};
const rows=[];
for(const mode of ['1440 desktop','1440 desktop CPU x4','390 touch CPU x4']){
 const row={mode};for(const name of ['baseline','after']){const runs=sets[name].filter(r=>r.mode===mode),st=runs.map(stages);row[name]={fps:round(median(runs.map(r=>r.sceneFPS))),readyMs:round(median(runs.map(r=>r.ready))),readyRange:runs.map(r=>round(r.ready)),posterMs:round(median(runs.map(r=>r.poster))),rafP95Ms:round(median(runs.map(r=>r.p95))),drawCalls:runs[1].diagnostics.drawCalls,triangles:runs[1].diagnostics.triangles,dpr:runs[1].diagnostics.dpr,quality:runs[1].qualityHistory,errors:runs.flatMap(r=>r.errors),overflow:runs.some(r=>r.overflow),stages:Object.fromEntries(Object.keys(st[0]).map(k=>[k,round(median(st.map(x=>x[k])))]))};}rows.push(row);
}
let ablations=[];
if(fs.existsSync(dir+'gate-ablation.json')){
 ablations=JSON.parse(fs.readFileSync(dir+'gate-ablation.json')).map(r=>({mode:r.mode,variant:r.variant,fps:r.variant==='no-updates'?null:round(r.sceneFPS),drawCalls:r.diagnostics.drawCalls,triangles:r.diagnostics.triangles,dpr:r.diagnostics.dpr,costs:Object.fromEntries(Object.entries(r.metrics||{}).map(([k,m])=>[k,{count:m.count,meanMs:round(m.total/m.count),p95Ms:round(median(m.samples.slice().sort((a,b)=>a-b).slice(Math.floor(m.samples.length*.9))))}]))}));
}
const summary={scenario:'Chrome headless, fresh contexts; 1440x1000 desktop, desktop CPU x4, 390x1000 touch CPU x4; desktop entire story forward/back in 8s; mobile visible hero/story entry forward/back in 8s. 3 alternating baseline/after runs. Localhost; GPU/OS shader caches not purged.',rows,ablations};
fs.writeFileSync(dir+'gate-summary.json',JSON.stringify(summary,null,2));console.log(JSON.stringify(summary,null,2));
