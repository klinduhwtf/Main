"""Звук для заставки «ТЕЛЕЦЕНТР» — «Два голоса». Домбра + современная подложка.

Синтез с нуля, без сэмплов: домбра — щипковая модель Карплуса — Стронга (две струны, кварта ре–соль),
удары — синусоидальный саб и шум. Тайминги совпадают с zastavka.html:
  0.2–3.3   перекличка двух фраз домбры, плавно нарастает: левый голос, ответ правого
  3.3       встреча: удар по обеим струнам + саб — вырастает узор, вспыхивает «лист»
  3.3–4.5   нарастающий бой домбры (как в күй), подложка раскрывается
  4.95      аккорд на появлении слова
  5.8–9.3   спокойный ритм домбры и подложка под живой линией
  9.3       шторка: свист и финальный удар
Выход: zvuk.wav (48 кГц, 24 бит, стерео). Запуск: python3 zvuk.py
"""
import wave
from pathlib import Path

import numpy as np
from scipy import signal

SR = 48000
DUR = 10.1
VOICE_L, VOICE_R, MEET, HORNS, WORD0, LINE0, WIPE = 0.2, 0.9, 3.3, 4.5, 4.95, 5.8, 9.3
VOLUME = 0.8          # общий уровень: на 20% тише прежнего
rng = np.random.default_rng(11)
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
    tail = min(len(sig), int(0.05 * SR))
    sig[-tail:] *= np.linspace(1, 0, tail)
    i = int(at * SR)
    if i >= N: return
    sig = sig[: N - i]
    gl, gr = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    L[i:i + len(sig)] += sig * gain * gl * np.sqrt(2)
    R[i:i + len(sig)] += sig * gain * gr * np.sqrt(2)


def pluck(freq, d=1.6, bright=0.5, decay=0.996):
    """Струна домбры: Карплус — Стронг, щипок с «щелчком» ногтя и корпусной резонанс."""
    n = int(d * SR)
    p = int(SR / freq)
    buf = rng.uniform(-1, 1, p) * 0.9
    buf = lp(buf, 1500 + 5000 * bright, 1)
    out = np.zeros(n)
    # векторно по периодам: усреднение соседних отсчётов = простой фильтр потерь
    for start in range(0, n, p):
        seg = buf[: min(p, n - start)]
        out[start:start + len(seg)] = seg
        buf = decay * 0.5 * (buf + np.roll(buf, -1))
    body = bp(out, 180, 2600) * 0.7 + out * 0.3                    # корпус
    click = hp(rng.standard_normal(int(0.004 * SR)), 2500) * 0.25  # ноготь
    body[: len(click)] += click
    return body


def strum(notes, at, gain, pan=0.0, spread=0.012, bright=0.6, up=False):
    """Удар по струнам: струны звучат с небольшим сдвигом, как при бое домбры."""
    seq = notes[::-1] if up else notes
    for k, n in enumerate(seq):
        place(pluck(note(n), 1.4, bright), at + k * spread, gain, pan + (k - 0.5) * 0.15)


# ---------- 0.15–1.8: перекличка двух голосов ----------
# левый голос — фраза вниз, правый — ответ вверх; кварта ре–соль, как строй домбры
phrase_l = [(0.00, "A3"), (0.32, "G3"), (0.60, "A3"), (0.90, "D3"), (1.30, "E3")]
phrase_r = [(0.00, "D4"), (0.26, "C4"), (0.50, "D4"), (0.76, "G3"), (1.10, "A3"), (1.50, "D4"), (1.80, "E4")]
ramp = lambda at: 0.35 + 0.65 * min(1, max(0, (at - VOICE_L) / 1.6)) ** 1.5   # первые ноты тише, голоса нарастают
for dt, n in phrase_l:
    place(pluck(note(n), 1.4, 0.45), VOICE_L + dt, 0.32 * ramp(VOICE_L + dt), pan=-0.6)
for dt, n in phrase_r:
    place(pluck(note(n), 1.4, 0.5), VOICE_R + 0.2 + dt, 0.32 * ramp(VOICE_R + 0.2 + dt), pan=0.6)

# лёгкий «воздух» нарастает к встрече
x = tt(MEET)
place(lp(bp(rng.standard_normal(len(x)), 600, 5000), 4000) * (x / MEET) ** 3, 0.0, 0.05, -0.3)
place(lp(bp(rng.standard_normal(len(x)), 600, 5000), 4000) * (x / MEET) ** 3, 0.0, 0.05, 0.3)

# ---------- 1.8: встреча ----------
x = tt(2.5)
sub = np.sin(2 * np.pi * np.cumsum(44 + 40 * np.exp(-x * 9)) / SR) * np.exp(-x * 1.6)
place(sub + lp(rng.standard_normal(len(x)), 180) * np.exp(-x * 14) * 0.8, MEET, 0.75)
strum(["D3", "G3", "D4"], MEET, 0.45, bright=0.85)
place(np.sin(2 * np.pi * note("D6") * tt(1.5)) * np.exp(-tt(1.5) * 3.5), MEET + 0.08, 0.05, 0.1)   # «лист»

