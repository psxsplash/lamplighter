# Builds the low-poly models as .glb files. Run through art/build.sh:
#   blender -b --factory-startup --python art/models.py -- <outdir>
import math
import os
import random
import sys

import bpy
import bmesh
import mathutils

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


# The valley, phase 2: a streamed outdoor area. Everything below is written in
# scene coordinates (x right, y up, z forward, metres) and turned into
# Blender's (-x, -z, y) on the way in: glTF turns Blender's +y into -z, and
# the editor's import, like Unity's, mirrors glTF's x, so the scene gets the
# coordinates back as given. The meshes are built at the world origin, so
# each node's transform is the identity and the scene places every chunk at
# (0, 0, 0).
VALLEY_CHUNK = 32.0       # metres a side of one ground chunk
VALLEY_COLS = 14          # chunks across x, from -224 to 224
VALLEY_ROWS = 14          # chunks along z, from -440 to the rim
VALLEY_STEP = 4.0         # the finest quad, in metres
# Quads a side: 8 (4 m) where the player walks, 4 (8 m) elsewhere. With 8 m
# quads under the player the whole quad ahead, which has a corner beside the
# camera, did not draw in pcsx-redux (psxsplash splits near-plane triangles
# only five times), so the ground the player walks on is smaller. Finer
# still makes the streamed region holding it too big for the PS1's RAM.
# (row, col) of the fine chunks: x -32..32, z -56..8, the start, the rim
# ahead of it and the three beacons.
VALLEY_FINE = {(VALLEY_ROWS - 1 - k, VALLEY_COLS // 2 + d) for k in (0, 1) for d in (-1, 0)}
VALLEY_RIM_Z = 8.0        # the north rim: the land ends here and drops to the sea
VALLEY_SEA_Y = -12.0
VALLEY_X0 = -VALLEY_CHUNK * VALLEY_COLS / 2
VALLEY_Z0 = VALLEY_RIM_Z - VALLEY_CHUNK * VALLEY_ROWS


def smoothstep(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3.0 - 2.0 * t)


def valley_height(x, z, rnd):
    # A floor near y = 0 around the player's start (the origin), hills rising
    # on the east and west flanks and to the south, a gentle swell over it all,
    # and a little jitter so the ground does not read as a sheet.
    flank = 11.0 * smoothstep((abs(x) - 30.0) / 40.0) + 8.0 * smoothstep((abs(x) - 100.0) / 50.0)
    south = 9.0 * smoothstep((-z - 60.0) / 80.0) + 8.0 * smoothstep((-z - 180.0) / 80.0)
    swell = 0.3 * math.sin(x * 0.15) * math.cos(z * 0.12) * smoothstep((math.hypot(x, z) - 6.0) / 10.0)
    jitter = rnd.uniform(-0.08, 0.08) if math.hypot(x, z) < 12.0 else rnd.uniform(-0.25, 0.25)
    if abs(z - VALLEY_RIM_Z) < 1e-3:
        jitter = rnd.uniform(-0.2, 0.0)  # the rim never stands proud of the floor
    return flank + south + swell + jitter


def scene_vert(bm, x, y, z):
    return bm.verts.new((-x, -z, y))


def valley():
    # One glTF of separate nodes: ground_<row>_<col> (grass, walkable) and
    # cliff_<col> (rock faces below the rim, not walkable). The exporter
    # cuts the streamed world into regions by object, so separate chunks
    # give it something to cut.
    reset()
    rnd = random.Random(11)
    per = int(VALLEY_CHUNK / VALLEY_STEP)  # finest quads a chunk
    n, m = per * VALLEY_COLS, per * VALLEY_ROWS
    # Heights on the finest grid, shared by every chunk, so neighbours meet.
    heights = [[valley_height(VALLEY_X0 + i * VALLEY_STEP, VALLEY_Z0 + j * VALLEY_STEP, rnd)
                for i in range(n + 1)] for j in range(m + 1)]

    def stride(r, c):
        return 1 if (r, c) in VALLEY_FINE else 2

    def height(i, j, r, c):
        # A fine chunk's border vertex next to a coarse chunk lies on the
        # coarse edge, so the two meet without a crack.
        s = stride(r, c)
        ii, jj = i - c * per, j - r * per
        for edge, nr, nc, down in [(ii == 0, r, c - 1, True), (ii == per, r, c + 1, True),
                                   (jj == 0, r - 1, c, False), (jj == per, r + 1, c, False)]:
            if not edge or not (0 <= nr < VALLEY_ROWS and 0 <= nc < VALLEY_COLS):
                continue
            ns = stride(nr, nc)
            along = j if down else i  # the coordinate that runs along the edge
            if ns > s and along % ns:
                a = along - along % ns
                t = (along - a) / ns
                if down:
                    return heights[a][i] * (1 - t) + heights[a + ns][i] * t
                return heights[j][a] * (1 - t) + heights[j][a + ns] * t
        return heights[j][i]

    for r in range(VALLEY_ROWS):
        for c in range(VALLEY_COLS):
            s = stride(r, c)
            q = per // s
            bm = bmesh.new()
            uv = bm.loops.layers.uv.new()
            grid = [[None] * (q + 1) for _ in range(q + 1)]
            for b in range(q + 1):
                for a in range(q + 1):
                    i, j = c * per + a * s, r * per + b * s
                    grid[b][a] = scene_vert(bm, VALLEY_X0 + i * VALLEY_STEP, height(i, j, r, c),
                                            VALLEY_Z0 + j * VALLEY_STEP)
            # A texture repeat per quad: no quad's UVs cross a repeat, where
            # the exporter would cut its triangles.
            for b in range(q):
                for a in range(q):
                    f = bm.faces.new((grid[b][a], grid[b + 1][a], grid[b + 1][a + 1], grid[b][a + 1]))
                    for l, (du, dv) in zip(f.loops, [(0, 0), (0, 1), (1, 1), (1, 0)]):
                        l[uv].uv = (du, dv)
            bm.normal_update()
            for f in bm.faces:
                if f.normal.z < 0:
                    f.normal_flip()
            obj_from_bmesh(f"ground_{r}_{c}", bm)
    # The cliff below the rim: per chunk column, the rim row at that column's
    # resolution, then two rows stepping out and down to the sea, jittered by
    # the same table for every column so neighbours meet.
    drops = [(0.6, -5.0), (1.4, VALLEY_SEA_Y - 0.5)]
    jitter = [[(rnd.uniform(-0.3, 0.3), rnd.uniform(-0.6, 0.6), rnd.uniform(-0.4, 0.4)) for _ in range(n + 1)]
              for _ in drops]
    r = VALLEY_ROWS - 1
    for c in range(VALLEY_COLS):
        s = stride(r, c)
        cols = range(c * per, (c + 1) * per + 1, s)
        bm = bmesh.new()
        uv = bm.loops.layers.uv.new()
        rows = [[scene_vert(bm, VALLEY_X0 + i * VALLEY_STEP, height(i, m, r, c), VALLEY_RIM_Z) for i in cols]]
        for k, (dz, y) in enumerate(drops):
            rows.append([scene_vert(bm, VALLEY_X0 + i * VALLEY_STEP + jitter[k][i][0], y + jitter[k][i][1],
                                    VALLEY_RIM_Z + dz + jitter[k][i][2]) for i in cols])
        for j in range(len(rows) - 1):
            for i in range(len(cols) - 1):
                f = bm.faces.new((rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]))
                for l, (du, dv) in zip(f.loops, [(0, 0), (1, 0), (1, 1), (0, 1)]):
                    l[uv].uv = (du, dv)  # one repeat per quad
        bm.normal_update()
        # Faces look out to sea: scene +z is Blender -y.
        for f in bm.faces:
            if f.normal.y > 0:
                f.normal_flip()
        bm.normal_update()
        obj_from_bmesh(f"cliff_{c}", bm)
    export("valley")



# The keep, phase 3: three rooms indoors, in scene coordinates like the
# valley. The hall (x -4..3.9, z 0..11.9) has the way out in its south wall,
# a doorway north into the keeper's study (z 12.1..20) and one east into the
# side chamber (x 4.1..10, z 3..9). The walls between rooms are 0.2 m thick,
# each side a face of the room it looks into, and the doorways are 2 m wide
# and 2.6 m tall with their reveals in the hall. Every quad is 4 m or less
# (8 m quads did not draw in pcsx-redux) and takes one texture repeat per
# 4 m, so no quad's UVs cross a repeat.
KEEP_H = 3.5          # floor to ceiling
KEEP_DOOR_W = 2.0
KEEP_DOOR_H = 2.6
KEEP_TILE = 4.0


def keep_quad(bm, uv, corners, normal):
    # corners in scene coordinates; normal the side it faces, in scene axes.
    verts = [scene_vert(bm, *c) for c in corners]
    f = bm.faces.new(verts)
    f.normal_update()
    want = (-normal[0], -normal[2], normal[1])  # the same direction in Blender's axes
    if f.normal.x * want[0] + f.normal.y * want[1] + f.normal.z * want[2] < 0:
        f.normal_flip()
    axis = max(range(3), key=lambda i: abs(normal[i]))
    a, b = [i for i in range(3) if i != axis]
    lo_a = min(c[a] for c in corners)
    lo_b = min(c[b] for c in corners)
    for l in f.loops:
        # Back from Blender's axes to the scene's for the UV.
        co = l.vert.co
        sc = (-co.x, co.z, -co.y)
        l[uv].uv = ((sc[a] - lo_a) / KEEP_TILE, (sc[b] - lo_b) / KEEP_TILE)


def split(lo, hi):
    # lo..hi in pieces of at most KEEP_TILE.
    n = max(1, math.ceil((hi - lo) / KEEP_TILE - 1e-6))
    return [(lo + (hi - lo) * i / n, lo + (hi - lo) * (i + 1) / n) for i in range(n)]


def keep_floor(bm, uv, x0, x1, z0, z1):
    for a0, a1 in split(x0, x1):
        for b0, b1 in split(z0, z1):
            keep_quad(bm, uv, [(a0, 0, b0), (a1, 0, b0), (a1, 0, b1), (a0, 0, b1)], (0, 1, 0))
            keep_quad(bm, uv, [(a0, KEEP_H, b0), (a1, KEEP_H, b0), (a1, KEEP_H, b1), (a0, KEEP_H, b1)],
                      (0, -1, 0))


def keep_wall(bm, uv, axis, at, lo, hi, normal, door=None):
    # A wall in the plane x = at (axis 0) or z = at (axis 2), running lo..hi
    # along the other axis, with an optional doorway centred on `door`.
    def pt(t, y):
        return (at, y, t) if axis == 0 else (t, y, at)

    def panel(t0, t1, y0, y1):
        for a0, a1 in split(t0, t1):
            for b0, b1 in split(y0, y1):
                keep_quad(bm, uv, [pt(a0, b0), pt(a1, b0), pt(a1, b1), pt(a0, b1)], normal)

    if door is None:
        panel(lo, hi, 0.0, KEEP_H)
        return
    d0, d1 = door - KEEP_DOOR_W / 2, door + KEEP_DOOR_W / 2
    panel(lo, d0, 0.0, KEEP_H)
    panel(d1, hi, 0.0, KEEP_H)
    panel(d0, d1, KEEP_DOOR_H, KEEP_H)


def keep_reveal(bm, uv, axis, a0, a1, door):
    # The doorway's inside faces through a wall from a0 to a1 (along `axis`).
    d0, d1 = door - KEEP_DOOR_W / 2, door + KEEP_DOOR_W / 2
    if axis == 2:  # the wall lies along x, the reveal runs along z
        keep_quad(bm, uv, [(d0, 0, a0), (d0, 0, a1), (d0, KEEP_DOOR_H, a1), (d0, KEEP_DOOR_H, a0)], (1, 0, 0))
        keep_quad(bm, uv, [(d1, 0, a0), (d1, 0, a1), (d1, KEEP_DOOR_H, a1), (d1, KEEP_DOOR_H, a0)], (-1, 0, 0))
        keep_quad(bm, uv, [(d0, KEEP_DOOR_H, a0), (d1, KEEP_DOOR_H, a0), (d1, KEEP_DOOR_H, a1),
                           (d0, KEEP_DOOR_H, a1)], (0, -1, 0))
        keep_quad(bm, uv, [(d0, 0, a0), (d1, 0, a0), (d1, 0, a1), (d0, 0, a1)], (0, 1, 0))
    else:
        keep_quad(bm, uv, [(a0, 0, d0), (a1, 0, d0), (a1, KEEP_DOOR_H, d0), (a0, KEEP_DOOR_H, d0)], (0, 0, 1))
        keep_quad(bm, uv, [(a0, 0, d1), (a1, 0, d1), (a1, KEEP_DOOR_H, d1), (a0, KEEP_DOOR_H, d1)], (0, 0, -1))
        keep_quad(bm, uv, [(a0, KEEP_DOOR_H, d0), (a1, KEEP_DOOR_H, d0), (a1, KEEP_DOOR_H, d1),
                           (a0, KEEP_DOOR_H, d1)], (0, -1, 0))
        keep_quad(bm, uv, [(a0, 0, d0), (a1, 0, d0), (a1, 0, d1), (a0, 0, d1)], (0, 1, 0))


def keep_room(name, build):
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new()
    build(bm, uv)
    obj_from_bmesh(name, bm)


def keep():
    # One glTF of three nodes at the world origin: hall, study, chamber.
    reset()

    def hall(bm, uv):
        keep_floor(bm, uv, -4.0, 3.9, 0.0, 11.9)
        keep_wall(bm, uv, 2, 0.0, -4.0, 3.9, (0, 0, 1), door=0.0)      # south, the way out
        keep_wall(bm, uv, 2, 11.9, -4.0, 3.9, (0, 0, -1), door=0.0)    # north, to the study
        keep_wall(bm, uv, 0, -4.0, 0.0, 11.9, (1, 0, 0))               # west
        keep_wall(bm, uv, 0, 3.9, 0.0, 11.9, (-1, 0, 0), door=6.0)     # east, to the chamber
        keep_reveal(bm, uv, 2, 11.9, 12.1, 0.0)
        keep_reveal(bm, uv, 0, 3.9, 4.1, 6.0)

    def study(bm, uv):
        keep_floor(bm, uv, -4.0, 4.0, 12.1, 20.0)
        keep_wall(bm, uv, 2, 12.1, -4.0, 4.0, (0, 0, 1), door=0.0)
        keep_wall(bm, uv, 2, 20.0, -4.0, 4.0, (0, 0, -1))
        keep_wall(bm, uv, 0, -4.0, 12.1, 20.0, (1, 0, 0))
        keep_wall(bm, uv, 0, 4.0, 12.1, 20.0, (-1, 0, 0))

    def chamber(bm, uv):
        keep_floor(bm, uv, 4.1, 10.0, 3.0, 9.0)
        keep_wall(bm, uv, 0, 4.1, 3.0, 9.0, (1, 0, 0), door=6.0)
        keep_wall(bm, uv, 0, 10.0, 3.0, 9.0, (-1, 0, 0))
        keep_wall(bm, uv, 2, 3.0, 4.1, 10.0, (0, 0, 1))
        keep_wall(bm, uv, 2, 9.0, 4.1, 10.0, (0, 0, -1))

    keep_room("hall", hall)
    keep_room("study", study)
    keep_room("chamber", chamber)
    export("keep")


def arch():
    # The keep's door in the valley: two stone posts 2.8 m tall and a lintel,
    # 2 m clear between the posts, which stand along Blender's Y (the scene's
    # z), so the way through runs along x.
    reset()
    bm = bmesh.new()
    for y in (-1.2, 1.2):
        bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.LocRotScale(
            (0, y, 1.4), None, (0.5, 0.4, 2.8)))
    bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.LocRotScale(
        (0, 0, 3.0), None, (0.6, 2.9, 0.4)))
    bm.normal_update()
    # One texture repeat per face, so the exporter cuts no triangle.
    uv = bm.loops.layers.uv.new()
    for f in bm.faces:
        axis = max(range(3), key=lambda i: abs(f.normal[i]))
        a, b = [i for i in range(3) if i != axis]
        lo = [min(v.co[k] for v in f.verts) for k in (a, b)]
        hi = [max(v.co[k] for v in f.verts) for k in (a, b)]
        for l in f.loops:
            l[uv].uv = ((l.vert.co[a] - lo[0]) / (hi[0] - lo[0]), (l.vert.co[b] - lo[1]) / (hi[1] - lo[1]))
    obj_from_bmesh("arch", bm)
    export("arch")


