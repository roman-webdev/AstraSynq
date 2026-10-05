import {spawn} from 'node:child_process';
for(let run=1;run<=3;run++)for(const mode of ['baseline','after']){
 console.log(`Run ${run}: ${mode}`);
 await new Promise((resolve,reject)=>{const child=spawn(process.execPath,['scripts/run-gate.mjs',mode,String(run)],{stdio:'inherit'});child.on('exit',code=>code===0?resolve():reject(new Error(`${mode} failed ${code}`)));});
}
