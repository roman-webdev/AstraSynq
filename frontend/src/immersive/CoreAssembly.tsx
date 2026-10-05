import {presets} from './quality';
import {coreMark,coreCost,coreCommit} from './telemetry';
import { useFrame, useLoader, useThree } from '@react-three/fiber';
import { useEffect, useMemo, useRef } from 'react';
import * as THREE from 'three';
import { RectAreaLightUniformsLib } from 'three/examples/jsm/lights/RectAreaLightUniformsLib.js';
import { BlenderModelLoader } from './BlenderModelLoader';
import { StudioEnvironmentLoader } from './StudioEnvironment';
import { BoardGeometryLoader, createRouteCurves } from './BoardGeometryLoader';
import { circuitMaterial } from './CircuitMaterial';
import type { SceneProps } from './CoreScene';

RectAreaLightUniformsLib.init();

export function CoreAssembly({motion,mobile,onReady,onFailure,quality='balanced'}:Pick<SceneProps,'motion'|'mobile'|'onReady'|'onFailure'|'quality'>){
 useEffect(()=>{coreCommit('assemblyCommit');});
 const gltf=useLoader(BlenderModelLoader,'/visuals/astra-core.model.bin');
 const model=useMemo(()=>{
  const assembly=gltf.scene.clone(true),surface=assembly.getObjectByName('Astra_board_surface')!,core=assembly.getObjectByName('Astra_chip')!,details=assembly.getObjectByName('Astra_board_details')!;
  const cloned=new Map<THREE.Material,THREE.Material>();
  assembly.traverse(o=>{if(o instanceof THREE.Mesh){o.castShadow=o!==surface;o.receiveShadow=true;o.raycast=()=>{};const clone=(m:THREE.Material)=>{if(!cloned.has(m))cloned.set(m,window.__ASTRA_PROFILE__?.materials===false?new THREE.MeshBasicMaterial({color:(m as THREE.MeshStandardMaterial).color,map:(m as THREE.MeshStandardMaterial).map}):m.clone());return cloned.get(m)!;};o.material=Array.isArray(o.material)?o.material.map(clone):clone(o.material);}});
  const find=(name:string)=>[...cloned.values()].find(m=>m.name===name) as THREE.MeshStandardMaterial|undefined;
  return {surface,core,details,materials:cloned,rim:find('Astra luminous skirt'),window:find('Astra window light'),die:find('Astra exposed silicon'),normalMaps:[...cloned.values()].filter(m=>m instanceof THREE.MeshStandardMaterial&&m.normalMap).length};
 },[gltf]);
 useEffect(()=>()=>{model.materials.forEach(m=>m.dispose());},[model]);
 const shadowTarget=useMemo(()=>new THREE.Object3D(),[]);
 const environment=useLoader(StudioEnvironmentLoader,'/visuals/astra-studio.bin');
 const {gl,camera,size,scene,viewport,invalidate}=useThree();
 const root=useRef<THREE.Group>(null),chip=useRef<THREE.Group>(null),packets=useRef<THREE.Points>(null),hover=useRef(0),pointer=useRef(new THREE.Vector2()),elapsed=useRef(0),frames=useRef(0),diagnosticTime=useRef(-1),lastAnchor=useRef(new THREE.Vector2(Infinity,Infinity)),ready=useRef(false),warmed=useRef(false);
 const key=useRef<THREE.RectAreaLight>(null),glint=useRef<THREE.RectAreaLight>(null);
 const shadowLight=useRef<THREE.DirectionalLight>(null),shadowScale=useRef(0);
 useEffect(()=>{const previous=gl.shadowMap.autoUpdate;gl.shadowMap.autoUpdate=false;gl.shadowMap.needsUpdate=true;return()=>{gl.shadowMap.autoUpdate=previous;gl.shadowMap.needsUpdate=true;};},[gl,model]);
 const time=useMemo(()=>({value:0}),[]),energy=useMemo(()=>({value:1}),[]);
 const geometry=useLoader(BoardGeometryLoader,`/visuals/astra-board-${mobile?'mobile':'desktop'}.bin`);
 const board=useMemo(()=>({...geometry,curves:createRouteCurves(mobile)}),[geometry,mobile]);
 const paths=useMemo(()=>board.curves.map(curve=>Float32Array.from(curve.getSpacedPoints(128).flatMap(v=>[v.x,v.y,v.z]))),[board]);
 const materials=useMemo(()=>({blue:circuitMaterial('#153d7c','#218bff',time,energy),gold:circuitMaterial('#887254','#ffd38e',time,energy,.095),pink:circuitMaterial('#612745','#ed498e',time,energy,.1)}),[time,energy]);
 const assets=useMemo(()=>{
  const spriteCanvas=document.createElement('canvas');spriteCanvas.width=spriteCanvas.height=64;const ctx=spriteCanvas.getContext('2d')!,g=ctx.createRadialGradient(32,32,0,32,32,32);g.addColorStop(0,'white');g.addColorStop(.15,'#a8d6ff');g.addColorStop(1,'rgba(75,134,255,0)');ctx.fillStyle=g;ctx.fillRect(0,0,64,64);const sprite=new THREE.CanvasTexture(spriteCanvas);
  return {sprite,positions:new Float32Array(board.curves.length*6)};
 },[gl,board.curves.length]);
 useEffect(()=>{scene.environment=environment;scene.environmentIntensity=.12;return()=>{scene.environment=null;};},[environment,scene]);
 useEffect(()=>{
  let cancelled=false,released=false;warmed.current=false;scene.userData.corePrepared=false;
  // Compile against the same linear HDR target used by the compositor. The
  // default canvas target would warm a different tone-mapping shader variant.
  const target=new THREE.WebGLRenderTarget(1,1,{type:THREE.HalfFloatType,depthBuffer:true}),previous=gl.getRenderTarget();
  const release=()=>{if(!released){released=true;target.dispose();}};
  let pending:Promise<THREE.Object3D>|undefined;
  coreMark('shader-start');try{gl.setRenderTarget((window.__ASTRA_PROFILE__?.post??presets[quality].post)?target:null);pending=gl.compileAsync(scene,camera);}catch{onFailure();}finally{gl.setRenderTarget(previous);}
  pending?.then(()=>{if(cancelled)return;coreMark('shader-end');warmed.current=true;scene.userData.corePrepared=true;invalidate();}).catch(()=>{if(!cancelled)onFailure();}).finally(release);
  return()=>{cancelled=true;release();};
 },[gl,scene,camera,environment,board,model,invalidate,onFailure]);

 
 useEffect(()=>()=>{Object.values(assets).forEach(v=>{if(v instanceof THREE.BufferGeometry||v instanceof THREE.Texture)v.dispose();});},[assets]);
 useEffect(()=>()=>Object.values(materials).forEach(m=>m.dispose()),[materials]);
 useEffect(()=>{const canvas=gl.domElement;const move=(e:PointerEvent)=>{if(e.pointerType!=='mouse')return;const b=canvas.getBoundingClientRect();motion.current.pointerX=(e.clientX-b.left)/b.width*2-1;motion.current.pointerY=1-(e.clientY-b.top)/b.height*2;};const leave=()=>{motion.current.pointerX=0;motion.current.pointerY=0;motion.current.hover=0;};canvas.addEventListener('pointermove',move);canvas.addEventListener('pointerleave',leave);return()=>{canvas.removeEventListener('pointermove',move);canvas.removeEventListener('pointerleave',leave);};},[gl,motion]);
 // Safari touch path: raycast only the processor; leave vertical gestures native.
 useEffect(()=>{
  const canvas=gl.domElement,ray=new THREE.Raycaster(),point=new THREE.Vector2();
  let gesture:{id:number;x:number;y:number;axis:'pending'|'scroll'|'drag'}|null=null;
  const start=(e:TouchEvent)=>{
   if(e.touches.length!==1||motion.current.paused||!chip.current){gesture=null;return;}
   const t=e.touches[0],b=canvas.getBoundingClientRect();
   point.set((t.clientX-b.left)/b.width*2-1,1-(t.clientY-b.top)/b.height*2);
   ray.setFromCamera(point,camera);
   if(!ray.intersectObject(chip.current,true).length)return;
   gesture={id:t.identifier,x:t.clientX,y:t.clientY,axis:'pending'};
  };
  const move=(e:TouchEvent)=>{
   if(!gesture)return;
   if(e.touches.length!==1){end();return;}
   const t=Array.from(e.touches).find(t=>t.identifier===gesture!.id);if(!t)return;
   const dx=t.clientX-gesture.x,dy=t.clientY-gesture.y;
   if(gesture.axis==='pending'&&Math.hypot(dx,dy)>=8)gesture.axis=Math.abs(dx)>Math.abs(dy)*1.25?'drag':'scroll';
   if(gesture.axis!=='drag')return;
   if(!e.cancelable){end();return;}e.preventDefault();
   motion.current.dragX=THREE.MathUtils.clamp(dx/160,-.35,.35);
   motion.current.dragY=THREE.MathUtils.clamp(dy/200,-.18,.18);
   motion.current.hover=1;
  };
  const end=()=>{gesture=null;motion.current.dragX=0;motion.current.dragY=0;motion.current.hover=0;};
  canvas.addEventListener('touchstart',start,{passive:true});canvas.addEventListener('touchmove',move,{passive:false});
  canvas.addEventListener('touchend',end);canvas.addEventListener('touchcancel',end);window.addEventListener('orientationchange',end);
  return()=>{end();canvas.removeEventListener('touchstart',start);canvas.removeEventListener('touchmove',move);canvas.removeEventListener('touchend',end);canvas.removeEventListener('touchcancel',end);window.removeEventListener('orientationchange',end);};
 },[gl,camera,motion]);
 const drag=useRef(new THREE.Vector2());
 const stations=useMemo(()=>{
  const positions:number[]=[],colors:number[]=[],v=new THREE.Vector3();board.curves.forEach((curve,i)=>{for(let k=1;k<=7;k++){curve.getPointAt(k*.067,v);positions.push(v.x,v.y,.036);const c=new THREE.Color(i%11===7?'#f787ad':i%3===0?'#ffdd9b':'#b7d9ff').multiplyScalar(2);colors.push(c.r,c.g,c.b);}});return {positions:new Float32Array(positions),colors:new Float32Array(colors)};
 },[board]);
 const localCorners=useMemo(()=>[new THREE.Vector3(-1.43,-1.43,.33),new THREE.Vector3(1.43,-1.43,.33),new THREE.Vector3(1.43,1.43,.33),new THREE.Vector3(-1.43,1.43,.33)],[]),projectedCorners=useMemo(()=>localCorners.map(v=>v.clone()),[localCorners]);
 const point=useMemo(()=>new THREE.Vector3(),[]),center=useMemo(()=>new THREE.Vector3(),[]),anchor=useMemo(()=>new THREE.Vector3(),[]);
 useFrame((_,delta)=>{
  const updateStart=performance.now();if(!root.current||!chip.current)return;if(window.__ASTRA_PROFILE__?.updates===false&&ready.current)return;const dt=Math.min(delta,.05),p=motion.current.progress;if(!motion.current.paused)elapsed.current+=dt;const t=elapsed.current;
  pointer.current.x=THREE.MathUtils.damp(pointer.current.x,motion.current.pointerX,4,dt);pointer.current.y=THREE.MathUtils.damp(pointer.current.y,motion.current.pointerY,4,dt);hover.current=THREE.MathUtils.damp(hover.current,motion.current.hover,5,dt);
  drag.current.x=THREE.MathUtils.damp(drag.current.x,motion.current.dragX??0,10,dt);drag.current.y=THREE.MathUtils.damp(drag.current.y,motion.current.dragY??0,10,dt);
  root.current.rotation.set(-1.03+.065*Math.sin(p*Math.PI*2)+pointer.current.y*.015+drag.current.y,.035*Math.sin(p*Math.PI*2)+drag.current.x,-.16+p*.5+pointer.current.x*.015);
  root.current.position.set(mobile?0:viewport.width*.22,mobile?.05:.15,-.25);root.current.scale.setScalar(mobile?1.5:Math.min(1.56,viewport.width*.16));
  time.value=t;energy.value=1+hover.current*.7;
  if(model.rim)model.rim.emissiveIntensity=2.8+.22*Math.sin(t*.65)+hover.current*.4;
  if(model.window)model.window.emissiveIntensity=2.2+.16*Math.sin(t*.9)+hover.current*.4;
  if(model.die)model.die.emissiveIntensity=.3+.07*Math.sin(t*.8)+hover.current*.3;
  if(key.current)key.current.intensity=7+.5*Math.sin(t*.55)+hover.current;
  if(glint.current){glint.current.position.set(Math.sin(t*.35)*1.4+pointer.current.x*.7,1.6,3);glint.current.intensity=.15+hover.current*1.5;}
  if(window.__ASTRA_PROFILE__?.particles!==false)paths.forEach((path,i)=>{for(let n=0;n<2;n++){const phase=(t*(.07+hover.current*.025)+i*.037+n*.5)%1,u=phase*128,j=Math.floor(u),a=u-j,offset=(i*2+n)*3;for(let axis=0;axis<3;axis++)assets.positions[offset+axis]=path[j*3+axis]*(1-a)+path[(j+1)*3+axis]*a+(axis===2?.018:0);}});
  if(packets.current)packets.current.geometry.setDrawRange(0,board.curves.length*presets[quality].packets);

  if(packets.current)packets.current.geometry.getAttribute('position').needsUpdate=true;
  root.current.updateMatrixWorld();chip.current.localToWorld(center.set(0,0,.25)).project(camera);
  // All casters and the light belong to one rigid assembly. Its shadow projection
  // stays identical in local coordinates, so retain the depth texture and only
  // transform its camera/matrix. Re-render when viewport scale changes.
  if(shadowLight.current){const light=shadowLight.current;light.shadow.camera.up.set(0,1,0).applyQuaternion(root.current.quaternion);light.shadow.updateMatrices(light);if(shadowScale.current!==root.current.scale.x){shadowScale.current=root.current.scale.x;gl.shadowMap.needsUpdate=true;}}
  const corners=projectedCorners;for(let i=0;i<4;i++)chip.current.localToWorld(corners[i].copy(localCorners[i])).project(camera);
  frames.current++;
  if(t-diagnosticTime.current>.1||!ready.current){diagnosticTime.current=t;
  const pose=root.current.rotation.toArray().slice(0,3).map(n=>Number(n).toFixed(3)).join(',');
  gl.domElement.dataset.normalMapCount=String(model.normalMaps);
  gl.domElement.dataset.shadowMode='rigid-cached';gl.domElement.dataset.coreGlow=String(model.die?.emissiveIntensity||0);
  Object.assign(gl.domElement.dataset,{chipX:String((center.x*.5+.5)*size.width),chipY:String((.5-center.y*.5)*size.height),chipLeft:String(Math.min(...corners.map(v=>(v.x*.5+.5)*size.width))),chipRight:String(Math.max(...corners.map(v=>(v.x*.5+.5)*size.width))),touchDrag:drag.current.x.toFixed(3),chipTop:String(Math.min(...corners.map(v=>(.5-v.y*.5)*size.height))),chipBottom:String(Math.max(...corners.map(v=>(.5-v.y*.5)*size.height))),pose,assemblyPose:pose,chipLocalPose:'0,0,0',boardLocalPose:'0,0,0',rotationProgress:p.toFixed(4),hover:hover.current.toFixed(3),boardPointer:pointer.current.x.toFixed(3),pulseTime:t.toFixed(3),frameCount:String(frames.current),drawCalls:String(gl.info.render.calls),triangles:String(gl.info.render.triangles),dpr:String(gl.getPixelRatio()),sceneRevision:'blender-physical',assetSource:'blender-5.2',materialDetails:'baked-normal-roughness',routeCount:String(board.curves.length)});
  }
  chip.current.localToWorld(anchor.set(0,1.4,.33)).project(camera);const x=Math.min(88,Math.max(55,(anchor.x*.5+.5)*100)),y=Math.max(20,(.5-anchor.y*.5)*100);
  if(Math.abs(x-lastAnchor.current.x)>.08||Math.abs(y-lastAnchor.current.y)>.08){lastAnchor.current.set(x,y);const object=gl.domElement.closest<HTMLElement>('.core-object');object?.style.setProperty('--chip-anchor-x',`${x.toFixed(2)}%`);object?.style.setProperty('--chip-anchor-y',`${y.toFixed(2)}%`);}
  coreCost('sceneUpdate',updateStart);if(warmed.current&&!ready.current){ready.current=true;requestAnimationFrame(onReady);gl.domElement.dispatchEvent(new Event('corebounds',{bubbles:true}));}
 });
 return <>
  <ambientLight color="#486ab8" intensity={.15}/><directionalLight position={[-4,8,10]} color="#78a4ed" intensity={.48}/>
  <group ref={root} name="astra-board-assembly">
   <primitive object={model.surface}/><primitive object={model.details} visible={quality!=='low'}/>
   <primitive object={shadowTarget}/><directionalLight ref={shadowLight} position={[-3,4,7]} target={shadowTarget} color="#93bbf3" intensity={.65} castShadow shadow-mapSize-width={mobile?512:1024} shadow-mapSize-height={mobile?512:1024} shadow-camera-left={-10} shadow-camera-right={10} shadow-camera-top={10} shadow-camera-bottom={-10} shadow-camera-near={.1} shadow-camera-far={30} shadow-bias={-.0001} shadow-normalBias={.006}/>
   <mesh geometry={board.metal}><meshStandardMaterial color="#b9c5d9" metalness={1} roughness={.16} envMapIntensity={1.1}/></mesh>
   <mesh geometry={board.blue} position={[0,0,.011]} material={materials.blue}/><mesh geometry={board.gold} position={[0,0,.011]} material={materials.gold}/><mesh geometry={board.pink} position={[0,0,.011]} material={materials.pink}/>
   <mesh visible={quality!=='low'} geometry={board.blueContours}><meshStandardMaterial color="#318eff" emissive="#0d5cff" emissiveIntensity={4.8}/></mesh>
   <mesh visible={quality!=='low'} geometry={board.goldContours}><meshStandardMaterial color="#ffdba0" emissive="#ffb86d" emissiveIntensity={3.1}/></mesh>
   <rectAreaLight position={[-4.6,3.1,.9]} color="#0873ff" intensity={5} width={2.8} height={1.1}/><rectAreaLight position={[4.1,3.9,1]} color="#ffcb84" intensity={2.5} width={1.8} height={.8}/>
   <points><bufferGeometry><bufferAttribute attach="attributes-position" args={[stations.positions,3]}/><bufferAttribute attach="attributes-color" args={[stations.colors,3]}/></bufferGeometry><pointsMaterial vertexColors map={assets.sprite} size={.04} sizeAttenuation transparent depthWrite={false} blending={THREE.AdditiveBlending} opacity={.85}/></points>
   <points ref={packets}><bufferGeometry><bufferAttribute attach="attributes-position" args={[assets.positions,3]}/></bufferGeometry><pointsMaterial map={assets.sprite} color="#bfe8ff" size={.065} sizeAttenuation transparent depthWrite={false} blending={THREE.AdditiveBlending} opacity={.9}/></points>
   <group ref={chip} name="astra-core-package">
    {quality==='low'&&<sprite position={[0,-.25,.4]} scale={[1.9,1.5,1]}><spriteMaterial map={assets.sprite} color="#459aff" transparent opacity={.16} depthWrite={false} blending={THREE.AdditiveBlending}/></sprite>}
    <mesh position={[0,0,.16]} onPointerOver={e=>{e.stopPropagation();motion.current.hover=1;}} onPointerOut={()=>{motion.current.hover=0;}}><boxGeometry args={[2.8,2.8,.32]}/><meshBasicMaterial visible={false}/></mesh>
    <primitive object={model.core}/>
    <rectAreaLight ref={key} position={[0,-1.5,.15]} color="#0873ff" intensity={7} width={2.7} height={.22}/><rectAreaLight ref={glint} position={[0,1.6,3]} color="#c1e3ff" intensity={.15} width={2.2} height={.3}/>
   </group>
  </group>
 </>;
}

