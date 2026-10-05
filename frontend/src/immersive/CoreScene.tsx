import {presets,useQuality,type Quality} from './quality';
import {coreMark,coreCommit} from './telemetry';
import { Canvas, useFrame, useLoader, useThree } from '@react-three/fiber';
import { PCFShadowMap } from 'three';
import { useEffect, type MutableRefObject } from 'react';
import { BlenderModelLoader } from './BlenderModelLoader';
import { StudioEnvironmentLoader } from './StudioEnvironment';
import { BoardGeometryLoader } from './BoardGeometryLoader';
import { CoreAssembly } from './CoreAssembly';
import { CoreFinish } from './CoreFinish';
import type { CoreMotion } from './motion';

export function preloadCoreAssets(mobile:boolean){
 useLoader.preload(BlenderModelLoader,'/visuals/astra-core.model.bin');
 useLoader.preload(StudioEnvironmentLoader,'/visuals/astra-studio.bin');
 useLoader.preload(BoardGeometryLoader,`/visuals/astra-board-${mobile?'mobile':'desktop'}.bin`);
}
export type SceneProps = {
  motion: MutableRefObject<CoreMotion>; active: boolean; mobile: boolean;
  onFailure: () => void; onReady: () => void; quality?:Quality;
};

function Cadence({ active, mobile, onFailure }: Pick<SceneProps, 'active' | 'mobile' | 'onFailure'>) {
  const { invalidate, gl } = useThree();
  useEffect(() => {
    const lost = (event: Event) => { event.preventDefault(); onFailure(); };
    gl.domElement.addEventListener('webglcontextlost', lost);
    return () => gl.domElement.removeEventListener('webglcontextlost', lost);
  }, [gl, onFailure]);
  useEffect(() => {
    if (!active) return;
    let id = 0, last = performance.now();
    const step = 1000 / (mobile ? 45 : 60);
    const tick = (now: number) => {
      if (now - last >= step) { last = now - (now - last) % step; invalidate(); }
      id = requestAnimationFrame(tick);
    };
    id = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(id);
  }, [active, mobile, invalidate]);
  return null;
}

export default function CoreScene(props: SceneProps) {
  useEffect(()=>{coreCommit('sceneCommit');});
  const {quality,observe}=useQuality(props.mobile,props.active);const preset=presets[quality];
  return <Canvas shadows={{type: PCFShadowMap}} aria-hidden="true" dpr={window.__ASTRA_PROFILE__?.dpr??preset.dpr} frameloop="demand"
    camera={{ position: [0, 0, 12], fov: 38 }}
    onCreated={()=>coreMark('r3f-init')} gl={{ alpha: false, antialias: true, powerPreference: props.mobile ? 'low-power' : 'high-performance' }}>
    <color attach="background" args={['#050b19']} />
    <fog attach="fog" args={['#050b19', 15, 35]} />
    <QualityObserver quality={quality} observe={observe}/><CoreAssembly quality={quality} motion={props.motion} mobile={props.mobile} onReady={props.onReady} onFailure={props.onFailure} />
    <CoreFinish quality={quality} mobile={props.mobile} motion={props.motion} />
    <Cadence active={props.active && !props.motion.current.paused} mobile={props.mobile} onFailure={props.onFailure} />
  </Canvas>;
}

function QualityObserver({quality,observe}:{quality:Quality;observe:(now:number)=>void}){const {gl}=useThree();useFrame(()=>{gl.domElement.dataset.quality=quality;observe(performance.now());},-2);return null;}
