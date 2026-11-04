// Раскадровка: node kadry.js [файл.png] — сетка ключевых кадров
const { chromium } = require("playwright");
const path = require("path");
const TIMES = [0.9, 1.6, 2.1, 2.7, 3.4, 3.9, 4.6, 6.5, 8.1, 8.4];
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
  p.on("pageerror", e => console.error(e.message));
  await p.goto("file://" + path.join(__dirname, "zastavka.html"));
  await p.waitForFunction(() => window.READY);
  const shots = [];
  for (const t of TIMES) { await p.evaluate(t => render(t), t); shots.push((await p.locator("#stage").screenshot()).toString("base64")); }
  await p.setContent(`<body style="margin:0;background:#111;display:grid;grid-template-columns:repeat(2,960px);gap:6px;font:20px sans-serif;color:#fff">` +
    shots.map((s, i) => `<div style="position:relative"><img src="data:image/png;base64,${s}" width=960><span style="position:absolute;left:10px;top:6px">${TIMES[i]} с</span></div>`).join("") + `</body>`);
  await p.setViewportSize({ width: 1926, height: 100 });
  await p.screenshot({ path: process.argv[2] || path.join(__dirname, "kadry.png"), fullPage: true });
  await b.close();
})();
