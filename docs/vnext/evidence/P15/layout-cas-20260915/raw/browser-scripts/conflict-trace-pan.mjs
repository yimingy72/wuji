import { chromium } from '@playwright/test';
import { writeFile } from 'node:fs/promises';
const BASE = 'http://127.0.0.1:44180';
const TASK = 'a41a59ed-29e1-4801-b68b-dfea395eae30';
const LAYOUT = `${BASE}/api/v2/tasks/${TASK}/layouts/knowledge-live`;
const events = [];
const now = () => new Date().toISOString();
const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
const page = await context.newPage();
page.on('request', (r) => {
  if (r.url().includes('/layouts/') && r.method() === 'PUT') {
    events.push({ at: now(), kind: 'request', ifMatch: r.headers()['if-match'], body: r.postData() });
  }
});
page.on('response', async (r) => {
  if (r.url().includes('/layouts/')) {
    let body = null;
    try { body = await r.text(); } catch {}
    events.push({ at: now(), kind: 'response', method: r.request().method(), status: r.status(), body: body?.slice(0, 160) });
  }
});
await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' });
await page.getByRole('button', { name: '建立会话' }).click();
await page.getByRole('region', { name: '任务拓扑图' }).waitFor({ timeout: 30000 });
await page.waitForTimeout(1500);
await page.locator('.react-flow__controls-fitview').click();
await page.waitForTimeout(2500);
const read = () => page.evaluate(async (url) => (await (await fetch(url, { headers: { Accept: 'application/json' }, cache: 'no-store' })).json()), LAYOUT);
const baseline = await read();
events.push({ at: now(), kind: 'baseline', revision: baseline.layout_revision });

const rival = await context.newPage();
await rival.goto(BASE + '/', { waitUntil: 'domcontentloaded' });
await rival.getByRole('region', { name: '任务拓扑图' }).waitFor({ timeout: 30000 });
await rival.waitForTimeout(1500);
const rivalResult = await rival.evaluate(async ({ url, expected, taskId }) => {
  const body = { schema_version: 'wuji.api.v2', selection_mode: 'follow_latest',
    entries: [{ anchor: { entity_type: 'origin', id: taskId, revision: null }, x: 77.5, y: -12.25, pinned: true }],
    viewport: { x: -10, y: 20, zoom: 0.9 } };
  const r = await fetch(url, { method: 'PUT', headers: { 'Content-Type': 'application/json', 'If-Match': expected }, body: JSON.stringify(body) });
  return { status: r.status, body: await r.json() };
}, { url: LAYOUT, expected: baseline.layout_revision, taskId: TASK });
events.push({ at: now(), kind: 'rival-write', value: rivalResult });
await rival.close();

const node = page.locator('.react-flow__node[data-id^="intent:"]').first();
const canvas = await page.locator('.react-flow').boundingBox();
const box = await node.boundingBox();
let point = null;
for (const fy of [0.1, 0.3, 0.5, 0.7]) {
  for (const fx of [0.2, 0.5, 0.8]) {
    const x = box.x + box.width * fx;
    const y = box.y + box.height * fy;
    if (x < canvas.x + 2 || y < canvas.y + 2 || x > canvas.x + canvas.width - 2 || y > canvas.y + canvas.height - 2) continue;
    const hit = await page.evaluate(([px, py]) => document.elementFromPoint(px, py)?.closest('.react-flow__node')?.getAttribute('data-id') ?? null, [x, y]);
    if (hit && hit.startsWith('intent:')) { point = { x, y }; break; }
  }
  if (point) break;
}
events.push({ at: now(), kind: 'drag-point', point });
await page.mouse.move(point.x, point.y);
await page.mouse.down();
// Drag far past the canvas edge so React Flow auto-pans while the save is in flight.
for (let step = 1; step <= 40; step += 1) {
  await page.mouse.move(point.x + step * 30, point.y + step * 8, { steps: 1 });
  await page.waitForTimeout(25);
}
await page.mouse.up();
for (let i = 0; i < 12; i += 1) {
  await page.waitForTimeout(1000);
  const current = await read();
  events.push({ at: now(), kind: `poll-${i + 1}`, revision: current.layout_revision, entries: current.entries.length, viewport: current.viewport });
}
const alerts = await page.locator('[role="alert"]').allInnerTexts().catch((error) => [`locator-error ${error}`]);
events.push({ at: now(), kind: 'alerts-visible', alerts });
await page.screenshot({ path: process.argv[2] ?? 'work/vnext/p15l-browser/conflict-pan.png' });
await browser.close();
await writeFile(process.argv[3] ?? 'work/vnext/p15l-browser/conflict-trace-pan.json', JSON.stringify(events, null, 2));
console.log(JSON.stringify(events.slice(0, 6), null, 2));
