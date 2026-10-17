# Lamplighter

A small psxsplash game and the sample project for the editor. The beacons of a
fog-bound valley have gone dark: relight them and the lighthouse lamp before the
Warden catches you, and mind the cliff edges.

Open `project/` in the editor (or pick it under New Project) and press Play.

The game is built in phases; `features.json` lists every engine feature it uses
and the phase that brings it in. `tests/featurecheck.py` exports the scenes and
the disc and fails when a listed feature is missing from the output.

Everything under `project/models`, `project/textures`, `project/music` and
`project/sounds`, the
menu font sheet `project/fonts/menu.png`, the `.scene` files and `disc.json`
are generated. To regenerate them you need Blender, Python 3 with Pillow and
numpy, `oggenc` (vorbis-tools) and a `splashpack-cli` from splashedit-ng:

    tools/build.sh path/to/splashpack-cli

The models are built by `art/models.py` (Blender), the textures and the memory
card icon by `art/textures.py`, the menu's bitmap font by `art/bitmapfont.py`,
the CD-DA music by `art/music.py`, the sound effects by `art/sfx.py`, the
scenes and `disc.json` by `tools/scenes.py`. The scripts in `project/scripts`,
Lua and the beacons' blocks script `beacons.blocks`, are written by hand.
The title font is EB Garamond Bold (SIL Open Font License, see
`project/fonts/OFL.txt`).

## Scenes and state

Scene 0 is the title, 1 the valley, 2 the keep, 3 the lighthouse. The game
state crosses scenes in `Persist`: `beacons` (a bit mask of the relit beacons)
and `lamp` (1 once the lighthouse lamp is lit). A save on the memory card is
the table `{scene, beacons, lamp}` under the key `LAMP`; the title offers
Continue only when it finds one. Each beacon also keeps `beacon_<name>` (1 once
lit), which `beacons.blocks` reads and writes and the title sets from the mask,
and `lost` is 1 after a fall off the valley's cliff until the title has said
so. Disc track 2 is the title theme. Track 3 was the valley's, but the valley
streams its scenery from the disc and psxsplash plays no CD music in a streamed
scene, so the valley's ambience is a looping SPU clip, `wind`.

## The valley

A 448 m square of ground in 32 m chunks, streamed by region, in fog. The
player starts 8 m from the cliff rim on the north edge, facing it; the whole
rim can be walked off, and the `Fall` trigger below it sends the player back
to the title. Three beacons, BeaconA (just ahead on the right), BeaconB and
BeaconC, light with Circle: each has a runtime point light `<name>_light`,
dark until `beacons.blocks` turns it on, and the chime plays once all three
are lit.