# The keeper: a robed figure 1.75 m tall, rigged with eleven bones, every
# vertex moved by one bone (rigid parts, as PS1 characters were). Built in
# Blender's axes, facing -Y, which comes into the scene facing +z.
KEEPER_BONES = [
    # name, parent, head, tail
    ("hips", None, (0, 0, 0.9), (0, 0, 1.05)),
    ("spine", "hips", (0, 0, 1.05), (0, 0, 1.25)),
    ("chest", "spine", (0, 0, 1.25), (0, 0, 1.5)),
    ("head", "chest", (0, 0, 1.5), (0, 0, 1.78)),
    ("arm_l", "chest", (0.24, 0, 1.46), (0.26, 0, 1.18)),
    ("forearm_l", "arm_l", (0.26, 0, 1.18), (0.27, -0.04, 0.92)),
    ("arm_r", "chest", (-0.24, 0, 1.46), (-0.26, 0, 1.18)),
    ("forearm_r", "arm_r", (-0.26, 0, 1.18), (-0.27, -0.04, 0.92)),
    ("thigh_l", "hips", (0.1, 0, 0.9), (0.1, 0, 0.48)),
    ("shin_l", "thigh_l", (0.1, 0, 0.48), (0.1, 0, 0.02)),
    ("thigh_r", "hips", (-0.1, 0, 0.9), (-0.1, 0, 0.48)),
    ("shin_r", "thigh_r", (-0.1, 0, 0.48), (-0.1, 0, 0.02)),
]
# Boxes: bone, material, centre, size.
KEEPER_PARTS = [
    ("hips", "robe", (0, 0, 0.97), (0.38, 0.24, 0.16)),
    ("spine", "robe", (0, 0, 1.15), (0.36, 0.22, 0.22)),
    ("chest", "robe", (0, 0, 1.37), (0.44, 0.26, 0.26)),
    ("head", "skin", (0, -0.01, 1.64), (0.2, 0.22, 0.24)),
    ("head", "hood", (0, 0.03, 1.68), (0.26, 0.24, 0.24)),
    ("arm_l", "robe", (0.27, 0, 1.32), (0.12, 0.14, 0.3)),
    ("forearm_l", "robe", (0.28, -0.02, 1.06), (0.11, 0.12, 0.26)),
    ("forearm_l", "skin", (0.28, -0.04, 0.89), (0.08, 0.09, 0.09)),
    ("arm_r", "robe", (-0.27, 0, 1.32), (0.12, 0.14, 0.3)),
    ("forearm_r", "robe", (-0.28, -0.02, 1.06), (0.11, 0.12, 0.26)),
    ("forearm_r", "skin", (-0.28, -0.04, 0.89), (0.08, 0.09, 0.09)),
    ("thigh_l", "robe", (0.11, 0, 0.69), (0.2, 0.26, 0.42)),
    ("shin_l", "robe", (0.12, 0, 0.26), (0.22, 0.28, 0.46)),
    ("thigh_r", "robe", (-0.11, 0, 0.69), (0.2, 0.26, 0.42)),
    ("shin_r", "robe", (-0.12, 0, 0.26), (0.22, 0.28, 0.46)),
]
KEEPER_MATERIALS = [("robe", (0.55, 0.32, 0.22, 1.0)), ("hood", (0.38, 0.22, 0.16, 1.0)),
                    ("skin", (0.85, 0.66, 0.52, 1.0))]


