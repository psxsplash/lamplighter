-- The valley's scene script. The valley streams its scenery from the disc,
-- which keeps the drive busy, and psxsplash plays no CD music in a streamed
-- scene, so its ambience is the looping SPU clip "wind" instead of disc
-- track 3.

function onSceneCreationEnd()
    Audio.Play("wind", 70)
end
