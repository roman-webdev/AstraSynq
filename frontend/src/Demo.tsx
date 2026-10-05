import {useEffect,useState,useRef,useId} from 'react';
import {request} from './api';
import {t,useLanguage} from './i18n';
export const syntheticDemo=import.meta.env.VITE_ASTRASYNQ_DEMO_MODE==='true';
export function DemoIndicator(){
 useLanguage();const [open,setOpen]=useState(false),root=useRef<HTMLDivElement>(null),id=useId();
 useEffect(()=>{if(!open)return;const outside=(e:PointerEvent)=>{if(!root.current?.contains(e.target as Node))setOpen(false);};document.addEventListener('pointerdown',outside);return()=>document.removeEventListener('pointerdown',outside);},[open]);
 return syntheticDemo?<div className="demo-indicator" ref={root} onBlur={e=>{if(!e.currentTarget.contains(e.relatedTarget))setOpen(false);}} onKeyDown={e=>{if(e.key==='Escape'){setOpen(false);root.current?.querySelector('button')?.focus();}}}>
 <button type="button" className="demo-badge" aria-label={t('Synthetic demo')} aria-expanded={open} aria-controls={open?id:undefined} onClick={()=>setOpen(!open)}><span className="demo-label-full">{t('Synthetic demo')}</span><span className="demo-label-short" aria-hidden="true">{t('Demo')}</span></button>
 {open&&<div id={id} className="demo-popover" role="note">{t('Synthetic demo data · sample CSV only · deliveries simulated · login by invitation')}</div>}
 </div>:null;
}
export function DemoAudit(){
 const [items,setItems]=useState<{id:string;action:string;timestamp:string}[]>([]);
 const [error,setError]=useState('');
 useEffect(()=>{request<{items:typeof items}>('/audit-logs').then(r=>setItems(r.items)).catch(e=>setError(e.message));},[]);
 return <section className="panel"><h2>{t('Synthetic audit trail')}</h2><p>{t('No persistent worker or timed schedules in this demo. Mock deliveries finish during commit.')}</p>{error?<p role="alert">{t(error)}</p>:<ul>{items.map(x=><li key={x.id}>{x.action} · {x.timestamp}</li>)}</ul>}</section>;
}
