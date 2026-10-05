import * as THREE from 'three';

/** A physical trace whose energy packet travels along its actual route UV. */
export function circuitMaterial(color: string, emission: string, time: {value:number}, energy: {value:number}, speed=.12) {
  const material=new THREE.MeshStandardMaterial({color, emissive:emission, emissiveIntensity:4, metalness:.7, roughness:.26});
  material.onBeforeCompile=shader=>{
    shader.uniforms.coreTime=time;shader.uniforms.coreEnergy=energy;shader.uniforms.coreSpeed={value:speed};
    shader.vertexShader='attribute float tracePhase; varying float vRoute; varying float vPhase;\n'+shader.vertexShader;
    shader.vertexShader=shader.vertexShader.replace('#include <uv_vertex>','#include <uv_vertex>\nvRoute=uv.x;vPhase=tracePhase;');
    shader.fragmentShader='uniform float coreTime; uniform float coreEnergy; uniform float coreSpeed; varying float vRoute; varying float vPhase;\n'+shader.fragmentShader;
    shader.fragmentShader=shader.fragmentShader.replace('#include <emissivemap_fragment>',`#include <emissivemap_fragment>
      float travel=fract(vRoute-coreTime*coreSpeed+vPhase);
      float pulse=smoothstep(.88,.97,travel)*(1.-smoothstep(.98,1.,travel));
      float wave=.18+.055*sin(vRoute*9.+coreTime*.6+vPhase*6.);
      totalEmissiveRadiance *= wave + pulse*coreEnergy;
    `);
  };
  material.customProgramCacheKey=()=> 'astra-physical-circuit-v1';
  return material;
}

