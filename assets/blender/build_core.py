"""Original AstraSynq model. Blender 5.2; run with --background --python.
No downloaded meshes/textures. XY board coordinates intentionally match Three.js.
"""
import bpy, math, json, random
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'frontend/public/visuals'
PREVIEW = ROOT / 'previews/core-blender'
OUT.mkdir(parents=True, exist_ok=True)
PREVIEW.mkdir(parents=True, exist_ok=True)
random.seed(48)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 48
scene.cycles.use_denoising = True
scene.cycles.device = 'GPU'
prefs = bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type = 'OPTIX'
prefs.get_devices()
for device in prefs.devices:
    device.use = device.type == 'OPTIX'
scene.world.color = (.018, .025, .05)
scene.view_settings.view_transform = 'AgX'
scene.render.resolution_x = 1600
scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.unit_settings.scale_length = .01

def mat(name, color, metal=0, rough=.4, emission=None, strength=0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Metallic'].default_value = metal
    p.inputs['Roughness'].default_value = rough
    if emission:
        p.inputs['Emission Color'].default_value = (*emission, 1)
        p.inputs['Emission Strength'].default_value = strength
    return m

ceramic = mat('Astra satin ceramic', (.014, .028, .059), .35, .32)
pcb = mat('Astra PCB lacquer', (.004, .012, .029), .16, .37)
substrate = mat('Astra graphite substrate', (.006, .01, .018), .3, .43)
silver = mat('Astra nickel contacts', (.55, .63, .74), 1, .15)
gold = mat('Astra gold bond pads', (.57, .33, .095), .96, .23)
die = mat('Astra exposed silicon', (.012, .037, .09), .5, .17, (.02, .25, 1), .75)
die.node_tree.nodes.get('Principled BSDF').inputs['Coat Weight'].default_value=.7
marking = mat('Astra etched marking', (.51, .62, .76), .6, .39)
rim = mat('Astra luminous skirt', (.17, .48, .88), .15, .23, (.05, .3, 1), 2.8)
window = mat('Astra window light', (.32, .65, .9), .2, .22, (.14, .56, 1), 1.45)
pink = mat('Astra magenta signals', (.2, .013, .053), .55, .28, (.95, .04, .2), 1.25)

# Bake micro-surface normals and roughness in Blender. These maps preserve the
# small material detail in WebGL without runtime procedural texture evaluation.
def baked_surface(material, prefix, base_roughness, bump_distance, scale):
    paths={kind:ROOT/'assets/blender'/(prefix+'_'+kind.lower()+'.png') for kind in ['NORMAL','ROUGHNESS']}
    if all(p.exists() for p in paths.values()):
        tree=material.node_tree;p=tree.nodes.get('Principled BSDF')
        textures={}
        for kind,path in paths.items():
            im=bpy.data.images.load(str(path));im.colorspace_settings.name='Non-Color';im.pack()
            tex=tree.nodes.new('ShaderNodeTexImage');tex.image=im;textures[kind]=tex
        tree.links.new(textures['ROUGHNESS'].outputs['Color'],p.inputs['Roughness'])
        normal=tree.nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.1 if prefix=='ceramic' else .06
        tree.links.new(textures['NORMAL'].outputs['Color'],normal.inputs['Color']);tree.links.new(normal.outputs['Normal'],p.inputs['Normal'])
        return
    bpy.ops.mesh.primitive_plane_add(size=2)
    plane = bpy.context.object
    plane.name = 'Temporary baking plane'
    plane.data.materials.append(material)
    tree = material.node_tree
    p = tree.nodes.get('Principled BSDF')
    noise = tree.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = scale
    noise.inputs['Detail'].default_value = 3
    uv = tree.nodes.new('ShaderNodeTexCoord')
    tree.links.new(uv.outputs['UV'], noise.inputs['Vector'])
    ramp = tree.nodes.new('ShaderNodeMapRange')
    ramp.inputs['To Min'].default_value = base_roughness-.08
    ramp.inputs['To Max'].default_value = base_roughness+.07
    tree.links.new(noise.outputs['Fac'], ramp.inputs['Value'])
    tree.links.new(ramp.outputs['Result'], p.inputs['Roughness'])
    bump = tree.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = .24
    bump.inputs['Distance'].default_value = bump_distance
    tree.links.new(noise.outputs['Fac'], bump.inputs['Height'])
    tree.links.new(bump.outputs['Normal'], p.inputs['Normal'])
    maps = {}
    scene.cycles.samples = 8
    for kind in ['NORMAL', 'ROUGHNESS']:
        im = bpy.data.images.new(prefix+'_'+kind.lower(), 512, 512, alpha=False)
        im.colorspace_settings.name = 'Non-Color'
        tex = tree.nodes.new('ShaderNodeTexImage')
        tex.image = im
        tree.nodes.active = tex
        bpy.ops.object.bake(type=kind, margin=8)
        im.filepath_raw = str(ROOT/'assets/blender'/ (im.name+'.png'))
        im.file_format = 'PNG'
        im.save()
        im.pack()
        maps[kind] = tex
    tree.links.new(maps['ROUGHNESS'].outputs['Color'], p.inputs['Roughness'])
    normal = tree.nodes.new('ShaderNodeNormalMap')
    normal.inputs['Strength'].default_value = .1 if prefix=='ceramic' else .06
    tree.links.new(maps['NORMAL'].outputs['Color'], normal.inputs['Color'])
    tree.links.new(normal.outputs['Normal'], p.inputs['Normal'])
    bpy.data.objects.remove(plane, do_unlink=True)

baked_surface(ceramic, 'ceramic', .32, .018, 180)
baked_surface(pcb, 'pcb', .37, .014, 220)
scene.cycles.samples = 48
model_objects = []
chip_objects = []
detail_objects = []
box_cache = {}

def box(name, center, dims, material, bevel=.015, target=None, angle=0):
    key=(tuple(round(d,5) for d in dims),round(bevel,5),material.name)
    if key in box_cache:
        o=bpy.data.objects.new(name,box_cache[key]);bpy.context.collection.objects.link(o)
        o.location=center;o.rotation_euler.z=angle
        if target is not None:target.append(o)
        return o
    bpy.ops.mesh.primitive_cube_add(size=1, location=center)
    o=bpy.context.object
    o.name=name
    o.dimensions=dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        mod=o.modifiers.new('Manufactured edge radius', 'BEVEL')
        mod.width=bevel
        mod.segments=2 if min(dims)>.06 else 1
        bpy.ops.object.modifier_apply(modifier=mod.name)
    for polygon in o.data.polygons:
        polygon.use_smooth=True
    mod=o.modifiers.new('Weighted face normals', 'WEIGHTED_NORMAL')
    mod.keep_sharp=True
    bpy.ops.object.modifier_apply(modifier=mod.name)
    o.rotation_euler.z=angle
    o.data.materials.append(material)
    box_cache[key]=o.data
    if target is not None:
        target.append(o)
    return o

def plate(name, side, height, radius, z, material):
    # True rounded rectangle extrusion, rather than a scaled box bevel.
    points=[]
    for cx,cy,start in [(side/2-radius,side/2-radius,0),(-side/2+radius,side/2-radius,90),(-side/2+radius,-side/2+radius,180),(side/2-radius,-side/2+radius,270)]:
        for i in range(13):
            a=math.radians(start+i*90/12)
            points.append((cx+radius*math.cos(a),cy+radius*math.sin(a)))
    n=len(points)
    vertices=[(x,y,z+h) for h in [0,height] for x,y in points]
    faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata(vertices,[],faces)
    mesh.update()
    o=bpy.data.objects.new(name,mesh)
    bpy.context.collection.objects.link(o)
    bpy.context.view_layer.objects.active=o
    o.select_set(True)
    bevel=o.modifiers.new('Machined lip', 'BEVEL');bevel.width=.009;bevel.segments=3
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    # Rounded shoulders catch light; planar faces stay planar.
    for p in mesh.polygons:
        p.use_smooth=len(p.vertices)==4
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(island_margin=.02)
    bpy.ops.object.mode_set(mode='OBJECT')
    o.data.materials.append(material)
    chip_objects.append(o)
    return o

board=box('Astra_board_surface',(0,0,-.055),(30,30,.1),pcb,.012,model_objects)
plate('Organic substrate',2.79,.035,.19,.015,substrate)
plate('Full underside luminous seam',2.74,.024,.21,.053,rim)
plate('Nickel edge inset',2.71,.018,.23,.077,silver)
lid=plate('Astra ceramic package',2.7,.132,.245,.095,ceramic)
plate('Inset die socket',1.03,.022,.125,.228,substrate)
plate('Die window luminous gasket',.955,.009,.105,.252,window)
plate('Polished silicon window',.865,.012,.087,.263,die)

# Engraving cutter and inlaid marking use the same glyph outlines.
def text_obj(name,z,material=None):
    curve=bpy.data.curves.new(name,'FONT');curve.body='ASTRA';curve.align_x='CENTER'
    curve.size=.18;curve.space_character=1.22;curve.extrude=.008;curve.bevel_depth=.0008
    o=bpy.data.objects.new(name,curve);bpy.context.collection.objects.link(o)
    o.location=(.58,-1.035,z)
    if material: o.data.materials.append(material)
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
    bpy.ops.object.convert(target='MESH')
    return bpy.context.object
cutter=text_obj('ASTRA engraving cutter',.222)
bpy.context.view_layer.objects.active=lid
boolean=lid.modifiers.new('Recessed ASTRA engraving','BOOLEAN');boolean.operation='DIFFERENCE';boolean.object=cutter
bpy.ops.object.modifier_apply(modifier=boolean.name)
bpy.data.objects.remove(cutter,do_unlink=True)
label=text_obj('ASTRA recessed nickel lettering',.2205,marking)
chip_objects.append(label)

lead_mesh=None
for e in range(4):
    for i in range(28):
        u=(i/27-.5)*2.43
        if lead_mesh is None:
            curve=bpy.data.curves.new('Drawn nickel lead','CURVE');curve.dimensions='3D';curve.resolution_u=5
            curve.bevel_depth=.0095;curve.bevel_resolution=2
            spline=curve.splines.new('BEZIER');spline.bezier_points.add(3)
            for point,xyz in zip(spline.bezier_points,[(0,-1.23,.057),(0,-1.35,.067),(0,-1.41,.038),(0,-1.52,.035)]):
                point.co=xyz;point.handle_left_type='AUTO';point.handle_right_type='AUTO'
            o=bpy.data.objects.new('Prototype drawn lead',curve);bpy.context.collection.objects.link(o)
            bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
            bpy.ops.object.convert(target='MESH');lead_mesh=o.data;lead_mesh.materials.append(silver)
            for p in lead_mesh.polygons:p.use_smooth=True
            bpy.data.objects.remove(o,do_unlink=True)
        o=bpy.data.objects.new('Polished round package lead',lead_mesh);bpy.context.collection.objects.link(o)
        o.location=([(u,0,0),(0,-u,0),(-u,0,0),(0,u,0)])[e];o.rotation_euler.z=e*math.pi/2
        chip_objects.append(o)
for c in range(10):
    for r in range(9):
        box('Window gold bond pad',((c-4.5)*.071,(r-4)*.067,.29),(.023,.027,.01),gold,.003,chip_objects)
        if c in [0,4,8]:
            box('Pin signal marker',((c-4.5)*.071,(r-4)*.067,.296),(.009,.014,.002),pink if c==4 else window,.001,chip_objects)

# Hairline silicon structures, not a uniform tiled top surface.
for i in range(18):
    x=(i-8.5)*.04
    box('Silicon lithography',(x,0,.276),(.0018,.73,.001),silver,0,chip_objects)

layout=json.loads((ROOT/'assets/blender/board-layout.json').read_text())
component_material=mat('Astra component ceramic',(.008,.012,.019),.18,.48)
for kind in ['components','landmarks','solder','pads']:
    for index,(x,y,z,sx,sy,sz,angle) in enumerate(layout[kind]):
        material=silver if kind=='solder' else gold if kind=='pads' else component_material
        box('PCB '+kind,(x,y,z),(sx,sy,sz),material,min(.008,sz*.12),detail_objects,angle)
        if kind=='landmarks':
            # Chamfered cap seam and a pair of real mounting/inspection details.
            box('Package lid',(x,y,z+sz/2+.006),(sx*.93,sy*.92,.018),ceramic,.007,detail_objects,angle)
            for s in [-1,1]:
                box('Package solder foot',(x+s*sx*.4,y-sy*.44,.034),(.065,.08,.026),silver,.006,detail_objects)

def join_by_material(objects,prefix):
    result=[]
    groups={}
    for o in objects:
        groups.setdefault(o.data.materials[0].name,[]).append(o)
    for material,group in groups.items():
        bpy.ops.object.select_all(action='DESELECT')
        for o in group:o.select_set(True)
        bpy.context.view_layer.objects.active=group[0]
        bpy.ops.object.join()
        o=bpy.context.object;o.name=prefix+' '+material
        result.append(o)
    return result

chip_objects=join_by_material(chip_objects,'Core')
detail_objects=join_by_material(detail_objects,'Board')
def parent_group(name,objects):
    o=bpy.data.objects.new(name,None);bpy.context.collection.objects.link(o)
    for child in objects:child.parent=o
    return o
core=parent_group('Astra_chip',chip_objects)
details=parent_group('Astra_board_details',detail_objects)
all_model=model_objects+chip_objects+detail_objects+[core,details]
bpy.ops.object.select_all(action='DESELECT')
for o in all_model:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(ROOT/'assets/blender/astra-core.gltf'),export_format='GLTF_SEPARATE',use_selection=True,export_yup=False,export_image_format='WEBP',export_image_quality=85,export_normals=True,export_texcoords=True,export_materials='EXPORT',export_cameras=False,export_lights=False)
print('ASTRA_MODEL_EXPORTED',flush=True)

