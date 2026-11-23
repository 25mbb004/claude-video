// usage: node render.mjs <outDir> <fps> [t1,t2,...]   (no list → full 15s)
import { createRequire } from 'node:module';
const { chromium } = createRequire(import.meta.url)('playwright');
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.dirname(fileURLToPath(import.meta.url));
const [outDir, fpsArg, list] = process.argv.slice(2);
const fps = Number(fpsArg || 24);
fs.mkdirSync(outDir, { recursive: true });
const times = list ? list.split(',').map(Number) : Array.from({ length: Math.round(15 * fps) }, (_, i) => i / fps);

const types = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript' };
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
page.on('console', m => { if (m.type() === 'error') console.error('[page]', m.text()); });
page.on('pageerror', e => console.error('[pageerror]', e.message));
await page.route('http://eclipse.local/**', async route => {
  const rel = decodeURIComponent(new URL(route.request().url()).pathname);
  const file = path.join(root, rel);
  if (!file.startsWith(root) || !fs.existsSync(file)) return route.fulfill({ status: 404, body: 'nf' });
  route.fulfill({ status: 200, contentType: types[path.extname(file)] || 'application/octet-stream', body: fs.readFileSync(file) });
});
await page.goto('http://eclipse.local/index.html');
await page.waitForFunction(() => window.ready === true, null, { timeout: 60000 });
await page.evaluate(() => document.fonts.ready);

const t0 = Date.now();
for (let i = 0; i < times.length; i++) {
  await page.evaluate(t => window.renderAt(t), times[i]);
  const name = list ? `t_${times[i].toFixed(2)}.jpg` : `f_${String(i).padStart(5, '0')}.jpg`;
  await page.screenshot({ path: path.join(outDir, name), type: 'jpeg', quality: 93 });
  if (i % 24 === 0) console.log(`frame ${i + 1}/${times.length}  ${((Date.now() - t0) / 1000).toFixed(1)}s`);
}
await browser.close();