def quat(axis, deg):
    return mathutils.Quaternion(axis, math.radians(deg))


def keeper_action(arm, name, frames, keys):
    # keys: frame -> {bone: quaternion}; bones not given stay at rest.
    arm.animation_data_create()
    act = bpy.data.actions.new(name)
    arm.animation_data.action = act
    for f, pose in keys:
        for pb in arm.pose.bones:
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = pose.get(pb.name, mathutils.Quaternion())
            pb.keyframe_insert("rotation_quaternion", frame=f)
    track = arm.animation_data.nla_tracks.new()
    track.name = name
    track.strips.new(name, 1, act)
    arm.animation_data.action = None
    act.use_fake_user = True


def rigged_figure(name, bones, parts, materials):
    # An armature of `bones` and a mesh of boxes, each box moved by one bone
    # alone; returns the armature object, at rest, for the actions.
    reset()
    scene = bpy.context.scene
    scene.render.fps = 24
    arm_data = bpy.data.armatures.new(name + "_rig")
    arm = bpy.data.objects.new(name + "_rig", arm_data)
    scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    for bname, parent, head, tail in bones:
        b = arm_data.edit_bones.new(bname)
        b.head, b.tail = head, tail
        if parent:
            b.parent = arm_data.edit_bones[parent]
            b.use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")

    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    deform = bm.verts.layers.deform.verify()
    bone_index = {b[0]: i for i, b in enumerate(bones)}
    mat_index = {m[0]: i for i, m in enumerate(materials)}
    for bone, mat, c, s in parts:
        r = bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.LocRotScale(c, None, s))
        for v in r["verts"]:
            v[deform][bone_index[bone]] = 1.0
        for f in {f for v in r["verts"] for f in v.link_faces}:
            f.material_index = mat_index[mat]
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    for mname, color in materials:
        m = bpy.data.materials.new(mname)
        m.diffuse_color = color
        # glTF takes the colour from the Principled BSDF.
        bsdf = m.node_tree.nodes.get("Principled BSDF") if m.node_tree else None
        if bsdf:
            bsdf.inputs["Base Color"].default_value = color
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    for bname, *_ in bones:
        ob.vertex_groups.new(name=bname)
    ob.parent = arm
    mod = ob.modifiers.new("rig", "ARMATURE")
    mod.object = arm
    return arm


