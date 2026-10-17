# Synthesises the sound effects as 16-bit mono WAV files:
#   python3 -P art/sfx.py <outdir>
# ignite  a beacon catching: a breathy whoomp and a few crackles, 1.2 s
# chime   all three beacons lit: a rising three-note bell, 2.4 s
# wind    the valley's ambience, a 4 s loop of moving air whose ends meet
# A fixed seed makes every run write the same bytes.
import os
import sys
import wave

import numpy as np

RATE = 22050
rng = np.random.default_rng(1163)


def lowpass(x, cutoff):
    # One-pole low-pass; `cutoff` in Hz, a number or one per sample.
    a = 1.0 - np.exp(-2.0 * np.pi * np.broadcast_to(cutoff, x.shape) / RATE)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


def ignite():
    n = int(1.2 * RATE)
    t = np.arange(n) / RATE
    # The whoomp: noise through a filter that opens then settles, under a
    # fast attack and a long fall.
    env = np.minimum(t / 0.04, 1.0) * np.exp(-t * 3.2)
    body = lowpass(rng.standard_normal(n), 300.0 + 2600.0 * np.exp(-t * 6.0)) * env * 2.2
    # Crackles: short clicks of bright noise scattered over the first second.
    crack = np.zeros(n)
    for start in rng.integers(int(0.05 * RATE), int(1.0 * RATE), 14):
        k = int(0.006 * RATE)
        crack[start:start + k] += rng.standard_normal(k) * np.exp(-np.arange(k) / (0.0015 * RATE)) * 0.5
    return body + crack


def chime():
    n = int(2.4 * RATE)
    t = np.arange(n) / RATE
    out = np.zeros(n)
    # C5, E5, G5 a fifth of a second apart, each a bell: the fundamental and
    # two inharmonic partials that die away faster.
    for k, f in enumerate([523.25, 659.25, 783.99]):
        tk = t - 0.2 * k
        on = tk >= 0
        tt = tk[on]
        bell = (np.sin(2 * np.pi * f * tt) * np.exp(-tt * 2.0)
                + 0.5 * np.sin(2 * np.pi * f * 2.76 * tt) * np.exp(-tt * 4.0)
                + 0.25 * np.sin(2 * np.pi * f * 5.40 * tt) * np.exp(-tt * 7.0))
        out[on] += bell * np.minimum(tt / 0.004, 1.0) * 0.4
    return out


def wind():
    n = int(4.0 * RATE)
    t = np.arange(n) / RATE
    # Gusts: low-passed noise whose cutoff and level drift with two slow
    # sines that both fit the loop a whole number of times, so the loop has
    # no seam in its envelope.
    drift = 0.5 + 0.3 * np.sin(2 * np.pi * t / 4.0) + 0.2 * np.sin(2 * np.pi * t * 3 / 4.0 + 1.0)
    noise = rng.standard_normal(n + RATE)
    air = lowpass(noise, np.concatenate([np.full(RATE, 500.0), 250.0 + 700.0 * drift]))
    # The filter warmed up on the extra second; cross-fade the tail of the
    # loop into what comes before its start so the noise itself meets too.
    lead, air = air[:RATE], air[RATE:]
    k = int(0.25 * RATE)
    fade = np.linspace(0.0, 1.0, k)
    air[-k:] = air[-k:] * (1.0 - fade) + lead[-k:] * fade
    return air * (0.4 + 0.6 * drift) * 1.6


def write(path, x, peak=0.8):
    x = x / np.max(np.abs(x)) * peak
    pcm = np.round(x * 32767.0).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    write(os.path.join(out, "ignite.wav"), ignite())
    write(os.path.join(out, "chime.wav"), chime())
    write(os.path.join(out, "wind.wav"), wind(), peak=0.5)


main()
