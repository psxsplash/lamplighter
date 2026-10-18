# Writes the Lamplighter scene files, the build list and disc.json into project/.
#   python3 -P tools/scenes.py [project-dir]
# Run tools/build.sh to regenerate everything (art, import, scenes) in order.
import json
import math
import os
import sys

PROJECT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "project")

# Build order: scene 0 is where the game starts, Scene.Load(i) opens scene i.
SCENES = ["title", "valley", "keep", "lighthouse"]

# CD-DA music, disc tracks 2 and up: Audio.PlayCDDA(2) is the title theme.
TRACKS = ["music/title.ogg", "music/valley.ogg"]

# Every scene carries the same memory card settings, or a save made in one
# scene is not found from another.
MEMCARD = {"enabled": True, "region": "BA", "product": "LAMP-00001", "title": "LAMPLIGHTER",
           "icons": ["textures/icon.png"]}

# Rotations as quaternions (x, y, z, w).
TURN_AROUND = (0.0, 1.0, 0.0, 0.0)       # 180 degrees about Y
LOOK_DOWN_50 = (0.4226, 0.0, 0.0, 0.9063)  # 50 degrees about X: pointing down and away
YAW_25 = (0.0, 0.2164, 0.0, 0.9763)        # 25 degrees about Y
YAW_145 = (0.0, 0.9537, 0.0, 0.3007)       # 145 degrees about Y

# The render buffer every scene fits in: the valley's need (145188 bytes at
# phase 2) with some room. Its ordering table is under the title's own.
RENDER_BUMP = 160 * 1024

# Colours, 0..1.
AMBER = [1.0, 0.78, 0.42]
PALE = [0.82, 0.84, 0.9]
DIM = [0.55, 0.6, 0.75]
SILHOUETTE = (0.32, 0.32, 0.42, 1.0)  # material tint for far-off shapes at night


def transform(pos=(0.0, 0.0, 0.0), rot=(0.0, 0.0, 0.0, 1.0), scale=(1.0, 1.0, 1.0)):
    return {"position": list(pos), "rotation": list(rot), "scale": list(scale)}


def obj(name, components, pos=(0.0, 0.0, 0.0), children=None, **kw):
    return {"name": name, "active": True, "transform": transform(pos, **kw),
            "components": components, "children": children or []}


def mesh(path, texture=None, color=(1.0, 1.0, 1.0, 1.0)):
    return {"type": "mesh", "mesh": path, "materials": [{"texture": texture, "color": list(color)}],
            "bitDepth": 8, "vertexColors": "baked", "flatColor": [128, 128, 128],
            "smoothNormals": True, "uvOffsetMaterial": 0, "dynamicLighting": "auto"}


def collider():
    return {"type": "collider", "kind": "static", "platform": False}


def script(path):
    return {"type": "script", "lua": path}


def player(nav=None):
    p = {"type": "player", "playerHeight": 1.8, "playerRadius": 0.5, "moveSpeed": 3.0,
         "sprintSpeed": 8.0, "maxStepHeight": 0.35, "walkableSlopeAngle": 46.0,
         "navCellSize": 0.05, "navCellHeight": 0.025, "navMinRegionArea": 8,
         "navMergeRegionArea": 20, "navMaxSimplifyError": 1.3, "navMaxEdgeLength": 12.0,
         "navPartitionMethod": "watershed", "navDetailSampleDist": 6.0,
         "navDetailMaxError": 0.025, "navMaxPlaneError": 0.15, "jumpHeight": 2.0,
         "gravity": 20.0}
    p.update(nav or {})
    return p


def sun(color=(1.0, 0.95, 0.85), intensity=0.75):
    return {"type": "light", "kind": "directional", "color": list(color), "intensity": intensity,
            "range": 10.0, "spotAngle": 30.0, "innerSpotAngle": 0.0, "enabled": True,
            "runtime": False}


def lamp(color, intensity, range_, enabled=False):
    # A point light lit on the console (runtime): it goes in psxsplash's light
    # table, at most 16 a scene, where Light.Find finds it by its object's name.
    return {"type": "light", "kind": "point", "color": list(color), "intensity": intensity,
            "range": range_, "spotAngle": 30.0, "innerSpotAngle": 0.0, "enabled": enabled,
            "runtime": True}


def baked_lamp(color, intensity, range_):
    # A point light baked into the vertex colours at export, not lit on the console.
    return {"type": "light", "kind": "point", "color": list(color), "intensity": intensity,
            "range": range_, "spotAngle": 30.0, "innerSpotAngle": 0.0, "enabled": True,
            "runtime": False}


# The editor's Terrain nav bake preset (core/scene.cpp applyNavPreset): the ten
# region-building fields. Step height and slope stay the player's own.
TERRAIN_NAV = {"navCellSize": 0.08, "navCellHeight": 0.04, "navMinRegionArea": 4,
               "navMergeRegionArea": 6, "navMaxSimplifyError": 0.4, "navMaxEdgeLength": 5.0,
               "navPartitionMethod": "monotone", "navDetailSampleDist": 4.0,
               "navDetailMaxError": 0.02, "navMaxPlaneError": 0.1}

