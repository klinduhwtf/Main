"""Звук для заставки «1 СТУДИЯ», вариант 3 — спокойный, серьёзный, без ритма.

Синтез с нуля (без сэмплов). Тайминги совпадают с zastavka_v3.html:
  0.0–2.4  низкий гул (ре) и мягкое нарастание «воздуха»
  2.4      глубокий негромкий удар + раскрытие струнного аккорда — появляется логотип
  3.3+     три редкие ноты «фортепиано» с неравными паузами
  7.2–8.0  затухание
Выход: zvuk_v3.wav (48 кГц, 24 бит, стерео).
Запуск: python3 zvuk_v3.py
"""
import wave
from pathlib import Path

import numpy as np
from scipy import signal

SR = 48000
DUR = 8.0
REVEAL, WORD0 = 2.4, 3.3
rng = np.random.default_rng(3)
N = int(SR * DUR)
t = np.arange(N) / SR
L = np.zeros(N); R = np.zeros(N)


def tt(d): return np.arange(int(d * SR)) / SR
def lp(x, f, o=2): return signal.sosfilt(signal.butter(o, f, "low", fs=SR, output="sos"), x)
def hp(x, f, o=2): return signal.sosfilt(signal.butter(o, f, "high", fs=SR, output="sos"), x)
def bp(x, a, b, o=2): return signal.sosfilt(signal.butter(o, [a, b], "band", fs=SR, output="sos"), x)


def note(name):
    names = {"C": -9, "C#": -8, "D": -7, "D#": -6, "E": -5, "F": -4, "F#": -3,
             "G": -2, "G#": -1, "A": 0, "A#": 1, "B": 2}
    return 440.0 * 2 ** ((names[name[:-1]] + 12 * (int(name[-1]) - 4)) / 12)


def place(sig, at, gain=1.0, pan=0.0):
    sig = sig.copy()
    tail = min(len(sig), int(0.3 * SR))                   # плавный хвост — без щелчка на обрыве
    sig[-tail:] *= np.linspace(1, 0, tail) ** 2
    i = int(at * SR); sig = sig[: max(0, N - i)]
    gl, gr = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    L[i:i + len(sig)] += sig * gain * gl * np.sqrt(2)
    R[i:i + len(sig)] += sig * gain * gr * np.sqrt(2)


def saw(freq, d, detune=0.0, vib=0.0, vib_rate=5.0, phase=0.0):
    x = tt(d)
    f = freq * (1 + detune) * (1 + vib * np.sin(2 * np.pi * vib_rate * x + phase))
    ph = np.cumsum(f) / SR + phase
    return 2 * (ph % 1.0) - 1


# ---------- Гул: ре (D1/D2) с медленным дыханием ----------
x = tt(DUR)
drone = (np.sin(2 * np.pi * note("D2") * x) * 0.6 + np.sin(2 * np.pi * note("D1") * x) * 0.5
         + lp(saw(note("D2"), DUR, 0.002) + saw(note("A2"), DUR, -0.002), 400) * 0.25)
drone *= (0.85 + 0.15 * np.sin(2 * np.pi * 0.18 * x))
drone_env = np.clip(x / 2.2, 0, 1) ** 1.5
place(drone * drone_env, 0.0, 0.35)

# ---------- Нарастание «воздуха» к появлению логотипа ----------
x = tt(REVEAL + 0.05)
air = bp(rng.standard_normal(len(x)), 400, 3000)
air2 = bp(rng.standard_normal(len(x)), 400, 3000)
swell = (x / (REVEAL + 0.05)) ** 3
place(lp(air, 1800) * swell, 0.0, 0.10, pan=-0.4)
place(lp(air2, 1800) * swell, 0.0, 0.10, pan=0.4)
# обратный «вдох» струнных
sw = sum(saw(note(n), len(x) / SR, d) for n in ("D3", "A3") for d in (-0.003, 0.003))
place(lp(sw, 900) * swell ** 1.5, 0.0, 0.05)

