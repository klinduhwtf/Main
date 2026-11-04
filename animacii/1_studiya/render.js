// Рендер заставки покадрово через Chromium → ffmpeg.
// Запуск: node render.js [v1|v2|v3] [mp4|prores|dnxhd|png|all] [fps]
//   node render.js v2 all       — вариант 2 со звуком во всех форматах
//   node render.js mp4          — вариант 1 (для совместимости со старым вызовом)
// Результат — в папке out/ рядом со скриптом.
const { chromium } = require("playwright");
const { spawn, spawnSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const VARIANTS = {
  v1: { html: "zastavka.html", name: "1_studiya_zastavka" },
  v2: { html: "zastavka_v2.html", name: "1_studiya_v2", audio: "zvuk_v2.wav" },
  v3: { html: "zastavka_v3.html", name: "1_studiya_v3", audio: "zvuk_v3.wav" },
};
let args = process.argv.slice(2);
const variant = VARIANTS[args[0]] ? args.shift() : "v1";
const V = VARIANTS[variant];
const mode = args[0] || "mp4";
const FPS = Number(args[1] || 25);
const OUT = path.join(__dirname, "out");
fs.mkdirSync(OUT, { recursive: true });

// Эфирные параметры: 1920x1080, Rec.709, ограниченный диапазон (16–235)
const COLOR = ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv"];
const VF = "scale=out_color_matrix=bt709:out_range=tv";

// Громкость: эфир — EBU R128 (−23 LUFS), MP4 для просмотра — −16 LUFS
const audioPath = V.audio && path.join(__dirname, V.audio);
function measuredLUFS() {
  const r = spawnSync("ffmpeg",
    ["-hide_banner", "-nostats", "-i", audioPath, "-af", "ebur128", "-f", "null", "-"], { encoding: "utf8" });
  const m = [...r.stderr.matchAll(/I:\s+(-?[\d.]+) LUFS/g)].pop();
  return Number(m[1]);
}
const audio = target => {
  if (!audioPath) return { inputs: [] };
  const gain = (target - measuredLUFS()).toFixed(2);
  return { inputs: ["-i", audioPath], gain, target };
};

const targets = {
  mp4: { file: `${V.name}.mp4`, lufs: -16,
    v: ["-vf", VF + ",format=yuv420p", "-c:v", "libx264", "-preset", "slow", "-crf", "19",
        "-profile:v", "high", "-movflags", "+faststart", ...COLOR],
    a: ["-c:a", "aac", "-b:a", "320k", "-ar", "48000"] },
  prores: { file: `${V.name}_prores422hq.mov`, lufs: -23,
    v: ["-vf", VF + ",format=yuv422p10le", "-c:v", "prores_ks", "-profile:v", "3", "-vendor", "apl0", ...COLOR],
    a: ["-c:a", "pcm_s24le", "-ar", "48000"] },
  dnxhd: { file: `${V.name}_dnxhr_hqx.mov`, lufs: -23,
    v: ["-vf", VF + ",format=yuv422p10le", "-c:v", "dnxhd", "-profile:v", "dnxhr_hqx", ...COLOR],
    a: ["-c:a", "pcm_s24le", "-ar", "48000"] },
};

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  page.on("pageerror", e => console.error("Ошибка на странице:", e.message));
  await page.goto("file://" + path.join(__dirname, V.html));
  await page.waitForFunction(() => window.READY === true);
  const dur = await page.evaluate(() => window.DURATION);
  const frames = Math.round(dur * FPS);

  const wanted = mode === "all" ? Object.keys(targets) : mode === "png" ? [] : [mode];
  const procs = wanted.map(k => {
    const T = targets[k];
    const A = audio(T.lufs);
    const ffArgs = ["-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", String(FPS), "-c:v", "png", "-i", "-",
      ...A.inputs, ...T.v,
      ...(audioPath ? ["-map", "0:v", "-map", "1:a", "-af", `volume=${A.gain}dB`, ...T.a, "-shortest"] : []),
      path.join(OUT, T.file)];
    const p = spawn("ffmpeg", ffArgs, { stdio: ["pipe", "inherit", "inherit"] });
    p.done = new Promise((res, rej) => p.on("close", c => c === 0 ? res() : rej(new Error(k + " ffmpeg " + c))));
    return p;
  });
  const pngDir = path.join(OUT, `${V.name}_png`);
  if (mode === "png" || mode === "all") fs.mkdirSync(pngDir, { recursive: true });

  for (let i = 0; i < frames; i++) {
    await page.evaluate(([t, fps]) => window.render(t, fps), [i / FPS, FPS]);
    const buf = await page.locator("#stage").screenshot({ type: "png" });
    if (mode === "png" || mode === "all")
      fs.writeFileSync(path.join(pngDir, `frame_${String(i).padStart(4, "0")}.png`), buf);
    for (const p of procs) if (!p.stdin.write(buf)) await new Promise(r => p.stdin.once("drain", r));
    if (i % 25 === 0) process.stdout.write(`кадр ${i}/${frames}\r`);
  }
  for (const p of procs) p.stdin.end();
  await Promise.all(procs.map(p => p.done));
  await browser.close();
  if (audioPath && (mode === "png" || mode === "all")) fs.copyFileSync(audioPath, path.join(pngDir, V.audio));
  console.log(`\nГотово: ${variant}, ${frames} кадров, ${FPS} fps → ${OUT}`);
})();
