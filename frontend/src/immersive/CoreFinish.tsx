import {presets,type Quality} from './quality';
import {coreCost} from './telemetry';
import { useFrame, useThree } from '@react-three/fiber';
import { useEffect, useMemo, type MutableRefObject } from 'react';
import * as THREE from 'three';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { ShaderPass } from 'three/examples/jsm/postprocessing/ShaderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/examples/jsm/postprocessing/OutputPass.js';
import type {CoreMotion} from './motion';
const boardBokeh=/* glsl */`
#include <common>
#include <packing>
varying vec2 vUv;
uniform sampler2D tColor;uniform sampler2D tDepth;
uniform float nearClip;uniform float farClip;uniform float focus;uniform float focusBand;uniform float aperture;uniform float maxblur;uniform float aspect;
void main(){
 vec4 center=texture2D(tColor,vUv);float depth=texture2D(tDepth,vUv).r;float viewZ=perspectiveDepthToViewZ(depth,nearClip,farClip);
 float radius=min(max(abs(focus+viewZ)-focusBand,0.)*aperture,maxblur);if(radius<maxblur*.04){gl_FragColor=center;return;}
 vec2 circle=vec2(radius,radius*aspect);vec4 color=center*2.;
 for(int i=0;i<4;i++){float a=float(i)*1.57079633;color+=texture2D(tColor,vUv+vec2(cos(a),sin(a))*circle);}gl_FragColor=color/6.;
}`;
function ComposedFinish({mobile,motion,quality='balanced'}:{quality?:Quality;mobile:boolean;motion:MutableRefObject<CoreMotion>}){
 const {gl,scene,camera,size}=useThree();
 const finish=useMemo(()=>{
  const target=new THREE.WebGLRenderTarget(1,1,{type:THREE.HalfFloatType,depthBuffer:true});
  target.depthTexture=new THREE.DepthTexture(1,1,THREE.UnsignedShortType);
  const composer=new EffectComposer(gl,target),render=new RenderPass(scene,camera);
  const lens=mobile?null:new ShaderPass({
   uniforms:{tColor:{value:null},tDepth:{value:null},nearClip:{value:(camera as THREE.PerspectiveCamera).near},farClip:{value:(camera as THREE.PerspectiveCamera).far},focus:{value:12.25},focusBand:{value:1.4},aperture:{value:.0006},maxblur:{value:.002},aspect:{value:1}},
   vertexShader:'varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',fragmentShader:boardBokeh
  },'tColor');
  const bloom=new UnrealBloomPass(new THREE.Vector2(1,1),mobile?.32:.42,.27,1.12),output=new OutputPass();composer.addPass(render);if(lens)composer.addPass(lens);composer.addPass(bloom);composer.addPass(output);
  return {composer,bloom,lens,output,pixelRatio:gl.getPixelRatio(),corner:new THREE.Vector3(),drawingSize:new THREE.Vector2(),coreMatrix:new THREE.Matrix4(),lastProgress:0,movingUntil:0,diagnosticTime:0};
 },[gl,scene,camera,mobile]);
 useEffect(()=>{finish.composer.setPixelRatio(gl.getPixelRatio());finish.composer.setSize(size.width,size.height);finish.bloom.setSize(size.width*gl.getPixelRatio()*.5,size.height*gl.getPixelRatio()*.5);},[finish,gl,size]);
 useEffect(()=>()=>{finish.lens?.dispose();finish.bloom.dispose();finish.output.dispose();finish.composer.dispose();},[finish]);
 useFrame(()=>{if(scene.userData.corePrepared!==true)return;const now=performance.now();if(Math.abs(motion.current.progress-finish.lastProgress)>.00008){finish.movingUntil=now+200;finish.lastProgress=motion.current.progress;}const moving=now<finish.movingUntil;if(finish.pixelRatio!==gl.getPixelRatio()){finish.pixelRatio=gl.getPixelRatio();finish.composer.setPixelRatio(finish.pixelRatio);finish.bloom.setSize(size.width*finish.pixelRatio*.5,size.height*finish.pixelRatio*.5);}
 if(finish.lens){finish.lens.enabled=presets[quality].lens&&!moving&&finish.pixelRatio>1.25;const core=scene.getObjectByName('astra-core-package'),u=finish.lens.uniforms!;if(core){finish.coreMatrix.multiplyMatrices(camera.matrixWorldInverse,core.matrixWorld);let near=Infinity,far=-Infinity;for(let i=0;i<8;i++){finish.corner.set(i&1?1.52:-1.52,i&2?1.52:-1.52,i&4?.36:0).applyMatrix4(finish.coreMatrix);near=Math.min(near,-finish.corner.z);far=Math.max(far,-finish.corner.z);}if(Number.isFinite(near)&&Number.isFinite(far)){u.focus.value=(near+far)*.5;u.focusBand.value=(far-near)*.5+.16;}}u.tDepth.value=finish.composer.readBuffer.depthTexture;u.aspect.value=size.width/size.height;gl.getDrawingBufferSize(finish.drawingSize);u.maxblur.value=7/finish.drawingSize.x;u.aperture.value=u.maxblur.value/2.6;gl.domElement.dataset.depthOfField=finish.lens.enabled?'board-only':'off';gl.domElement.dataset.focusDepth=Number(u.focus.value).toFixed(3);}else gl.domElement.dataset.depthOfField='off';
 gl.info.autoReset=false;gl.info.reset();const renderStart=performance.now();const post=window.__ASTRA_PROFILE__?.post??presets[quality].post;gl.domElement.dataset.postprocessing=post?'bloom':'off';if(post)finish.composer.render();else{gl.setRenderTarget(null);gl.render(scene,camera);}coreCost('renderSubmit',renderStart);if(now-finish.diagnosticTime>100){finish.diagnosticTime=now;gl.domElement.dataset.drawCalls=String(gl.info.render.calls);gl.domElement.dataset.triangles=String(gl.info.render.triangles);gl.domElement.dataset.scrollQuality=moving?'motion':'detail';}
 },1);return null;
}

function PlainFinish(){const {gl,scene,camera}=useThree();useFrame(()=>{if(!scene.userData.corePrepared)return;const start=performance.now();gl.info.autoReset=false;gl.info.reset();gl.setRenderTarget(null);gl.render(scene,camera);coreCost('renderSubmit',start);Object.assign(gl.domElement.dataset,{postprocessing:'off',depthOfField:'off',drawCalls:String(gl.info.render.calls),triangles:String(gl.info.render.triangles)});},1);return null;}
export function CoreFinish(props:{mobile:boolean;motion:MutableRefObject<CoreMotion>;quality?:Quality}){const post=window.__ASTRA_PROFILE__?.post??presets[props.quality||'balanced'].post;return post?<ComposedFinish {...props}/>:<PlainFinish/>;}
