/** Keep the link semantic; Lenis can claim this event, otherwise use native scrolling. */
export function scrollLandingTop(){
 const event=new Event('astra:scroll-top',{cancelable:true});
 if(window.dispatchEvent(event))window.scrollTo({top:0,behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});
 if(location.hash!=='#/')history.replaceState(history.state,'','#/');
}