# The valley's nav, phase 4: the Terrain preset made 2468 regions over the
# 448 m valley, and psxsplash's path search (Actor.FindPath's and the
# agents') finds no path at all in a scene of more than 256 (navregion.cpp,
# NAV_MAX_SEARCH_REGIONS), which the Warden walks by. Watershed regions, simplified harder and allowed longer
# edges, make under 200 that follow the ground's swells as closely as the
# preset's long monotone strips did.
VALLEY_NAV = dict(TERRAIN_NAV, navPartitionMethod="watershed", navMaxSimplifyError=3.0,
                  navMaxEdgeLength=40.0, navMergeRegionArea=400)


def interactable(radius, button, repeatable=True):
    # button is a pad bit: 13 Circle, 14 Cross (which also jumps).
    return {"type": "interactable", "radius": radius, "button": button, "repeatable": repeatable,
            "cooldownFrames": 30, "showPrompt": False, "promptCanvas": "", "lineOfSight": False,
            "facingAngle": 90.0}


def trigger(size, lua):
    return {"type": "trigger", "size": list(size), "lua": lua}


def walkoff(size):
    # Nav boundary edges whose midpoint lies in this box let the player walk off.
    return {"type": "walkoff", "size": list(size)}


def audio(clip, name, loop=False, volume=100):
    return {"type": "audio", "clip": clip, "clipName": name, "sampleRate": 22050, "loop": loop,
            "defaultVolume": volume, "trimLeadingSilence": False}


# UI. Rects are screen pixels on the 320 x 240 screen, anchored to its top
# left unless stretched; colours are 0..1.

def ttf_font(name, path, size):
    return {"name": name, "source": path, "size": size}


def bitmap_font(name, path, cell, advance):
    return {"name": name, "bitmap": path, "glyphWidth": cell[0], "glyphHeight": cell[1],
            "advances": [advance] * 96}


# The game's two fonts: the title in a TTF, the menu in a bitmap sheet from
# art/bitmapfont.py (16 x 24 cells, 12 px a glyph).
FONTS = [ttf_font("title", "fonts/EBGaramond12-Bold.ttf", 28),
         bitmap_font("menu", "fonts/menu.png", (16, 24), 12)]


def element(kind, name, rect, color, visible=True, stretch=False, **fields):
    a1 = [1.0, 1.0] if stretch else [0.0, 0.0]
    return dict({"type": kind, "name": name, "visible": visible, "rect": list(rect),
                 "anchorMin": [0.0, 0.0], "anchorMax": a1, "color": list(color)}, **fields)


def text(name, s, x, y, w, h, color, font=None, visible=True):
    # psxsplash draws custom-font glyphs as textured sprites, where colour 128
    # is full intensity, so their colour is stored halved to show as given.
    # The system font is drawn at the colour as it is.
    if font:
        color = [c / 2 for c in color]
    return element("text", name, (x, y, w, h), color, visible, text=s, font=font)


def box(name, rect, color, stretch=False):
    return element("box", name, rect, color, stretch=stretch)


def progress(name, rect, color, background, value=0):
    return element("progress", name, rect, color, background=list(background), value=value)


def sheet_image(name, sheet, cell, x, y):
    # A UI image showing one 16 x 16 cell of a scene sprite sheet. Textured
    # UI is drawn at its colour over 128, so the neutral tint is stored halved.
    return element("image", name, (x, y, 16, 16), [0.5, 0.5, 0.5], texture=None, bitDepth=4,
                   cutout=True, sheet=sheet, cell=cell)


def canvas(name, elements, sortOrder=0, defaultFont=None, visible=True):
    return {"name": name, "visible": visible, "sortOrder": sortOrder, "defaultFont": defaultFont,
            "elements": elements}


def loading_canvas(caption):
    # Shown while the scene loads (settings.loadingCanvas): the game's name,
    # the scene's caption (none when empty) and a bar psxsplash fills, the
    # progress element named "loading".
    caption_el = [text("caption", caption, 160 - 6 * len(caption), 124, 12 * len(caption), 24, DIM,
                       font="menu")] if caption else []
    return canvas("Loading", [
        box("backdrop", (0, 0, 0, 0), [0.03, 0.04, 0.09], stretch=True),
        text("name", "Lamplighter", 91, 84, 140, 36, AMBER, font="title"),
        *caption_el,
        progress("loading", (80, 168, 160, 6), AMBER, [0.12, 0.13, 0.2]),
    ], sortOrder=255)


def title_canvas():
    # The menu: title.lua moves "cursor" between the items, shows "continue"
    # only when the memory card holds a save, and recolours the picked item.
    return canvas("Title", [
        text("title", "LAMPLIGHTER", 60, 30, 210, 36, AMBER, font="title"),
        text("tagline", "Relight the beacons", 84, 70, 160, 10, DIM),
        # Shown by title.lua after a fall off the valley's cliffs.
        text("lost", "You fell from the cliff edge", 48, 104, 230, 10, AMBER, visible=False),
        # Shown by title.lua after the Warden caught the player (scripts/warden.lua).
        text("caught", "The Warden caught you", 76, 104, 180, 10, AMBER, visible=False),
        # Shown by title.lua after the lighthouse's credits (scripts/lighthouse.lua).
        text("lit", "The valley is lit again", 68, 104, 190, 10, AMBER, visible=False),
        text("newgame", "New game", 112, 148, 100, 24, PALE, font="menu"),
        text("continue", "Continue", 112, 172, 100, 24, PALE, font="menu", visible=False),
        # The unlit lantern, cell 0 of the lantern sheet, centred on the item's line.
        sheet_image("cursor", "lantern", 0, 92, 152),
        text("hint", "UP/DOWN choose   X select", 60, 222, 220, 10, DIM),
    ])


