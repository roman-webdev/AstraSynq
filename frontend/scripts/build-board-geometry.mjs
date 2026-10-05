import fs from 'node:fs';
import zlib from 'node:zlib';
import {createReferenceBoard} from '../src/immersive/ReferenceBoard.ts';
for(const mobile of [false,true]){
 const board=createReferenceBoard(mobile),header={},chunks=[];let offset=0;
 for(const name of ['blue','gold','pink','metal','blueContours','goldContours']){
  const geometry=board[name],attributes={...geometry.attributes,index:geometry.index};header[name]={};
  for(const [key,attribute] of Object.entries(attributes)){
   if(!attribute||((key==='uv'||key==='tracePhase')&&!['blue','gold','pink'].includes(name)))continue;
   let array=attribute.array;let range;
   if(array instanceof Float32Array){
    const min=Array(attribute.itemSize).fill(Infinity),max=Array(attribute.itemSize).fill(-Infinity);
    for(let i=0;i<array.length;i++){const axis=i%attribute.itemSize;min[axis]=Math.min(min[axis],array[i]);max[axis]=Math.max(max[axis],array[i]);}
    range={min,max};array=Uint16Array.from(array,(value,i)=>{const axis=i%attribute.itemSize;return max[axis]===min[axis]?0:Math.round((value-min[axis])/(max[axis]-min[axis])*65535);});
   }
   const data=Buffer.from(array.buffer,array.byteOffset,array.byteLength);
   header[name][key]={offset,length:array.length,type:array.constructor.name,itemSize:attribute.itemSize,...(range?{range}:{})};chunks.push(data);offset+=data.length;
   if(offset%4){const padding=4-offset%4;chunks.push(Buffer.alloc(padding));offset+=padding;}
  }
 }
 const meta=Buffer.from(JSON.stringify(header)),prefix=Buffer.alloc(4+Math.ceil(meta.length/4)*4);prefix.writeUInt32LE(meta.length);meta.copy(prefix,4);
 const compressed=zlib.gzipSync(Buffer.concat([prefix,...chunks]),{level:9});const file=`public/visuals/astra-board-${mobile?'mobile':'desktop'}.bin`;
 fs.writeFileSync(new URL(`../${file}`,import.meta.url),compressed);console.log(`${file}: ${compressed.length} bytes`);
 Object.values(board).forEach(value=>value?.dispose?.());
}
