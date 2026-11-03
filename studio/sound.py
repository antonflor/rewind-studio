"""Light, synthesized sound bed for studio videos (no sample files, no licensing questions).

A quiet warm pad runs under the whole video; each slide gets a soft whoosh as it enters,
faint ticks as elements land, a pluck when a figure finishes counting and a chime for the
hero figure and the closing slide. Everything is generated with numpy at 48 kHz.
"""
import wave

import numpy as np

SR = 48000


def _db(d):
    return 10 ** (d / 20)


def _lowpass(x, a):
    y = np.empty_like(x)
    acc = 0.0
    for k in range(len(x)):
        acc += a * (x[k] - acc)
        y[k] = acc
    return y


def _whoosh(rng, d=0.7):
    n = int(d * SR)
    x = rng.standard_normal(n)
    x = _lowpass(x, 0.06) - _lowpass(x, 0.006)
    env = np.sin(np.pi * np.linspace(0, 1, n)) ** 2
    x *= env
    return x / np.max(np.abs(x))


def _tick():
    t = np.arange(int(0.05 * SR)) / SR
    return np.sin(2 * np.pi * 2400 * t) * np.exp(-t * 140)


def _pluck(f, d=0.6):
    t = np.arange(int(d * SR)) / SR
    x = np.sin(2 * np.pi * f * t) + .35 * np.sin(4 * np.pi * f * t) + .12 * np.sin(6 * np.pi * f * t)
    return x * np.exp(-t * 7) * np.minimum(1, t / 0.004)


def _chime(freqs, d=1.8):
    t = np.arange(int(d * SR)) / SR
    x = np.zeros_like(t)
    for k, f in enumerate(freqs):
        x += (0.8 ** k) * (np.sin(2 * np.pi * f * t) + .25 * np.sin(2 * np.pi * 2.01 * f * t)) * np.exp(-t * (2.6 + k * .4))
    return x * np.minimum(1, t / 0.006) / len(freqs)


def write(timeline, total, path, seed=7):
    """timeline: [{scene, offset, dur, events: [{t, kind}]}] as produced by the motion runtime."""
    rng = np.random.default_rng(seed)
    n = int(total * SR)
    left, right = np.zeros(n), np.zeros(n)

    def add(sig, at, gain, pan=0.0):
        i = int(at * SR)
        if i >= n:
            return
        j = min(n, i + len(sig))
        s = sig[: j - i] * gain
        left[i:j] += s * np.sqrt((1 - pan) / 2)
        right[i:j] += s * np.sqrt((1 + pan) / 2)

    t = np.arange(n) / SR
    pad = np.zeros(n)
    for f, g in [(110, 1.0), (164.81, .7), (220, .5), (277.18, .35), (329.63, .3), (493.88, .12)]:
        for det in (-0.6, 0.6):
            pad += g * np.sin(2 * np.pi * (f + det) * t + rng.uniform(0, 6.28))
    pad *= 0.75 + 0.25 * np.sin(2 * np.pi * 0.11 * t)
    pad *= np.minimum(1, t / 2.0) * np.minimum(1, (total - t) / 2.5) / np.max(np.abs(pad))
    left += pad * _db(-30)
    right += pad * _db(-30)

    whoosh, tick = _whoosh(rng), _tick()
    for si, scene in enumerate(timeline):
        o = scene["offset"]
        add(whoosh, o, _db(-24), pan=-.3 if si % 2 else .3)
        last, pan = -1.0, -0.4
        for e in sorted(scene["events"], key=lambda e: e["t"]):
            at = o + e["t"]
            if e["kind"] == "block":
                if e["t"] < 0.2 or at - last < 0.1:
                    continue
                add(tick, at, _db(-32), pan)
                pan, last = -pan, at
            elif e["kind"] == "land":
                add(_pluck(1318.5), at - 0.02, _db(-30), 0.2)
            elif e["kind"] == "land-big":
                add(_chime([659.25, 987.77, 1318.5]), at - 0.05, _db(-20))
        if scene["scene"] == "cover":
            add(_chime([659.25, 987.77]), o + 0.35, _db(-24))
        if scene["scene"] == "closing":
            add(_chime([440, 554.37, 659.25, 880]), o + 0.45, _db(-19))

    mix = np.stack([left, right], 1)
    mix *= _db(-1.5) / np.max(np.abs(mix))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((mix * 32767).astype("<i2").tobytes())
    return path
