import { ArrowUpRight, CheckCircle2, Database, FileCheck2, LayoutDashboard, Radio, ShieldCheck } from 'lucide-react';
import { t, useLanguage } from '../i18n';
export function WorkspaceBridge() {
 useLanguage();const features=[['records',Database],['imports',FileCheck2],['events',Radio]] as const;
 return <section className="core-workspace-bridge" aria-labelledby="core-workspace-heading">
 <div className="bridge-grid"><div className="bridge-lead"><span className="eyebrow">{t('core.workspace.label')}</span><h2 id="core-workspace-heading">{t('core.bridgeTitle')}</h2><p>{t('core.bridgeBody')}</p>
 <ul className="bridge-features">{features.map(([key,Icon])=><li key={key}><Icon size={20} strokeWidth={1.5} aria-hidden="true"/><div><strong>{t('core.bridge.'+key)}</strong><span>{t('core.bridge.'+key+'Body')}</span></div></li>)}</ul>
 <a className="button primary" href="#/overview">{t('Open workspace')}<ArrowUpRight size={18} aria-hidden="true"/></a><span className="bridge-access"><ShieldCheck size={15} aria-hidden="true"/>{t('core.bridge.access')}</span></div>
 <div className="bridge-product"><div className="bridge-window-bar"><span>AstraSynq / {t('Overview')}</span><span className="bridge-demo-tag">{t('SYNTHETIC DATA')}</span></div><div className="core-workspace-preview">
 <div className="preview-nav"><strong>AstraSynq.</strong><span className="preview-nav-active"><LayoutDashboard size={16} aria-hidden="true"/>{t('Overview')}</span><span><FileCheck2 size={16} aria-hidden="true"/>{t('Import data')}</span></div><div className="preview-content"><span className="preview-kicker">{t('core.bridge.previewLabel')}</span><h3>{t('Overview')}</h3>
 <div className="metrics-grid">{[['Clean records','8'],['Data quality','100%'],['Completed imports','1']].map(([label,value])=><div className="metric-card" key={label}><span>{t(label)}</span><strong>{value}</strong><small>{t('Ready to use')}</small></div>)}</div>
 <div className="panel"><div className="panel-heading"><h3>{t('Recent imports')}</h3><span className="pill green">{t('Completed')}</span></div><div className="preview-record"><FileCheck2 size={19} aria-hidden="true"/><div><strong>leads_sample.csv</strong><span>{t('8 records ready')}</span></div><CheckCircle2 size={19} aria-hidden="true"/></div></div>
 <div className="bridge-event"><span className="status-dot"/><span>{t('Completed')}</span><span>Webhook / Telegram</span></div></div></div><p className="bridge-product-note">{t('core.bridge.previewNote')}</p></div></div></section>;
}
