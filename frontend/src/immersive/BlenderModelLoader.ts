import {coreMark} from './telemetry';
import { Loader } from 'three';
import { GLTFLoader, type GLTF } from 'three/examples/jsm/loaders/GLTFLoader.js';

/** Native gzip keeps repeated CAD geometry compact without WASM/blob workers.
 * External texture URLs also work with the app's existing strict CSP.
 */
export class BlenderModelLoader extends Loader<GLTF> {
  load(url: string, onLoad: (model: GLTF) => void, _progress?: (event: ProgressEvent) => void, onError?: (error: unknown) => void) {
    coreMark('model-load-start');this.manager.itemStart(url);
    fetch(url).then(async response => {
      if (!response.ok || !response.body) throw new Error('Core model unavailable');
      const buffer = await new Response(response.body.pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
      if (buffer.byteLength > 16 * 1024 * 1024) throw new Error('Unexpected core model size');
      coreMark('model-decompressed');const model = await new GLTFLoader(this.manager).parseAsync(buffer, '/visuals/');
      coreMark('model-textures-decoded');onLoad(model);
    }).catch(error => { this.manager.itemError(url); onError?.(error); }).finally(() => this.manager.itemEnd(url));
  }
}
