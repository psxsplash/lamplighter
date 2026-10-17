# Lamplighter

A small psxsplash game and the sample project for the editor. The beacons of a
fog-bound valley have gone dark: relight them and the lighthouse lamp before the
Warden catches you, and mind the cliff edges.

Open `project/` in the editor (or pick it under New Project) and press Play.

The game is built in phases; `features.json` lists every engine feature it uses
and the phase that brings it in. `tests/featurecheck.py` exports the scenes and
the disc and fails when a listed feature is missing from the output.

Everything under `project/models`, `project/textures` and `project/music`, the
menu font sheet `project/fonts/menu.png`, the `.scene` files and `disc.json`
are generated. To regenerate them you need Blender, Python 3 with Pillow and
numpy, `oggenc` (vorbis-tools) and a `splashpack-cli` from splashedit-ng:

    tools/build.sh path/to/splashpack-cli

The models are built by `art/models.py` (Blender), the textures and the memory
card icon by `art/textures.py`, the menu's bitmap font by `art/bitmapfont.py`,
the CD-DA music by `art/music.py`, the scenes and `disc.json` by
`tools/scenes.py`. The Lua scripts in `project/scripts` are written by hand.
The title font is EB Garamond Bold (SIL Open Font License, see
`project/fonts/OFL.txt`).

## Scenes and state

Scene 0 is the title, 1 the valley, 2 the keep, 3 the lighthouse. The game
state crosses scenes in `Persist`: `beacons` (a bit mask of the relit beacons)
and `lamp` (1 once the lighthouse lamp is lit). A save on the memory card is
the table `{scene, beacons, lamp}` under the key `LAMP`; the title offers
Continue only when it finds one. Disc track 2 is the title theme, track 3 the
valley.