# Render-only native curves/lights reproduce the dynamic WebGL trace layout.
def cable(name,points,material,radius):
    curve=bpy.data.curves.new(name,'CURVE');curve.dimensions='3D';curve.resolution_u=1
    curve.bevel_depth=radius;curve.bevel_resolution=1
    spline=curve.splines.new('POLY');spline.points.add(len(points)-1)
    for p,xyz in zip(spline.points,points):p.co=(*xyz,1)
    o=bpy.data.objects.new(name,curve);bpy.context.collection.objects.link(o);o.data.materials.append(material)
    return o
blue_route=mat('Render blue trace',(.013,.043,.13),.75,.27,(.03,.25,1),1.6)
gold_route=mat('Render warm trace',(.23,.11,.022),.85,.28,(1,.56,.16),1)
for i,route in enumerate(layout['routes']):
    color=gold_route if i%30%11 in [2,5,9] else pink if i%30%11==7 else blue_route
    cable('Polished metallic data conduit',route,silver,.012)
    cable('Luminous data route',[(x,y,z+.011) for x,y,z in route],color,.0045)
    # Small solder dots at intervals instead of floating spark sprites.
    for point in route[4::8]:
        box('Trace inspection pad',(point[0],point[1],.047),(.025,.025,.008),gold,.003)
