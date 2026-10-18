-- The lamp at the top of the lighthouse (scene 3), on the Lens object with an
-- Interactable on Circle. A press in reach lights it: `lamp` = 1 in Persist,
-- the `lens` animation turns the lens, and the `finale` cutscene circles the
-- tower while the runtime light "Lamp light" comes up. The finale's
-- onComplete plays the `credits` cutscene, and the credits' onComplete
-- returns to the title, which says the valley is lit again (`lost` 3,
-- title.lua).

local function backToTitle()
    Persist.Set("lost", 3)
    Scene.Load(0)
end

function onInteract(self)
    Controls.SetEnabledPlayer1(false)
    Persist.Set("lamp", 1)
    Animation.Play("lens", {loop = true})
    Cutscene.Play("finale", {onComplete = function()
        Cutscene.Play("credits", {onComplete = backToTitle})
    end})
end
