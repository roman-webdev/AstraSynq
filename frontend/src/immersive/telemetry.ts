type Metric={count:number;total:number;max:number;samples:number[]};
declare global{interface Window{__ASTRA_METRICS__?:Record<string,Metric>}}
export function coreMark(name:string){performance.mark('astra:'+name);}
export function coreCost(name:string,start:number){const ms=performance.now()-start,all=window.__ASTRA_METRICS__??={},m=all[name]??={count:0,total:0,max:0,samples:[]};m.count++;m.total+=ms;m.max=Math.max(m.max,ms);if(m.samples.length<2048)m.samples.push(ms);}
export function coreCommit(name:string){coreCost(name,performance.now());}
