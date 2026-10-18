-- The Warden in the valley (scene 1), on the Warden object: a skinned mesh
-- with the clips "walk", "run" and "idle". He walks his patrol, corner to
-- corner, each leg a path from Actor.FindPath over the valley's nav regions,
-- and waits a moment at each corner. A player who comes within SIGHT of him
-- is chased: he runs, finding a new path to the player every REPATH, until
-- the player is more than LOSE away for LOSE_TIME, when he goes back to the
-- nearest corner of his patrol. Within CATCH he has caught the player:
--   lost  2 in Persist, the `gameover` cutscene ("Caught by the Warden"), and
--   back to the title, which says so (title.lua)
--
-- psxsplash's Lua has whole numbers only. Positions are in GTE units, 4096
-- to the unit, one unit 100 m at the valley's GTE scaling of 100, with y
-- pointing down: a metre is 40.96 (written raw below, from metres * 4096 /
-- 100). He keeps his own position in sixteenths of that, to walk slower
-- than a whole raw step a frame. onUpdate's dt is 4096 a thirtieth of a
-- second.

local NAME = "Warden"
local function raw(dm) return dm * 4096 / 1000 end  -- decimetres to GTE raw

-- The patrol's corners in scene metres (x, z): round between BeaconB and
-- BeaconC, south of the start. Heights come from the nav regions.
local PATROL = {{-18, -30}, {0, -44}, {20, -24}, {2, -22}}
local SIGHT = raw(100)     -- 10 m: he sees the player
local LOSE = raw(160)      -- 16 m: he loses the player ...
local LOSE_TIME = 2 * 30 * 4096  -- ... after two seconds that far off
local CATCH = raw(14)      -- 1.4 m: caught
local EYES = raw(18)       -- the player's position is the eyes, 1.8 m up
local WALK = 31            -- 1.4 m/s in sixteenths of raw a frame
local RUN = 57             -- 2.6 m/s; the player walks at 3 m/s
local REPATH = 20 * 4096   -- a new path to the player every 20 frames
local PAUSE = 45 * 4096    -- the wait at a corner, a second and a half
local TURN = 48            -- most he turns a frame, 1024 to half a turn

local x, y, z              -- his position: x, z in sixteenths of raw, y raw
local yaw = 0              -- his heading, 2048 to the turn
local path, step = nil, 1  -- waypoints {x, y, z} raw, and the one he walks to
local corner = 1           -- the patrol corner he is at or walking to
local state = "start"      -- start, patrol, wait, chase, caught
local timer = 0
local repath = 0          -- time since the last path to the player
local clip
local actor                -- this object, as Actor.* takes it

local function FP(r) return FixedPoint.newFromRaw(r) end

local function play(name)
    if clip ~= name then
        clip = name
        SkinnedAnim.Play(NAME, name, {loop = true})
    end
end

local function isqrt(n)
    if n <= 0 then return 0 end
    local r, s = n, (n + 1) / 2
    while s < r do
        r = s
        s = (r + n / r) / 2
    end
    return r
end

-- Distance across the ground, raw, from him to (px, pz) raw.
local function dist(px, pz)
    local dx, dz = px - x / 16, pz - z / 16
    return isqrt(dx * dx + dz * dz)
end

-- Heading of (dx, dz) as psxsplash turns an object: 0 faces +z, 512 +x.
-- An octant approximation of atan2, as the engine's own getActorRotation.
local function heading(dx, dz)
    local ax, az = dx, dz
    if ax < 0 then ax = -ax end
    if az < 0 then az = -az end
    if ax == 0 and az == 0 then return yaw end
    local a
    if ax < az then a = ax * 256 / az else a = 512 - az * 256 / ax end
    if dz < 0 then a = 1024 - a end
    if dx < 0 then a = -a end
    return a
end

local function turnTo(want)
    local d = want - yaw
    while d > 1024 do d = d - 2048 end
    while d < -1024 do d = d + 2048 end
    if d > TURN then d = TURN elseif d < -TURN then d = -TURN end
    yaw = yaw + d
    if yaw > 1024 then yaw = yaw - 2048 elseif yaw < -1024 then yaw = yaw + 2048 end
end

