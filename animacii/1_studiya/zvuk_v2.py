"""Синтез звуковой отбивки для заставки «1 СТУДИЯ» (вариант 2).

Всё генерируется с нуля (без сэмплов), поэтому прав на музыку не нужно.
Темп 120 BPM, тайминги совпадают с анимацией в zastavka_v2.html:
  0.0–2.0  нарастание: пульс на долях, шумовой свип, «обратная тарелка»
  2.0      удар: саб-бум + бочка + крэш + аккордовый стэб — появляется «1»
  2.75+    короткие тики на каждую букву «СТУДИЯ»
  3.5      финальный аккорд с колокольчиком, затухает к 7.0
Выход: zvuk_v2.wav (48 кГц, 24 бит, стерео) и zvuk_v2_env.js — огибающая
громкости по кадрам (по ней анимируется звуковая волна в кадре).

Запуск: python3 zvuk_v2.py [fps]
"""
import json
import sys
import wave
from pathlib import Path

import numpy as np
from scipy import signal

SR = 48000
DUR = 7.0
FPS = int(sys.argv[1]) if len(sys.argv) > 1 else 25
HIT, LETTER0, LETTER_STEP, N_LETTERS, CHORD = 2.0, 2.75, 0.125, 6, 3.5

rng = np.random.default_rng(1)
N = int(SR * DUR)
t = np.arange(N) / SR
L = np.zeros(N)
R = np.zeros(N)


def note(name):
    names = {"C": -9, "C#": -8, "D": -7, "D#": -6, "E": -5, "F": -4, "F#": -3,
             "G": -2, "G#": -1, "A": 0, "A#": 1, "B": 2}
    n, octv = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((names[n] + 12 * (octv - 4)) / 12)


def place(sig, at, gain=1.0, pan=0.0):
    """Положить моно-сигнал в микс с момента at (с), pan от -1 до 1."""
    i = int(at * SR)
    sig = sig[: max(0, N - i)]
    gl, gr = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    L[i:i + len(sig)] += sig * gain * gl * np.sqrt(2)
    R[i:i + len(sig)] += sig * gain * gr * np.sqrt(2)


def tt(d):
    return np.arange(int(d * SR)) / SR


def lp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, "low", fs=SR, output="sos"), x)


def hp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, "high", fs=SR, output="sos"), x)


def bp(x, lo, hi, order=2):
    return signal.sosfilt(signal.butter(order, [lo, hi], "band", fs=SR, output="sos"), x)


def sweep(x, fc, kind="low", width=1.0, blk=128):
    """Фильтр с плавно меняющейся частотой среза fc (массив по сэмплам).
    Состояние фильтра переносится между блоками — без щелчков."""
    y = np.zeros_like(x)
    zi = np.zeros((1, 2)) if kind == "low" else np.zeros((2, 2))
    for i in range(0, len(x), blk):
        f = float(fc[i])
        if kind == "low":
            sos = signal.butter(2, min(f, SR / 2 - 100), "low", fs=SR, output="sos")
        else:
            sos = signal.butter(2, [f * 0.7, min(f * 1.4 * width, SR / 2 - 100)], "band", fs=SR, output="sos")
        y[i:i + blk], zi = signal.sosfilt(sos, x[i:i + blk], zi=zi)
    return y


def saw(freq, d, detune=0.0):
    x = tt(d)
    ph = np.cumsum(np.full(len(x), freq * (1 + detune))) / SR if np.isscalar(freq) else np.cumsum(freq) / SR
    return 2 * (ph % 1.0) - 1


def kick(d=0.6, f0=150, f1=42, gain=1.0):
    x = tt(d)
    f = f1 + (f0 - f1) * np.exp(-x * 28)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 7)
    click = hp(rng.standard_normal(len(x)), 2000) * np.exp(-x * 300) * 0.3
    return (s + click) * gain


# ---------- 0–2 с: нарастание ----------
# Пульс на долях (тихая бочка), громче к удару
for k, at in enumerate([0.0, 0.5, 1.0, 1.5]):
    place(kick(0.45, 120, 50), at, 0.25 + 0.12 * k)

# Ускоряющаяся дробь в последнюю долю: 1/8 → 1/16 → 1/32
roll = [1.5, 1.625, 1.75, 1.8125, 1.875, 1.90625, 1.9375, 1.96875]
for k, at in enumerate(roll):
    x = tt(0.12)
    sn = bp(rng.standard_normal(len(x)), 900, 7000) * np.exp(-x * 40)
    place(sn, at, 0.08 + 0.03 * k, pan=(-0.3 if k % 2 else 0.3))

# Шумовой свип вверх с нарастанием
x = tt(HIT)
noise = rng.standard_normal(len(x))
sw = sweep(noise, 300 * (9000 / 300) ** (x / HIT), kind="band")
env = (x / HIT) ** 2.2
place(sw * env, 0.0, 0.35, pan=-0.2)
place(np.roll(sw, 300) * env, 0.0, 0.35, pan=0.2)

# Тональный подъём (пила, октава вверх), низкочастотный фильтр открывается
f = note("D2") * 2 ** (x / HIT)
rise = lp(saw(f, HIT) + saw(f * 1.005, HIT), 2500) * env
place(rise, 0.0, 0.12)

