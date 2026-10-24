"""Build Delta's interviewer avatar ("Aria") with MPFB, headless.

    blender --background --python build_avatar.py -- <out.glb> [skin] [hair] [suit]

Everything used is CC0: MakeHuman base mesh + system assets, Margaret Toigo's
Suits 01, Mika Suominen's TalkingHead rig/weights, Visemes 02, Faceunits 01.
Mirrors the steps in TalkingHead's blender/MPFB/MPFB.md.
"""
import os
import sys

import bpy
from mathutils import Vector

from bl_ext.user_default.mpfb.services import (
    ExportService, FaceService, HumanService, ObjectService, TargetService,
)

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.path.abspath(argv[0] if argv else "aria.glb")
SKIN = argv[1] if len(argv) > 1 else "young_asian_female"
HAIR = argv[2] if len(argv) > 2 else "long01"
SUIT = argv[3] if len(argv) > 3 else "toigo_female_suit"
os.makedirs(os.path.dirname(OUT), exist_ok=True)

# Start from an empty scene.
bpy.ops.wm.read_factory_settings(use_empty=True)

human_info = HumanService._create_default_human_info_dict()
human_info.update({
    "name": "Aria",
    "phenotype": {
        "gender": 0.0,          # female
        "age": 0.555,           # ~32 years
        "muscle": 0.5,
        "weight": 0.47,
        "proportions": 0.65,
        "height": 0.45,
        "cupsize": 0.5,
        "firmness": 0.55,
        "race": {"asian": 0.55, "caucasian": 0.3, "african": 0.15},
    },
    "rig": "custom.talkinghead",
    "eyes": "high-poly/high-poly.mhclo",
    "eyebrows": "eyebrow001/eyebrow001.mhclo",
    "eyelashes": "eyelashes01/eyelashes01.mhclo",
    "teeth": "teeth_base/teeth_base.mhclo",
    "tongue": "tongue01/tongue01.mhclo",
    "hair": f"{HAIR}/{HAIR}.mhclo",
    "clothes": [f"{SUIT}/{SUIT}.mhclo"],
    "skin_mhmat": f"{SKIN}/{SKIN}.mhmat",
    "skin_material_type": "GAMEENGINE",
    "eyes_material_type": "GAMEENGINE",
    "clothes_material_type": "GAMEENGINE",
})
settings = HumanService.get_default_deserialization_settings()
settings["subdiv_levels"] = 0          # keep it light for the web
basemesh = HumanService.deserialize_from_dict(human_info, settings)
rig = basemesh.parent
print("BUILT", basemesh.name, "rig:", rig.name if rig else None,
      "children:", sorted(c.name for c in rig.children) if rig else [])

# Export copy with Meta visemes + ARKit face units (MPFB "Export copy" defaults
# from MPFB.md: bake masks/subdiv/modelling shapekeys, delete helpers, interpolate).
export_copy = ExportService.create_character_copy(basemesh, name_suffix="_export")
new_basemesh = ObjectService.find_object_of_type_amongst_nearest_relatives(export_copy)
TargetService.bake_targets(new_basemesh)
FaceService.load_targets(new_basemesh, load_microsoft_visemes=False, load_meta_visemes=True, load_arkit_faceunits=True)
FaceService.interpolate_targets(new_basemesh)
ExportService.bake_modifiers_remove_helpers(new_basemesh, bake_masks=True, bake_subdiv=True, remove_helpers=True, also_proxy=True)

# TalkingHead expects the root armature to be called "Armature".
rig.name = "Aria_design_rig"
export_copy.name = "Armature"
export_copy.data.name = "Armature"

objects = [export_copy] + list(export_copy.children_recursive)
for o in objects:
    if o.type == "MESH" and o.data.shape_keys:
        print("SHAPEKEYS", o.name, len(o.data.shape_keys.key_blocks),
              [k.name for k in o.data.shape_keys.key_blocks][:6])

# Hide the design copy; apply transforms on the export copy.
for o in [rig] + list(rig.children_recursive):
    o.hide_set(True)
    o.hide_render = True
bpy.ops.object.select_all(action="DESELECT")
for o in objects:
    o.select_set(True)
bpy.context.view_layer.objects.active = export_copy
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

bpy.ops.export_scene.gltf(
    filepath=OUT, export_format="GLB", use_selection=True,
    export_animations=False, export_morph=True, export_skins=True,
    export_morph_normal=True, export_yup=True,
)
print("EXPORTED", OUT, os.path.getsize(OUT))
try:  # keep the editable source; Blender may warn about stale shape-key pointers
    bpy.ops.wm.save_as_mainfile(filepath=OUT.replace(".glb", ".blend"))
except RuntimeError as exc:
    print("BLEND SAVE WARNING", exc)

# Face preview render (EEVEE), to judge the look before using it in the app.
head = export_copy.pose.bones.get("Head")
target = export_copy.matrix_world @ head.head if head else Vector((0, 0, 1.55))
target = target + Vector((0, 0, 0.06))
cam_data = bpy.data.cameras.new("cam")
cam_data.lens = 85
cam = bpy.data.objects.new("cam", cam_data)
bpy.context.scene.collection.objects.link(cam)
cam.location = target + Vector((0, -1.1, 0.0))
cam.rotation_euler = (1.5708, 0, 0)
bpy.context.scene.camera = cam
for name, loc, energy in (("key", (-1.2, -1.5, 2.3), 400), ("fill", (1.4, -1.2, 1.8), 180), ("rim", (0, 1.5, 2.2), 250)):
    light_data = bpy.data.lights.new(name, "AREA")
    light_data.energy = energy
    light_data.size = 1.5
    light = bpy.data.objects.new(name, light_data)
    light.location = loc
    direction = target - Vector(loc)
    light.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(light)
world = bpy.data.worlds.new("w")
world.color = (0.05, 0.05, 0.07)
bpy.context.scene.world = world
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE_NEXT"
scene.render.resolution_x, scene.render.resolution_y = 640, 640
scene.render.filepath = OUT.replace(".glb", "_face.png")
bpy.ops.render.render(write_still=True)
cam.location = target + Vector((0, -2.6, -0.35))
scene.render.filepath = OUT.replace(".glb", "_upper.png")
bpy.ops.render.render(write_still=True)
print("RENDERED")
