-- The lamp at the top of the lighthouse (scene 3), on the Lens object with an
-- Interactable on Circle. A press in reach lights it: `lamp` = 1 in Persist,
-- the `lens` animation turns the lens, and the `finale` cutscene circles the
-- tower while the runtime light "Lamp light" comes up. Then the `credits`
-- roll, and the title says the valley is lit again (`lost` 3, title.lua).
--
-- The credits start on the frame after the finale ends, not from the
-- finale's onComplete: psxsplash f671202 drops the onComplete of a cutscene
-- played from inside another's onComplete (it unrefs the callback slot
-- after the first one returns, cutscene.cpp fireOnComplete).

local rolling = false   -- the finale has ended: start the credits

local function backToTitle()
    Persist.Set("lost", 3)
    Scene.Load(0)
end

function onInteract(self)
    Controls.SetEnabledPlayer1(false)
    Persist.Set("lamp", 1)
    Animation.Play("lens", {loop = true})
    Cutscene.Play("finale", {onComplete = function() rolling = true end})
end

function onUpdate(self, dt)
    if rolling then
        rolling = false
        Cutscene.Play("credits", {onComplete = backToTitle})
    end
end
