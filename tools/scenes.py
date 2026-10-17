# Writes the Lamplighter scene files and the build list into project/.
#   python3 -P tools/scenes.py [project-dir]
# Run tools/build.sh to regenerate everything (art, import, scenes) in order.
import json
import os
import sys

PROJECT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "project")

# Build order: scene 0 is where the game starts, Scene.Load(i) opens scene i.
SCENES = ["title", "valley", "keep", "lighthouse"]


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


def player():
    return {"type": "player", "playerHeight": 1.8, "playerRadius": 0.5, "moveSpeed": 3.0,
            "sprintSpeed": 8.0, "maxStepHeight": 0.35, "walkableSlopeAngle": 46.0,
            "navCellSize": 0.05, "navCellHeight": 0.025, "navMinRegionArea": 8,
            "navMergeRegionArea": 20, "navMaxSimplifyError": 1.3, "navMaxEdgeLength": 12.0,
            "navPartitionMethod": "watershed", "navDetailSampleDist": 6.0,
            "navDetailMaxError": 0.025, "navMaxPlaneError": 0.15, "jumpHeight": 2.0,
            "gravity": 20.0}


def sun():
    return {"type": "light", "kind": "directional", "color": [1.0, 0.95, 0.85], "intensity": 0.75,
            "range": 10.0, "spotAngle": 30.0, "innerSpotAngle": 0.0, "enabled": True,
            "runtime": False}


def scene(objects, sceneType="exterior"):
    return {"format": "splashedit-ng/scene", "version": 1,
            "settings": {"gteScaling": 100.0, "sceneType": sceneType,
                         "fog": {"enabled": False, "color": [0.5, 0.5, 0.6], "density": 5},
                         "networkId": "", "script": None},
            "objects": objects}


def placeholder(texture):
    # Phase 0: every scene is a ground square, one beacon and the player.
    # Later phases replace each with its real content.
    return scene([
        obj("Ground", [mesh("models/ground.mesh", "textures/" + texture), collider()]),
        obj("Beacon", [mesh("models/beacon.mesh", "textures/stone.png"), collider()],
            pos=(0.0, 0.0, 4.0)),
        obj("Player", [player()], pos=(0.0, 0.0, -5.0)),
        obj("Sun", [sun()]),
    ])


def main():
    os.makedirs(PROJECT, exist_ok=True)
    for name, tex in zip(SCENES, ["stone.png", "grass.png", "stone.png", "stone.png"]):
        with open(os.path.join(PROJECT, name + ".scene"), "w", newline="\n") as f:
            json.dump(placeholder(tex), f, indent=2)
            f.write("\n")
    with open(os.path.join(PROJECT, "scenes.list"), "w", newline="\n") as f:
        for name in SCENES:
            f.write(name + ".scene\n")


main()
