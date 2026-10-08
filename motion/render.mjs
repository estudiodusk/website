// Renders dusk-intro.html frame by frame (deterministic) and encodes MP4 with ffmpeg.
// usage: node render.mjs [out.mp4] [fps] [workers]    |   node render.mjs --stills t1,t2,...
import { chromium } from '/opt/node22/lib/node_modules/playwright/index.mjs';
import { mkdirSync, rmSync } from 'fs';
import { execSync } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

const dir = path.dirname(fileURLToPath(import.meta.url));
const url = 'file://' + path.join(dir, 'dusk-intro.html');
const exe = process.env.CHROMIUM || '/opt/pw-browsers/chromium';
const launch = () => chromium.launch({ executablePath: exe, args: ['--no-sandbox', '--force-color-profile=srgb'] });

async function page(b) {
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  await p.goto(url); await p.waitForFunction(() => window.READY);
  return p;
}

if (process.argv[2] === '--stills') {
  const ts = process.argv[3].split(',').map(Number);
  const out = process.argv[4] || '/tmp/stills'; mkdirSync(out, { recursive: true });
  const b = await launch(); const p = await page(b);
  for (const t of ts) { await p.evaluate(t => window.render(t), t); await p.screenshot({ path: `${out}/t${t}.png` }); }
  await b.close(); process.exit(0);
}

const outFile = process.argv[2] || path.join(dir, 'dusk-intro.mp4');
const fps = +(process.argv[3] || 30), workers = +(process.argv[4] || 4);
const tmp = path.join(dir, '.frames'); rmSync(tmp, { recursive: true, force: true }); mkdirSync(tmp);
const total = Math.round(15.6 * fps);
const b = await launch();
await Promise.all(Array.from({ length: workers }, async (_, w) => {
  const p = await page(b);
  for (let f = w; f < total; f += workers) {
    await p.evaluate(t => window.render(t), f / fps);
    await p.screenshot({ path: `${tmp}/f${String(f).padStart(5, '0')}.jpg`, type: 'jpeg', quality: 96 });
  }
}));
await b.close();
execSync(`ffmpeg -y -loglevel error -framerate ${fps} -i ${tmp}/f%05d.jpg -c:v libx264 -preset slow -crf 16 -pix_fmt yuv420p -movflags +faststart ${outFile}`);
rmSync(tmp, { recursive: true, force: true });
console.log('ok', outFile);
