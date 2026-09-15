import { chromium } from '@playwright/test';
import { writeFile, mkdir } from 'node:fs/promises';
import path from 'node:path';

const BASE = 'http://127.0.0.1:44180';
const TASK = 'a41a59ed-29e1-4801-b68b-dfea395eae30';
const ORIGIN_ID = TASK;
const LAYOUT = `${BASE}/api/v2/tasks/${TASK}/layouts/knowledge-live`;
const OUT = process.argv[2] ?? 'work/vnext/p15l-browser';
await mkdir(OUT, { recursive: true });

const report = { steps: [], console: [], pageErrors: [], requestFailures: [], timing: {} };
const record = (name, value) => { report.steps.push({ name, value }); console.log(name, JSON.stringify(value)); };
const clock = () => new Date().toISOString();

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
const page = await context.newPage();
page.on('console', (msg) => { if (msg.type() === 'error' || msg.type() === 'warning') report.console.push({ at: clock(), type: msg.type(), text: msg.text() }); });
page.on('pageerror', (error) => report.pageErrors.push({ at: clock(), text: String(error) }));
page.on('requestfailed', (request) => report.requestFailures.push({ at: clock(), url: request.url(), failure: request.failure()?.errorText ?? null }));

const readServer = (target = page) => target.evaluate(async (url) => {
  const started = Date.now();
  const response = await fetch(url, { headers: { Accept: 'application/json' }, cache: 'no-store' });
  const body = await response.json();
  return { ms: Date.now() - started, status: response.status, body };
}, LAYOUT);

const revision = async (target = page) => (await readServer(target)).body.layout_revision;

async function stableRevision(target = page, attempts = 8, gap = 1200) {
  let previous = null;
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    const current = await revision(target);
    if (current === previous) return current;
    previous = current;
    await target.waitForTimeout(gap);
  }
  return previous;
}

async function waitForRevisionAbove(baseline, timeout = 20000) {
  const started = Date.now();
  const samples = [];
  while (Date.now() - started < timeout) {
    const observed = await readServer(page);
    samples.push({ at: clock(), ms: observed.ms, revision: observed.body.layout_revision });
    if (Number(observed.body.layout_revision) > Number(baseline)) {
      return { elapsed: Date.now() - started, samples, layout: observed };
    }
    await page.waitForTimeout(400);
  }
  return { elapsed: Date.now() - started, samples, layout: null };
}

async function hitPoint(locator) {
  const id = await locator.getAttribute('data-id');
  for (let attempt = 0; attempt < 2; attempt += 1) {
    const canvas = await page.locator('.react-flow').boundingBox();
    const box = await locator.boundingBox();
    for (const fy of [0.08, 0.2, 0.35, 0.5, 0.65, 0.8, 0.92]) {
      for (const fx of [0.05, 0.2, 0.35, 0.5, 0.65, 0.8, 0.95]) {
        const x = box.x + box.width * fx;
        const y = box.y + box.height * fy;
        if (x < canvas.x + 2 || y < canvas.y + 2 || x > canvas.x + canvas.width - 2 || y > canvas.y + canvas.height - 2) continue;
        const hit = await page.evaluate(([px, py]) => document.elementFromPoint(px, py)?.closest('.react-flow__node')?.getAttribute('data-id') ?? null, [x, y]);
        if (hit === id) return { x, y, id };
      }
    }
    await page.locator('.react-flow__controls-fitview').click();
    await page.waitForTimeout(1200);
  }
  return null;
}

async function dragNode(locator, dx, dy) {
  const point = await hitPoint(locator);
  if (!point) throw new Error('cannot reach node inside the visible canvas');
  await page.mouse.move(point.x, point.y);
  await page.mouse.down();
  for (let step = 1; step <= 16; step += 1) {
    await page.mouse.move(point.x + (dx * step) / 16, point.y + (dy * step) / 16, { steps: 1 });
    await page.waitForTimeout(20);
  }
  await page.mouse.up();
  await page.waitForTimeout(400);
  return point;
}

