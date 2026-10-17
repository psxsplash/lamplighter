# Builds the low-poly models as .glb files. Run through art/build.sh:
#   blender -b --factory-startup --python art/models.py -- <outdir>
import os
import sys

import bpy
import bmesh

OUT = sys.argv[sys.argv.index("--") + 1]


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def export(name):
    os.makedirs(OUT, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, name + ".glb"),
                              export_format="GLB", export_apply=True)


def obj_from_bmesh(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def ground():
    # A flat 16 m square in 4 x 4 quads, UVs tiling the texture once per quad.
    reset()
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=4, y_segments=4, size=8.0)
    uv = bm.loops.layers.uv.new()
    for f in bm.faces:
        for l in f.loops:
            co = l.vert.co
            l[uv].uv = ((co.x + 8.0) / 4.0, (co.y + 8.0) / 4.0)
    obj_from_bmesh("ground", bm)
    export("ground")


def beacon():
    # An eight-sided stone pillar with a wider cap, 2.4 m tall.
    reset()
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.45,
                          radius2=0.35, depth=2.0)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, 1.0))
    cap = bmesh.new()
    bmesh.ops.create_cone(cap, cap_ends=True, segments=8, radius1=0.6,
                          radius2=0.6, depth=0.4)
    bmesh.ops.translate(cap, verts=cap.verts, vec=(0, 0, 2.2))
    me = bpy.data.meshes.new("tmp")
    cap.to_mesh(me)
    cap.free()
    bm.from_mesh(me)
    uv = bm.loops.layers.uv.new()
    for f in bm.faces:
        for l in f.loops:
            co = l.vert.co
            import math
            l[uv].uv = ((math.atan2(co.y, co.x) / math.pi + 1.0), co.z / 2.4)
    obj_from_bmesh("beacon", bm)
    export("beacon")


ground()
beacon()
