import * as THREE from 'three';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
type P=[number,number,number];type Box={x:number;y:number;sx:number;sy:number};
export function createReferenceBoard(mobile:boolean){
 const curves:THREE.Curve<THREE.Vector3>[]=[],segments:[P,P][]=[],components:number[][]=[],landmarks:number[][]=[],solder:number[][]=[],pads:number[][]=[],occupied:Box[]=[];
 const parts={blue:[] as THREE.BufferGeometry[],gold:[] as THREE.BufferGeometry[],pink:[] as THREE.BufferGeometry[],metal:[] as THREE.BufferGeometry[],blueContours:[] as THREE.BufferGeometry[],goldContours:[] as THREE.BufferGeometry[]};
 const path=(pts:P[])=>{const c=new THREE.CurvePath<THREE.Vector3>();for(let i=1;i<pts.length;i++)c.add(new THREE.LineCurve3(new THREE.Vector3(...pts[i-1]),new THREE.Vector3(...pts[i])));return c;};
 const tube=(c:THREE.Curve<THREE.Vector3>,width:number,phase=0)=>{const g=new THREE.TubeGeometry(c,mobile?22:24,width,mobile?4:5,false);const a=new Float32Array(g.getAttribute('position').count);a.fill(phase);g.setAttribute('tracePhase',new THREE.BufferAttribute(a,1));return g;};
 const orient=(u:number,r:number,e:number,z=.035):P=>e===0?[u,r,z]:e===1?[r,-u,z]:e===2?[-u,-r,z]:[-r,u,z];
 const lanes=mobile?16:30;
 for(let e=0;e<4;e++)for(let i=0;i<lanes;i++){
  const t=i/(lanes-1)*2-1,pin=t*1.26,bank=t*6.2,shoulder=pin+(bank-pin)*.32;
  const pts=[orient(pin,1.39,e),orient(pin,1.92,e),orient(shoulder,1.92+Math.abs(shoulder-pin),e),orient(shoulder,5.55,e),orient(bank,5.55+Math.abs(bank-shoulder),e),orient(bank,12.3,e)];
  const c=path(pts),phase=(i*.061+e*.19)%1,primary=i===0||i===lanes-1;curves.push(c);for(let j=1;j<pts.length;j++)segments.push([pts[j-1],pts[j]]);
  const kind=[2,5,9].includes(i%11)?'gold':i%11===7?'pink':'blue';parts[kind].push(tube(c,primary?.012:mobile?.0055:.0045,phase));parts.metal.push(tube(c,primary?.024:mobile?.014:.012,phase));
  for(const p of [pts[0],pts[2],pts[4],pts[5]])pads.push([p[0],p[1],.029,.035,.035,.013,0]);const seat=orient(pin,1.42,e);solder.push([seat[0],seat[1],.038,.035,.13,.024,e%2?Math.PI/2:0]);
 }
 const crosses=(a:P,b:P,box:Box)=>{const dx=b[0]-a[0],dy=b[1]-a[1],minX=box.x-box.sx/2-.08,maxX=box.x+box.sx/2+.08,minY=box.y-box.sy/2-.08,maxY=box.y+box.sy/2+.08;let lo=0,hi=1;for(const [p,q] of [[-dx,a[0]-minX],[dx,maxX-a[0]],[-dy,a[1]-minY],[dy,maxY-a[1]]]){if(Math.abs(p)<1e-9){if(q<0)return false;}else{const at=q/p;if(p<0)lo=Math.max(lo,at);else hi=Math.min(hi,at);if(lo>hi)return false;}}return true;};
 const free=(b:Box)=>!(Math.abs(b.x)<1.55+b.sx/2&&Math.abs(b.y)<1.55+b.sy/2)&&!occupied.some(a=>Math.abs(a.x-b.x)<(a.sx+b.sx)/2+.16&&Math.abs(a.y-b.y)<(a.sy+b.sy)/2+.16)&&!segments.some(([a,c])=>crosses(a,c,b));
 for(const [x,y,sx,sy,h,warm] of [[-4.85,4.75,2.7,1.65,.32,0],[4.95,4.8,1.85,2.5,.4,1],[-4.9,-4.7,2.55,1.65,.3,0],[4.8,-4.85,2.1,2.15,.36,0],[-9.2,9.25,2.5,1.6,.35,0],[9.15,9.1,1.9,2.3,.38,1],[-9.1,-9.1,1.8,2.5,.34,1],[9.2,-9.25,2.4,1.5,.29,0]]){
  const b={x,y,sx,sy};if(!free(b))continue;occupied.push(b);landmarks.push([x,y,h/2+.04,sx,sy,h,0]);const hx=sx/2+.018,hy=sy/2+.018,k=.14,z=.1;
  const c=path([[x-hx+k,y-hy,z],[x+hx-k,y-hy,z],[x+hx,y-hy+k,z],[x+hx,y+hy-k,z],[x+hx-k,y+hy,z],[x-hx+k,y+hy,z],[x-hx,y+hy-k,z],[x-hx,y-hy+k,z],[x-hx+k,y-hy,z]]);parts[warm?'goldContours':'blueContours'].push(tube(c,.055));
  const n=mobile?5:9;for(let i=0;i<n;i++)for(const side of [-1,1])solder.push([x+(i/(n-1)-.5)*sx*.82,y+side*(sy/2+.045),.045,.046,.11,.028,0]);
 }
 for(const xsign of [-1,1])for(const ysign of [-1,1])for(const [cx,cy] of [[2.8,2.8],[3.9,3.7],[2.8,4.4]]){
  const x=cx*xsign,y=cy*ysign,sx=.78,sy=.58,h=.14,b={x,y,sx,sy};if(!free(b))continue;occupied.push(b);components.push([x,y,h/2+.025,sx,sy,h,0]);for(let i=0;i<7;i++)for(const side of [-1,1])solder.push([x+(i/6-.5)*sx*.8,y+side*(sy/2+.06),.035,.035,.14,.028,0]);
 }
 const centers:number[][]=[];for(const sx of [-1,1])for(const sy of [-1,1])for(const [x,y] of [[2.45,2.5],[3.2,3.7],[3,4.6],[4.8,7.5],[7.5,4.8],[7.7,7.8],[10.4,5.4],[5.4,10.4]])centers.push([x*sx,y*sy]);
 const rows=mobile?3:4,cols=mobile?3:5;centers.forEach(([cx,cy],bank)=>{for(let r=0;r<rows;r++)for(let col=0;col<cols;col++){const tall=(r+col+bank)%4===0,sx=tall?.38:.24,sy=tall?.28:.16,h=tall?.1:.065,x=cx+(col-(cols-1)/2)*.56,y=cy+(r-(rows-1)/2)*.48,b={x,y,sx,sy};if(!free(b))continue;occupied.push(b);components.push([x,y,h/2+.025,sx,sy,h,0]);solder.push([x-sx/2-.032,y,.04,.043,sy*.8,.032,0],[x+sx/2+.032,y,.04,.043,sy*.8,.032,0]);}});
 const merge=(a:THREE.BufferGeometry[])=>{if(!a.length)return new THREE.BufferGeometry();const g=mergeGeometries(a,false)!;a.forEach(x=>x.dispose());return g;};
 return {curves,components,landmarks,solder,pads,blue:merge(parts.blue),gold:merge(parts.gold),pink:merge(parts.pink),metal:merge(parts.metal),blueContours:merge(parts.blueContours),goldContours:merge(parts.goldContours)};
}
