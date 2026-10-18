-- The kill box under the valley's cliff rim (a Trigger component). A player
-- who walks off the edge falls into it: the `gameover` cutscene fades the
-- fog to black with "You fell", then the title, which shows the lose line
-- for `lost` 1 and clears the mark.

function onTriggerEnter(index)
    Persist.Set("lost", 1)
    Controls.SetEnabledPlayer1(false)
    local line = UI.FindElement(UI.FindCanvas("Gameover"), "line")
    local s = "You fell"
    UI.SetText(line, s)
    UI.SetPosition(line, 160 - 4 * #s, 116)
    Cutscene.Play("gameover", {onComplete = function() Scene.Load(0) end})
end
