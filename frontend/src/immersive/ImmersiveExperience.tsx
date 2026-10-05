import {Component,lazy,Suspense,useCallback,useEffect,useRef,useState,type ReactNode} from 'react';
import {t,useLanguage} from '../i18n';
import {WorkspaceBridge} from './WorkspaceBridge';
import {CoreFallback} from './CoreFallback';
import {useMedia,type CoreMotion} from './motion';
import {coreMark,coreCommit,coreCost} from './telemetry';
import './immersive.css';
let sceneModule:Promise<typeof import('./CoreScene')>|undefined;
const loadCoreScene=()=>sceneModule??=(()=>{coreMark('import-start');return import('./CoreScene').then(m=>{coreMark('import-end');return m;});})();
const CoreScene=lazy(loadCoreScene);
class SceneBoundary extends Component<{children:ReactNode;onFailure:()=>void},{failed:boolean}>{state={failed:false};static getDerivedStateFromError(){return {failed:true};}componentDidCatch(){this.props.onFailure();}render(){return this.state.failed?null:this.props.children;}}
function supportsWebGL(){try{const gl=document.createElement('canvas').getContext('webgl2');if(!gl)return false;gl.getExtension('WEBGL_lose_context')?.loseContext();return true;}catch{return false;}}
const stages=['input','validation','deduplication','persistence','event','delivery','workspace'];
const tokens=['CSV / API / JSON','field · code · row','email → unique','PostgreSQL','✓','Webhook / Telegram','AstraSynq / Overview'];
export function ImmersiveExperience({hero,footer}:{hero:ReactNode;footer:ReactNode}){
 const lang=useLanguage(),reduced=useMedia('(prefers-reduced-motion: reduce)'),mobile=useMedia('(max-width: 767px), (pointer: coarse) and (max-height: 500px)');
 const story=useRef<HTMLDivElement>(null),visual=useRef<HTMLDivElement>(null);
 const motion=useRef<CoreMotion>({progress:0,paused:false,hover:0,pointerX:0,pointerY:0});
 const [stage,setStage]=useState(0),[active,setActive]=useState(true),[ready,setReady]=useState(false),[failed,setFailed]=useState(false),[eligible,setEligible]=useState(false),[checked,setChecked]=useState(false),[storyActive,setStoryActive]=useState(false);
 const [posterVisible,setPosterVisible]=useState(true);
 useEffect(()=>{if(!ready){setPosterVisible(true);return;}const timer=setTimeout(()=>setPosterVisible(false),220);return()=>clearTimeout(timer);},[ready]);
 const failure=useCallback(()=>{setFailed(true);setReady(false);},[]),onReady=useCallback(()=>{coreMark('first-frame');setReady(true);},[]);
 useEffect(()=>{const device=navigator as Navigator & {connection?:{saveData?:boolean}};setEligible(!reduced&&!device.connection?.saveData&&supportsWebGL());setChecked(true);},[reduced]);
 useEffect(()=>{if(!eligible||failed)return;void loadCoreScene().then(module=>module.preloadCoreAssets(mobile)).catch(failure);
 const links=['astra-core.model.bin','astra-studio.bin','astra-ceramic_normal.webp','astra-ceramic_roughness.webp','astra-pcb_normal.webp','astra-pcb_roughness.webp',`astra-board-${mobile?'mobile':'desktop'}.bin`].map(file=>{if(document.querySelector(`link[rel=preload][href="/visuals/${file}"]`))return null;const link=document.createElement('link');link.rel='preload';link.as='fetch';link.crossOrigin='anonymous';link.href='/visuals/'+file;document.head.appendChild(link);return link;});return()=>links.forEach(link=>link?.remove());},[eligible,failed,mobile,failure]);
 useEffect(()=>{motion.current.paused=reduced;},[reduced]);useEffect(()=>{if(!eligible)setReady(false);},[eligible]);
 useEffect(()=>{const observer=new IntersectionObserver(([entry])=>setActive(entry.isIntersecting&&!document.hidden),{threshold:0});if(visual.current)observer.observe(visual.current);const visibility=()=>setActive(!document.hidden&&!!visual.current&&visual.current.getBoundingClientRect().bottom>0&&visual.current.getBoundingClientRect().top<innerHeight);document.addEventListener('visibilitychange',visibility);return()=>{observer.disconnect();document.removeEventListener('visibilitychange',visibility);};},[mobile]);
 useEffect(()=>{let cancelled=false,cleanup=()=>{};if(reduced||failed||!eligible||window.__ASTRA_PROFILE__?.story===false){motion.current.progress=0;setStage(0);return;}
 Promise.all([import('gsap'),import('gsap/ScrollTrigger'),!mobile?import('lenis'):Promise.resolve(null)]).then(([{gsap},{ScrollTrigger},lenisModule])=>{if(cancelled)return;gsap.registerPlugin(ScrollTrigger);let currentStage=-1;
 const tween=gsap.fromTo(motion.current,{progress:0},{progress:1,ease:'none',scrollTrigger:{trigger:story.current,start:'top 65%',end:'bottom 85%',scrub:.3},onUpdate:()=>{const started=performance.now();const next=Math.min(6,Math.floor(motion.current.progress*7));if(next!==currentStage){currentStage=next;setStage(next);}coreCost('gsapUpdate',started);}});
 const lenis=lenisModule?new lenisModule.default({duration:.85,smoothWheel:true,syncTouch:false,anchors:false}):null;const tick=(seconds:number)=>lenis?.raf(seconds*1000);if(lenis){lenis.on('scroll',ScrollTrigger.update);gsap.ticker.add(tick);}
 let resizeTimer:ReturnType<typeof setTimeout>;let resizeFrame=0;
 const resize=()=>{clearTimeout(resizeTimer);cancelAnimationFrame(resizeFrame);resizeTimer=setTimeout(()=>{resizeFrame=requestAnimationFrame(()=>{if(cancelled)return;lenis?.resize();ScrollTrigger.refresh();visual.current?.setAttribute('data-layout-refresh',String(performance.now()));});},180);};
 window.addEventListener('resize',resize);window.addEventListener('orientationchange',resize);window.visualViewport?.addEventListener('resize',resize);
 const reconcile=()=>{lenis?.scrollTo(window.scrollY,{immediate:true});ScrollTrigger.refresh();};const scrollTop=(event:Event)=>{if(lenis){event.preventDefault();lenis.scrollTo(0,{duration:.9});}};window.addEventListener('astra:scroll-top',scrollTop);window.addEventListener('hashchange',reconcile);window.addEventListener('popstate',reconcile);document.fonts.ready.then(()=>{if(!cancelled)ScrollTrigger.refresh();});
 cleanup=()=>{clearTimeout(resizeTimer);cancelAnimationFrame(resizeFrame);window.removeEventListener('resize',resize);window.removeEventListener('orientationchange',resize);window.visualViewport?.removeEventListener('resize',resize);tween.scrollTrigger?.kill();tween.kill();gsap.ticker.remove(tick);lenis?.destroy();window.removeEventListener('astra:scroll-top',scrollTop);window.removeEventListener('hashchange',reconcile);window.removeEventListener('popstate',reconcile);};}).catch(()=>{if(!cancelled)failure();});return()=>{cancelled=true;cleanup();};},[reduced,mobile,lang,failed,eligible,failure]);
 useEffect(()=>{const observer=new IntersectionObserver(([entry])=>setStoryActive(entry.isIntersecting),{threshold:0});if(story.current)observer.observe(story.current);return()=>observer.disconnect();},[]);
 useEffect(()=>{coreCommit('storyCommit');});
 const animated=checked&&eligible&&!failed;
 return <><section className={`immersive-shell ${reduced?'is-reduced':''}`} data-stage={stage} data-motion={reduced?'reduced':'running'}><div className="core-visual-sticky" ref={visual}><div className="core-visual" data-state={!checked?'loading':animated?(ready?'webgl':'loading'):'fallback'} style={{opacity:'var(--scene-visibility, 1)'}}><div className="core-object">
 {(!animated||!ready||posterVisible)&&<CoreFallback/>}
 {animated&&<SceneBoundary onFailure={failure}><Suspense fallback={null}><CoreScene motion={motion} active={active} mobile={mobile} onFailure={failure} onReady={onReady}/></Suspense></SceneBoundary>}
 {storyActive&&<div className="core-explainer" data-core-explainer={stages[stage]}><span>{String(stage+1).padStart(2,'0')} / {t(`core.${stages[stage]}.label`)}</span><p key={stages[stage]}>{t(`core.${stages[stage]}.brief`)}</p><i aria-hidden="true"/></div>}
 </div></div></div><div className="immersive-content"><section className="hero immersive-hero">{hero}<div className="hero-scene-space" aria-hidden="true"/></section>{footer}<div ref={story} className="core-story" id="core-story" aria-label={t('core.story')}><div className="core-story-heading"><span className="eyebrow">{t('core.eyebrow')}</span><p>{t('core.storyIntro')}</p></div>
 {stages.map((key,i)=><section className={`core-stage ${stage===i?'is-current':''}`} id={`core-${key}`} key={key} aria-labelledby={`core-title-${key}`} data-story-stage={key}><span className="core-stage-index">0{i+1}<span/>{t(`core.${key}.label`)}</span><h2 id={`core-title-${key}`}>{t(`core.${key}.title`)}</h2><p>{t(`core.${key}.body`)}</p><div className="core-mobile-explainer">{t(`core.${key}.brief`)}</div><div className={`core-stage-diagram diagram-${key}`} aria-hidden="true"><span>{i<3?'CSV':i<5?'Core':'✓'}</span><b>→</b><span>{tokens[i]}</span></div><span className="core-stage-foot">{t(`core.${key}.note`)}</span></section>)}
 </div></div></section><WorkspaceBridge/></>;
}