-- A path from Actor.FindPath to (tx, ty, tz) raw: the centres of the nav
-- regions on the way, then the target itself. Leading waypoints further from
-- the target than he is are dropped, so he does not double back to the
-- middle of the region he is leaving.
local function plan(tx, ty, tz)
    local found = Actor.FindPath(actor, {x = FP(tx), y = FP(ty), z = FP(tz)})
    if found == nil or #found == 0 then
        print("Warden: no path")
        path, step = {{tx, ty, tz}}, 1
        return
    end
    path = {}
    for i = 1, #found do
        local w = found[i]
        path[i] = {w.x._raw, w.y._raw, w.z._raw}
    end
    path[#path][2] = path[#path > 1 and #path - 1 or 1][2]  -- the target's height: the last region's floor
    step = 1
    local here = dist(tx, tz)
    while step < #path do
        local w = path[step]
        local dx, dz = tx - w[1], tz - w[3]
        if isqrt(dx * dx + dz * dz) < here then break end
        step = step + 1
    end
    return #found
end

local function toCorner(i)
    corner = i
    local c = PATROL[i]
    local n = plan(raw(c[1] * 10), y, raw(c[2] * 10))
    print("Warden: corner " .. i .. ", " .. tostring(n) .. " waypoints")
end

-- Walks toward the current waypoint at `speed`; true once past the last.
local function walk(speed, dt)
    local w = path[step]
    local move = speed * dt / 4096
    local dx, dz = w[1] * 16 - x, w[3] * 16 - z
    local d = isqrt((dx / 16) * (dx / 16) + (dz / 16) * (dz / 16)) * 16
    turnTo(heading(dx, dz))
    if d <= move then
        x, z, y = w[1] * 16, w[3] * 16, w[2]
        step = step + 1
        if step > #path then return true end
    else
        x = x + dx * move / d
        z = z + dz * move / d
        y = y + (w[2] - y) * move / d
    end
    return false
end

local function place()
    Actor.SetPosition(actor, {x = FP(x / 16), y = FP(y), z = FP(z / 16)})
    Actor.SetRotation(actor, {x = FP(0), y = FP(yaw * 4), z = FP(0)})
end

function onCreate(self)
    -- psxsplash gives every scripted object an actor id: self is an actor.
    actor = self
    local p = Actor.GetPosition(actor)
    x, y, z = p.x._raw * 16, p.y._raw, p.z._raw * 16
    play("idle")
end

-- Caught: hold the player and play the `gameover` cutscene, the fog going
-- to black with the line; the title follows when it ends.
local function gameOver(s)
    Controls.SetEnabledPlayer1(false)
    local line = UI.FindElement(UI.FindCanvas("Gameover"), "line")
    UI.SetText(line, s)
    UI.SetPosition(line, 160 - 4 * #s, 116)
    Cutscene.Play("gameover", {onComplete = function() Scene.Load(0) end})
end

function onUpdate(self, dt)
    if state == "caught" then return end
    local eye = Player.GetPosition()
    local px, py, pz = eye.x._raw, eye.y._raw + EYES, eye.z._raw
    local d = dist(px, pz)

    if d < CATCH then
        state = "caught"
        play("idle")
        Persist.Set("lost", 2)
        gameOver("Caught by the Warden")
        return
    end

    if state == "start" then
        state = "patrol"
        play("walk")
        toCorner(2)
    elseif state ~= "chase" and d < SIGHT then
        state = "chase"
        print("Warden: chase")
        play("run")
        plan(px, py, pz)
        timer = 0
    end

    if state == "chase" then
        if d > LOSE then
            timer = timer + dt
            if timer >= LOSE_TIME then
                -- Back to the nearest corner of the patrol.
                local best, bestD = 1, nil
                for i = 1, #PATROL do
                    local cd = dist(raw(PATROL[i][1] * 10), raw(PATROL[i][2] * 10))
                    if bestD == nil or cd < bestD then best, bestD = i, cd end
                end
                state = "patrol"
                print("Warden: lost the player")
                play("walk")
                toCorner(best)
            end
        else
            timer = 0
        end
        if state == "chase" then
            repath = repath + dt
            if repath >= REPATH then
                repath = 0
                plan(px, py, pz)
            end
            if walk(RUN, dt) then plan(px, py, pz) end
        end
    elseif state == "patrol" then
        if walk(WALK, dt) then
            state = "wait"
            timer = 0
            play("idle")
        end
    elseif state == "wait" then
        timer = timer + dt
        if timer >= PAUSE then
            state = "patrol"
            play("walk")
            toCorner(corner % #PATROL + 1)
        end
    end
    place()
end