for x,y,z,sx,sy,sz,angle in layout['landmarks']:
    hx,hy=sx/2+.025,sy/2+.025
    cable('Landmark blue seam',[(x-hx,y-hy,.09),(x+hx,y-hy,.09),(x+hx,y+hy,.09),(x-hx,y+hy,.09),(x-hx,y-hy,.09)],blue_route,.033)

def light(name,position,color,power,size,target=(0,0,0),size_y=None):
    data=bpy.data.lights.new(name,'AREA');data.color=color;data.energy=power
    data.shape='RECTANGLE';data.size=size;data.size_y=size_y or size
    o=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(o);o.location=position
    o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
    return o
light('Soft blue reflection',(-3,2,5),(.22,.49,1),700,5)
light('Warm edge reflection',(5,3,4),(1,.69,.36),320,4)
light('Top strip reflection',(0,-3,6),(.6,.8,1),170,4,size_y=.5)
light('Skirt bounce',(0,-1.5,.35),(.025,.25,1),30,2.5,target=(0,-2.4,0),size_y=.1)
light('Board blue landmark',(-5,3,.9),(.015,.16,1),80,2.5,target=(-5,3,0))
camera_data=bpy.data.cameras.new('Macro camera');camera=bpy.data.objects.new('Macro camera',camera_data)
bpy.context.collection.objects.link(camera);scene.camera=camera
camera.location=(5,-7,7.5);target=Vector((.0,.0,.05))
camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
camera_data.lens=48
camera_data.dof.use_dof=True
focus=bpy.data.objects.new('Core focus',None);bpy.context.collection.objects.link(focus);focus.location=(0,0,.22)
camera_data.dof.focus_object=focus;camera_data.dof.aperture_fstop=3.5
scene.render.filepath=str(PREVIEW/'cycles-reference.png')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'assets/blender/astra-core.blend'))
bpy.ops.render.render(write_still=True)
manifest={'blender':bpy.app.version_string,'source':'assets/blender/astra-core.gltf','license':'Original AstraSynq geometry and Blender-baked procedural textures; no external assets','coordinates':'XY board, Z up; export_yup=False','mesh_count':len(model_objects+chip_objects+detail_objects),'cycles_samples':scene.cycles.samples}
(ROOT/'assets/blender/manifest.json').write_text(json.dumps(manifest,indent=2))
print('ASTRA_MODEL_COMPLETE',json.dumps(manifest),flush=True)
