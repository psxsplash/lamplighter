-- The keeper in the keep's study (scene 2), on the Keeper object: a skinned
-- mesh with the clips "idle" and "talk", and an Interactable on Circle.
-- He idles from the start. Each press in reach shows the Dialogue canvas
-- with the next line, the keeper talking; the press after the last line
-- hides it, sets him idling again and marks the talk as heard in Persist:
--   keeper  1 once the player has heard him out

local LINES = {
    "So, a lamplighter at last.",
    "The Warden put out every beacon.",
    "Relight the three in the valley,",
    "then the lighthouse lamp.",
    "Go on. The fog will not wait.",
}

local canvas, body
local line = 0  -- the line on screen, 0 when the dialogue is hidden

local function idle()
    SkinnedAnim.Play("Keeper", "idle", {loop = true})
end

function onCreate(self)
    canvas = UI.FindCanvas("Dialogue")
    body = UI.FindElement(canvas, "body")
    idle()
end

function onInteract(self)
    line = line + 1
    if line > #LINES then
        line = 0
        UI.SetCanvasVisible(canvas, false)
        idle()
        Persist.Set("keeper", 1)
        return
    end
    UI.SetText(body, LINES[line])
    if line == 1 then
        UI.SetCanvasVisible(canvas, true)
        SkinnedAnim.Play("Keeper", "talk", {loop = true})
    end
end
