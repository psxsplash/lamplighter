# Builds the low-poly models as .glb files. Run through art/build.sh:
#   blender -b --factory-startup --python art/models.py -- <outdir>
import math
import os
import random
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
            l[uv].uv = ((math.atan2(co.y, co.x) / math.pi + 1.0), co.z / 2.4)
    obj_from_bmesh("beacon", bm)
    export("beacon")


def planar_uv(bm, scale):
    # Box-projected UVs: each face takes the two axes its normal is not
    # along, one texture repeat per `scale` metres.
    uv = bm.loops.layers.uv.new()
    for f in bm.faces:
        axis = max(range(3), key=lambda i: abs(f.normal[i]))
        a, b = [i for i in range(3) if i != axis]
        for l in f.loops:
            l[uv].uv = (l.vert.co[a] / scale, l.vert.co[b] / scale)


def cliff():
    # A headland: a flat-topped rock 20 m wide and 14 m deep whose far edge
    # (Blender +Y) drops 12 m to the sea. The top is a 4 x 4 grid of quads,
    # the rim row and the two rows of cliff face below it jittered so the
    # edge reads as broken rock.
    reset()
    rnd = random.Random(7)
    bm = bmesh.new()
    xs = [-10.0 + 5.0 * i for i in range(5)]
    ys = [-8.0, -3.0, 1.0, 4.0, 6.0]
    rows = []
    for j, y in enumerate(ys):
        rim = j == len(ys) - 1
        rows.append([bm.verts.new((x, y + (rnd.uniform(-0.6, 0.4) if rim else 0.0),
                                   rnd.uniform(-0.3, 0.0) if rim else rnd.uniform(-0.05, 0.05)))
                     for x in xs])
    for dz, dy in [(-5.0, 0.8), (-12.0, 1.6)]:
        rows.append([bm.verts.new((x, rows[-1][i].co.y + dy + rnd.uniform(-0.5, 0.5),
                                   dz + rnd.uniform(-0.4, 0.4)))
                     for i, x in enumerate(xs)])
    for j in range(len(rows) - 1):
        for i in range(len(xs) - 1):
            bm.faces.new((rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]))
    bm.normal_update()
    # Outward normals: up on the top, towards +Y on the face.
    for f in bm.faces:
        if f.normal.z + f.normal.y < 0:
            f.normal_flip()
    bm.normal_update()
    planar_uv(bm, 4.0)
    obj_from_bmesh("cliff", bm)
    export("cliff")


def sea():
    # The sea at the foot of the cliff: a 96 m square in 6 x 6 quads, one
    # texture repeat per 8 m.
    reset()
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=6, y_segments=6, size=48.0)
    planar_uv(bm, 8.0)
    obj_from_bmesh("sea", bm)
    export("sea")


ground()
beacon()
cliff()
sea()
