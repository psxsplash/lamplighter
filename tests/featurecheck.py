# Exports every scene of the project and the disc, then checks each feature in
# features.json against the output. A feature whose phase is at or below the
# file's "phase" has to be in use; one that is not fails the check.
#
#   python3 -P tests/featurecheck.py <splashedit-ng checkout> <splashpack-cli> <psxsplash cdrom .ps-exe>
#
# The splashedit-ng checkout provides tests/splashdiff.py, which reads splashpacks.
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# FEATURECHECK_PROJECT points the check at another project (its own tests use it).
PROJECT = os.environ.get("FEATURECHECK_PROJECT", os.path.join(ROOT, "project"))


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        sys.stdout.write(p.stdout + p.stderr)
        sys.exit(f"featurecheck: failed: {' '.join(cmd)}")
    return p.stdout


def main():
    editor, cli, engine = sys.argv[1:4]
    sys.path.insert(0, os.path.join(editor, "tests"))
    import splashdiff

    # FEATURECHECK_FEATURES replaces features.json (the self-test uses it).
    spec = json.load(open(os.environ.get("FEATURECHECK_FEATURES", os.path.join(ROOT, "features.json"))))
    listing = os.path.join(PROJECT, "scenes.list")
    if os.path.exists(listing):
        scenes = [l.strip() for l in open(listing) if l.strip()]
    else:
        scenes = sorted(f for f in os.listdir(PROJECT) if f.endswith(".scene"))
    out = tempfile.mkdtemp(prefix="lamplighter-")

    stats, packs, sidecars, texts = [], [], set(), []
    for s in scenes:
        base = os.path.join(out, os.path.splitext(s)[0])
        stats += run([cli, "export", os.path.join(PROJECT, s), "-o", base + ".splashpack",
                      "--project", PROJECT, "--stats"]).splitlines()
        packs.append(splashdiff.Pack(base + ".splashpack"))
        for f in os.listdir(out):
            if f.startswith(os.path.basename(base) + "."):
                sidecars.add(os.path.splitext(f)[1])
        texts.append(open(os.path.join(PROJECT, s)).read())
    disc = run([cli, "disc", *[os.path.join(PROJECT, s) for s in scenes], "--engine", engine,
                "-o", os.path.join(out, "lamplighter.bin"), "--project", PROJECT]).splitlines()
    lua = []
    for p in packs:
        for blob in p.lua:
            lua.append(blob.decode("latin-1") if isinstance(blob, bytes) else str(blob))

    # The agent on `obj` plays a clip in at least one state it stays in
    # (Idle, Patrol, Seek, Flee, Wander), and every such clip loops; a clip
    # that plays once stops on its last frame. Read from the --stats lines
    # `agent ... clips=State:index,... <obj>` and `skin clip ... loop=0|1 <obj>/<clip>`.
    def agent_clips(obj):
        held = {"Idle", "Patrol", "Seek", "Flee", "Wander"}
        agent = re.compile(r"^agent object=\d+ .*\bclips=(\S+) " + re.escape(obj) + "$")
        clip = re.compile(r"^skin clip .*\bloop=([01]) " + re.escape(obj) + "/(.+)$")
        states = None
        for l in stats:
            m = agent.match(l)
            if m:
                states = [] if m.group(1) == "-" else [x.split(":") for x in m.group(1).split(",")]
        if states is None:
            return False, f"no agent on {obj}"
        clips = [(m.group(2), m.group(1) == "1") for m in map(clip.match, stats) if m]
        used = [(s, int(i)) for s, i in states if s in held]
        if not used:
            return False, f"{obj}: no clip in a held state"
        once = [f"{s}:{clips[i][0]}" for s, i in used if i >= len(clips) or not clips[i][1]]
        if once:
            return False, f"{obj}: plays once in {','.join(once)}"
        return True, f"{obj}: " + ",".join(f"{s}:{clips[i][0]}" for s, i in used)

    def lines_match(lines, pat):
        r = re.compile(pat)
        return any(r.search(l) for l in lines)

    def check(c):
        k = c["kind"]
        if k == "scenes":
            return len(scenes) >= c["min"], f"{len(scenes)} scenes"
        if k == "header":
            vals = [p.h[c["field"]] for p in packs]
            return any(vals), f"{c['field']} per scene {vals}"
        if k == "stats":
            return lines_match(stats, c["re"]), c["re"]
        if k == "disc":
            return lines_match(disc, c["re"]), c["re"]
        if k == "lua":
            return lines_match(lua, c["re"]), c["re"]
        if k == "scene":
            return lines_match(texts, c["re"]), c["re"]
        if k == "sidecar":
            return c["ext"] in sidecars, f"{c['ext']} beside a pack"
        if k == "agent-clips":
            return agent_clips(c["object"])
        sys.exit(f"featurecheck: unknown check kind {k}")

    phase = int(os.environ.get("FEATURECHECK_PHASE", spec["phase"]))
    required = failed = 0
    for f in spec["features"]:
        ok, why = check(f["check"])
        need = f["phase"] <= phase
        required += need
        failed += need and not ok
        state = "PASS" if ok else ("FAIL" if need else "planned")
        print(f"feature {f['id']} {state} (phase {f['phase']}): {f['what']} [{why}]")
    print(f"featurecheck: phase {phase}, {required} required, {failed} failed, "
          f"{len(spec['features'])} listed")
    sys.exit(1 if failed or required == 0 else 0)


main()
