# Writes the Lamplighter scene files, the build list and disc.json into project/.
#   python3 -P tools/scenes.py [project-dir]
# Run tools/build.sh to regenerate everything (art, import, scenes) in order.
import json
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


# The editor's Terrain nav bake preset (core/scene.cpp applyNavPreset): the ten
# region-building fields. Step height and slope stay the player's own.
TERRAIN_NAV = {"navCellSize": 0.08, "navCellHeight": 0.04, "navMinRegionArea": 4,
               "navMergeRegionArea": 6, "navMaxSimplifyError": 0.4, "navMaxEdgeLength": 5.0,
               "navPartitionMethod": "monotone", "navDetailSampleDist": 4.0,
               "navDetailMaxError": 0.02, "navMaxPlaneError": 0.1}


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


def canvas(name, elements, sortOrder=0, defaultFont=None):
    return {"name": name, "visible": True, "sortOrder": sortOrder, "defaultFont": defaultFont,
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
        text("newgame", "New game", 112, 148, 100, 24, PALE, font="menu"),
        text("continue", "Continue", 112, 172, 100, 24, PALE, font="menu", visible=False),
        text("cursor", ">", 92, 148, 16, 24, AMBER, font="menu"),
        text("hint", "UP/DOWN choose   X select", 60, 222, 220, 10, DIM),
    ])


def scene(objects, sceneType="exterior", script=None, canvases=(), loading=None,
          sky=(0.5, 0.5, 0.6), fog=0, stream=False, bump=0):
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
    return {"format": "splashedit-ng/scene", "version": 1, "settings": settings,
            "objects": objects, "fonts": [dict(f) for f in FONTS], "canvases": canvases}


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
    ], canvases=[title_canvas()], loading="", sky=(0.03, 0.04, 0.1), bump=RENDER_BUMP)


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
        obj("Rim edge", [walkoff((448.0, 40.0, 3.0))], pos=(0.0, 4.0, VALLEY_RIM_Z)),
        obj("Fall", [trigger((460.0, 10.0, 24.0), "scripts/fall.lua")],
            pos=(0.0, -8.0, VALLEY_RIM_Z + 10.0)),
        obj("Ignite sound", [audio("sounds/ignite.wav", "ignite")]),
        obj("Chime sound", [audio("sounds/chime.wav", "chime")]),
        obj("Wind sound", [audio("sounds/wind.wav", "wind", loop=True)]),
        obj("Player", [player(TERRAIN_NAV)], pos=(0.0, 0.5, 0.0)),
        obj("Sun", [sun(color=(0.85, 0.82, 0.9), intensity=0.6)], rot=LOOK_DOWN_50),
    ], script="scripts/valley.lua", loading="The valley", sky=FOG, fog=10, stream=True)


def placeholder(texture, caption, script=None):
    # Phase 0: a ground square, one beacon and the player. Later phases
    # replace each with its real content.
    return scene([
        obj("Ground", [mesh("models/ground.mesh", "textures/" + texture), collider()]),
        obj("Beacon", [mesh("models/beacon.mesh", "textures/stone.png"), collider()],
            pos=(0.0, 0.0, 4.0)),
        obj("Player", [player()], pos=(0.0, 0.0, -5.0)),
        obj("Sun", [sun()], rot=LOOK_DOWN_50),
    ], script=script, loading=caption)


def write_json(path, data):
    with open(path, "w", newline="\n") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def main():
    os.makedirs(PROJECT, exist_ok=True)
    scenes = {
        "title": title(),
        "valley": valley(),
        "keep": placeholder("stone.png", "The keep"),
        "lighthouse": placeholder("stone.png", "The lighthouse"),
    }
    for name in SCENES:
        write_json(os.path.join(PROJECT, name + ".scene"), scenes[name])
    with open(os.path.join(PROJECT, "scenes.list"), "w", newline="\n") as f:
        for name in SCENES:
            f.write(name + ".scene\n")
    write_json(os.path.join(PROJECT, "disc.json"),
               {"volume": "LAMPLIGHTER", "licence": "psxsplash", "tracks": TRACKS})


main()
