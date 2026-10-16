"""Render a GLB to a PNG with Blender, headless. Runs inside Blender:

    blender -b --factory-startup -P tools/render_glb.py -- IN.glb OUT.png [SIZE]

Three-quarter view from above, framed to the model, soft studio light,
transparent background. Used by `tbcgen model` / `tbcgen shapes`.
"""
import math
import sys

import bpy
from mathutils import Vector

src, dst = sys.argv[sys.argv.index("--") + 1:][:2]
size = int(sys.argv[sys.argv.index("--") + 3]) if len(sys.argv) > sys.argv.index("--") + 3 else 1200

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
scene = bpy.context.scene

# bounds of everything imported (world space)
pts = [o.matrix_world @ Vector(c) for o in scene.objects if o.type == "MESH" for c in o.bound_box]
lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
centre, radius = (lo + hi) / 2, (hi - lo).length / 2

# camera: 35 deg above the horizon, 40 deg round, telephoto to keep it flat
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
scene.collection.objects.link(cam)
cam.data.lens = 85
el, az = math.radians(35), math.radians(-40)
direction = Vector((math.cos(el) * math.sin(az), -math.cos(el) * math.cos(az), math.sin(el)))
cam.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
cam.data.clip_start, cam.data.clip_end = radius * 0.01, radius * 100
scene.camera = cam
scene.render.resolution_x = scene.render.resolution_y = size
# exact fit to every object's bounding-box corners, then 8% margin
coords = [c for p in pts for c in p]
bpy.context.view_layer.update()
fit, _ = cam.camera_fit_coords(bpy.context.evaluated_depsgraph_get(), coords)
cam.location = centre + (fit - centre) * 1.08

# key + fill + rim, sized to the model
for name, energy, el_d, az_d in (("key", 3.0, 50, -60), ("fill", 1.2, 20, 60), ("rim", 2.0, 40, 160)):
    light = bpy.data.objects.new(name, bpy.data.lights.new(name, "SUN"))
    light.data.energy = energy
    light.data.angle = math.radians(15)
    e, a = math.radians(el_d), math.radians(az_d)
    d = Vector((math.cos(e) * math.sin(a), -math.cos(e) * math.cos(a), math.sin(e)))
    light.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(light)

world = bpy.data.worlds.new("world")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.8, 0.8, 0.82, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
scene.world = world

scene.render.engine = "CYCLES"                  # CPU, works headless everywhere
scene.cycles.device = "CPU"
scene.cycles.samples = 48
scene.cycles.use_denoising = True
scene.render.film_transparent = True
scene.render.resolution_x = scene.render.resolution_y = size
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.view_settings.view_transform = "Standard"
scene.render.filepath = dst
bpy.ops.render.render(write_still=True)