# Cutscenes and animations, phase 5. Frames are 30 a second. Values are in
# each track's units (docs/scene-format.md in splashedit-ng): scene metres
# for camera and light positions, Euler degrees for rotations (yaw 0 looks
# along +z, yaw 90 along +x), 0..1 colours, 0/1 for visibility, rumble and
# light switches, pixels for UI positions, the light's own intensity.

def key(frame, *value, interp="linear"):
    v = list(value) + [0.0] * (3 - len(value))
    return {"frame": frame, "value": [float(x) for x in v], "interp": interp}


def track(kind, target, *keys):
    return {"type": kind, "target": target, "keyframes": list(keys)}


def sequence(name, frames, *tracks):
    # A cutscene (Cutscene.Play) or an animation (Animation.Play): at most
    # 8 tracks of 64 keys each. Cutscenes also carry audioEvents.
    return {"name": name, "durationFrames": frames, "tracks": list(tracks)}


def cutscene(name, frames, *tracks):
    return dict(sequence(name, frames, *tracks), audioEvents=[])


def look(frm, to):
    # The camera rotation (pitch, yaw) that looks from `frm` towards `to`.
    dx, dy, dz = (to[i] - frm[i] for i in range(3))
    yaw = math.degrees(math.atan2(dx, dz))
    pitch = math.degrees(math.atan2(-dy, math.hypot(dx, dz)))
    return pitch, yaw


def lantern_sheet(anims=()):
    # art/textures.py's lantern sheet: cell 0 unlit, cells 1-4 a flickering
    # flame. `dark` and `flame` are the valley tally's (scripts/valley.lua);
    # the title only shows cell 0 as its menu cursor and plays none.
    return {"name": "lantern", "texture": "textures/lantern.png", "bitDepth": 4,
            "cellWidth": 16, "cellHeight": 16, "anims": list(anims)}


def sprite_anim(name, first, count, duration, loop=True):
    return {"name": name, "firstFrame": first, "frameCount": count, "frameDuration": duration,
            "loop": loop}


def scene(objects, sceneType="exterior", script=None, canvases=(), loading=None,
          sky=(0.5, 0.5, 0.6), fog=0, stream=False, bump=0, cutscenes=(), animations=(),
          spriteSheets=()):
    # psxsplash clears the screen to the fog colour, fog on or off: `sky`.
    # `fog` is the density, 0 for none: the far plane is 20000 / density in
    # screen depth, about 98 m at 5 with this GTE scaling.
    settings = {"gteScaling": 100.0, "sceneType": sceneType,
                "fog": {"enabled": fog > 0, "color": list(sky), "density": fog or 5},
                "networkId": "", "script": script, "memCard": dict(MEMCARD)}
    if bump:
        # psxsplash sizes its render buffers once, from the first scene it
        # loads, and stops on a later scene that needs more: the title (scene
        # 0) asks for the most any scene needs (`bump=` in export --stats).
        settings["bumpAllocatorSize"] = bump
    if stream:
        # Static scenery streams off the disc by region (no CD-DA in such a scene).
        settings["streamWorld"] = True
    canvases = list(canvases)
    if loading is not None:
        settings["loadingCanvas"] = "Loading"
        canvases.append(loading_canvas(loading))
    out = {"format": "splashedit-ng/scene", "version": 1, "settings": settings,
           "objects": objects, "fonts": [dict(f) for f in FONTS], "canvases": canvases}
    if cutscenes:
        out["cutscenes"] = list(cutscenes)
    if animations:
        out["animations"] = list(animations)
    if spriteSheets:
        out["spriteSheets"] = list(spriteSheets)
    return out


def title():
    # Night on a headland: the player stands 4 m back from the cliff edge
    # (z = 6), a dark beacon at the rim, the sea 12 m below and a long, low
    # headland across the bay, darkened to a silhouette, with its own dark
    # beacon on the skyline. The cliff model drops towards its -Z, so the near one is turned
    # around and the far one, angled a little, faces the player.
    moon = sun(color=(0.55, 0.62, 0.9), intensity=0.6)
    return scene([
        obj("Cliff", [mesh("models/cliff.mesh", "textures/rock.png"), collider()], rot=TURN_AROUND),
        obj("Beacon", [mesh("models/beacon.mesh", "textures/stone.png"), collider()],
            pos=(2.0, 0.0, 4.8)),
        obj("Sea", [mesh("models/sea.mesh", "textures/sea.png", color=(0.7, 0.75, 0.9, 1.0))],
            pos=(0.0, -12.0, 40.0)),
        obj("Headland", [mesh("models/cliff.mesh", "textures/rock.png", color=SILHOUETTE)],
            pos=(-8.0, 0.0, 50.0), rot=YAW_25, scale=(2.0, 1.0, 1.5)),
        obj("Far beacon", [mesh("models/beacon.mesh", "textures/stone.png", color=SILHOUETTE)],
            pos=(-8.0, 0.0, 52.0), scale=(1.5, 1.5, 1.5)),
        # Half a metre up: the exporter puts the eyes on the first surface
        # below the player, and the jittered cliff top is not flat.
        obj("Player", [player()], pos=(0.0, 0.5, 2.0)),
        obj("Menu", [script("scripts/title.lua")]),
        obj("Moon", [moon], rot=LOOK_DOWN_50),
    ], canvases=[title_canvas()], loading="", sky=(0.03, 0.04, 0.1), bump=RENDER_BUMP,
        spriteSheets=[lantern_sheet()])