# ---------- подложка: тёплый аккорд Dsus (без терции — открыто, по-степному) ----------
def pad(notes, d, attack):
    x = tt(d)
    s = np.zeros(len(x))
    for k, n in enumerate(notes):
        for det in (-0.003, 0.003):
            ph = np.cumsum(np.full(len(x), note(n) * (1 + det))) / SR + k * 0.3
            s += 2 * (ph % 1) - 1
    s = lp(s, 900, 4) / (len(notes) * 2)
    return s * np.minimum(1, x / attack) ** 2


p = pad(["D2", "A2", "D3", "G3", "A3"], DUR - MEET, 1.2)
p *= np.clip((WIPE + 0.4 - (MEET + tt(DUR - MEET))) / 0.6, 0, 1)
place(p, MEET, 0.20, -0.2)
place(p, MEET + 0.011, 0.20, 0.2)

# ---------- 1.8–3.0: бой домбры нарастает (ритм «тақ-та-та») ----------
k = 0
tb = MEET + 0.25
while tb < WORD0 - 0.05:
    up = k % 3 == 2
    g = 0.12 + 0.2 * (tb - MEET) / (WORD0 - MEET)
    strum(["D3", "G3"], tb, g, pan=0.0, spread=0.008, bright=0.7, up=up)
    tb += (0.16, 0.08, 0.08)[k % 3]
    k += 1

# ---------- 3.45: слово ----------
x = tt(2.0)
place(np.sin(2 * np.pi * np.cumsum(50 + 30 * np.exp(-x * 10)) / SR) * np.exp(-x * 2.4), WORD0, 0.5)
strum(["D3", "A3", "D4", "G4"], WORD0, 0.42, bright=0.9, spread=0.016)

# ---------- 4.3–7.8: спокойный ритм под живой линией ----------
k = 0
tb = LINE0
while tb < WIPE - 0.1:
    up = k % 3 == 2
    strum(["D3", "G3"], tb, 0.09 if not up else 0.06, spread=0.008, bright=0.5, up=up)
    tb += (0.24, 0.12, 0.12)[k % 3]
    k += 1
for dt, n in [(0.6, "A4"), (1.5, "G4"), (2.4, "D4")]:             # отголоски «голосов»
    place(pluck(note(n), 1.4, 0.4), LINE0 + dt, 0.12, pan=(-0.5 if dt < 1 else 0.5 if dt < 2 else 0))

# ---------- 7.8: шторка ----------
x = tt(0.7)
sw = bp(rng.standard_normal(len(x)), 800, 9000) * np.sin(np.pi * x / 0.7) ** 2
place(sw, WIPE - 0.05, 0.12, -0.4)
x = tt(1.0)
place(np.sin(2 * np.pi * np.cumsum(48 + 30 * np.exp(-x * 10)) / SR) * np.exp(-x * 4), WIPE + 0.55, 0.45)
strum(["D3", "G3", "D4"], WIPE + 0.55, 0.35, bright=0.8)

# ---------- небольшой зал ----------
ir_t = tt(1.6)
irL = lp(rng.standard_normal(len(ir_t)), 6000) * np.exp(-ir_t * 4.0)
irR = lp(rng.standard_normal(len(ir_t)), 6000) * np.exp(-ir_t * 4.0)
for ir in (irL, irR):
    ir[: int(0.015 * SR)] = 0
wetL = signal.fftconvolve(L, irL)[:N] / np.sqrt(np.sum(irL ** 2)) * 0.18
wetR = signal.fftconvolve(R, irR)[:N] / np.sqrt(np.sum(irR ** 2)) * 0.18
L, R = L + wetL, R + wetR

fade = np.clip((DUR - t) / 0.35, 0, 1) * np.clip(t / 0.4, 0, 1)
L, R = hp(L * fade, 28), hp(R * fade, 28)
peak = max(np.abs(L).max(), np.abs(R).max())
L, R = (np.tanh(L / peak * 1.2) / np.tanh(1.2) * 0.89 * VOLUME, np.tanh(R / peak * 1.2) / np.tanh(1.2) * 0.89 * VOLUME)

out = Path(__file__).with_name("zvuk.wav")
pcm = (np.stack([L, R], 1) * (2 ** 23 - 1)).astype("<i4").tobytes()
b24 = b"".join(pcm[i:i + 3] for i in range(0, len(pcm), 4))
with wave.open(str(out), "wb") as w:
    w.setnchannels(2); w.setsampwidth(3); w.setframerate(SR); w.writeframes(b24)
print("ok:", out)
