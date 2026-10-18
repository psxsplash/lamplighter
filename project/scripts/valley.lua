-- The valley's scene script. The valley streams its scenery from the disc,
-- which keeps the drive busy, and psxsplash plays no CD music in a streamed
-- scene, so its ambience is the looping SPU clip "wind" instead of disc
-- track 3.
--
-- After Continue on the title, `shrine` in Persist is the save shrine the
-- game was saved at (1 or 2): the player starts 3 m in front of it, facing
-- it, instead of at the cliff. It is cleared once used, so coming back out
-- of the keep is the usual way in again.
--
-- A New game clears `intro` (title.lua), and the valley then plays the
-- `intro` cutscene once: a sweep from the cliff rim over the dark beacons.
--
-- The same file is the script of the `Tally` object, which draws the beacon
-- tally: three lanterns of the `lantern` sprite sheet in the top right
-- corner, BeaconA to BeaconC left to right. A lit beacon's lantern plays
-- `flame`, an unlit one shows `dark`. A scene script gets no onUpdate, so the
-- object's onUpdate watches `beacons` (bits 1, 2, 4, set by beacons.blocks)
-- and relights the tally when it changes. The scene and the object each run
-- this file in an environment of their own: the scene uses
-- onSceneCreationEnd, the object onCreate and onUpdate.

-- In front of each shrine (tools/scenes.py SHRINES), in GTE raw units: one
-- metre is 4096 / 100 at the valley's GTE scaling, y points down, and the
-- player's position is the eyes, about 2 m over the ground here.
local function raw(dm) return dm * 4096 / 1000 end
local SPAWN = {{raw(70), raw(-20), raw(-30)}, {raw(260), raw(-20), raw(-470)}}

function onSceneCreationEnd()
    local at = SPAWN[Persist.Get("shrine") or 0]
    if at then
        Player.SetPosition(at[1], at[2], at[3])
        Persist.Set("shrine", 0)
    end
    Audio.Play("wind", 70)
    -- The intro, once a New game: the player's controls are held until the
    -- camera is back at their eyes.
    if Persist.Get("intro") ~= 1 then
        Persist.Set("intro", 1)
        Controls.SetEnabledPlayer1(false)
        Cutscene.Play("intro", {onComplete = function() Controls.SetEnabledPlayer1(true) end})
    end
end

-- The tally (the Tally object). Screen pixels, each lantern 16 x 16.
local TALLY_X, TALLY_Y, TALLY_STEP = 258, 10, 18
local BITS = {1, 2, 4}   -- BeaconA, BeaconB, BeaconC in `beacons`
local lanterns = {}
local shown = -1   -- the `beacons` mask the tally shows

local function showTally(mask)
    shown = mask
    for i = 1, 3 do
        local bit = BITS[i]
        if mask % (2 * bit) >= bit then
            Sprite.PlayAnim(lanterns[i], "flame")
        else
            Sprite.PlayAnim(lanterns[i], "dark")
        end
    end
end

function onCreate(self)
    for i = 1, 3 do
        lanterns[i] = Sprite.Create("lantern")
        Sprite.SetPos(lanterns[i], TALLY_X + (i - 1) * TALLY_STEP, TALLY_Y)
    end
    showTally(Persist.Get("beacons") or 0)
end

function onUpdate(self, dt)
    local mask = Persist.Get("beacons") or 0
    if mask ~= shown then showTally(mask) end
end