const canvasRelativeBox = async (locator) => {
  const canvas = await page.locator('.react-flow').boundingBox();
  const box = await locator.boundingBox();
  return { x: Math.round(box.x - canvas.x), y: Math.round(box.y - canvas.y), width: Math.round(box.width), height: Math.round(box.height) };
};
const transform = () => page.evaluate(() => getComputedStyle(document.querySelector('.react-flow__viewport')).transform);

await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' });
await page.getByRole('button', { name: '建立会话' }).waitFor({ timeout: 15000 });
await page.getByRole('button', { name: '建立会话' }).click();
await page.getByRole('region', { name: '任务拓扑图' }).waitFor({ timeout: 30000 });
await page.waitForTimeout(1500);
record('session-established', true);

await page.locator('.react-flow__controls-fitview').click();
const baselineRevision = await stableRevision();
const baseline = await readServer(page);
record('phase1-baseline', { revision: baselineRevision, layout: baseline.body });

// Phase 1: a second tab advances the shared layout; the first tab must not overwrite it.
const rival = await context.newPage();
await rival.goto(BASE + '/', { waitUntil: 'domcontentloaded' });
await rival.getByRole('region', { name: '任务拓扑图' }).waitFor({ timeout: 30000 });
await rival.waitForTimeout(1500);
const rivalWrite = await rival.evaluate(async ({ url, expected }) => {
  const body = {
    schema_version: 'wuji.api.v2', selection_mode: 'follow_latest',
    entries: [{ anchor: { entity_type: 'origin', id: window.__WUJI_CONFIG__?.taskId ?? '', revision: null }, x: 77.5, y: -12.25, pinned: true }],
    viewport: { x: -10.0, y: 20.0, zoom: 0.9 },
  };
  const response = await fetch(url, { method: 'PUT', headers: { 'Content-Type': 'application/json', 'If-Match': expected }, body: JSON.stringify(body) });
  return { status: response.status, body: await response.json() };
}, { url: LAYOUT, expected: baselineRevision });
record('phase1-second-tab-put', rivalWrite);
const rivalServer = (await readServer(rival)).body;
record('phase1-second-tab-server', rivalServer);
await rival.close();

const intentNode = page.locator('.react-flow__node[data-id^="intent:"]').first();
await intentNode.waitFor({ timeout: 15000 });
await dragNode(intentNode, 150, 70);
const conflictAlert = page.locator('[role="alert"]').filter({ hasText: '服务器布局已更新' }).first();
let conflictVisible = false;
try { await conflictAlert.waitFor({ state: 'visible', timeout: 20000 }); conflictVisible = true; } catch { conflictVisible = false; }
record('phase1-conflict-alert-visible', conflictVisible);
await page.screenshot({ path: path.join(OUT, 'browser-conflict-not-overwritten.png') });
const afterConflict = (await readServer(page)).body;
record('phase1-server-after-conflict', afterConflict);
record('phase1-conflict-did-not-overwrite', {
  revision: afterConflict.layout_revision === rivalServer.layout_revision,
  entries: JSON.stringify(afterConflict.entries) === JSON.stringify(rivalServer.entries),
  viewport: JSON.stringify(afterConflict.viewport) === JSON.stringify(rivalServer.viewport),
});
if (conflictVisible) await conflictAlert.locator('button').first().click().catch(() => {});
await page.waitForTimeout(600);

// Phase 2: real drag plus viewport zoom must persist and survive a refresh.
await page.locator('.react-flow__controls-fitview').click();
await page.waitForTimeout(1200);
const freshRevision = await stableRevision();
const freshBaseline = (await readServer(page)).body;
record('phase2-baseline', { revision: freshRevision, layout: freshBaseline });

const startPoint = await dragNode(intentNode, 150, 70);
record('phase2-drag-start-point', startPoint);
const paneBox = await page.locator('.react-flow__pane').boundingBox();
await page.mouse.move(paneBox.x + paneBox.width / 2, paneBox.y + paneBox.height / 2);
await page.mouse.wheel(0, -220);
await page.waitForTimeout(800);