# «Обратная тарелка» в удар
x = tt(1.2)
rc = hp(rng.standard_normal(len(x)), 5000) * (x / 1.2) ** 4
place(rc, HIT - 1.2, 0.5, pan=-0.15)
place(rc[:-500], HIT - 1.2 + 500 / SR, 0.5, pan=0.15)

# ---------- 2.0 с: удар ----------
x = tt(2.5)
sub = np.sin(2 * np.pi * np.cumsum(38 + 40 * np.exp(-x * 6)) / SR) * np.exp(-x * 1.6)
place(sub, HIT, 0.9)
place(kick(0.8, 180, 45), HIT, 0.9)
crash = hp(rng.standard_normal(len(x)), 3500) * np.exp(-x * 2.2)
place(crash, HIT, 0.22, pan=-0.35)
place(hp(rng.standard_normal(len(x)), 3500) * np.exp(-x * 2.2), HIT, 0.22, pan=0.35)

# Стэб: ре минор (D2 A2 D3 F3 A3 E4), «медь» из пил
stab_notes = ["D2", "A2", "D3", "F3", "A3", "E4"]
x = tt(1.6)
stab = sum(saw(note(n), 1.6) + saw(note(n), 1.6, detune=0.004) for n in stab_notes)
stab_env = np.minimum(1, x / 0.008) * np.exp(-x * 3.2)
stab = signal.sosfilt(signal.butter(2, 2200, "low", fs=SR, output="sos"), stab) * stab_env
place(stab / len(stab_notes), HIT, 0.55)

# ---------- 2.75+ с: тики на буквы ----------
for k in range(N_LETTERS):
    x = tt(0.09)
    fq = note("A5") * 2 ** (k * 2 / 12)
    tick = (np.sin(2 * np.pi * fq * x) * 0.6 + hp(rng.standard_normal(len(x)), 6000) * 0.4) * np.exp(-x * 60)
    place(tick, LETTER0 + k * LETTER_STEP, 0.12, pan=-0.5 + k * 0.2)

# ---------- 3.5 с: финальный аккорд ----------
x = tt(DUR - CHORD)
pad_notes = ["D3", "A3", "C4", "E4", "F4"]          # Dm9 без терции внизу
pad = sum(saw(note(n), DUR - CHORD, d) for n in pad_notes for d in (-0.003, 0.0, 0.003))
cut = 600 + 2400 * np.exp(-x * 0.9)                  # фильтр медленно закрывается
pad_f = sweep(pad, cut, kind="low")
pad_env = np.minimum(1, x / 0.03) * np.exp(-x * 0.55)
place(pad_f * pad_env / 15, CHORD, 0.9)
place(sub[: len(x)] * 0.5, CHORD, 0.5)               # мягкий низ под аккорд
place(kick(0.6, 140, 45), CHORD, 0.45)

# Колокольчик: D5 → A5 → D6
for k, (n, at) in enumerate([("D5", 0.0), ("A5", 0.125), ("D6", 0.25)]):
    x = tt(2.5)
    fq = note(n)
    bell = (np.sin(2 * np.pi * fq * x) + 0.4 * np.sin(2 * np.pi * fq * 2.76 * x) * np.exp(-x * 4)) * np.exp(-x * 2.2)
    place(bell, CHORD + at, 0.10, pan=(-0.3, 0.0, 0.3)[k])

# ---------- Реверб (синтетическая импульсная характеристика 1.8 с) ----------
ir_t = tt(1.8)
irL = rng.standard_normal(len(ir_t)) * np.exp(-ir_t * 3.8)
irR = rng.standard_normal(len(ir_t)) * np.exp(-ir_t * 3.8)
irL, irR = lp(irL, 6000), lp(irR, 6000)
wetL = signal.fftconvolve(L, irL)[:N] / np.sqrt(np.sum(irL ** 2)) * 0.18
wetR = signal.fftconvolve(R, irR)[:N] / np.sqrt(np.sum(irR ** 2)) * 0.18
L, R = L + wetL, R + wetR

# Уход в тишину к концу и мягкий лимитер
fade = np.clip((DUR - t) / 0.5, 0, 1) ** 2
L, R = L * fade, R * fade
L, R = hp(L, 25), hp(R, 25)
peak = max(np.abs(L).max(), np.abs(R).max())
L, R = np.tanh(L / peak * 1.2) / np.tanh(1.2), np.tanh(R / peak * 1.2) / np.tanh(1.2)
L, R = L * 0.89, R * 0.89                            # ≈ −1 dBFS

out = Path(__file__).with_name("zvuk_v2.wav")
pcm = (np.stack([L, R], 1) * (2 ** 23 - 1)).astype(np.int32)
b = pcm.astype("<i4").tobytes()
b24 = b"".join(b[i:i + 3] for i in range(0, len(b), 4))
with wave.open(str(out), "wb") as w:
    w.setnchannels(2); w.setsampwidth(3); w.setframerate(SR); w.writeframes(b24)

# Огибающая по кадрам (RMS, нормированная 0..1) — для звуковой волны в кадре
mono = (L + R) / 2
spf = SR // FPS
envf = [float(np.sqrt(np.mean(mono[i * spf:(i + 1) * spf] ** 2))) for i in range(int(DUR * FPS))]
mx = max(envf)
envf = [round(e / mx, 4) for e in envf]
Path(__file__).with_name("zvuk_v2_env.js").write_text(
    f"window.ENV_FPS = {FPS};\nwindow.ENV = {json.dumps(envf)};\n")
print("ok:", out, f"{len(envf)} кадров огибающей")
