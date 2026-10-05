import { useMemo } from 'react';
/** Original vector circuit environment. Never downloads reference imagery. */
export function BoardAtmosphere({active,mobile}:{active:boolean;mobile:boolean}) {
  const paths=useMemo(()=>Array.from({length:mobile?24:56},(_,i)=>{
    const side=i%4,lane=Math.floor(i/4),spacing=mobile?32:19;
    const x=1060+(lane-6)*spacing,y=450+(lane-6)*spacing;
    if(side===0)return `M ${x} 350 V ${190+lane*7} L ${x-120} ${70+lane*7} V -80`;
    if(side===1)return `M 1180 ${y} H ${1330+lane*8} L ${1450+lane*8} ${y+120} H 1800`;
    if(side===2)return `M ${x} 550 V ${650+lane*6} L ${x+130} ${780+lane*6} V 1060`;
    return `M 940 ${y} H ${750-lane*12} L ${620-lane*12} ${y-130} H -150`;
  }),[mobile]);
  return <div className="board-atmosphere" aria-hidden="true" data-active={active}>
    <div className="board-field">
      <svg className="board-perspective" viewBox="0 0 1600 900" preserveAspectRatio="xMidYMid slice">
        <defs>
          <linearGradient id="board-trace-color"><stop stopColor="#ed409b"/><stop offset=".55" stopColor="#7765ea"/><stop offset="1" stopColor="#569eff"/></linearGradient>
          <pattern id="board-cells" width="180" height="180" patternUnits="userSpaceOnUse">
            <path d="M 0 30 H 58 L 88 60 V 180 M 0 39 H 49 L 79 69 V 180 M 180 95 H 140 L 105 130 V 180 M 180 104 H 149 L 114 139 V 180 M 0 140 H 25 L 48 163 V 180" fill="none" stroke="#537cb0" strokeWidth=".8" opacity=".25"/>
            <rect x="112" y="23" width="37" height="21" rx="3" fill="#132a3d" stroke="#376478" strokeWidth=".7"/>
            <path d="M 116 29 H 143 M 116 35 H 136" stroke="#40647b" strokeWidth=".8"/>
            <circle cx="58" cy="30" r="2.4" fill="#7cb5c6" opacity=".4"/><circle cx="140" cy="95" r="2" fill="#837dbc" opacity=".4"/>
          </pattern>
        </defs>
        
        <g className="board-routing" fill="none" stroke="url(#board-trace-color)">{paths.map((d,i)=><path key={i} d={d} strokeWidth={i%7===0?4:1} opacity={i%7===0?.75:.28}/>)}</g>
        <g className="board-waves" fill="none" stroke="#8cd4ff" strokeWidth="2" strokeLinecap="round" strokeDasharray="40 620">{paths.filter((_,i)=>i%(mobile?8:5)===0).map((d,i)=><path key={i} d={d} style={{animationDelay:`${-i*.8}s`}}/>)}</g>
      </svg>
      <div className="board-iridescence"/><div className="board-depth"/>
    </div>
  </div>;
}
