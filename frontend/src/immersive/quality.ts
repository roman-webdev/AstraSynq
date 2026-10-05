import {useEffect,useRef,useState} from 'react';
export type Quality='high'|'balanced'|'low';
export const presets={high:{dpr:1.75,post:true,lens:true,packets:2},balanced:{dpr:1.25,post:true,lens:false,packets:1},low:{dpr:1,post:false,lens:false,packets:1}};
// Profiling overrides exist only in an explicitly injected browser harness.
declare global {interface Window {__ASTRA_PROFILE__?:{quality?:Quality;dpr?:number;post?:boolean;particles?:boolean;updates?:boolean;materials?:boolean;story?:boolean}}}
export function initialQuality(mobile:boolean):Quality{return window.__ASTRA_PROFILE__?.quality||(mobile?'low':'balanced');}
export function nextQuality(q:Quality,fps:number,mobile:boolean,stable:number):Quality{
 if(q==='high'&&fps<45)return 'balanced';
 if(q==='balanced'&&fps<28)return 'low';
 if(!mobile&&q==='balanced'&&fps>=55&&stable>=3)return 'high';
 return q;
}
export function useQuality(mobile:boolean,active=true){
 const [quality,setQuality]=useState<Quality>(()=>initialQuality(mobile)),current=useRef(quality),history=useRef({start:0,frames:0,stable:0,downgraded:false});current.current=quality;
 useEffect(()=>{setQuality(initialQuality(mobile));history.current={start:0,frames:0,stable:0,downgraded:false};},[mobile]);
 useEffect(()=>{history.current.start=0;history.current.frames=0;history.current.stable=0;},[active]);
 const observe=(now:number)=>{if(window.__ASTRA_PROFILE__?.quality)return;const h=history.current;if(!h.start)h.start=now;h.frames++;if(now-h.start<2000)return;const fps=h.frames*1000/(now-h.start);h.stable=fps>=55?h.stable+1:0;const next=nextQuality(current.current,fps,mobile,h.downgraded?0:h.stable);if(next!==current.current){h.downgraded=next!=='high';setQuality(next);}h.start=now;h.frames=0;};
 return {quality,observe};
}