# ---------- 2.4 с: глубокий мягкий удар ----------
x = tt(4.0)
boom = np.sin(2 * np.pi * np.cumsum(36 + 22 * np.exp(-x * 5)) / SR) * np.exp(-x * 1.1)
thump = lp(rng.standard_normal(len(x)), 180) * np.exp(-x * 9) * 0.8
place(boom + thump, REVEAL, 0.75)
# тихий «тимпан» сверху — мягкий шумовой хвост
place(lp(hp(rng.standard_normal(len(x)), 120), 900) * np.exp(-x * 4) * 0.25, REVEAL, 0.3)

# ---------- Струнный аккорд: Dm(add9) → медленно гаснет ----------
d = DUR - REVEAL
x = tt(d)
chord = ["D2", "A2", "D3", "F3", "A3", "E4"]
pad = np.zeros(len(x))
for k, n in enumerate(chord):
    for j, det in enumerate((-0.004, 0.0, 0.004)):
        pad += saw(note(n), d, det, vib=0.0025, vib_rate=4.6 + 0.3 * j, phase=k * 0.7 + j)
pad = lp(pad, 1400, 4) / (len(chord) * 3)
pad_env = np.minimum(1, x / 0.9) ** 2 * np.exp(-x * 0.22)
pl, pr = pad * pad_env, np.roll(pad, 240) * pad_env
place(pl, REVEAL, 0.9, pan=-0.35)
place(pr, REVEAL, 0.9, pan=0.35)


# ---------- «Фортепиано»: три ноты с неравными паузами ----------
def piano(f, d=4.0):
    x = tt(d)
    s = np.zeros(len(x))
    for h in range(1, 9):
        fh = f * h * np.sqrt(1 + 0.0004 * h * h)          # лёгкая негармоничность струны
        s += np.sin(2 * np.pi * fh * x) / h ** 1.3 * np.exp(-x * (0.9 + 0.55 * h))
    hammer = lp(rng.standard_normal(len(x)), 2500) * np.exp(-x * 120) * 0.15
    return (s + hammer) * np.minimum(1, x / 0.004)


for n, at, g, pan in [("A3", WORD0, 0.22, -0.15), ("D4", WORD0 + 0.85, 0.20, 0.1), ("F4", WORD0 + 2.05, 0.16, 0.2)]:
    place(piano(note(n)), at, g, pan)
place(piano(note("D3")), WORD0 + 2.05, 0.10, -0.2)

# ---------- Реверб, большой зал (3 с) ----------
ir_t = tt(3.0)
irL = lp(rng.standard_normal(len(ir_t)), 5000) * np.exp(-ir_t * 2.3)
irR = lp(rng.standard_normal(len(ir_t)), 5000) * np.exp(-ir_t * 2.3)
for ir in (irL, irR):
    ir[: int(0.02 * SR)] = 0                                 # предзадержка 20 мс
wetL = signal.fftconvolve(L, irL)[:N] / np.sqrt(np.sum(irL ** 2)) * 0.30
wetR = signal.fftconvolve(R, irR)[:N] / np.sqrt(np.sum(irR ** 2)) * 0.30
L, R = L + wetL, R + wetR

fade = np.clip((DUR - t) / 0.8, 0, 1) ** 2
L, R = hp(L * fade, 25), hp(R * fade, 25)
peak = max(np.abs(L).max(), np.abs(R).max())
L, R = np.tanh(L / peak * 1.1) / np.tanh(1.1) * 0.89, np.tanh(R / peak * 1.1) / np.tanh(1.1) * 0.89

out = Path(__file__).with_name("zvuk_v3.wav")
pcm = (np.stack([L, R], 1) * (2 ** 23 - 1)).astype("<i4").tobytes()
b24 = b"".join(pcm[i:i + 3] for i in range(0, len(pcm), 4))
with wave.open(str(out), "wb") as w:
    w.setnchannels(2); w.setsampwidth(3); w.setframerate(SR); w.writeframes(b24)
print("ok:", out)
