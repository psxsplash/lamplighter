-- Title menu, on the Menu object. Up and Down move the cursor, Cross picks.
--   New game: clears the game state and opens the valley (scene 1).
--   Continue: shown only when the memory card holds a save; restores the
--   state from it and opens the scene it was made in.
--
-- Game state lives in Persist, which keeps numbers across Scene.Load:
--   beacons  bit mask of the relit beacons (1, 2, 4)
--   lamp     1 once the lighthouse lamp is lit
-- A save is the table {scene = <index>, beacons = <mask>, lamp = <0 or 1>}
-- under SAVE_KEY on the card in port 0.

local SAVE_KEY = "LAMP"
local VALLEY = 1
local CURSOR_X = 92
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
    UI.SetPosition(cursor, CURSOR_X, itemY(choice))
end

local function resetState()
    Persist.Set("beacons", 0)
    Persist.Set("lamp", 0)
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
            Persist.Set("beacons", save.beacons or 0)
            Persist.Set("lamp", save.lamp or 0)
            Scene.Load(save.scene)
        end
    end
end