def export_rigged(name):
    os.makedirs(OUT, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, name + ".glb"), export_format="GLB",
                              export_apply=True, export_skins=True, export_animations=True,
                              export_animation_mode="ACTIONS")


def keeper():
    arm = rigged_figure("keeper", KEEPER_BONES, KEEPER_PARTS, KEEPER_MATERIALS)
    # idle: two seconds of breathing, the head looking slowly about.
    keeper_action(arm, "idle", 48, [
        (1, {}),
        (12, {"chest": quat((1, 0, 0), 3), "head": quat((0, 0, 1), 12)}),
        (24, {"chest": quat((1, 0, 0), 0), "arm_l": quat((0, 1, 0), 4), "arm_r": quat((0, 1, 0), -4)}),
        (36, {"chest": quat((1, 0, 0), 3), "head": quat((0, 0, 1), -12)}),
        (48, {}),
    ])
    # talk: one second, the head nodding and the right forearm raised and
    # waving as the keeper speaks.
    up = quat((1, 0, 0), -70)
    keeper_action(arm, "talk", 24, [
        (1, {"forearm_r": up, "arm_r": quat((1, 0, 0), -50)}),
        (6, {"forearm_r": quat((1, 0, 0), -85) @ quat((0, 1, 0), 20), "arm_r": quat((1, 0, 0), -60),
             "head": quat((1, 0, 0), 10)}),
        (12, {"forearm_r": up, "arm_r": quat((1, 0, 0), -50), "head": quat((1, 0, 0), -4),
              "chest": quat((0, 0, 1), 5)}),
        (18, {"forearm_r": quat((1, 0, 0), -85) @ quat((0, 1, 0), -20), "arm_r": quat((1, 0, 0), -60),
              "head": quat((1, 0, 0), 10)}),
        (24, {"forearm_r": up, "arm_r": quat((1, 0, 0), -50)}),
    ])
    export_rigged("keeper")