# The valley's terrain: art/models.py builds a 14 x 14 grid of 32 m ground
# chunks (x -224..224, z -440..8) and a cliff face under each chunk of the north
# rim at z = 8, all as nodes of models/valley at the world origin.
VALLEY_COLS = VALLEY_ROWS = 14
VALLEY_RIM_Z = 8.0
VALLEY_SEA_Y = -12.0
FOG = (0.45, 0.5, 0.58)
EMBER = (1.0, 0.62, 0.25)

# The beacons: name, base position. Bases sit 0.6 m into the ground, which
# swells and dips by up to 0.55 m away from the start. BeaconA is 5 m ahead of
# the start, right of the way to the rim and in reach after a few steps;
# the others are further up the valley.
BEACONS = [("BeaconA", (2.0, -0.6, 5.0)), ("BeaconB", (-12.0, -0.6, -18.0)),
           ("BeaconC", (14.0, -0.6, -36.0))]


def beacon(name, pos):
    # beacons.blocks, shared by all three, tells them apart by `my name`:
    # interacting remembers beacon_<name> = 1 and turns on <name>_light.
    # psxsplash measures the reach from the player's eyes to the object's
    # origin, the buried base, so 5 m is about 4.3 m across the ground.
    return obj(name, [mesh("models/beacon.mesh", "textures/stone.png"), collider(),
                      interactable(5.0, 13, repeatable=False), script("scripts/beacons.blocks")],
               pos=pos)


def beacon_light(name, pos):
    # Over the beacon's cap, dark until lit.
    return obj(name + "_light", [lamp(EMBER, 2.0, 9.0)], pos=(pos[0], pos[1] + 2.9, pos[2]))


# The Warden: models/warden, a skinned mesh with the clips walk, run and
# idle. psxsplash's agent moves him: round the four corners of his patrol on
# the nav regions, and after the player once he sees him, playing idle,
# walk or run for the state he is in (the clips loop); scripts/warden.lua
# says when to chase, give up and pause at a corner. He starts at the first
# corner. A script, a skin or an agent keeps an
# object out of the streamed regions, so he is always loaded.
WARDEN_CLIPS = ["models/warden/walk.anim", "models/warden/run.anim", "models/warden/idle.anim"]
# Cloak, hood, mask, eyes and boots, in the order of the model's materials.
WARDEN_COLOURS = [(0.16, 0.17, 0.22, 1.0), (0.1, 0.1, 0.14, 1.0), (0.78, 0.76, 0.7, 1.0),
                  (1.0, 0.45, 0.2, 1.0), (0.08, 0.07, 0.07, 1.0)]
WARDEN_START = (-18.0, 0.0, -30.0)
# The patrol's corners (x, z), round between BeaconB and BeaconC, south of
# the start, all at his start height: the ground there is within 0.55 m of
# it, and the agent takes his height from the nav floor as he walks.
WARDEN_PATROL = [(-18.0, -30.0), (0.0, -44.0), (20.0, -24.0), (2.0, -22.0)]
# The agent stores its speed as whole GTE units a frame (at the valley's GTE
# scaling of 100, 30 frames a second); 2 a frame is his walk, 1.46 m/s.
WARDEN_WALK = 2 * 30 * 100 / 4096

# Save shrines, phase 4: name, foot. Circle in reach saves the game
# (scripts/shrine.lua); Continue on the title puts the player back 3 m in
# front of the shrine saved at (scripts/valley.lua). Shrine 1 is 7 m to the
# right of the start, Shrine 2 beyond BeaconC, both clear of the patrol.
SHRINES = [("Shrine 1", (7.0, -0.2, 0.0)), ("Shrine 2", (26.0, -0.2, -44.0))]
SHRINE_GLOW = (0.6, 0.75, 1.0)


def warden():
    m = mesh("models/warden/warden.mesh")
    m["materials"] = [{"texture": None, "color": list(c)} for c in WARDEN_COLOURS]
    return obj("Warden", [m, skin(WARDEN_CLIPS), script("scripts/warden.lua"), warden_agent()],
               pos=WARDEN_START)


def warden_agent():
    # Sees all round, 10 m (a square: psxsplash takes the larger of the x and
    # z distances), as far as 8 nav regions away, which on the valley's
    # coarse nav is no limit inside 10 m. 60 engine updates unseen (about
    # four seconds at the valley's frame rate) and he has lost the player.
    # Deaf.
    return {"type": "agent", "startEnabled": True, "moveSpeed": WARDEN_WALK, "stopDistance": 0.5,
            "vision": True, "visionRange": 10.0, "fov": 360.0, "visionRegionDepth": 8,
            "hearingRange": 0.0, "alertTimeout": 60,
            "waypoints": [[x, WARDEN_START[1], z] for x, z in WARDEN_PATROL],
            # Indices into WARDEN_CLIPS.
            "stateClips": {"Idle": 2, "Patrol": 0, "Seek": 1}}


