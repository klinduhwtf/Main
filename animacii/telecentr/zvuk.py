"""Звук для заставки «ТЕЛЕЦЕНТР» — та же оркестровая основа, что у «1 СТУДИЯ» v4,
чтобы заставки канала звучали одной семьёй, плюс свои детали: перелив и «сигнал эфира».

Синтез с нуля (без сэмплов). Тайминги совпадают с zastavka.html:
  0.0–3.2  гул в ре, «воздух», мягкая дробь литавр нарастает
  0.9–3.2  восходящий перелив (челеста) — вышка прорисовывается снизу вверх
  3.2      глубокий удар + аккорд Dsus2 — загорается маяк
  3.2, 3.65, 4.1, 6.4  «сигнал эфира» — волны от маяка
  4.4      аккорд разрешается в ре мажор — появляется «СТУДИЯ»
  5.8      тихий высокий звон на блике
  8.2–9.0  затухание
Выход: zvuk.wav (48 кГц, 24 бит, стерео).
Запуск: python3 zvuk.py
"""
import wave
from pathlib import Path

import numpy as np
from scipy import signal

SR = 48000
DUR = 9.0
REVEAL, WORD0, SHINE = 3.2, 4.4, 5.8
rng = np.random.default_rng(7)
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


# ---------- Гул в ре ----------
x = tt(DUR)
drone = (np.sin(2 * np.pi * note("D2") * x) * 0.6 + np.sin(2 * np.pi * note("D1") * x) * 0.5
         + lp(saw(note("D2"), DUR, 0.002) + saw(note("A2"), DUR, -0.002), 380) * 0.25)
drone *= (0.88 + 0.12 * np.sin(2 * np.pi * 0.15 * x))
place(drone * np.clip(x / 2.6, 0, 1) ** 1.5, 0.0, 0.32)

# ---------- «Воздух» ----------
x = tt(REVEAL + 0.05)
swell = (x / (REVEAL + 0.05)) ** 3
place(lp(bp(rng.standard_normal(len(x)), 400, 3000), 1800) * swell, 0.0, 0.08, pan=-0.4)
place(lp(bp(rng.standard_normal(len(x)), 400, 3000), 1800) * swell, 0.0, 0.08, pan=0.4)

# ---------- Дробь литавр: частые мягкие удары сливаются в гул, нарастает к удару ----------
roll_start = REVEAL - 1.8
x = tt(1.8)
roll = np.zeros(len(x))
k = 0.0
while k < 1.8:
    i = int(k * SR)
    seg = tt(0.25)
    f = note("D2") * (1 + 0.01 * rng.standard_normal())
    hitw = (np.sin(2 * np.pi * f * seg) * 0.7 + lp(rng.standard_normal(len(seg)), 300) * 0.5) * np.exp(-seg * 18)
    n = min(len(hitw), len(roll) - i)
    roll[i:i + n] += hitw[:n] * (0.6 + 0.4 * rng.random())
    k += 1 / 17 + 0.006 * rng.standard_normal()      # ~17 ударов в секунду, неровно — слышится как тремоло
roll *= (x / 1.8) ** 2.2
place(roll, roll_start, 0.35, pan=0.15)

# ---------- 3.2 с: удар ----------
x = tt(4.5)
boom = np.sin(2 * np.pi * np.cumsum(36 + 24 * np.exp(-x * 5)) / SR) * np.exp(-x * 1.0)
thump = lp(rng.standard_normal(len(x)), 200) * np.exp(-x * 8) * 0.9
place(boom + thump, REVEAL, 0.8)
place(lp(hp(rng.standard_normal(len(x)), 150), 1200) * np.exp(-x * 3.5) * 0.3, REVEAL, 0.3)


# ---------- Аккорды: струнные + медь ----------
def strings(notes, d, attack=0.8, cutoff=1500):
    x = tt(d)
    s = np.zeros(len(x))
    for k, n in enumerate(notes):
        for j, det in enumerate((-0.004, 0.0, 0.004)):
            s += saw(note(n), d, det, vib=0.0025, vib_rate=4.6 + 0.3 * j, phase=k * 0.7 + j)
    s = lp(s, cutoff, 4) / (len(notes) * 3)
    return s * np.minimum(1, x / attack) ** 2


def brass(notes, d, attack=0.25):
    # медь: фильтр раскрывается на атаке — характерное «вау»
    x = tt(d)
    s = sum(saw(note(n), d, det) for n in notes for det in (-0.002, 0.002)) / (len(notes) * 2)
    cut = 500 + 2600 * (1 - np.exp(-x / attack)) * np.exp(-x * 0.5)
    return sweep_lp(s, cut) * np.minimum(1, x / 0.06)


def sweep_lp(x, fc, blk=128):
    y = np.zeros_like(x); zi = np.zeros((1, 2))
    for i in range(0, len(x), blk):
        sos = signal.butter(2, float(fc[i]), "low", fs=SR, output="sos")
        y[i:i + blk], zi = signal.sosfilt(sos, x[i:i + blk], zi=zi)
    return y


