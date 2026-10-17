# Lamplighter

A small psxsplash game and the sample project for the editor. The beacons of a
fog-bound valley have gone dark: relight them and the lighthouse lamp before the
Warden catches you, and mind the cliff edges.

Open `project/` in the editor (or pick it under New Project) and press Play.

The game is built in phases; `features.json` lists every engine feature it uses
and the phase that brings it in. `tests/featurecheck.py` exports the scenes and
the disc and fails when a listed feature is missing from the output.

Everything under `project/models` and `project/textures`, and the `.scene`
files, is generated. To regenerate it you need Blender, Python 3 with Pillow and
a `splashpack-cli` from splashedit-ng:

    tools/build.sh path/to/splashpack-cli

The models are built by `art/models.py` (Blender), the textures by
`art/textures.py`, the scenes by `tools/scenes.py`.