def shrine(name, pos):
    # psxsplash measures the reach from the eyes to the shrine's foot, so
    # 4 m is about 3.5 m across the ground.
    return obj(name, [mesh("models/shrine/shrine.mesh", "textures/stone.png"), collider(),
                      interactable(4.0, 13), script("scripts/shrine.lua")], pos=pos)


def shrine_light(name, pos):
    # A pale lamp in the lantern housing, lit from the start.
    return obj(name + "_light", [lamp(SHRINE_GLOW, 1.2, 5.0, enabled=True)],
               pos=(pos[0], pos[1] + 1.4, pos[2]))


def shrine_canvas():
    # shrine.lua shows "saved" for two seconds after a save, or says the
    # card did not take it.
    return canvas("Shrine", [
        text("saved", "", 40, 200, 240, 10, PALE, visible=False),
    ], sortOrder=10)


# Phase 5. psxsplash draws a UI box opaque (uisystem.cpp), so a fade is a
# full-screen box whose colour runs between the fog's and black, not a
# blend over the scene.

# The lighthouse gate: 14 m to the right of the start and 2 m back from it,
# inland of the rim and clear of the Warden's patrol (its nearest corner is 23 m off).
# with all three beacons lit opens the lighthouse (scene 3); otherwise the
# `gate` cutscene says what is missing (scripts/lighthouse_gate.lua).
LIGHTHOUSE_GATE = (14.0, -0.3, -2.0)


def story_canvas():
    # The intro's fade and line, and the gate's refusal; hidden until a
    # cutscene shows them.
    return canvas("Story", [dict(e, visible=False) for e in [
        box("fade", (0, 0, 0, 0), [0.0, 0.0, 0.0], stretch=True),
        text("intro", "The beacons have gone dark", 56, 200, 210, 10, FOG),
        text("gate", "The lamp needs all three beacons", 32, 200, 260, 10, PALE)]], sortOrder=20)


def gameover_canvas():
    # Over everything: the fade and the line, which warden.lua and fall.lua
    # set ("Caught by the Warden", "You fell") before the `gameover` cutscene.
    return canvas("Gameover", [dict(e, visible=False) for e in [
        box("fade", (0, 0, 0, 0), list(FOG), stretch=True),
        text("line", "", 80, 116, 160, 10, [0.0, 0.0, 0.0])]], sortOrder=30)


# The intro, once a New game (Persist `intro`, scripts/valley.lua): out of
# black into the fog over the sea, then a sweep from the cliff rim back over
# the dark beacons and down to the player's eyes, the line fading in and out
# of the fog colour on the way. valley.lua holds the player's controls until
# it ends.
INTRO_PATH = [
    # frame, camera position, the point it looks at
    (0, (0.0, 5.0, 13.0), (0.0, 1.0, -6.0)),
    (60, (-2.0, 6.5, 4.0), (2.0, 0.5, -12.0)),
    (120, (-6.0, 8.0, -10.0), (14.0, 0.0, -36.0)),
    (170, (6.0, 6.0, -24.0), (-12.0, 1.0, -18.0)),
    (230, (0.0, 2.2, -2.0), (0.0, 2.0, 8.0)),
]


def unwrap(yaws):
    # Yaw keys interpolate linearly: keep each within half a turn of the last.
    out = [yaws[0]]
    for y in yaws[1:]:
        while y - out[-1] > 180:
            y -= 360
        while y - out[-1] < -180:
            y += 360
        out.append(y)
    return out


def camera_path(path, interp="easeInOut"):
    looks = [look(p, t) for _, p, t in path]
    yaws = unwrap([y for _, y in looks])
    return (track("cameraPosition", "", *[key(f, *p, interp=interp) for f, p, _ in path]),
            track("cameraRotation", "", *[key(f, looks[i][0], yaws[i], 0.0, interp=interp)
                                          for i, (f, _, _) in enumerate(path)]))


def valley_cutscenes():
    black, fog = (0.0, 0.0, 0.0), FOG
    intro = cutscene("intro", 240,
        *camera_path(INTRO_PATH),
        track("uiElementVisible", "Story/fade", key(0, 1, interp="step"), key(24, 0, interp="step")),
        track("uiColor", "Story/fade", key(0, *black), key(24, *fog)),
        track("uiElementVisible", "Story/intro", key(0, 0, interp="step"), key(40, 1, interp="step"),
              key(200, 0, interp="step")),
        track("uiColor", "Story/intro", key(40, *fog), key(70, *AMBER), key(170, *AMBER), key(200, *fog)))
    # Its last key is short of the end: psxsplash ends a cutscene on the
    # first frame past its length, which can skip a key on the last frame.
    gate = cutscene("gate", 66,
        track("uiElementVisible", "Story/gate", key(0, 1, interp="step"), key(60, 0, interp="step")))
    # The game over, in place: the fog closes in and goes black, the line
    # comes up out of the dark; warden.lua or fall.lua then loads the title.
    gameover = cutscene("gameover", 90,
        track("uiElementVisible", "Gameover/fade", key(0, 1, interp="step")),
        track("uiColor", "Gameover/fade", key(0, *fog), key(30, *black)),
        track("uiElementVisible", "Gameover/line", key(20, 1, interp="step")),
        track("uiColor", "Gameover/line", key(20, *black), key(45, *AMBER)))
    return [intro, gate, gameover]


