import {syntheticDemo,DemoAudit,DemoIndicator} from './Demo';
import {IntegrationsScreen,DeliveriesScreen,AutomationsScreen,AutomationMetrics} from './Integrations';
import {AuthProvider,useAuth,LoginScreen,ProfileMenu,Forbidden,UsersScreen} from './Auth';
import { LandingHeader } from './immersive/LandingHeader';
import { scrollLandingTop } from './immersive/landingNavigation';
import { ImmersiveExperience } from './immersive/ImmersiveExperience';
import { t, formatNumber, formatDate, formatChartDate, LanguageSwitcher, useLanguage } from './i18n';
import { lazy, Suspense, useEffect, useRef, useState, type ChangeEvent, type ReactNode } from 'react';
import { AnimatePresence, motion, MotionConfig, useReducedMotion } from 'motion/react';
const DashboardChart=lazy(()=>import('./DashboardChart'));
import { ArrowDown, ArrowDownToLine, ArrowLeft, ArrowRight, ArrowUpRight, Bell, Braces, Check, CheckCheck, CheckCircle2, ChevronDown, CircleHelp, Database, FileSpreadsheet, GitBranch, LayoutDashboard, Loader2, Play, PlugZap, Search, ShieldCheck, Sparkles, Upload, Waypoints, X, XCircle } from 'lucide-react';
import { request, download, type ImportResult, type Summary } from './api';
const number = formatNumber;
function ApiDocsLink(props:React.AnchorHTMLAttributes<HTMLAnchorElement>){return import.meta.env.DEV || import.meta.env.VITE_SHOW_API_DOCS === 'true' ? <a {...props}/> : null;}
function Brand({ light = false }: {
    light?: boolean;
}) { return <a className={`brand ${light ? 'light' : ''}`} href="#/" onClick={event=>{if(document.querySelector('.landing')&&!event.metaKey&&!event.ctrlKey&&!event.shiftKey&&!event.altKey&&event.button===0){event.preventDefault();scrollLandingTop();}}} aria-label={t("AstraSynq home")}><Waypoints size={27} strokeWidth={1.6}/><span>Astra<span className="brand-thin">Synq</span><span className="brand-period">.</span></span></a>; }
function Button({ children, className = '', ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) { return <button className={`button ${className}`} {...props}>{children}</button>; }
function Pill({ children, tone = 'green' }: {
    children: ReactNode;
    tone?: string;
}) { return <span className={`pill ${tone}`}>{children}</span>; }
function Reveal({ children, className = '' }: {
    children: ReactNode;
    className?: string;
}) { const reduced = useReducedMotion(); return <motion.div className={className} initial={reduced ? false : { opacity: 0, y: 18 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.1 }} transition={{ duration: .4 }}>{children}</motion.div>; }
function Landing() {
    const stages = [
        { title: t("Collect"), icon: FileSpreadsheet, label: t("01 / INPUT"), detail: t("Bring your CSV into one workspace. Map your columns once and keep the source intact."), tag: t("12 source records") },
        { title: t("Validate"), icon: ShieldCheck, label: t("02 / QUALITY"), detail: t("Check emails, amounts and dates. Every issue gets a field, a reason and a row number."), tag: t("2 issues identified") },
        { title: t("Deduplicate"), icon: GitBranch, label: t("03 / PRECISION"), detail: t("Compare normalized emails against the file and existing records. Keep each lead once."), tag: t("2 duplicates separated") },
        { title: t("Sync"), icon: PlugZap, label: t("04 / OUTPUT"), detail: t("Save clean records, then route a completion event through the durable outbox."), tag: t("8 records ready") },
    ];
    return <div className="landing">
    <LandingHeader><Brand light/><LanguageSwitcher /><nav aria-label={t("Main navigation")}><a href="#workflow">{t("The workflow")}</a><a href="#built-for">{t("Built for clarity")}</a><ApiDocsLink href="/docs" target="_blank" rel="noreferrer">{t("API docs")}<ArrowUpRight size={13}/></ApiDocsLink></nav><DemoIndicator/><a className="nav-cta" href="#/overview">{t("Open workspace")}<ArrowUpRight size={16}/></a></LandingHeader>
    <main>
      <ImmersiveExperience hero={<div className="hero-copy"><div className="eyebrow"><span className="status-dot"/>{t("CLARITY IN MOTION")}<span className="eyebrow-line"/></div><h1>{t("Messy data.")}<br /><span>{t("Clear direction.")}</span></h1><p className="hero-description">{t("Turn scattered records into reliable workflows.")}<br className="desktop-break"/>{' '}{t("Import, validate and connect your business data")}<br className="desktop-break"/>{' '}{t("in one considered workspace.")}</p><div className="hero-actions"><a className="button primary" href="#/overview">{t("Explore the workspace")}<ArrowUpRight size={18}/></a><a className="text-link" href="#core-story">{t("See how it flows")}<ArrowDown size={16}/></a></div><div className="hero-note"><ShieldCheck size={15}/><span>{t(syntheticDemo?"Synthetic demo data. Invitation login required.":"Synthetic demo data. No account needed.")}</span></div></div>} footer={<div className="hero-foot"><span className="mono">{t("LESS MANUAL WORK. MORE MOMENTUM.")}</span><div><span>CSV & REST API</span><span>{t("Validation built in")}</span><span>{t("Ready to connect")}</span></div><a href="#workflow" aria-label={t("Explore workflow")}><ArrowDown size={18}/></a></div>}/><section className="workflow-section" id="workflow"><Reveal className="section-heading"><div><span className="eyebrow dark">{t("01 / THE WORKFLOW")}</span><h2>{t("A clear path.")}<br />{t("From input to impact.")}</h2></div><p>{t("Every record has a next step.")}<br />{t("Every decision leaves a trace.")}</p></Reveal><div className="workflow-grid">{stages.map((s, i) => <Reveal className="workflow-card" key={s.title}><div className="workflow-card-top"><s.icon size={23} strokeWidth={1.5}/><span className="mono">0{i + 1}</span></div><h3>{s.title}</h3><p>{s.detail}</p><span className="workflow-bottom">{[t("CSV upload & column mapping"), t("Field-level issue reports"), t("Exact email matching"), t("Event delivery \u00B7 simulated")][i]}<ArrowUpRight size={15}/></span></Reveal>)}</div></section>
      <section className="clarity-section" id="built-for"><Reveal><span className="eyebrow dark">{t("02 / BUILT FOR CLARITY")}</span><h2>{t("Your data deserves")}<br />{t("a better working day.")}</h2><p>{t("Built for the quiet, important work between systems.")}<br />{t("Less spreadsheet cleanup. More confidence in what comes next.")}</p><a className="button dark-button" href="#/import">{t("Try a sample import")}<ArrowUpRight size={18}/></a></Reveal><Reveal className="clarity-panel"><span className="mono">{t("ONE WORKSPACE. A COMPLETE PICTURE.")}</span><div><Database /><strong>{t("See what changed.")}</strong><p>{t("Clean records, import history and quality signals in one overview.")}</p></div><div><Braces /><strong>{t("Connect with confidence.")}</strong><p>{t("Typed API contracts and transparent results at every step.")}</p></div><div><GitBranch /><strong>{t("Keep the context.")}</strong><p>{t("Know which rows passed, which failed and why.")}</p></div></Reveal></section>
      <section className="closing-section"><span className="eyebrow">{t("YOUR NEXT CLEAR STEP")}</span><h2>{t("Let your data")}<br /><span>{t("move forward.")}</span></h2><a className="button primary" href="#/import">{t("Start with a sample")}<ArrowUpRight size={18}/></a><p>{t("A local prototype. A real import journey.")}</p></section>
    </main><footer className="landing-footer"><Brand light/><span>{t("Designed for the work between systems.")}</span><ApiDocsLink href="/docs" target="_blank" rel="noreferrer">{t("API documentation")}<ArrowUpRight size={14}/></ApiDocsLink></footer>
  </div>;
}
function Workspace({ page, children }: {
    page: string;
    children: ReactNode;
}) {
    const {user}=useAuth();
    const [showInfo, setShowInfo] = useState(false);
    useEffect(() => {
        if (!showInfo)
            return;
        const previous = document.activeElement as HTMLElement | null;
        const dialog = document.querySelector('.info-modal') as HTMLElement | null;
        dialog?.querySelector<HTMLButtonElement>('button')?.focus();
        const handler = (event: KeyboardEvent) => {
            if (event.key === 'Escape')
                setShowInfo(false);
            if (event.key === 'Tab') {
                const buttons = dialog?.querySelectorAll<HTMLButtonElement>('button');
                if (!buttons?.length)
                    return;
                if (event.shiftKey && document.activeElement === buttons[0]) {
                    event.preventDefault();
                    buttons[buttons.length - 1].focus();
                }
                else if (!event.shiftKey && document.activeElement === buttons[buttons.length - 1]) {
                    event.preventDefault();
                    buttons[0].focus();
                }
            }
        };
        document.addEventListener('keydown', handler);
        return () => { document.removeEventListener('keydown', handler); previous?.focus(); };
    }, [showInfo]);
    return <div className="workspace"><a className="skip-link" href="#workspace-content" onClick={e=>{e.preventDefault();document.getElementById("workspace-content")?.focus();}}>{t("Skip to content")}</a><aside className="sidebar" inert={showInfo}><Brand light/><div className="workspace-switch"><span className="workspace-avatar">N</span><div>Northstar Studio<small>{t("Demo workspace")}</small></div><ChevronDown size={14}/></div><span className="sidebar-label mono">{t("WORKSPACE")}</span><nav aria-label={t("Workspace navigation")}><a href="#/overview" className={page === 'overview' ? 'active' : ''}><LayoutDashboard size={18}/>{t("Overview")}<span className="nav-active-dot"/></a>{user?.role!=='viewer' && <a href="#/import" className={page === 'import' ? 'active' : ''}><Upload size={18}/>{t("Import data")}</a>}{user?.role==='admin' && <a href="#/users" className={page==='users'?'active':''}><ShieldCheck size={18}/>{t("Users")}</a>}{["integrations","deliveries","automations"].map(p=><a key={p} href={`#/${p}`} className={page===p?"active":""}><PlugZap size={18}/>{t(p[0].toUpperCase()+p.slice(1))}</a>)}<ApiDocsLink href="/docs" target="_blank" rel="noreferrer"><Braces size={18}/>{t("API documentation")}<ArrowUpRight size={13}/></ApiDocsLink></nav><div className="sidebar-preview"><PlugZap size={19}/><strong>{t("Connections, considered.")}</strong><p>{t("Webhook and Telegram use durable delivery jobs.")}</p><span className="mono">{t("DURABLE DELIVERY")}<ArrowUpRight size={12}/></span></div><div className="sidebar-bottom"><button onClick={() => setShowInfo(true)}><CircleHelp size={17}/>{t("About this demo")}</button><a href="#/"><ArrowLeft size={17}/>{t("Back to AstraSynq")}</a><div className="user-block"><span>{user?.email.slice(0,2).toUpperCase()}</span><div>{user?.email}<small>{t(user?.role||'')}</small></div></div></div></aside><div className="workspace-main" inert={showInfo}><header className="workspace-top"><div className="breadcrumb">{t("Workspace")}<span>/</span> <strong>{page === 'overview' ? t("Overview") : page==='users'?t("Users") : ['integrations','deliveries','automations'].includes(page)?t(page[0].toUpperCase()+page.slice(1)):t("Import data")}</strong></div><div className="top-right"><LanguageSwitcher /><button className="icon-button" onClick={() => setShowInfo(true)} aria-label={t("Demo information")}><CircleHelp size={18}/></button><ProfileMenu/></div></header><main id="workspace-content" tabIndex={-1} className="workspace-content">{children}</main><footer className="workspace-footer"><span>{t("AstraSynq \u00B7 Local prototype")}</span><span>{t("PostgreSQL \u00B7 durable storage")}</span></footer></div>{showInfo && <div className="modal-backdrop" onClick={() => setShowInfo(false)}><section className="info-modal" role="dialog" aria-modal="true" aria-labelledby="demo-title" onClick={e => e.stopPropagation()}><button className="icon-button modal-close" onClick={() => setShowInfo(false)} aria-label={t("Close demo information")}><X /></button><Sparkles className="teal"/><h2 id="demo-title">{t("A little room to explore.")}</h2><p>{t("This workspace uses synthetic data. Upload, map, validate and save records through the local FastAPI demo.")}</p><p>{t(syntheticDemo?"Mock deliveries finish during commit. No external integrations or persistent worker.":"Records persist in PostgreSQL and are scoped by workspace. Enabled integrations deliver through the worker; receivers deduplicate event IDs.")}</p><Button className="primary" onClick={() => setShowInfo(false)}>{t("Got it")}<Check size={16}/></Button></section></div>}</div>;
}
function Overview() {
    const {user}=useAuth();
    const reduced = useReducedMotion();
    const [data, setData] = useState<Summary | null>(null);
    const [error, setError] = useState('');
    const [query, setQuery] = useState('');
    const [importPage, setImportPage] = useState(1);
    const [importList, setImportList] = useState<{items:Summary['imports'];total:number}>({items:[],total:0});
    const [days, setDays] = useState('14');
    const [exporting, setExporting] = useState(false);
    const [details, setDetails] = useState<string | null>(null);
    const load = () => { setError(''); request<Summary>('/dashboard/summary').then(setData).catch(e => setError(e.message)); };
    useEffect(load, []);
    useEffect(() => { let active=true; request<{items:Summary['imports'];total:number}>(`/imports?page=${importPage}&page_size=6&search=${encodeURIComponent(query)}`).then(result => {if(active)setImportList(result);}).catch(e=>{if(active)setError(e.message);}); return ()=>{active=false;}; }, [query,importPage,data]);
    async function exportData() { setExporting(true); try {
        await download('/leads/export.csv', 'astrasynq_leads.csv');
    }
    catch (e) {
        setError((e as Error).message);
    }
    finally {
        setExporting(false);
    } }
    return <Workspace page="overview"><div className="page-heading"><div><span className="eyebrow dark small">{t("YOUR DATA, IN FOCUS")}</span><h1>{t("Overview")}<span className="heading-period">.</span></h1><p>{t("A little less noise. A clearer picture of your workflows.")}</p></div>{user?.role!=='viewer' && <a className="button primary" href="#/import"><Upload size={16}/>{t("Import data")}</a>}</div>{error && <div className="error-banner" role="alert">{t(error)}<button onClick={load}>{t("Retry")}</button></div>}{!data && !error && <div className="loading-state"><Loader2 className="spin"/>{t("Connecting to your demo workspace\u2026")}</div>}{data && <>
      <div className="metrics-grid">{[{ label: t("Clean records"), value: number(data.record_count), icon: Database, note: t("Unique leads in your workspace"), chip: t("Ready to use") }, { label: t("Completed imports"), value: number(data.import_count), icon: FileSpreadsheet, note: t("Each source, accounted for"), chip: t("All processed") }, { label: t("Data quality"), value: `${number(data.quality)}%`, icon: ShieldCheck, note: t("Valid rows across all imports"), chip: t("Quality signal") }, { label: t("Connections"), value: number(data.integration_count), icon: PlugZap, note: 'Webhook + Telegram', chip: t("Enabled") }].map((m, i) => <Reveal className={`metric-card ${i === 2 ? "metric-quality" : ""}`} key={m.label}><div><span>{m.label}</span><m.icon size={18}/></div><strong>{m.value}</strong><div className="metric-note"><span className={i === 3 ? 'neutral-note' : ''}>{m.chip}</span><small>{m.note}</small></div></Reveal>)}</div>
      <div className="dashboard-charts"><section className="panel volume-panel"><div className="panel-heading"><div><h2>{t("Records over time")}</h2><p>{t("Clean records by creation date")}</p></div><label className="select-shell"><select aria-label={t("Chart date range")} value={days} onChange={e => setDays(e.target.value)}><option value="14">{t("Last 14 days")}</option><option value="7">{t("Last 7 days")}</option></select><ChevronDown size={14}/></label></div><div className="chart-legend"><span className="status-dot"/>{t("Clean records")}<span className="mono">{t("SYNTHETIC DATA")}</span></div><div className="volume-chart"><Suspense fallback={<span role="status">{t('Loading chart…')}</span>}><DashboardChart series={data.series} days={days} reduced={reduced}/></Suspense></div></section><section className="panel quality-panel"><div className="panel-heading"><div><h2>{t("Quality breakdown")}</h2><p>{t("quality.source", { count: number(data.valid + data.invalid + data.duplicate) })}</p></div><ShieldCheck size={18} className="muted"/></div><div className="quality-number"><strong>{number(data.quality)}<span>%</span></strong><p>{t("clean on arrival")}</p></div><div className="quality-stack" aria-label={t("Data quality breakdown")}>{[['valid', data.valid], ['invalid', data.invalid], ['duplicate', data.duplicate]].map(([kind, count]) => <div key={kind} className={String(kind)} style={{ flex: Number(count) }}/>)}</div><div className="quality-legend">{[[t("Valid records"), data.valid, 'valid'], [t("Validation issues"), data.invalid, 'invalid'], [t("Duplicates"), data.duplicate, 'duplicate']].map(([label, count, kind]) => <div key={String(label)}><span className={`legend-dot ${kind}`}/><span>{label}</span><strong>{number(Number(count))}</strong></div>)}</div></section></div>
      <section className="panel imports-panel"><div className="panel-heading"><div><h2>{t("Recent imports")}<span className="count-badge">{data.import_count}</span></h2><p>{t("The story behind your records.")}</p></div><div className="table-actions"><label className="search-box"><Search size={15}/><input aria-label={t("Search imports")} placeholder={t("Search imports\u2026")} value={query} onChange={e => {setQuery(e.target.value);setImportPage(1);}}/></label><button className="button secondary small-button" onClick={exportData} disabled={exporting}><ArrowDownToLine size={15}/>{exporting ? t("Exporting\u2026") : t("Export records")}</button></div></div><div className="table-wrap" role="region" tabIndex={0} aria-label={t("table")}><table><thead><tr><th>{t("Source file")}</th><th>{t("Imported")}</th><th>{t("Rows")}</th><th>{t("Quality")}</th><th>{t("Status")}</th><th><span className="sr-only">{t("Details")}</span></th></tr></thead><tbody>{importList.items.map(i => <tr key={i.id}><td><span className="file-table-icon"><FileSpreadsheet size={16}/></span><strong>{i.filename}</strong></td><td>{formatDate(i.created_at)}</td><td className="mono">{number(i.total)}</td><td><span className="table-quality">{number(Math.round(i.valid / Math.max(1,i.total) * 100))}%<span style={{ width: 52 }}><i style={{ width: `${i.valid / Math.max(1,i.total) * 100}%` }}/></span></span></td><td><Pill><Check size={12}/>{t(i.status === 'completed' ? "Completed" : i.status)}</Pill></td><td><button className="icon-button" aria-label={t("details.for", { file: i.filename })} onClick={() => setDetails(details === i.id ? null : i.id)}><ChevronDown size={15}/></button></td></tr>)}</tbody></table>{!importList.items.length && <div className="empty-state">{t("search.empty", { query })}</div>}</div><div className="wizard-footer"><Button className="secondary" disabled={importPage===1} onClick={()=>setImportPage(p=>p-1)}>{t("Previous page")}</Button><span>{t("Page {page}",{page:number(importPage)})}</span><Button className="secondary" disabled={importPage*6>=importList.total} onClick={()=>setImportPage(p=>p+1)}>{t("Next page")}</Button></div>{details && (() => { const i = importList.items.find(i => i.id === details); return i && <div className="import-inline-detail"><CheckCheck size={18}/><strong>{i.filename}</strong><span>{t("import.details", { valid: number(i.valid), issues: number(i.invalid), duplicates: number(i.duplicate) })}</span><button className="icon-button" onClick={() => setDetails(null)} aria-label={t("Close import details")}><X size={15}/></button></div>; })()}</section>
      <AutomationMetrics/><div className="dashboard-bottom"><div><span className="connection-icon"><PlugZap size={20}/></span><div><h3>{t("The next step is connection.")}</h3><p>{t("Explore the API contract for webhooks, notifications and background jobs.")}</p></div></div><ApiDocsLink href="/docs" target="_blank" rel="noreferrer">{t("View API docs")}<ArrowUpRight size={17}/></ApiDocsLink></div>
    </>}</Workspace>;
}
const fields = ['email', 'name', 'company', 'amount', 'currency', 'created_at', 'external_id'];
function ImportWizard() {
    const reduced = useReducedMotion();
    const [step, setStep] = useState(0);
    const [item, setItem] = useState<ImportResult | null>(null);
    const [mapping, setMapping] = useState<Record<string, string>>({});
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    const [tab, setTab] = useState('all');
    const [inserted, setInserted] = useState(0);
    const [dragging, setDragging] = useState(false);
    const input = useRef<HTMLInputElement>(null);
    const [announcement, setAnnouncement] = useState('');
    useEffect(() => { const id=localStorage.getItem('astrasynq.active-import'); if(!id)return; let active=true; request<ImportResult>(`/imports/${id}`).then(result=>{if(!active)return;setItem(result);setMapping(result.mapping);setInserted(result.inserted);setStep(result.status==='completed'?3:result.status==='analyzed'?2:1);}).catch(e=>{if(active)setError(e.message);});return ()=>{active=false;}; }, []);
    useEffect(() => { window.scrollTo(0, 0); }, [step]);
    async function upload(file: File) { setError(''); if (!file.name.toLowerCase().endsWith('.csv')) {
        setError("Choose a .csv file.");
        return;
    } if (file.size > 5 * 1024 * 1024) {
        setError("Files must be 5 MB or smaller.");
        return;
    } setBusy(true); try {
        const form = new FormData();
        form.append('file', file);
        const result = await request<ImportResult>('/imports', { method: 'POST', body: form });
        setItem(result);
        localStorage.setItem('astrasynq.active-import',result.id);
        setMapping(result.mapping);
        setStep(1);
        setAnnouncement("File uploaded. Map your columns.");
    }
    catch (e) {
        setError((e as Error).message);
    }
    finally {
        setBusy(false);
    } }
    async function sample() { setBusy(true); setError(''); try {
        const response = await fetch('/api/v1/samples/leads.csv');
        if (!response.ok)
            throw new Error("Sample is unavailable. Check that the API is running.");
        await upload(new File([await response.blob()], 'astrasynq_sample.csv', { type: 'text/csv' }));
    }
    catch (e) {
        setError((e as Error).message);
        setBusy(false);
    } }
    async function analyze() { if (!item)
        return; setBusy(true); setError(''); try {
        const actual = Object.fromEntries(Object.entries(mapping).filter(([, v]) => v));
        await request(`/imports/${item.id}/mapping`, { method: 'PUT', body: JSON.stringify({ fields: actual }) });
        const result = await request<ImportResult>(`/imports/${item.id}/analyze`, { method: 'POST' });
        setItem(result);
        setTab('all');
        setStep(2);
        setAnnouncement(t("analysis.done", { count: number(result.valid) }));
    }
    catch (e) {
        setError((e as Error).message);
    }
    finally {
        setBusy(false);
    } }
    async function commit() { if (!item)
        return; setBusy(true); setError(''); try {
        const result = await request<{
            inserted: number;
        }>(`/imports/${item.id}/commit`, { method: 'POST' });
        setInserted(result.inserted);
        setStep(3);
        setAnnouncement("Import complete.");
    }
    catch (e) {
        setError((e as Error).message);
        if((e as Error).message==='workspace_changed')setStep(2);
        const fresh = await request<ImportResult>(`/imports/${item.id}`).catch(() => null);
        if (fresh)
            setItem(fresh);
    }
    finally {
        setBusy(false);
    } }
    const reset = () => { localStorage.removeItem('astrasynq.active-import'); setStep(0); setItem(null); setMapping({}); setError(''); setTab('all'); if (input.current)
        input.current.value = ''; };
    return <Workspace page="import"><div className="page-heading"><div><span className="eyebrow dark small">{t("FROM SOURCE TO SIGNAL")}</span><h1>{t("Import data")}<span className="heading-period">.</span></h1><p>{t("A few considered steps. A cleaner dataset.")}</p></div><a className="text-link dark-link" href="#/overview"><ArrowLeft size={16}/>{t("Back to overview")}</a></div><ol className="wizard-steps">{[t("Upload"), t("Map columns"), t("Review"), t("Complete")].map((label, i) => <li key={label} className={i === step ? 'current' : i < step ? 'done' : ''} aria-current={i === step ? 'step' : undefined}><span>{i < step ? <Check size={15}/> : i + 1}</span><div>{label}<small>{[t("Choose your source"), t("Make the connection"), t("Know what will change"), t("Ready to move forward")][i]}</small></div>{i < 3 && <div className="wizard-step-line"/>}</li>)}</ol><span className="sr-only" aria-live="polite">{announcement}</span>{error && <div className="error-banner" role="alert"><XCircle size={18}/>{t(error)}</div>}
      <AnimatePresence mode="wait"><motion.div key={step} initial={reduced ? false : { opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: reduced ? 0 : .18 }}>
      {step === 0 && <div className="upload-layout"><section className="panel upload-panel"><div className="panel-heading"><div><h2>{t("Start with your source")}</h2><p>{t("Bring your leads into a single, clear workspace.")}</p></div><span className="mono muted">01 / 04</span></div><input ref={input} id="csv-file" aria-label={t("Choose CSV file")} type="file" accept=".csv,text/csv" className="sr-only" onChange={(e: ChangeEvent<HTMLInputElement>) => { const f = e.target.files?.[0]; if (f)
        void upload(f); }}/><div className={`dropzone ${dragging ? 'dragging' : ''}`} onDragOver={e => { e.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={e => { e.preventDefault(); setDragging(false); if (!busy && e.dataTransfer.files[0])
        void upload(e.dataTransfer.files[0]); }}><div className="upload-icon">{busy ? <Loader2 className="spin" size={28}/> : <Upload size={28} strokeWidth={1.4}/>}</div><h3>{busy ? t("Reading your source\u2026") : t("Drop your CSV here")}</h3><p>{t("or choose a file from your device")}</p><Button className="dark-button" onClick={() => input.current?.click()} disabled={busy}>{t("Choose CSV file")}<ArrowUpRight size={16}/></Button><span className="upload-limits">{syntheticDemo?<>5 {t("source rows")} · synthetic-demo.csv</>:t("UTF-8 CSV \u00B7 up to 5 MB \u00B7 10,000 rows")}</span></div><div className="sample-strip"><FileSpreadsheet size={22}/><div><strong>{t("Just exploring?")}</strong><p>{syntheticDemo?<>5 {t("source rows")}</>:t("Try 12 sample rows with a few intentional imperfections.")}</p></div><button disabled={busy} onClick={sample}>{t("Use sample")}<ArrowRight size={16}/></button></div></section><aside className="import-guidance"><span className="eyebrow dark small">{t("A GOOD START")}</span><h2>{t("A little preparation.")}<br />{t("A smoother import.")}</h2><div><span>01</span><section><h3>{t("One header row")}</h3><p>{t("Name your columns so we can connect them to the right fields.")}</p></section></div><div><span>02</span><section><h3>{t("Email is essential")}</h3><p>{t("We use normalized emails to identify unique records.")}</p></section></div><div><span>03</span><section><h3>{t("Keep it simple")}</h3><p>{t("Optional fields: name, company, amount, currency, date and external ID.")}</p></section></div><button className="text-link dark-link" onClick={() => download('/samples/leads.csv', 'astrasynq_sample.csv').catch(e => setError(e.message))}><ArrowDownToLine size={16}/>{t("Download sample CSV")}</button><div className="privacy-note"><ShieldCheck size={18}/><p>{t("Local demo storage.")}<br />{t(syntheticDemo?"Synthetic demo data · sample CSV only · deliveries simulated · login by invitation":"Use sample or non-sensitive data.")}</p></div></aside></div>}
      {step === 1 && item && <section className="panel mapping-panel"><div className="panel-heading"><div><h2>{t("Connect your columns")}</h2><p>{t("Match each destination field to a column in your source.")}</p></div><Pill tone="neutral"><FileSpreadsheet size={13}/>{number(item.total)} {t("source rows")}</Pill></div><div className="file-summary"><FileSpreadsheet size={20}/><strong>{item.filename}</strong><span>{number(item.columns.length)} {t("columns detected")}</span></div><div className="mapping-table"><div className="mapping-head"><span>{t("DESTINATION FIELD")}</span><span>{t("SOURCE COLUMN")}</span><span>{t("VALIDATION")}</span></div>{fields.map(field => <div className="mapping-row" key={field}><label htmlFor={`map-${field}`}><span className="mono">{field}</span>{field === 'email' && <span className="required-label">{t("Required")}</span>}</label><div className="mapping-choice"><ArrowRight size={15}/><select id={`map-${field}`} value={mapping[field] || ''} onChange={e => setMapping({ ...mapping, [field]: e.target.value })}><option value="">{t("Skip this field")}</option>{item.columns.map(c => <option key={c} value={c}>{c}</option>)}</select></div><span className="mapping-rule">{({ email: t("Email format + uniqueness"), amount: t("Non-negative decimal"), currency: t("Supported currency code"), created_at: t("ISO 8601 date"), name: t("Trim whitespace"), company: t("Trim whitespace"), external_id: t("Source identifier") } as Record<string, string>)[field]}</span></div>)}</div><div className="wizard-footer"><Button className="secondary" onClick={reset} disabled={busy}><ArrowLeft size={16}/>{t("Change file")}</Button><span>{t("Email must be mapped. Optional fields may be skipped.")}</span><Button className="primary" onClick={analyze} disabled={busy || !mapping.email}>{busy ? <Loader2 className="spin" size={16}/> : <ShieldCheck size={16}/>}{t("Validate records")}<ArrowRight size={16}/></Button></div></section>}
      {step === 2 && item && <section className="panel review-panel"><div className="panel-heading"><div><h2>{t("A clearer picture of your source")}</h2><p>{t("Only valid, unique records will be added to your workspace.")}</p></div><Pill><CheckCircle2 size={13}/>{t("Analysis complete")}</Pill></div><div className="review-stats">{[[t("Source rows"), item.total, 'neutral'], [t("Ready to import"), item.valid, 'green'], [t("Validation issues"), item.invalid, 'orange'], [t("Duplicates"), item.duplicate, 'purple']].map(([label, count, tone]) => <div className={String(tone)} key={String(label)}><span>{label}</span><strong>{count}</strong></div>)}</div><div className="review-toolbar"><div className="review-tabs" role="group" aria-label={t("Row classifications")}>{[['all', t("All rows"), item.total], ['valid', t("Valid"), item.valid], ['invalid', t("Issues"), item.invalid], ['duplicate', t("Duplicates"), item.duplicate]].map(([value, label, count]) => <button key={String(value)} aria-pressed={tab === value} className={tab === value ? 'active' : ''} onClick={() => setTab(String(value))}>{label}<span>{count}</span></button>)}</div><button className="text-link dark-link" onClick={() => download(`/imports/${item.id}/issues.csv`, 'astrasynq_issues.csv').catch(e => setError(e.message))}><ArrowDownToLine size={15}/>{t("Issues report")}</button></div><div className="table-wrap" role="region" tabIndex={0} aria-label={t("table")}><table className="review-table"><thead><tr><th>{t("Row")}</th><th>Email</th><th>{t("Name")}</th><th>{t("Status")}</th><th>{t("Details")}</th></tr></thead><tbody>{item.rows.filter(r => tab === 'all' || r.classification === tab).slice(0, 100).map(row => <tr key={row.row_number}><td className="mono muted">{row.row_number}</td><td className="mono">{row.data.email || 'вЂ”'}</td><td>{row.data.name || 'вЂ”'}</td><td><Pill tone={row.classification === 'valid' ? 'green' : row.classification === 'invalid' ? 'orange' : 'purple'}>{row.classification === 'valid' ? <Check size={12}/> : <CircleHelp size={12}/>} {row.classification === 'invalid' ? t("Issue") : row.classification === 'valid' ? t("Valid") : t("Duplicate")}</Pill></td><td className="row-issue">{row.issues.length ? row.issues.map(i => t(i.code)).join(' ') : t("Ready to import")}</td></tr>)}</tbody></table>{!item.rows.some(r => tab === 'all' || r.classification === tab) && <div className="empty-state">{t("No rows in this category.")}</div>}</div>{item.total > 100 && <p className="preview-limit">{t("Showing the first 100 matching rows. Download the report for all issues.")}</p>}<div className="review-notice"><ShieldCheck size={22}/><div><strong>{t("review.import", { count: number(item.valid) })} {t("review.skip", { count: number(item.invalid + item.duplicate) })}</strong><p>{t("review.issues", { issues: number(item.invalid), duplicates: number(item.duplicate) })}</p></div></div><div className="wizard-footer"><Button className="secondary" disabled={busy} onClick={() => setStep(1)}><ArrowLeft size={16}/>{t("Back to mapping")}</Button><span>{t("Save to this temporary demo workspace.")}</span><Button className="primary" onClick={commit} disabled={busy || item.valid === 0}>{busy ? <Loader2 className="spin" size={16}/> : <Database size={16}/>}{t("import.action", { count: number(item.valid) })}<ArrowRight size={16}/></Button></div></section>}
      {step === 3 && item && <section className="panel complete-panel"><div className="complete-icon"><CheckCheck size={34}/></div><span className="eyebrow dark small">{t("A CLEAR STEP FORWARD")}</span><h2>{t("Your data is ready.")}</h2><p><strong>{t("complete.result", { count: number(inserted) })}</strong><br />{t("complete.skip", { issues: number(item.invalid), duplicates: number(item.duplicate) })}</p><div className="completion-summary"><div><FileSpreadsheet size={18}/><span>{item.filename}</span><Pill><Check size={12}/>{t("Completed")}</Pill></div><div><Database size={18}/><span>{t("Workspace updated")}</span><CheckCircle2 size={17} className="teal"/></div><div><Bell size={18}/><span>{t("Notifications")}</span><Pill tone="neutral">{t("Durable outbox")}</Pill></div></div><div className="complete-actions"><a className="button primary" href="#/overview">{t("View overview")}<ArrowUpRight size={17}/></a><Button className="secondary" onClick={reset}><Upload size={16}/>{t("Import another file")}</Button></div><span className="completion-note">{t("Import persisted. Delivery status is available in Deliveries.")}</span></section>}
      </motion.div></AnimatePresence>
    </Workspace>;
}
function routeFromHash() { const hash = window.location.hash; return hash.startsWith('#/') ? hash.slice(2).split('?')[0] : ''; }
function AuthRoutes({route}:{route:string}){const {user}=useAuth();if(!route)return <Landing/>;if(!user)return <LoginScreen expired={route!=='login'}/>;if(['integrations','deliveries','automations'].includes(route))return <Workspace page={route}>{route==='integrations'?<IntegrationsScreen/>:route==='deliveries'?<DeliveriesScreen/>:<><AutomationsScreen/>{syntheticDemo&&<DemoAudit/>}</>}</Workspace>;if(route==='users')return <Workspace page="users">{user.role==='admin'?<UsersScreen/>:<Forbidden/>}</Workspace>;if(route==='import')return user.role==='viewer'?<Workspace page="import"><Forbidden/></Workspace>:<ImportWizard/>;return <Overview/>;}
export function App(){useLanguage();const [route,setRoute]=useState(routeFromHash);useEffect(()=>{const listener=()=>{const next=routeFromHash();setRoute(previous=>{if(previous!==next)window.scrollTo(0,0);return next;});};window.addEventListener('hashchange',listener);return()=>window.removeEventListener('hashchange',listener);},[]);return <MotionConfig reducedMotion="user"><AuthProvider><AuthRoutes route={route}/></AuthProvider></MotionConfig>;}
