"""Bundle geometry with native gzip; keep texture URLs external for strict CSP."""
from pathlib import Path
import json,struct,gzip,shutil
root=Path(__file__).resolve().parents[2]
folder=root/'assets/blender'
out=root/'frontend/public/visuals'
model=json.loads((folder/'astra-core.gltf').read_text())
assert len(model['buffers'])==1
binary=(folder/model['buffers'][0].pop('uri')).read_bytes()
textures=[]
for image in model.get('images',[]):
    original=folder/image['uri']
    name='astra-'+original.name
    shutil.copyfile(original,out/name)
    shutil.copyfile(original,folder/name)
    image['uri']=name
    textures.append({'file':name,'bytes':(out/name).stat().st_size})
document=json.dumps(model,separators=(',',':')).encode()
document+=b' '*((-len(document))%4)
binary+=b'\0'*((-len(binary))%4)
payload=struct.pack('<III',0x46546c67,2,28+len(document)+len(binary))+struct.pack('<II',len(document),0x4e4f534a)+document+struct.pack('<II',len(binary),0x004e4942)+binary
packed=gzip.compress(payload,compresslevel=9,mtime=0)
(folder/'astra-core.glb').write_bytes(payload)
(out/'astra-core.model.bin').write_bytes(packed)
manifest=json.loads((folder/'manifest.json').read_text())
manifest.update({'model':'frontend/public/visuals/astra-core.model.bin','geometry_raw_bytes':len(payload),'geometry_gzip_bytes':len(packed),'textures':textures,'transfer_bytes':len(packed)+sum(t['bytes'] for t in textures),'compression':'gzip via native DecompressionStream; external WebP textures; CSP unchanged'})
(folder/'manifest.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps(manifest,indent=2))
