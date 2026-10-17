# The CD-DA music, synthesised: stereo 44100 Hz 16-bit WAVs, deterministic.
#   python3 -P art/music.py <outdir>
# title.wav (disc track 2): a slow A minor theme, pad, arpeggio and a bell
# melody, 36 s. valley.wav (track 3): D minor ambience, a drone, slow pad
# chords, wind and scattered bell notes, 40 s. tools/build.sh encodes both
# to Ogg Vorbis for the project.
import os
import random
import sys
import wave

import numpy as np

RATE = 44100


def hz(midi):
    return 440.0 * 2.0 ** ((midi - 69) / 12.0)


def envelope(n, attack, release):
    t = np.arange(n) / RATE
    env = np.minimum(1.0, t / max(attack, 1e-3))
    tail = (n / RATE) - t
    return env * np.minimum(1.0, tail / max(release, 1e-3))


def lowpass(x, cutoff):
    # One-pole low-pass, run along the signal.
    a = np.exp(-2.0 * np.pi * cutoff / RATE)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc = (1.0 - a) * x[i] + a * acc
        y[i] = acc
    return y


def pad(midi, seconds, bright=5):
    # Three slightly detuned voices, each the first `bright` harmonics of a saw.
    n = int(seconds * RATE)
    t = np.arange(n) / RATE
    out = np.zeros(n)
    for detune in (-0.06, 0.0, 0.07):
        f = hz(midi + detune)
        for k in range(1, bright + 1):
            out += np.sin(2 * np.pi * f * k * t) / (k * 1.6)
    return out * envelope(n, min(1.2, seconds / 3), min(1.5, seconds / 2)) / 3.0


def bell(midi, seconds=2.5):
    n = int(seconds * RATE)
    t = np.arange(n) / RATE
    f = hz(midi)
    tone = (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * f * 2.0 * t) * np.exp(-t * 3.0)
            + 0.18 * np.sin(2 * np.pi * f * 3.01 * t) * np.exp(-t * 5.0))
    return tone * np.exp(-t * 1.6) * envelope(n, 0.005, 0.2)


def pluck(midi, seconds=0.9):
    n = int(seconds * RATE)
    t = np.arange(n) / RATE
    f = hz(midi)
    tone = sum(np.sin(2 * np.pi * f * k * t) * np.exp(-t * (2.5 + 2.0 * k)) / k for k in range(1, 5))
    return tone * envelope(n, 0.004, 0.1)


class Mix:
    def __init__(self, seconds):
        self.n = int(seconds * RATE)
        self.l = np.zeros(self.n)
        self.r = np.zeros(self.n)

    def add(self, at, sound, gain, pan=0.0):
        i = int(at * RATE)
        if i >= self.n:
            return
        s = sound[:self.n - i] * gain
        self.l[i:i + len(s)] += s * np.sqrt(0.5 * (1.0 - pan))
        self.r[i:i + len(s)] += s * np.sqrt(0.5 * (1.0 + pan))

    def echo(self, delay, feedback, wet):
        # Ping-pong delay: each repeat crosses to the other side.
        d = int(delay * RATE)
        l, r = self.l.copy(), self.r.copy()
        el, er = np.zeros(self.n), np.zeros(self.n)
        for start in range(d, self.n, d):
            end = min(self.n, start + d)
            el[start:end] = (r[start - d:end - d] + er[start - d:end - d] * feedback)
            er[start:end] = (l[start - d:end - d] + el[start - d:end - d] * feedback)
        self.l += el * wet
        self.r += er * wet

    def write(self, path, fade=2.0):
        env = envelope(self.n, 0.5, fade)
        peak = max(np.abs(self.l).max(), np.abs(self.r).max())
        scale = 0.7 * 32767 / peak
        data = np.empty(self.n * 2, dtype="<i2")
        data[0::2] = np.round(self.l * env * scale)
        data[1::2] = np.round(self.r * env * scale)
        with wave.open(path, "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(data.tobytes())


def title():
    beat = 60.0 / 66.0
    bar = 4 * beat
    # (root, chord tones as MIDI notes) per bar: Am F C G Am F Dm E Am Am.
    chords = [(45, [57, 60, 64]), (41, [57, 60, 65]), (48, [55, 60, 64]), (43, [55, 59, 62]),
              (45, [57, 60, 64]), (41, [57, 60, 65]), (38, [57, 62, 65]), (40, [56, 59, 64]),
              (45, [57, 60, 64]), (45, [57, 60, 64])]
    # Melody: (bar, beat, MIDI note, beats held).
    melody = [(1, 0, 76, 2), (1, 2, 74, 1), (1, 3, 72, 1), (2, 0, 72, 3), (3, 0, 71, 2), (3, 2, 74, 2),
              (4, 0, 76, 2), (4, 2, 79, 1), (4, 3, 77, 1), (5, 0, 76, 3), (6, 0, 74, 2), (6, 2, 77, 2),
              (7, 0, 76, 2), (7, 2, 71, 2), (8, 0, 69, 4)]
    mix = Mix(len(chords) * bar + 1.0)
    for i, (root, tones) in enumerate(chords):
        at = i * bar
        mix.add(at, pad(root, bar + 0.4, bright=4), 0.30)
        for k, m in enumerate(tones):
            mix.add(at, pad(m, bar + 0.4, bright=3), 0.10, pan=(k - 1) * 0.5)
        if 0 < i < len(chords) - 1:
            order = tones + [tones[1] + 12, tones[2] + 12, tones[1] + 12, tones[2], tones[1]]
            for s in range(8):
                mix.add(at + s * beat / 2, pluck(order[s % len(order)]), 0.16, pan=0.6 if s % 2 else -0.6)
    for b, bt, m, held in melody:
        mix.add(b * bar + bt * beat, bell(m, held * beat + 1.5), 0.24, pan=0.1)
    mix.echo(beat * 0.75, 0.35, 0.35)
    return mix


def valley():
    rnd = random.Random(11)
    seconds = 40.0
    mix = Mix(seconds)
    # Drone: D2 and A2, the whole length.
    mix.add(0.0, pad(38, seconds, bright=3), 0.32, pan=-0.2)
    mix.add(0.0, pad(45, seconds, bright=3), 0.22, pan=0.2)
    # Pad chords, 10 s each: Dm Bb Gm A.
    for i, tones in enumerate([[62, 65, 69], [62, 65, 70], [62, 67, 70], [61, 64, 69]]):
        for k, m in enumerate(tones):
            mix.add(i * 10.0, pad(m, 10.6, bright=2), 0.09, pan=(k - 1) * 0.6)
    # Wind: noise low-passed, swelling twice.
    noise = np.array([rnd.uniform(-1.0, 1.0) for _ in range(mix.n)])
    t = np.arange(mix.n) / RATE
    wind = lowpass(noise, 380.0) * (0.55 + 0.45 * np.sin(2 * np.pi * t / 20.0 - 1.2))
    mix.add(0.0, wind, 0.9, pan=0.3)
    # Bells from D minor pentatonic, at seeded times.
    scale = [74, 77, 79, 81, 84, 86]
    at = 1.5
    while at < seconds - 4.0:
        mix.add(at, bell(rnd.choice(scale), 3.5), 0.16, pan=rnd.uniform(-0.7, 0.7))
        at += rnd.choice([1.7, 2.6, 3.4, 4.3])
    mix.echo(0.62, 0.45, 0.4)
    return mix


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    title().write(os.path.join(out, "title.wav"))
    valley().write(os.path.join(out, "valley.wav"), fade=4.0)


main()
