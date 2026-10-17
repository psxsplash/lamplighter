-- The save shrines in the valley (scene 1), Shrine 1 and Shrine 2, both on
-- this script with an Interactable on Circle. A press in reach saves the
-- game on the memory card in port 0, under the title's key:
--   {scene = 1, beacons = <mask>, lamp = <0 or 1>, keeper = <0 or 1>,
--    shrine = <1 or 2>}
-- and says so for two seconds on the Shrine canvas. Continue on the title
-- loads it and valley.lua puts the player back in front of the shrine.

local SAVE_KEY = "LAMP"
local SHOW = 2 * 30 * 4096  -- two seconds; onUpdate's dt is 4096 a frame at 30 Hz

local id = 1                -- which shrine this is
local saved                 -- the canvas line
local shown = 0             -- time left on screen

function onCreate(self)
    -- Each object runs its own copy of the script; tell the two apart.
    if self == Entity.Find("Shrine 2") then id = 2 end
    saved = UI.FindElement(UI.FindCanvas("Shrine"), "saved")
end

function onInteract(self)
    local ok = MemCard.Save(0, SAVE_KEY, {
        scene = 1,
        beacons = Persist.Get("beacons") or 0,
        lamp = Persist.Get("lamp") or 0,
        keeper = Persist.Get("keeper") or 0,
        shrine = id,
    })
    if ok then
        UI.SetText(saved, "The shrine keeps your progress")
    else
        UI.SetText(saved, "The memory card did not take it")
    end
    UI.SetVisible(saved, true)
    shown = SHOW
end

function onUpdate(self, dt)
    if shown > 0 then
        shown = shown - dt
        if shown <= 0 then UI.SetVisible(saved, false) end
    end
end
