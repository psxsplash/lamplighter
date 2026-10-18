-- The trigger in the lighthouse gate in the valley, on the rim to the right
-- of the start. With all three beacons lit (`beacons` 7 in Persist) walking
-- through it opens the lighthouse (scene 3); otherwise the `gate` cutscene
-- says "The lamp needs all three beacons" for two seconds.

function onTriggerEnter(index)
    if Cutscene.IsPlaying() then return end
    if Persist.Get("beacons") == 7 then
        Scene.Load(3)
    else
        Cutscene.Play("gate")
    end
end
