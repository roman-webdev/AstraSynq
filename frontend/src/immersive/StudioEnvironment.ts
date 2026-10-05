import * as THREE from 'three';

/** Precomputed PMREM: no room rendering or reflection convolution on first visit. */
export class StudioEnvironmentLoader extends THREE.Loader<THREE.DataTexture> {
  load(url: string, onLoad: (texture: THREE.DataTexture) => void, _progress?: (event: ProgressEvent) => void, onError?: (error: unknown) => void) {
    this.manager.itemStart(url);
    fetch(url).then(async response => {
      if (!response.ok || !response.body) throw new Error('Studio material unavailable');
      const buffer = await new Response(response.body.pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
      const header = new DataView(buffer), width = header.getUint32(0, true), height = header.getUint32(4, true);
      if (width !== 336 || height !== 256 || buffer.byteLength !== 8 + width * height * 8) throw new Error('Invalid studio material');
      const texture = new THREE.DataTexture(new Uint16Array(buffer, 8), width, height, THREE.RGBAFormat, THREE.HalfFloatType);
      texture.mapping = THREE.CubeUVReflectionMapping;
      texture.minFilter = texture.magFilter = THREE.LinearFilter;
      texture.generateMipmaps = false;
      texture.needsUpdate = true;
      onLoad(texture);
    }).catch(error => { this.manager.itemError(url); onError?.(error); }).finally(() => this.manager.itemEnd(url));
  }
}
