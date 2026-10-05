import { useSyncExternalStore, useEffect, useId, useRef, useState } from 'react';
import en from './locales/en.json';
import uk from './locales/uk.json';
import ru from './locales/ru.json';
export type Language = 'en' | 'uk' | 'ru';
const dictionaries: Record<Language, Record<string,string>> = { en, uk, ru };
const key = 'astrasynq.language';
let language: Language = 'en';
try { const saved = localStorage.getItem(key); if(saved === 'en' || saved === 'uk' || saved === 'ru') language = saved; } catch { /* Storage may be disabled. */ }
const listeners = new Set<() => void>();
export const getLanguage = () => language;
export function setLanguage(next: Language) {
  language = next;
  document.documentElement.lang = next;
  try { localStorage.setItem(key, next); } catch { /* Keep the session choice. */ }
  listeners.forEach(listener => listener());
}
export function useLanguage() { return useSyncExternalStore(listener => { listeners.add(listener); return () => { listeners.delete(listener); }; }, getLanguage); }
export function t(key: string, values: Record<string,string|number> = {}) {
  const text = dictionaries[language][key] ?? en[key as keyof typeof en] ?? key;
  return text.replace(/\{(\w+)\}/g, (match, name: string) => String(values[name] ?? match));
}
const locale = () => ({en:'en-US',uk:'uk-UA',ru:'ru-RU'})[language];
export const formatNumber = (value: number) => new Intl.NumberFormat(locale()).format(value);
export const formatDate = (value: string) => new Intl.DateTimeFormat(locale(), {month:'short', day:'numeric'}).format(new Date(value));
export const formatChartDate = (value: string) => new Intl.DateTimeFormat(locale(), {month:'short',day:'numeric'}).format(new Date(value));
document.documentElement.lang = language;
export function LanguageSwitcher() {
  const selected = useLanguage(), [open,setOpen]=useState(false), id=useId();
  const root=useRef<HTMLDivElement>(null), trigger=useRef<HTMLButtonElement>(null);
  const languages:Language[]=['en','uk','ru'], names={en:'English',uk:'Українська',ru:'Русский'};
  const close=(focus=false)=>{setOpen(false);if(focus)trigger.current?.focus();};
  useEffect(()=>{if(!open)return;const outside=(e:PointerEvent)=>{if(!root.current?.contains(e.target as Node))setOpen(false);};document.addEventListener('pointerdown',outside);root.current?.querySelector<HTMLButtonElement>('[aria-checked="true"]')?.focus();return()=>document.removeEventListener('pointerdown',outside);},[open]);
  return <div ref={root} className="language-switcher" onBlur={e=>{if(!e.currentTarget.contains(e.relatedTarget))setOpen(false);}} onKeyDown={e=>{
    if(e.key==='Escape'){e.preventDefault();close(true);}
    if(['ArrowDown','ArrowUp','Home','End'].includes(e.key)){e.preventDefault();if(!open){setOpen(true);return;}const items=Array.from(root.current!.querySelectorAll<HTMLButtonElement>('[role="menuitemradio"]'));const index=items.indexOf(document.activeElement as HTMLButtonElement);items[e.key==='Home'?0:e.key==='End'?2:(index+(e.key==='ArrowDown'?1:2))%3]?.focus();}
  }}>
    <button ref={trigger} type="button" className="language-trigger" aria-label={t('language')} aria-haspopup="menu" aria-expanded={open} aria-controls={open?id:undefined} onClick={()=>setOpen(!open)}>{selected==='uk'?'UA':selected.toUpperCase()} <span aria-hidden="true">⌄</span></button>
    {open&&<div id={id} className="language-menu" role="menu" aria-label={t('language')}>{languages.map(lang=><button type="button" role="menuitemradio" tabIndex={-1} key={lang} lang={lang} aria-checked={selected===lang} onClick={()=>{setLanguage(lang);close(true);}}>{names[lang]}<span aria-hidden="true">{selected===lang?'✓':''}</span></button>)}</div>}
  </div>;
}
