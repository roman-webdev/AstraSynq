import { useRef } from 'react';
import { motion, useReducedMotion, useScroll, useTransform } from 'motion/react';
import { ArrowRight, CheckCircle2, Database, FileSpreadsheet } from 'lucide-react';
import { t, formatNumber } from './i18n';
export function DataStory() {
  const ref = useRef<HTMLElement>(null);
  const reduced = useReducedMotion();
  const { scrollYProgress } = useScroll({target:ref,offset:['start 85%','end 45%']});
  const rawOpacity = useTransform(scrollYProgress,[0,.55],[1,.45]);
  const cleanOpacity = useTransform(scrollYProgress,[.2,.8],[.35,1]);
  const cleanScale = useTransform(scrollYProgress,[.2,.8],[.94,1]);
  const splitOffset = useTransform(scrollYProgress,[0,.5],[25,0]);
  return <section ref={ref} className="story-section">
    <span className="eyebrow dark">CSV → AstraSynq</span>
    <h2>{t('story.raw')}<br/><span>{t('story.clean')}</span></h2>
    <div className="story-flow">
      <div className="story-source"><FileSpreadsheet/><strong>CSV</strong><motion.div className="raw-lines" style={{opacity:reduced?1:rawOpacity}}>{Array.from({length:12},(_,i)=><span key={i}/>)}</motion.div><small>{t('12 source records')}</small></div>
      <ArrowRight className="story-arrow" aria-hidden="true"/>
      <motion.div className="story-split" style={{x:reduced?0:splitOffset}}>{[['Valid',8,'green'],['Issues',2,'orange'],['Duplicates',2,'purple']].map(([label,count,tone])=><div className={'story-lane '+tone} key={label}><strong>{t(String(label))}</strong><span>{formatNumber(Number(count))}</span></div>)}</motion.div>
      <ArrowRight className="story-arrow" aria-hidden="true"/>
      <motion.div className="story-output" style={{opacity:reduced?1:cleanOpacity,scale:reduced?1:cleanScale}}><Database/><strong>{t('story.dataset')}</strong><span>{t('8 records ready')}</span><div className="clean-lines" aria-hidden="true">{Array.from({length:8},(_,i)=><span key={i}/>)}</div><CheckCircle2/></motion.div>
    </div>
  </section>;
}