# The Warden, phase 4: a tall cloaked figure, 2.1 m to the top of the hood,
# rigged like the keeper (eleven bones under the hips, rigid parts) and built
# the same way, in Blender's axes facing -Y. Pose rotations are in each
# bone's own axes: about X, a negative angle swings a hanging bone (an arm
# or a leg) forward, a positive one tips an upright bone (the spine, chest,
# head) forward.
WARDEN_BONES = [
    ("hips", None, (0, 0, 1.08), (0, 0, 1.25)),
    ("spine", "hips", (0, 0, 1.25), (0, 0, 1.48)),
    ("chest", "spine", (0, 0, 1.48), (0, 0, 1.78)),
    ("head", "chest", (0, 0, 1.78), (0, 0, 2.1)),
    ("arm_l", "chest", (0.3, 0, 1.72), (0.32, 0, 1.38)),
    ("forearm_l", "arm_l", (0.32, 0, 1.38), (0.33, -0.04, 1.06)),
    ("arm_r", "chest", (-0.3, 0, 1.72), (-0.32, 0, 1.38)),
    ("forearm_r", "arm_r", (-0.32, 0, 1.38), (-0.33, -0.04, 1.06)),
    ("thigh_l", "hips", (0.12, 0, 1.08), (0.12, 0, 0.56)),
    ("shin_l", "thigh_l", (0.12, 0, 0.56), (0.12, 0, 0.02)),
    ("thigh_r", "hips", (-0.12, 0, 1.08), (-0.12, 0, 0.56)),
    ("shin_r", "thigh_r", (-0.12, 0, 0.56), (-0.12, 0, 0.02)),
]
WARDEN_PARTS = [
    ("hips", "cloak", (0, 0, 1.16), (0.44, 0.28, 0.2)),
    ("spine", "cloak", (0, 0, 1.37), (0.42, 0.26, 0.26)),
    ("chest", "cloak", (0, 0, 1.63), (0.58, 0.32, 0.32)),
    ("head", "mask", (0, -0.03, 1.92), (0.2, 0.2, 0.24)),
    ("head", "eyes", (0, -0.13, 1.95), (0.16, 0.02, 0.04)),
    ("head", "hood", (0, 0.03, 1.97), (0.3, 0.28, 0.3)),
    ("arm_l", "cloak", (0.33, 0, 1.55), (0.14, 0.16, 0.36)),
    ("forearm_l", "cloak", (0.34, -0.02, 1.24), (0.13, 0.14, 0.3)),
    ("forearm_l", "mask", (0.34, -0.04, 1.03), (0.09, 0.1, 0.1)),
    ("arm_r", "cloak", (-0.33, 0, 1.55), (0.14, 0.16, 0.36)),
    ("forearm_r", "cloak", (-0.34, -0.02, 1.24), (0.13, 0.14, 0.3)),
    ("forearm_r", "mask", (-0.34, -0.04, 1.03), (0.09, 0.1, 0.1)),
    ("thigh_l", "cloak", (0.13, 0, 0.82), (0.22, 0.28, 0.52)),
    ("shin_l", "boots", (0.13, 0, 0.3), (0.2, 0.26, 0.56)),
    ("thigh_r", "cloak", (-0.13, 0, 0.82), (0.22, 0.28, 0.52)),
    ("shin_r", "boots", (-0.13, 0, 0.3), (0.2, 0.26, 0.56)),
]
WARDEN_MATERIALS = [("cloak", (0.16, 0.17, 0.22, 1.0)), ("hood", (0.1, 0.1, 0.14, 1.0)),
                    ("mask", (0.78, 0.76, 0.7, 1.0)), ("eyes", (1.0, 0.45, 0.2, 1.0)),
                    ("boots", (0.08, 0.07, 0.07, 1.0))]


