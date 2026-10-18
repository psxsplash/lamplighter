-- Title menu, on the Menu object. Up and Down move the cursor, Cross picks.
--   New game: clears the game state and opens the valley (scene 1).
--   Continue: shown only when the memory card holds a save; restores the
--   state from it and opens the scene it was made in.
--
-- Game state lives in Persist, which keeps numbers across Scene.Load:
--   beacons  bit mask of the relit beacons (1, 2, 4)
--   lamp     1 once the lighthouse lamp is lit
--   lost     1 when the player fell off a cliff: the title shows "lost";
--            2 when the Warden caught the player (scripts/warden.lua): "caught";
--            3 after the lighthouse's credits (scripts/lighthouse.lua): "lit"
--   intro    1 once the valley has played its intro (scripts/valley.lua):
--            New game clears it, Continue sets it
--   keeper   1 once the keep's keeper has been heard out (scripts/keeper.lua)
--   shrine   the save shrine to start at in the valley (scripts/valley.lua)
-- A save is the table {scene = <index>, beacons = <mask>, lamp = <0 or 1>,
-- keeper = <0 or 1>, shrine = <1 or 2>} under SAVE_KEY on the card in port 0,
-- made at a shrine (scripts/shrine.lua).

local SAVE_KEY = "LAMP"
local VALLEY = 1
-- The cursor is a UI image, the unlit lantern of the `lantern` sprite sheet
-- (16 x 16), centred on the 24-pixel line of the item it points at.
local CURSOR_X = 92
local CURSOR_DY = 4
-- Menu text colours, halved: custom-font text is drawn as textured sprites,
-- where 128 is full intensity (tools/scenes.py stores them the same way).
local PICKED = {128, 100, 54}
local IDLE = {105, 107, 115}

local canvas
local newGame, continue, cursor
local save        -- the table MemCard.Load found, or nil
local choice = 1  -- 1 New game, 2 Continue
local busy = false

local function itemY(i)
    if i == 1 then return 148 end
    return 172
end

local function show()
    local picked, other = newGame, continue
    if choice == 2 then picked, other = continue, newGame end
    UI.SetColor(picked, PICKED[1], PICKED[2], PICKED[3])
    UI.SetColor(other, IDLE[1], IDLE[2], IDLE[3])
    UI.SetPosition(cursor, CURSOR_X, itemY(choice) + CURSOR_DY)
end

-- The valley's beacons script (beacons.blocks) also keeps one key per beacon,
-- beacon_<name> = 1 once lit; they follow the bits of `beacons`.
local BEACONS = {"BeaconA", "BeaconB", "BeaconC"}

local function setBeacons(mask)
    Persist.Set("beacons", mask)
    local bit = 4
    for i = 3, 1, -1 do
        local on = 0
        if mask >= bit then
            on = 1
            mask = mask - bit
        end
        Persist.Set("beacon_" .. BEACONS[i], on)
        bit = bit / 2
    end
end

local function resetState()
    setBeacons(0)
    Persist.Set("lamp", 0)
    Persist.Set("keeper", 0)
    Persist.Set("shrine", 0)
    Persist.Set("intro", 0)
end

function onCreate(self)
    -- The D-pad drives the menu, not the player standing on the cliff.
    Controls.SetEnabledPlayer1(false)
    canvas = UI.FindCanvas("Title")
    newGame = UI.FindElement(canvas, "newgame")
    continue = UI.FindElement(canvas, "continue")
    cursor = UI.FindElement(canvas, "cursor")
    -- Look for a save before the music starts reading the disc.
    save = MemCard.Load(0, SAVE_KEY)
    if type(save) ~= "table" or save.scene == nil then save = nil end
    UI.SetVisible(continue, save ~= nil)
    -- Back from a fall off a cliff (scripts/fall.lua), caught by the
    -- Warden (scripts/warden.lua) or the end (scripts/lighthouse.lua): say
    -- so, once.
    local lost = Persist.Get("lost")
    if lost == 1 then
        UI.SetVisible(UI.FindElement(canvas, "lost"), true)
    elseif lost == 2 then
        UI.SetVisible(UI.FindElement(canvas, "caught"), true)
    elseif lost == 3 then
        UI.SetVisible(UI.FindElement(canvas, "lit"), true)
    end
    Persist.Set("lost", 0)
    show()
    Audio.PlayCDDA(2)
end

function onButtonPress(self, button)
    if busy then return end
    if button == Input.UP or button == Input.DOWN then
        if save ~= nil then
            choice = 3 - choice
            show()
        end
    elseif button == Input.CROSS then
        busy = true
        if choice == 1 then
            resetState()
            Scene.Load(VALLEY)
        else
            resetState()
            setBeacons(save.beacons or 0)
            Persist.Set("lamp", save.lamp or 0)
            Persist.Set("keeper", save.keeper or 0)
            Persist.Set("shrine", save.shrine or 0)
            -- A saved game has had its intro.
            Persist.Set("intro", 1)
            Scene.Load(save.scene)
        end
    end
end
