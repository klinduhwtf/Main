// Рендер заставки покадрово через Chromium → ffmpeg.
// Запуск: node render.js [mp4|prores|dnxhd|png|all] [fps]
// Результат — в папке out/ рядом со скриптом.
const { chromium } = require("playwright");
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");

const mode = process.argv[2] || "mp4";
const FPS = Number(process.argv[3] || 25);
const OUT = path.join(__dirname, "out");
fs.mkdirSync(OUT, { recursive: true });

// Эфирные параметры: 1920x1080, Rec.709, ограниченный диапазон (16–235)
const COLOR = ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv"];
const VF = "scale=out_color_matrix=bt709:out_range=tv";

const targets = {
  mp4: ["-vf", VF + ",format=yuv420p", "-c:v", "libx264", "-preset", "slow", "-crf", "19",
        "-profile:v", "high", "-movflags", "+faststart", ...COLOR, "1_studiya_zastavka.mp4"],
  prores: ["-vf", VF + ",format=yuv422p10le", "-c:v", "prores_ks", "-profile:v", "3",
           "-vendor", "apl0", ...COLOR, "1_studiya_zastavka_prores422hq.mov"],
  dnxhd: ["-vf", VF + ",format=yuv422p10le", "-c:v", "dnxhd", "-profile:v", "dnxhr_hqx",
          ...COLOR, "1_studiya_zastavka_dnxhr_hqx.mov"],
};

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  await page.goto("file://" + path.join(__dirname, "zastavka.html"));
  await page.waitForFunction(() => window.READY === true);
  const dur = await page.evaluate(() => window.DURATION);
  const frames = Math.round(dur * FPS);

  const wanted = mode === "all" ? Object.keys(targets) : mode === "png" ? [] : [mode];
  const procs = wanted.map(k => {
    const args = ["-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", String(FPS), "-c:v", "png", "-i", "-",
      ...targets[k].slice(0, -1), path.join(OUT, targets[k].at(-1))];
    const p = spawn("ffmpeg", args, { stdio: ["pipe", "inherit", "inherit"] });
    p.done = new Promise((res, rej) => p.on("close", c => c === 0 ? res() : rej(new Error(k + " ffmpeg " + c))));
    return p;
  });
  const pngDir = path.join(OUT, "png");
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
  console.log(`\nГотово: ${frames} кадров, ${FPS} fps → ${OUT}`);
})();