def stride(swing, knee, arm, lean):
    # One pose of a walk cycle, the left leg forward by `swing` degrees and
    # the right back, the back knee bent by `knee`, the arms swinging the
    # other way by `arm`, the chest tipped forward by `lean`.
    x = (1, 0, 0)
    return {"thigh_l": quat(x, -swing), "shin_l": quat(x, 4), "thigh_r": quat(x, swing),
            "shin_r": quat(x, knee), "arm_l": quat(x, arm), "arm_r": quat(x, -arm),
            "chest": quat(x, lean)}


def passing(knee, lean):
    # Mid-stride: the right leg passing under the body, its knee lifted.
    x = (1, 0, 0)
    return {"thigh_r": quat(x, -12), "shin_r": quat(x, knee), "thigh_l": quat(x, 4), "chest": quat(x, lean)}


def mirrored(pose):
    swap = {"l": "r", "r": "l"}
    out = {}
    for bone, q in pose.items():
        side = bone.rsplit("_", 1)
        out[side[0] + "_" + swap[side[1]] if len(side) == 2 and side[1] in swap else bone] = q
    return out


def warden():
    arm = rigged_figure("warden", WARDEN_BONES, WARDEN_PARTS, WARDEN_MATERIALS)
    # walk: one second a cycle (two steps) at his patrol pace.
    a, b = stride(24, 28, 18, 4), passing(42, 4)
    keeper_action(arm, "walk", 24, [(1, a), (7, b), (13, mirrored(a)), (19, mirrored(b)), (25, a)])
    # run: two thirds of a second a cycle, longer strides, leaning in.
    a, b = stride(38, 50, 36, 14), passing(70, 14)
    keeper_action(arm, "run", 16, [(1, a), (5, b), (9, mirrored(a)), (13, mirrored(b)), (17, a)])
    # idle: two seconds, the head turning slowly as he watches.
    keeper_action(arm, "idle", 48, [
        (1, {}),
        (16, {"head": quat((0, 0, 1), 25), "chest": quat((1, 0, 0), 2)}),
        (32, {"head": quat((0, 0, 1), -25), "chest": quat((1, 0, 0), 2)}),
        (48, {}),
    ])
    export_rigged("warden")


