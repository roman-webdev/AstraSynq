import * as THREE from 'three';

export type BoardGeometry = Record<'blue'|'gold'|'pink'|'metal'|'blueContours'|'goldContours',THREE.BufferGeometry>;
type ArrayDescriptor={offset:number;length:number;type:'Float32Array'|'Uint16Array'|'Uint32Array';itemSize:number;range?:{min:number[];max:number[]}};
/** Route tubes are built offline. Loading only allocates typed views, not thousands of curves/vertices. */
export class BoardGeometryLoader extends THREE.Loader<BoardGeometry>{
 load(url:string,onLoad:(board:BoardGeometry)=>void,_progress?:unknown,onError?:(error:unknown)=>void){
  this.manager.itemStart(url);
  fetch(url).then(async response=>{
   if(!response.ok||!response.body)throw new Error('Board geometry unavailable');
   const buffer=await new Response(response.body.pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
   if(buffer.byteLength>16*1024*1024)throw new Error('Unexpected board geometry size');
   const length=new DataView(buffer).getUint32(0,true),start=4+Math.ceil(length/4)*4;
   const header=JSON.parse(new TextDecoder().decode(new Uint8Array(buffer,4,length))) as Record<string,Record<string,ArrayDescriptor>>;
   const board={} as BoardGeometry;
   for(const [name,attributes] of Object.entries(header)){
    const geometry=new THREE.BufferGeometry();
    for(const [key,descriptor] of Object.entries(attributes)){
     const ArrayType=descriptor.type==='Float32Array'?Float32Array:descriptor.type==='Uint16Array'?Uint16Array:Uint32Array;
     const source=new ArrayType(buffer,start+descriptor.offset,descriptor.length);
     const array=descriptor.range?Float32Array.from(source,(value,index)=>{const axis=index%descriptor.itemSize;return descriptor.range!.min[axis]+value/65535*(descriptor.range!.max[axis]-descriptor.range!.min[axis]);}):source;
     const attribute=new THREE.BufferAttribute(array,descriptor.itemSize);
     if(key==='index')geometry.setIndex(attribute);else geometry.setAttribute(key,attribute);
    }
    geometry.computeBoundingSphere();board[name as keyof BoardGeometry]=geometry;
   }
   onLoad(board);
  }).catch(error=>{this.manager.itemError(url);onError?.(error);}).finally(()=>this.manager.itemEnd(url));
 }
}

export function createRouteCurves(mobile:boolean){
 const curves:THREE.Curve<THREE.Vector3>[]=[],lanes=mobile?16:30;
 const orient=(u:number,r:number,e:number)=>new THREE.Vector3(...(e===0?[u,r,.035]:e===1?[r,-u,.035]:e===2?[-u,-r,.035]:[-r,u,.035]) as [number,number,number]);
 for(let e=0;e<4;e++)for(let i=0;i<lanes;i++){
  const pin=(i/(lanes-1)*2-1)*1.26,bank=(i/(lanes-1)*2-1)*6.2,shoulder=pin+(bank-pin)*.32;
  const points=[orient(pin,1.39,e),orient(pin,1.92,e),orient(shoulder,1.92+Math.abs(shoulder-pin),e),orient(shoulder,5.55,e),orient(bank,5.55+Math.abs(bank-shoulder),e),orient(bank,12.3,e)];
  const path=new THREE.CurvePath<THREE.Vector3>();for(let j=1;j<points.length;j++)path.add(new THREE.LineCurve3(points[j-1],points[j]));curves.push(path);
 }
 return curves;
}