def valley():
    # Dusk in a fog-bound valley that ends to the north in a cliff over the
    # sea. The player starts 8 m from the rim facing it (+z), BeaconA close
    # by on the right.
    ground = [obj(f"Ground {r}-{c}", [mesh(f"models/valley/ground_{r}_{c}.mesh", "textures/grass.png"),
                                      collider()])
              for r in range(VALLEY_ROWS) for c in range(VALLEY_COLS)]
    cliffs = [obj(f"Cliff {c}", [mesh(f"models/valley/cliff_{c}.mesh", "textures/rock.png")])
              for c in range(VALLEY_COLS)]
    return scene([
        *ground,
        *cliffs,
        obj("Sea", [mesh("models/sea.mesh", "textures/sea.png", color=(0.7, 0.75, 0.9, 1.0))],
            pos=(0.0, VALLEY_SEA_Y, VALLEY_RIM_Z + 48.0), scale=(4.8, 1.0, 1.0)),
        *[beacon(n, p) for n, p in BEACONS],
        *[beacon_light(n, p) for n, p in BEACONS],
        # The whole rim can be walked off; the box below it catches the fall.
        # The valley's coarse nav (VALLEY_NAV) lets the player off as much as
        # 5 m short of the rim (measured at x = 4, z = 3.4, phase 5), so the
        # box reaches back under the ground to z = 1.
        obj("Rim edge", [walkoff((448.0, 40.0, 3.0))], pos=(0.0, 4.0, VALLEY_RIM_Z)),
        obj("Fall", [trigger((460.0, 10.0, 32.0), "scripts/fall.lua")],
            pos=(0.0, -8.0, VALLEY_RIM_Z + 9.0)),
        obj("Ignite sound", [audio("sounds/ignite.wav", "ignite")]),
        obj("Chime sound", [audio("sounds/chime.wav", "chime")]),
        obj("Wind sound", [audio("sounds/wind.wav", "wind", loop=True)]),
        # The keep's gate, 5 m to the left of the start: walking through it
        # opens the keep (scene 2).
        obj("Keep gate", [mesh("models/arch/arch.mesh", "textures/stone.png")], pos=KEEP_GATE),
        obj("Keep door", [trigger((1.2, 3.0, 2.0), "scripts/keep_door.lua")],
            pos=(KEEP_GATE[0], 1.5, KEEP_GATE[2])),
        # The lighthouse gate (phase 5), the keep's arch again, 14 m to the
        # right of the start.
        obj("Lighthouse arch", [mesh("models/arch/arch.mesh", "textures/stone.png")], pos=LIGHTHOUSE_GATE),
        obj("Lighthouse gate", [trigger((1.2, 3.0, 2.0), "scripts/lighthouse_gate.lua")],
            pos=(LIGHTHOUSE_GATE[0], 1.5, LIGHTHOUSE_GATE[2])),
        warden(),
        *[shrine(n, p) for n, p in SHRINES],
        *[shrine_light(n, p) for n, p in SHRINES],
        obj("Player", [player(VALLEY_NAV)], pos=(0.0, 0.5, 0.0)),
        obj("Sun", [sun(color=(0.85, 0.82, 0.9), intensity=0.6)], rot=LOOK_DOWN_50),
        # The beacon tally in the top right corner: valley.lua again, as an
        # object script, which gets the onUpdate a scene script does not.
        obj("Tally", [script("scripts/valley.lua")]),
    ], script="scripts/valley.lua", canvases=[shrine_canvas(), story_canvas(), gameover_canvas()],
        loading="The valley", sky=FOG, fog=10, stream=True, cutscenes=valley_cutscenes(),
        spriteSheets=[lantern_sheet([sprite_anim("dark", 0, 1, 6, loop=False),
                                     sprite_anim("flame", 1, 4, 7)])])


# Where the keep's gate stands in the valley: left of the start (-x), the
# way through running along x. The ground there is within 0.1 m of y = 0.
KEEP_GATE = (-5.0, -0.1, 0.0)

# The keep, phase 3: three rooms joined by doorways, built by art/models.py
# as models/keep/{hall,study,chamber} at the world origin. Each room object
# carries its Room box, a little inside its walls (the exporter adds 0.5 m a
# side when it sorts triangles into rooms), and a Portal object stands in
# each doorway, 2 m wide and 2.6 m tall, its local +z through the doorway.
KEEP_ROOMS = [
    # object, mesh, box centre, box size
    ("Hall", "hall", (-0.05, 1.75, 5.95), (7.9, 3.5, 11.9)),
    ("Study", "study", (0.0, 1.75, 16.05), (8.0, 3.5, 7.9)),
    ("Chamber", "chamber", (7.05, 1.75, 6.0), (5.9, 3.5, 6.0)),
]
KEEP_PORTALS = [
    # object, room A, room B, centre, rotation
    ("Study door", "Hall", "Study", (0.0, 1.3, 12.0), (0.0, 0.0, 0.0, 1.0)),
    ("Chamber door", "Hall", "Chamber", (4.0, 1.3, 6.0), (0.0, 0.7071068, 0.0, 0.7071068)),
]
KEEP_DOOR = (2.0, 2.6)  # width, height
CANDLE = (1.0, 0.72, 0.4)
KEEP_DARK = (0.02, 0.02, 0.05)

