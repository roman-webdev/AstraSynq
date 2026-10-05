import {spawn} from 'node:child_process';
const [mode,...args]=process.argv.slice(2);
const env={...process.env,ASTRASYNQ_PREVIEW_URL:'http://127.0.0.1:4191',ASTRASYNQ_QA_OUTPUT:'../previews/performance-gate/regression',ASTRASYNQ_IMMERSIVE_OUTPUT:'../previews/performance-gate'};
if(mode==='baseline'){env.ASTRA_GATE_URL='http://127.0.0.1:4192';env.ASTRA_GATE_OUTPUT='../work/immersive/gate-baseline-final.json';}
if(mode==='after')env.ASTRA_GATE_OUTPUT='../work/immersive/gate-after-final.json';
if(mode==='ablation'){env.ASTRA_ABLATIONS='1';env.ASTRA_GATE_OUTPUT='../work/immersive/gate-ablation.json';}
if(['baseline','after'].includes(mode)&&args[0])env.ASTRA_GATE_OUTPUT=`../work/immersive/gate-${mode}-${args[0]}.json`;
const command=mode==='app'?['--test','tests/i18n.e2e.mjs']:mode==='visual'?['--test','tests/immersive.e2e.mjs']:mode==='new'?['--test','tests/performance-gate.e2e.mjs']:['scripts/performance-gate.mjs'];
const child=spawn(process.execPath,[...command,...args],{env,stdio:'inherit'});child.on('exit',code=>process.exitCode=code);
