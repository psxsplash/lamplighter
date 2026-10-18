# Tests tests/featurecheck.py itself, so a feature check that can never pass
# (or never fail) shows up here and not as a green build.
#
#   python3 -P tests/featurecheck_selftest.py <splashedit-ng checkout> <splashpack-cli> <psxsplash cdrom .ps-exe>
#
# 1. Lamplighter at its own phase passes.
# 2. Lamplighter one phase further fails, naming the missing features
#    (while features.json plans a later phase).
# 3. On a control project (the editor's third-person template plus a CD-DA
#    track), every check kind reports a feature it uses as PASS and one it
#    does not use as FAIL.
# 4. agent-clips fails on a copy of lamplighter whose Warden walk plays once,
#    and on one whose agent has no state clips.
import json
import math
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
failures = 0


def check(cond, what):
    global failures
    print(("ok   " if cond else "FAIL ") + what)
    failures += not cond


def run(args, **env):
    e = dict(os.environ, **env)
    p = subprocess.run([sys.executable, "-P", os.path.join(HERE, "featurecheck.py"), *args],
                       capture_output=True, text=True, env=e)
    return p.returncode, p.stdout + p.stderr


def tone(path):
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(44100)
        frames = b"".join(struct.pack("<hh", v, v) for v in
                          (int(8000 * math.sin(i * 2 * math.pi * 440 / 44100)) for i in range(44100 * 3)))
        w.writeframes(frames)


def main():
    args = sys.argv[1:4]
    phase = json.load(open(os.path.join(ROOT, "features.json")))["phase"]

    rc, out = run(args)
    check(rc == 0, f"phase {phase}: lamplighter passes")
    check(f"featurecheck: phase {phase}," in out and " 0 failed" in out, "summary line says 0 failed")

    # Only while features.json plans a later phase: at the last one there is
    # nothing left to fail, and step 3 still proves that FAIL is reported.
    features = json.load(open(os.path.join(ROOT, "features.json")))["features"]
    if any(f["phase"] > phase for f in features):
        rc, out = run(args, FEATURECHECK_PHASE=str(phase + 1))
        missing = [l for l in out.splitlines() if " FAIL " in l]
        check(rc == 1, f"phase {phase + 1}: lamplighter fails")
        check(len(missing) > 0, f"phase {phase + 1}: {len(missing)} features reported FAIL")
    else:
        print(f"skip phase {phase + 1}: no feature is planned past phase {phase}")

    # Every check kind once with a value the control project has (must PASS)
    # and once with one it lacks (must FAIL).
    kinds = {
        "scenes": ({"min": 1}, {"min": 5}),
        "header": ({"field": "interactableCount"}, {"field": "roomCount"}),
        "stats": ({"re": "^nav regions=[1-9]"}, {"re": "^rooms=[1-9]"}),
        "disc": ({"re": "^track 2 lba="}, {"re": "^track 3 lba="}),
        "lua": ({"re": "Entity\\.Find"}, {"re": "NoSuchCall"}),
        "scene": ({"re": "\\.blocks\""}, {"re": "\\.nosuchext\""}),
        "sidecar": ({"ext": ".vram"}, {"ext": ".nosuchext"}),
    }
    feats = []
    for k, (yes, no) in kinds.items():
        feats.append({"id": k + "-yes", "phase": 0, "what": "", "check": dict(kind=k, **yes)})
        feats.append({"id": k + "-no", "phase": 0, "what": "", "check": dict(kind=k, **no)})
    ctl = tempfile.mkdtemp(prefix="featurecheck-control-")
    shutil.copytree(os.path.join(args[0], "templates", "third-person"), ctl, dirs_exist_ok=True)
    os.remove(os.path.join(ctl, "template.json"))
    tone(os.path.join(ctl, "tone.wav"))
    with open(os.path.join(ctl, "disc.json"), "w") as f:
        json.dump({"volume": "", "licence": "", "tracks": ["tone.wav"]}, f)
    spec = os.path.join(ctl, "features-selftest.json")
    with open(spec, "w") as f:
        json.dump({"phase": 0, "features": feats}, f)
    rc, out = run(args, FEATURECHECK_PROJECT=ctl, FEATURECHECK_FEATURES=spec)
    lines = out.splitlines()
    for k in kinds:
        check(any(l.startswith(f"feature {k}-yes PASS") for l in lines), f"{k}: a used feature PASSes")
        check(any(l.startswith(f"feature {k}-no FAIL") for l in lines), f"{k}: a missing feature FAILs")
    check(rc == 1, "control project fails overall")
    check(f"{len(feats)} listed" in out, f"all {len(feats)} control features reported")
    shutil.rmtree(ctl)

    # agent-clips on copies of lamplighter: the Warden's walk made one-shot,
    # then his state clips taken away; each must FAIL.
    spec = {"phase": 0, "features": [{"id": "agent-clips", "phase": 0, "what": "",
                                      "check": {"kind": "agent-clips", "object": "Warden"}}]}
    for name, edit in (("one-shot walk", "anim"), ("no state clips", "scene")):
        tmp = tempfile.mkdtemp(prefix="featurecheck-agent-")
        shutil.copytree(os.path.join(ROOT, "project"), tmp, dirs_exist_ok=True)
        if edit == "anim":
            f = os.path.join(tmp, "models", "warden", "walk.anim")
            a = json.load(open(f))
            a["loop"] = False
            json.dump(a, open(f, "w"), indent=2)
        else:
            f = os.path.join(tmp, "valley.scene")
            sc = json.load(open(f))
            for o in sc["objects"]:
                for c in o.get("components", []):
                    if c.get("type") == "agent":
                        c["stateClips"] = {}
            json.dump(sc, open(f, "w"), indent=2)
        sp = os.path.join(tmp, "features-selftest.json")
        json.dump(spec, open(sp, "w"))
        rc, out = run(args, FEATURECHECK_PROJECT=tmp, FEATURECHECK_FEATURES=sp)
        check(rc == 1 and "feature agent-clips FAIL" in out, f"agent-clips: {name} FAILs")
        shutil.rmtree(tmp)

    print(f"featurecheck_selftest: {failures} failures")
    sys.exit(1 if failures else 0)


main()
