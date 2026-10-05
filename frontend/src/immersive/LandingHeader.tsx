import { useEffect, useRef, type ReactNode } from 'react';

export function LandingHeader({children}:{children:ReactNode}){
 const header=useRef<HTMLElement>(null),spacer=useRef<HTMLDivElement>(null);
 useEffect(()=>{
  const element=header.current!;let last=scrollY,travel=0,frame=0;
  const show=(visible:boolean)=>{element.dataset.visible=String(visible);};
  const update=()=>{
   frame=0;const current=Math.max(0,scrollY),delta=current-last;last=current;
   travel=Math.sign(delta)===Math.sign(travel)?travel+delta:delta;
   element.dataset.raised=String(current>40);
   if(current<element.offsetHeight+30||element.contains(document.activeElement))show(true);
   else if(travel<-12)show(true);else if(travel>18)show(false);
  };
  const scroll=()=>{if(!frame)frame=requestAnimationFrame(update);};
  const resize=new ResizeObserver(()=>{spacer.current?.style.setProperty('height',`${element.offsetHeight}px`);});resize.observe(element);
  const focus=()=>show(true);element.addEventListener('focusin',focus);window.addEventListener('scroll',scroll,{passive:true});update();
  return()=>{resize.disconnect();cancelAnimationFrame(frame);element.removeEventListener('focusin',focus);window.removeEventListener('scroll',scroll);};
 },[]);
 return <><div ref={spacer} className="landing-header-spacer" aria-hidden="true"/><header ref={header} className="landing-nav landing-nav-fixed" data-visible="true">{children}</header></>;
}
