// usage: node animrender.mjs <outDir> <fps> [t1,t2,...]   (no list → full 15 s)
import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const { chromium } = createRequire(import.meta.url)('playwright');
const root = path.dirname(fileURLToPath(import.meta.url));
const [outDir, fpsArg, list] = process.argv.slice(2);
const fps = Number(fpsArg || 24);
fs.mkdirSync(outDir, { recursive: true });
const times = list ? list.split(',').map(Number) : Array.from({ length: Math.round(15 * fps) }, (_, i) => i / fps);
const types = { '.html': 'text/html', '.frag': 'text/plain', '.glsl': 'text/plain', '.png': 'image/png', '.jpg': 'image/jpeg' };
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
page.on('pageerror', e => console.error('[pageerror]', e.message));
await page.route('http://f5.local/**', async route => {
  const file = path.join(root, decodeURIComponent(new URL(route.request().url()).pathname));
  if (!file.startsWith(root) || !fs.existsSync(file)) return route.fulfill({ status: 404, body: 'nf' });
  route.fulfill({ status: 200, contentType: types[path.extname(file)] || 'application/octet-stream', body: fs.readFileSync(file) });
});
await page.goto('http://f5.local/anim.html');
await page.waitForFunction(() => window.ready === true, null, { timeout: 120000 });
const err = await page.evaluate(() => window.err);
if (err) { console.error('ERROR', err); process.exit(1); }
const t0 = Date.now();
for (let i = 0; i < times.length; i++) {
  await page.evaluate(t => window.renderAt(t), times[i]);
  const name = list ? `t_${times[i].toFixed(2)}.jpg` : `f_${String(i).padStart(5, '0')}.jpg`;
  await page.locator('#c').screenshot({ path: path.join(outDir, name), type: 'jpeg', quality: 94 });
  if (i % 48 === 0) console.log(`frame ${i + 1}/${times.length}  ${((Date.now() - t0) / 1000).toFixed(1)}s`);
}
await browser.close();
