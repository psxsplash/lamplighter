# Tests tests/featurecheck.py itself, so a feature check that can never pass
# (or never fail) shows up here and not as a green build.
#
#   python3 -P tests/featurecheck_selftest.py <splashedit-ng checkout> <splashpack-cli> <psxsplash cdrom .ps-exe>
#
# 1. Lamplighter at its own phase passes.
# 2. Lamplighter one phase further fails, naming the missing features.
# 3. A control project (the editor's third-person template plus a CD-DA track)
#    makes the lua, blocks, interactables and cd-music checks pass, so each of
#    those check kinds can report a feature as used.
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

    rc, out = run(args, FEATURECHECK_PHASE=str(phase + 1))
    missing = [l for l in out.splitlines() if " FAIL " in l]
    check(rc == 1, f"phase {phase + 1}: lamplighter fails")
    check(len(missing) > 0, f"phase {phase + 1}: {len(missing)} features reported FAIL")

    ctl = tempfile.mkdtemp(prefix="featurecheck-control-")
    shutil.copytree(os.path.join(args[0], "templates", "third-person"), ctl, dirs_exist_ok=True)
    os.remove(os.path.join(ctl, "template.json"))
    tone(os.path.join(ctl, "tone.wav"))
    with open(os.path.join(ctl, "disc.json"), "w") as f:
        json.dump({"volume": "", "licence": "", "tracks": ["tone.wav"]}, f)
    rc, out = run(args, FEATURECHECK_PROJECT=ctl, FEATURECHECK_PHASE="99")
    lines = out.splitlines()
    for fid in ["lua", "blocks", "interactables", "cd-music", "nav"]:
        check(any(l.startswith(f"feature {fid} PASS") for l in lines), f"control project: {fid} PASS")
    check(any(l.startswith("feature scenes FAIL") for l in lines), "control project: scenes FAIL (one scene)")
    check(rc == 1, "control project at phase 99 fails overall")
    shutil.rmtree(ctl)

    print(f"featurecheck_selftest: {failures} failures")
    sys.exit(1 if failures else 0)


main()
