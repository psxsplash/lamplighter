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
the table `{scene, beacons, lamp, keeper, shrine}` under the key `LAMP`, made
at one of the valley's save shrines; the title offers Continue only when it
finds one, and Continue restores `beacons`, `lamp`, `keeper` and `shrine`. Each beacon also keeps `beacon_<name>` (1 once
lit), which `beacons.blocks` reads and writes and the title sets from the mask,
and `lost` is 1 after a fall off the valley's cliff, 2 after the Warden
caught the player and 3 after the lighthouse's credits, until the title has
said so; `intro` is 1 once the valley has played its intro (New game clears
it, Continue sets it); `keeper` is 1 once the keep's
keeper has been heard out; `shrine` (1 or 2) is the shrine a continued game
starts at, cleared once the valley has used it (New game clears both). Disc track 2 is the title theme. Track 3 was the valley's, but the valley
streams its scenery from the disc and psxsplash plays no CD music in a streamed
scene, so the valley's ambience is a looping SPU clip, `wind`.

## The valley

A 448 m square of ground in 32 m chunks, streamed by region, in fog. The
player starts 8 m from the cliff rim on the north edge, facing it; the whole
rim can be walked off, and the `Fall` trigger below it ends the game: the
`gameover` cutscene closes the fog in to black under "You fell", then the
title says so.

A New game opens on the `intro` cutscene (`valley.lua`, once, kept in
`Persist` as `intro`): out of black into the fog over the sea, then the
camera sweeps from the cliff rim back over the dark beacons and down to the
player's eyes under the line "The beacons have gone dark", and the player's
controls come back when it ends. psxsplash draws a UI box opaque, so its
fades are a full-screen box whose colour runs between black and the fog's.

The `Lighthouse gate`, an arch 14 m to the right of the start and 2 m back
from it, well away from the Warden, opens the lighthouse once all three
beacons are lit (`beacons` is 7); before that the `gate` cutscene shows "The
lamp needs all three beacons" for two seconds (`lighthouse_gate.lua`). Three beacons, BeaconA (just ahead on the right), BeaconB and
BeaconC, light with Circle: each has a runtime point light `<name>_light`,
dark until `beacons.blocks` turns it on, and the chime plays once all three
are lit.
The keep's gate stands 5 m to the left of the start; walking through it
(the `Keep door` trigger) opens the keep.

The Warden (`models/warden`, eleven bones and a root, clips `walk`, `run` and
`idle`) walks a patrol of four corners south of the start, round between
BeaconB and BeaconC, at 1.4 m/s, each leg a path from `Actor.FindPath`, and
waits a moment at each corner (`warden.lua`). Come within 10 m and he runs at
you at 2.6 m/s, finding a new path to you every 20 frames; you walk at 3 m/s,
so walking away loses him once you are 16 m off for two seconds, and he goes
back to the nearest corner. Within 1.4 m he catches you and the title says
so: the `gameover` cutscene under "Caught by the Warden", then the
title. A script and a skin keep him out of the streamed regions. The valley's
nav is baked as watershed regions, 182 of them: psxsplash's pathfinding
finds no path in a scene of more than 256.

Two save shrines, `Shrine 1` 7 m to the right of the start and `Shrine 2`
beyond BeaconC, each with a pale runtime light, save the game with Circle
(`shrine.lua`) and say so on screen for two seconds. Continue starts the
player 3 m in front of the shrine saved at, facing it (`valley.lua`).

Known issue (psxsplash f671202): after a save at a shrine, a later scene
load in the same session can crash the console; a save made in a scene
that does not stream, or a Continue from a fresh boot, does not.

## The keep

Indoors, not streamed: three rooms, each a Room box, joined by doorways that
are Portals, so psxsplash draws a room only when the camera's room sees it
through a portal. The player comes in at the south end of the hall facing
the doorway north into the keeper's study; the side chamber opens off the
hall to the east, and the south door (`Way out`) leads back to the valley.
The keeper is a skinned mesh (`models/keeper`, eleven bones and a root,
clips `idle` and `talk`), 3 m in from the doorway, with an Interactable on Circle: `keeper.lua` plays
idle from the start, shows the hidden `Dialogue` canvas and steps its lines
one press at a time with the keeper talking, then hides it, goes back to
idle and sets `keeper` to 1 in `Persist`.

## The lighthouse

The player comes out on the gallery at the top of the tower
(`models/lighthouse`, a tower 24 m tall in white and red bands, in a night
sea mist), facing the lamp: the lens on its pedestal under the lantern roof.
Circle at the lens (`lighthouse.lua`) lights it: `lamp` is set to 1 in
`Persist`, the `lens` animation turns the lens once every three seconds
(`Animation.Play`), and the `finale` cutscene pulls the camera back over the
parapet and once round the tower while the runtime light `Lamp light` comes
up from a red glow to a warm white and the pad rumbles. Then the `credits`
cutscene scrolls the `Credits` canvas up the screen, and the title says "The
valley is lit again". The credits start on the frame after the finale ends:
psxsplash f671202 drops the `onComplete` of a cutscene played from inside
another's `onComplete`.