def box_uv(bm):
    # One texture repeat per face, so the exporter cuts no triangle.
    uv = bm.loops.layers.uv.new()
    for f in bm.faces:
        axis = max(range(3), key=lambda i: abs(f.normal[i]))
        a, b = [i for i in range(3) if i != axis]
        lo = [min(v.co[k] for v in f.verts) for k in (a, b)]
        hi = [max(v.co[k] for v in f.verts) for k in (a, b)]
        for l in f.loops:
            l[uv].uv = ((l.vert.co[a] - lo[0]) / (hi[0] - lo[0]), (l.vert.co[b] - lo[1]) / (hi[1] - lo[1]))


def shrine():
    # A wayside save shrine, phase 4: a stepped stone base, a pillar and a
    # lantern housing on top, 1.7 m tall, its origin at the foot.
    reset()
    bm = bmesh.new()
    for c, s in [((0, 0, 0.15), (1.0, 1.0, 0.3)), ((0, 0, 0.75), (0.5, 0.5, 0.9)),
                 ((0, 0, 1.4), (0.8, 0.8, 0.4)), ((0, 0, 1.65), (0.5, 0.5, 0.1))]:
        bmesh.ops.create_cube(bm, size=1.0, matrix=mathutils.Matrix.LocRotScale(c, None, s))
    bm.normal_update()
    box_uv(bm)
    obj_from_bmesh("shrine", bm)
    export("shrine")


ground()
beacon()
cliff()
sea()
valley()
keep()
arch()
keeper()
warden()
shrine()