const saved = await waitForRevisionAbove(freshRevision, 20000);
report.timing.phase2_save = saved.elapsed;
record('phase2-save-elapsed-ms', saved.elapsed);
record('phase2-server-after-save', saved.layout?.body ?? null);
record('phase2-poll-samples', saved.samples);
if (!saved.layout) throw new Error('layout save did not reach the server within 20s');

const intentEntry = saved.layout.body.entries.find((entry) => entry.anchor.entity_type === 'intent');
record('phase2-intent-entry', intentEntry ?? null);
const nodeBeforeReload = await canvasRelativeBox(intentNode);
const transformBeforeReload = await transform();
record('phase2-node-before-reload', nodeBeforeReload);
record('phase2-viewport-before-reload', transformBeforeReload);
await page.screenshot({ path: path.join(OUT, 'browser-layout-saved.png') });

await page.reload({ waitUntil: 'domcontentloaded' });
await page.getByRole('region', { name: '任务拓扑图' }).waitFor({ timeout: 30000 });
await page.waitForTimeout(2000);
const reloadedNode = page.locator('.react-flow__node[data-id^="intent:"]').first();
await reloadedNode.waitFor({ timeout: 15000 });
const nodeAfterReload = await canvasRelativeBox(reloadedNode);
const transformAfterReload = await transform();
const serverAfterReload = (await readServer(page)).body;
record('phase2-node-after-reload', nodeAfterReload);
record('phase2-viewport-after-reload', transformAfterReload);
record('phase2-server-after-reload', serverAfterReload);
record('phase2-persisted-across-reload', {
  delta_x: Math.abs(nodeAfterReload.x - nodeBeforeReload.x),
  delta_y: Math.abs(nodeAfterReload.y - nodeBeforeReload.y),
  viewport_equal: transformAfterReload === transformBeforeReload,
  entry_matches_dom: intentEntry
    ? Math.abs(intentEntry.x - serverAfterReload.entries.find((entry) => entry.anchor.entity_type === 'intent').x) < 0.001
    : false,
});
await page.screenshot({ path: path.join(OUT, 'browser-layout-after-reload.png') });
await page.screenshot({ path: path.join(OUT, 'browser-layout-full-after-reload.png'), fullPage: true });

// Phase 3: an old revision from the browser is rejected and cannot overwrite.
const currentRevision = serverAfterReload.layout_revision;
const stale = await page.evaluate(async ({ url, expected }) => {
  const body = {
    schema_version: 'wuji.api.v2', selection_mode: 'follow_latest',
    entries: [], viewport: { x: 0, y: 0, zoom: 0.82 },
  };
  const response = await fetch(url, { method: 'PUT', headers: { 'Content-Type': 'application/json', 'If-Match': expected }, body: JSON.stringify(body) });
  return { status: response.status, body: await response.json() };
}, { url: LAYOUT, expected: String(Number(currentRevision) - 1) });
record('phase3-stale-put', stale);
const finalServer = (await readServer(page)).body;
record('phase3-server-after-stale', finalServer);
record('phase3-stale-did-not-overwrite', {
  revision: finalServer.layout_revision === serverAfterReload.layout_revision,
  entries: JSON.stringify(finalServer.entries) === JSON.stringify(serverAfterReload.entries),
  viewport: JSON.stringify(finalServer.viewport) === JSON.stringify(serverAfterReload.viewport),
});
await page.screenshot({ path: path.join(OUT, 'browser-layout-final.png') });

report.consoleErrors = report.console.filter((entry) => entry.type === 'error');
await browser.close();
await writeFile(path.join(OUT, 'browser-report.json'), JSON.stringify(report, null, 2));
console.log('console errors:', report.consoleErrors.length, JSON.stringify(report.consoleErrors));
console.log('page errors:', report.pageErrors.length, JSON.stringify(report.pageErrors));
console.log('failed requests:', report.requestFailures.length, JSON.stringify(report.requestFailures));
