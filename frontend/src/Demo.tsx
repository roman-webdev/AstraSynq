import {useEffect,useState} from 'react';
import {request} from './api';
import {t,useLanguage} from './i18n';
export const syntheticDemo=import.meta.env.VITE_ASTRASYNQ_DEMO_MODE==='true';
export function DemoBanner(){useLanguage();return syntheticDemo?<aside role="note" className="synthetic-banner">{t('Synthetic demo data · sample CSV only · deliveries simulated · login by invitation')}</aside>:null;}
export function DemoAudit(){
 const [items,setItems]=useState<{id:string;action:string;timestamp:string}[]>([]);
 const [error,setError]=useState('');
 useEffect(()=>{request<{items:typeof items}>('/audit-logs').then(r=>setItems(r.items)).catch(e=>setError(e.message));},[]);
 return <section className="panel"><h2>{t('Synthetic audit trail')}</h2><p>{t('No persistent worker or timed schedules in this demo. Mock deliveries finish during commit.')}</p>{error?<p role="alert">{t(error)}</p>:<ul>{items.map(x=><li key={x.id}>{x.action} · {x.timestamp}</li>)}</ul>}</section>;
}
