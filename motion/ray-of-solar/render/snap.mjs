// usage: node snap.mjs <outDir> page?query=name [more...]   e.g. "shader.html?s=chrome&shot=0=chrome_0"
import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const { chromium } = createRequire(import.meta.url)('playwright');
const root = path.dirname(fileURLToPath(import.meta.url));
const [outDir, ...jobs] = process.argv.slice(2);
fs.mkdirSync(outDir, { recursive: true });
const types = { '.html': 'text/html', '.js': 'text/javascript', '.frag': 'text/plain', '.glsl': 'text/plain', '.css': 'text/css', '.png': 'image/png', '.jpg': 'image/jpeg' };
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--disable-gpu-watchdog'] });
for (const job of jobs) {
  const i = job.lastIndexOf('='); const url = job.slice(0, i), name = job.slice(i + 1);
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  page.on('pageerror', e => console.error('[pageerror]', e.message));
  await page.route('http://f5.local/**', async route => {
    const file = path.join(root, decodeURIComponent(new URL(route.request().url()).pathname));
    if (!file.startsWith(root) || !fs.existsSync(file)) return route.fulfill({ status: 404, body: 'nf' });
    route.fulfill({ status: 200, contentType: types[path.extname(file)] || 'application/octet-stream', body: fs.readFileSync(file) });
  });
  const t0 = Date.now();
  await page.goto('http://f5.local/' + url);
  await page.waitForFunction(() => window.done === true, null, { timeout: 0, polling: 500 });
  const err = await page.evaluate(() => window.err);
  if (err) { console.error(name, 'ERROR', err); await page.close(); continue; }
  await page.evaluate(() => document.fonts && document.fonts.ready);
  await page.screenshot({ path: path.join(outDir, name + '.png') });
  console.log(name, ((Date.now() - t0) / 1000).toFixed(1) + 's');
  await page.close();
}
await browser.close();
