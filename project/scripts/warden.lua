-- The Warden in the valley (scene 1), on the Warden object: a skinned mesh
-- with the clips "walk", "run" and "idle", and psxsplash's agent component
-- (tools/scenes.py). The engine walks him round the four corners of his
-- patrol on the nav regions, turns him the way he goes, and watches for the
-- player, 10 m all round. This script says what he does about it:
--   he sees the player: he runs at him (Seek, the engine finding the way
--   and following the player as he moves)
--   60 updates without seeing him (the agent's alert timeout, which counts
--   the engine's updates, not thirtieths of a second: about four seconds
--   at the valley's frame rate): he walks on to the corner he was making for
--   at each corner he waits a second and a half
--   within CATCH he has caught the player: lost 2 in Persist, the
--   `gameover` cutscene ("Caught by the Warden"), and back to the title,
--   which says so (title.lua)
-- The skin's clips do not loop, so the clip for each state is played from
-- here, looping, and not by the agent.
--
-- psxsplash's Lua has whole numbers only. Positions are in GTE units, 4096
-- to the unit, one unit 100 m at the valley's GTE scaling of 100, with y
-- pointing down: a metre is 40.96 (written raw below, from metres * 4096 /
-- 100). The agent's speed is whole raw units a frame at 30 frames a second:
-- 2 is 1.46 m/s, 3 is 2.20 m/s, 4 is 2.93 m/s. The player's 3 m/s is stored
-- as 4 too, so he runs at 3, under the player's speed, and not at the 4
-- nearer 2.6 m/s, which is the player's own. The engine steps an agent
-- along the longer of x and z, so going diagonally he is up to 1.4 times as
-- fast, and the d-pad's walk loses some to rounding: a walking player does
-- not get away from him; a sprinting one does. onUpdate's dt is 4096 a
-- thirtieth of a second.

local NAME = "Warden"
local function raw(dm) return dm * 4096 / 1000 end  -- decimetres to GTE raw

local IDLE, PATROL, SEEK = 0, 1, 2  -- the agent states he uses
local CLIPS = {[IDLE] = "idle", [PATROL] = "walk", [SEEK] = "run"}
local WALK = 2             -- 1.46 m/s, raw a frame (the component's speed)
local RUN = 3              -- 2.20 m/s
local CATCH = raw(14)      -- 1.4 m across the ground: caught
local PAUSE = 45 * 4096    -- the wait at a corner, a second and a half

local actor                -- this object, as Actor.* and Agent.* take it
local wait                 -- time left of a wait at a corner, nil walking
local caught = false

local function FP(r) return FixedPoint.newFromRaw(r) end

local function isqrt(n)
    if n <= 0 then return 0 end
    local r, s = n, (n + 1) / 2
    while s < r do
        r = s
        s = (r + n / r) / 2
    end
    return r
end

function onCreate(self)
    -- psxsplash gives every scripted object an actor id: self is an actor.
    actor = self
    SkinnedAnim.Play(NAME, "idle", {loop = true})
end

function onStateEnter(self, state, old)
    local clip = CLIPS[state]
    if clip then SkinnedAnim.Play(NAME, clip, {loop = true}) end
end

function onTargetSeen(self, target)
    if caught then return end
    wait = nil
    Agent.SetPatrolEnabled(self, true)
    Agent.SetSpeed(self, FP(RUN))
    Agent.SetState(self, SEEK)
    Agent.SetTarget(self, Actor.GetPlayer())
    print("Warden: chase")
end

function onTargetLost(self, target)
    if caught then return end
    -- Stop drops the player as his target; in Patrol the agent then sets
    -- off for the corner he was walking to before the chase.
    Agent.Stop(self)
    Agent.SetSpeed(self, FP(WALK))
    Agent.SetState(self, PATROL)
    print("Warden: lost the player")
end

-- index counts the corners from 0. The agent has already turned to the
-- next one; Idle would go straight back to Patrol while patrolling is on,
-- so it is off until the wait is over.
function onPatrolPoint(self, index)
    Agent.SetPatrolEnabled(self, false)
    Agent.Stop(self)
    Agent.SetState(self, IDLE)
    wait = PAUSE
    print("Warden: corner " .. (index + 1))
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
    if caught then return end
    local me = Actor.GetPosition(actor)
    local eye = Player.GetPosition()
    local dx, dz = eye.x._raw - me.x._raw, eye.z._raw - me.z._raw

    if isqrt(dx * dx + dz * dz) < CATCH then
        caught = true
        Agent.SetEnabled(self, false)
        Agent.SetState(self, IDLE)
        Persist.Set("lost", 2)
        gameOver("Caught by the Warden")
        return
    end

    if wait then
        wait = wait - dt
        if wait <= 0 then
            wait = nil
            Agent.SetPatrolEnabled(self, true)  -- Idle goes on to Patrol
            print("Warden: walking on")
        end
    end
end