# Dsus2 на «1», затем ре мажор (add9) на «СТУДИЯ»
d1 = WORD0 - REVEAL + 0.6
sus = ["D2", "A2", "D3", "E3", "A3", "D4"]
maj = ["D2", "A2", "D3", "F#3", "A3", "E4"]
s1 = strings(sus, d1)
s1 *= np.concatenate([np.ones(len(s1) - int(0.6 * SR)), np.linspace(1, 0, int(0.6 * SR))])
place(s1, REVEAL, 0.8, pan=-0.3)
place(s1, REVEAL + 200 / SR, 0.8, pan=0.3)
b1 = brass(["D3", "A3", "E4"], d1) * np.exp(-tt(d1) * 0.6)
b1 *= np.concatenate([np.ones(len(b1) - int(0.6 * SR)), np.linspace(1, 0, int(0.6 * SR))])
place(b1, REVEAL, 0.22)

d2 = DUR - WORD0
s2 = strings(maj, d2, attack=0.6) * np.exp(-tt(d2) * 0.18)
place(s2, WORD0, 0.85, pan=-0.3)
place(s2, WORD0 + 200 / SR, 0.85, pan=0.3)
b2 = brass(["D3", "F#3", "A3", "D4"], d2, attack=0.35) * np.exp(-tt(d2) * 0.45)
place(b2, WORD0, 0.24)

# ---------- 5.8 с: тихий высокий звон на блике ----------
x = tt(3.0)
for f, g, pan in ((note("A5"), 0.05, -0.2), (note("D6"), 0.04, 0.2)):
    bell = (np.sin(2 * np.pi * f * x) + 0.3 * np.sin(2 * np.pi * f * 2.76 * x) * np.exp(-x * 3)) * np.exp(-x * 1.6)
    place(bell * np.minimum(1, x / 0.01), SHINE + (0.12 if pan > 0 else 0), g, pan)

# ---------- 0.9–3.2 с: восходящий перелив — вышка растёт ----------
arp = ["D4", "A4", "D5", "E5", "F#5", "A5", "D6", "E6", "A6"]
for k, n in enumerate(arp):
    at = 0.9 + k * (2.2 / len(arp))
    x = tt(1.6)
    f = note(n)
    cel = (np.sin(2 * np.pi * f * x) + 0.35 * np.sin(2 * np.pi * f * 4.0 * x) * np.exp(-x * 9)) * np.exp(-x * 3.2)
    place(cel * np.minimum(1, x / 0.004), at, 0.035 + 0.025 * k / len(arp), pan=-0.5 + k / len(arp))

# ---------- «сигнал эфира»: короткий чистый тон с отзвуком на каждой волне ----------
for i, p0 in enumerate((REVEAL, REVEAL + 0.45, REVEAL + 0.9, 6.4)):
    x = tt(1.2)
    f = note("A5") if i < 3 else note("D6")
    ping = np.sin(2 * np.pi * f * x) * np.exp(-x * 7) * np.minimum(1, x / 0.003)
    g = (0.07, 0.05, 0.035, 0.035)[i]
    place(ping, p0, g, pan=(-0.25, 0.25, 0.0, 0.0)[i])
    place(ping, p0 + 0.18, g * 0.35, pan=(0.35, -0.35, 0.2, -0.2)[i])   # отзвук

# ---------- Реверб, большой зал (3 с) ----------
ir_t = tt(3.0)
irL = lp(rng.standard_normal(len(ir_t)), 5000) * np.exp(-ir_t * 2.3)
irR = lp(rng.standard_normal(len(ir_t)), 5000) * np.exp(-ir_t * 2.3)
for ir in (irL, irR):
    ir[: int(0.02 * SR)] = 0                                 # предзадержка 20 мс
wetL = signal.fftconvolve(L, irL)[:N] / np.sqrt(np.sum(irL ** 2)) * 0.30
wetR = signal.fftconvolve(R, irR)[:N] / np.sqrt(np.sum(irR ** 2)) * 0.30
L, R = L + wetL, R + wetR

fade = np.clip((DUR - t) / 0.8, 0, 1) ** 2 * np.clip(t / 0.3, 0, 1)
L, R = hp(L * fade, 25), hp(R * fade, 25)
peak = max(np.abs(L).max(), np.abs(R).max())
L, R = np.tanh(L / peak * 1.1) / np.tanh(1.1) * 0.89, np.tanh(R / peak * 1.1) / np.tanh(1.1) * 0.89

out = Path(__file__).with_name("zvuk.wav")
pcm = (np.stack([L, R], 1) * (2 ** 23 - 1)).astype("<i4").tobytes()
b24 = b"".join(pcm[i:i + 3] for i in range(0, len(pcm), 4))
with wave.open(str(out), "wb") as w:
    w.setnchannels(2); w.setsampwidth(3); w.setframerate(SR); w.writeframes(b24)
print("ok:", out)
