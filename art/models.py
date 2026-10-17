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


ground()
beacon()
cliff()
sea()
valley()
