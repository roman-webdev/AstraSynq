import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import {t,formatChartDate,formatNumber} from './i18n';
import type {Summary} from './api';
export default function DashboardChart({series,days,reduced}:{series:Summary['series'];days:string;reduced:boolean|null}){
 return <ResponsiveContainer width="100%" height="100%"><AreaChart data={series.slice(-Number(days)).map(point=>({...point,label:formatChartDate(point.date)}))} margin={{top:10,right:5,left:-28,bottom:0}}><CartesianGrid stroke="#e8ecef" vertical={false}/><XAxis dataKey="label" axisLine={false} tickLine={false} tick={{fontSize:10,fill:'#79848c'}} minTickGap={25}/><YAxis tickFormatter={formatNumber} axisLine={false} tickLine={false} tick={{fontSize:10,fill:'#79848c'}} allowDecimals={false}/><Tooltip formatter={value=>formatNumber(Number(value??0))} contentStyle={{borderRadius:10,border:'1px solid #dce5e3',fontSize:12}}/><Area type="monotone" dataKey="records" name={t('Clean records')} stroke="#199986" fill="#e5f3ee" strokeWidth={2.5} isAnimationActive={!reduced} animationDuration={650}/></AreaChart></ResponsiveContainer>;
}