# The keeper's clip set: SkinnedAnim.Play("Keeper", "idle" or "talk").
KEEPER_CLIPS = ["models/keeper/idle.anim", "models/keeper/talk.anim"]
# Robe, hood and skin, in the order of the model's materials.
KEEPER_COLOURS = [(0.55, 0.32, 0.22, 1.0), (0.38, 0.22, 0.16, 1.0), (0.85, 0.66, 0.52, 1.0)]


def room(size, offset):
    return {"type": "room", "size": list(size), "offset": list(offset)}


def portal(a, b, width, height):
    return {"type": "portal", "roomA": a, "roomB": b, "width": width, "height": height}


def skin(clips, fps=15):
    return {"type": "skin", "clips": list(clips), "fps": fps}


def keeper():
    # In the study, 3 m in from the hall door (nearer since phase 4, so he
    # is larger from the hall), turned three quarters to it, so his talking
    # arm reads in profile. keeper.lua plays idle from the start and talk
    # while the dialogue is up; Circle in reach steps it.
    # psxsplash measures the reach from the eyes to his feet, so 4 m is
    # about 3.5 m across the floor.
    m = mesh("models/keeper/keeper.mesh")
    m["materials"] = [{"texture": None, "color": list(c)} for c in KEEPER_COLOURS]
    return obj("Keeper", [m, skin(KEEPER_CLIPS), interactable(4.0, 13), script("scripts/keeper.lua")],
               pos=(0.0, 0.0, 15.0), rot=YAW_145)


def dialogue_canvas():
    # Hidden until the keeper speaks; keeper.lua shows it and sets "body"
    # one line a press. The system font takes no line breaks, so a line is
    # one row of at most 34 characters.
    return canvas("Dialogue", [
        box("panel", (16, 164, 288, 60), [0.04, 0.05, 0.12]),
        text("name", "The keeper", 28, 168, 140, 24, AMBER, font="menu"),
        text("body", "", 28, 198, 272, 10, PALE),
        text("hint", "O", 286, 210, 10, 10, DIM),
    ], sortOrder=10, visible=False)


def keep():
    # The keeper's tower, indoors at night: the player comes in by the south
    # door of the hall (the way out behind them) facing the study door, the
    # keeper visible beyond it; the side chamber opens to the right.
    rooms = [obj(name, [mesh(f"models/keep/{m}.mesh", "textures/stone.png"), collider(),
                        room(size, centre)])
             for name, m, centre, size in KEEP_ROOMS]
    portals = [obj(name, [portal(a, b, *KEEP_DOOR)], pos=pos, rot=rot)
               for name, a, b, pos, rot in KEEP_PORTALS]
    return scene([
        *rooms,
        *portals,
        keeper(),
        obj("Way out", [trigger((2.0, 3.0, 1.0), "scripts/keep_exit.lua")], pos=(0.0, 1.5, 0.5)),
        # Candles, baked into the walls (a quarter brighter at phase 4: the
        # keep read too dark on the console).
        obj("Hall candle", [baked_lamp(CANDLE, 2.5, 10.0)], pos=(-2.0, 3.0, 6.0)),
        obj("Study candle", [baked_lamp(CANDLE, 3.0, 9.0)], pos=(2.0, 3.0, 17.0)),
        obj("Chamber candle", [baked_lamp(CANDLE, 2.2, 8.0)], pos=(8.0, 3.0, 6.0)),
        # Half a metre up: the exporter puts the eyes on the floor below.
        # player()'s nav fields are the editor's Indoor bake preset.
        obj("Player", [player()], pos=(0.0, 0.5, 2.5)),
        obj("Moon", [sun(color=(0.5, 0.55, 0.8), intensity=0.6)], rot=LOOK_DOWN_50),
    ], sceneType="interior", canvases=[dialogue_canvas()], loading="The keep", sky=KEEP_DARK)


# The lighthouse, phase 5: the player comes out on the gallery at the top of
# the tower (models/lighthouse/tower, its floor at y = 0), facing the lamp:
# the lens on its pedestal under the lantern roof, the sea 22 m below.
# Circle at the lens lights it (scripts/lighthouse.lua): Persist `lamp` = 1,
# the `lens` animation turns it and the `finale` cutscene circles the tower
# while the runtime light `Lamp light` comes up; then the `credits` roll and
# the title says the valley is lit again.
LIGHTHOUSE_COLOURS = [(0.86, 0.85, 0.8, 1.0), (0.62, 0.16, 0.12, 1.0), (0.18, 0.18, 0.2, 1.0)]
LENS_COLOURS = [(1.0, 0.86, 0.5, 1.0), (0.45, 0.33, 0.14, 1.0)]
LENS_AT = (0.0, 1.4, 0.0)
LAMP_GLOW = (1.0, 0.86, 0.55)
# Night, with a sea mist: the fog (98 m at density 5) also keeps the scene's
# ordering table under the title's, which sizes psxsplash's render buffers
# (without it the sea's diagonal asks for twice the title's).
NIGHT = (0.03, 0.04, 0.1)


def tower():
    m = mesh("models/lighthouse/tower.mesh")
    m["materials"] = [{"texture": "textures/stone.png" if i < 2 else None, "color": list(c)}
                      for i, c in enumerate(LIGHTHOUSE_COLOURS)]
    return obj("Tower", [m, collider()])


