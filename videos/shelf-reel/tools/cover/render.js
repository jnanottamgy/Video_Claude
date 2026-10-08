// The Instagram cover: tools/cover/cover.html (the hook frame + a S.H.E.L.F lockup) screenshotted at 1080x1920.
//   node tools/cover/render.js renders/deliver_v2/SHELF_cover.png     (run from videos/shelf-reel)
const http = require('http'), fs = require('fs'), path = require('path');
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const root = path.resolve(__dirname, '..', '..');
const types = { '.html': 'text/html', '.jpg': 'image/jpeg', '.png': 'image/png', '.woff2': 'font/woff2' };
const server = http.createServer((req, res) => {
  const file = path.join(root, decodeURIComponent(req.url.split('?')[0]));
  if (!file.startsWith(root) || !fs.existsSync(file)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'Content-Type': types[path.extname(file)] || 'application/octet-stream' });
  fs.createReadStream(file).pipe(res);
}).listen(0, '127.0.0.1', async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await p.goto(`http://127.0.0.1:${server.address().port}/tools/cover/cover.html`);
  await p.evaluate(async () => { await document.fonts.ready; });
  const bad = await p.evaluate(() => [...document.fonts].filter((f) => f.status !== 'loaded').map((f) => f.family));
  if (bad.length) throw new Error('fonts not loaded: ' + bad.join(', '));
  await p.screenshot({ path: process.argv[2], type: 'png' });
  await b.close();
  server.close();
});
