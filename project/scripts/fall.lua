-- The kill box under the valley's cliff rim (a Trigger component). A player
-- who walks off the edge falls into it: mark the fall for the title screen
-- and go back there. title.lua shows the lose line and clears the mark.

function onTriggerEnter(index)
    Persist.Set("lost", 1)
    Scene.Load(0)
end