def lens():
    # Unlit, its own colours at a little over half: the lamp light sits
    # inside it and would light only its insides, and the glass panels have
    # to show for its turning to.
    m = mesh("models/lighthouse/lens.mesh")
    m["materials"] = [{"texture": None, "color": list(c)} for c in LENS_COLOURS]
    m.update(vertexColors="flat", flatColor=[160, 160, 160], dynamicLighting="off")
    # psxsplash measures the reach from the eyes to the lens's centre.
    return obj("Lens", [m, interactable(3.0, 13, repeatable=False), script("scripts/lighthouse.lua")],
               pos=LENS_AT)


def credits_canvas():
    # Hidden until the `credits` cutscene shows it and scrolls the lines up
    # from below the screen.
    lines = [text("l0", "Lamplighter", 91, 0, 140, 36, AMBER, font="title")]
    for i, s in enumerate(["The lamp burns again", "A psxsplash sample game", "Built with splashedit-ng",
                           "Title type: EB Garamond, OFL", "Thank you for playing"]):
        lines.append(text(f"l{i + 1}", s, 160 - 4 * len(s), 0, 8 * len(s), 10, PALE if i else AMBER))
    return canvas("Credits", [box("backdrop", (0, 0, 0, 0), [0.0, 0.0, 0.0], stretch=True), *lines],
                  sortOrder=30, visible=False)


CREDITS_FIRST_Y = 250   # each line starts below the screen ...
CREDITS_GAP = 34        # ... this far under the one before
CREDITS_RISE = 220      # and rises this far, the first line ending 30 px down
ORBIT_CENTRE = (0.0, 1.8, 0.0)


def lighthouse_sequences():
    # The finale: from the player's eyes back out over the parapet and once
    # round the tower, 9 m out and 3.5 m up, while the lamp catches.
    path = [(0, (0.0, 2.0, -2.4), LENS_AT), (40, (0.0, 3.5, -9.0), ORBIT_CENTRE)]
    for k in range(1, 13):
        a = math.radians(180 + 30 * k)
        path.append((40 + 20 * k, (9.0 * math.sin(a), 3.5, 9.0 * math.cos(a)), ORBIT_CENTRE))
    cam_pos, cam_rot = camera_path(path, interp="linear")
    finale = cutscene("finale", 320, cam_pos, cam_rot,
        track("lightEnabled", "Lamp light", key(0, 1, interp="step")),
        track("lightIntensity", "Lamp light", key(0, 0.0), key(12, 0.8), key(24, 0.3), key(120, 2.4)),
        track("lightColor", "Lamp light", key(0, 0.8, 0.3, 0.1), key(120, *LAMP_GLOW)),
        track("rumbleSmall", "", key(0, 1, interp="step"), key(30, 0, interp="step")))
    xs = [91] + [160 - 4 * len(e["text"]) for e in credits_canvas()["elements"][2:]]
    rolls = [track("uiPosition", f"Credits/l{i}",
                   key(0, x, CREDITS_FIRST_Y + CREDITS_GAP * i),
                   key(330, x, CREDITS_FIRST_Y + CREDITS_GAP * i - CREDITS_RISE))
             for i, x in enumerate(xs)]
    credits = cutscene("credits", 390, track("uiCanvasVisible", "Credits", key(0, 1, interp="step")), *rolls)
    # The lens turns once every three seconds, started by lighthouse.lua.
    turn = sequence("lens", 90, track("objectRotation", "Lens", key(0, 0, 0, 0), key(90, 0, 360, 0)))
    return [finale, credits], [turn]


def lighthouse():
    cutscenes, animations = lighthouse_sequences()
    return scene([
        tower(),
        lens(),
        # Dark until the finale lights it.
        obj("Lamp light", [lamp(LAMP_GLOW, 3.0, 14.0)], pos=LENS_AT),
        obj("Sea", [mesh("models/sea.mesh", "textures/sea.png", color=(0.7, 0.75, 0.9, 1.0))],
            pos=(0.0, -22.0, 0.0), scale=(2.0, 1.0, 2.0)),
        obj("Headland", [mesh("models/cliff.mesh", "textures/rock.png", color=SILHOUETTE)],
            pos=(-14.0, -22.0, -40.0), rot=YAW_25, scale=(2.0, 1.5, 1.5)),
        # Half a metre up: the exporter puts the eyes on the floor below.
        obj("Player", [player()], pos=(0.0, 0.5, -2.6)),
        obj("Moon", [sun(color=(0.55, 0.62, 0.9), intensity=0.6)], rot=LOOK_DOWN_50),
    ], canvases=[credits_canvas()], loading="The lighthouse", sky=NIGHT, fog=5,
        cutscenes=cutscenes, animations=animations)


def write_json(path, data):
    with open(path, "w", newline="\n") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def main():
    os.makedirs(PROJECT, exist_ok=True)
    scenes = {
        "title": title(),
        "valley": valley(),
        "keep": keep(),
        "lighthouse": lighthouse(),
    }
    for name in SCENES:
        write_json(os.path.join(PROJECT, name + ".scene"), scenes[name])
    with open(os.path.join(PROJECT, "scenes.list"), "w", newline="\n") as f:
        for name in SCENES:
            f.write(name + ".scene\n")
    write_json(os.path.join(PROJECT, "disc.json"),
               {"volume": "LAMPLIGHTER", "licence": "psxsplash", "tracks": TRACKS})


main()
