#!/usr/bin/env node
// Phone vs laptop check for a scene before it goes live (PIPELINE.md, 6e).
//
//   node scripts/device-check.mjs [page address] [--out folder]
//
//   node scripts/device-check.mjs                                   local server, default scene
//   node scripts/device-check.mjs "http://localhost:4173/?config=last-year-v3"
//   node scripts/device-check.mjs https://sanketsh4h.github.io/annakut/
//
// Opens the page in headless Chromium as five devices, each in a fresh
// profile (nothing saved from an earlier visit), and checks each one:
//
//   laptop          1440 x 900 window at 2x, Chromium     expects WebGPU
//   android-chrome  Pixel 7                               expects WebGPU
//   iphone-safari   iPhone 15                             expects WebGL 2
//   iphone-chrome   iPhone 15 with Chrome's user agent    expects WebGL 2 (Safari's engine)
//   mac-safari      1440 x 900 with Safari's user agent   expects WebGL 2
//
// Each must report the expected renderer, "default" quality and a
// full-resolution canvas, load every scene file, and raise no page errors.
// Then it photographs the same views on every device (the start view, and
// the walk's first and last stops if the scene has a walk) and writes
// index.html in the output folder with them side by side. It exits with 1 if
// any check fails.
//
// What it cannot see: Safari's own WebGPU and WebGL. The two iPhone rows and
// the Mac Safari row only prove that the page picks WebGL 2 for them; their
// pictures are drawn by Chromium. A real iPhone is still needed (6e, step 3).
//
// Needs Playwright and its Chromium. If Playwright is not installed in this
// folder, set PLAYWRIGHT_PATH to a node_modules folder that has it.

import { mkdirSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';

const args = process.argv.slice(2);
const outAt = args.indexOf('--out');
const outDir = resolve(outAt >= 0 ? args[outAt + 1] : join(tmpdir(), 'annakut-device-check'));
const address = args.find((a, i) => !a.startsWith('--') && i !== outAt + 1) || 'http://localhost:4173/';

function loadPlaywright() {
    const places = [import.meta.url, process.env.PLAYWRIGHT_PATH && join(resolve(process.env.PLAYWRIGHT_PATH), 'x.js')];
    for (const place of places.filter(Boolean)) {
        try {
            return createRequire(place)('playwright');
        } catch {
            /* try the next place */
        }
    }
    console.error('Playwright not found. Install it here (npm install --no-save playwright && npx playwright install chromium)');
    console.error('or set PLAYWRIGHT_PATH to a node_modules folder that has it.');
    process.exit(2);
}
const { chromium, devices } = loadPlaywright();

const iphone = devices['iPhone 15'];
const laptopWindow = { viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 };
const PROFILES = [
    { name: 'laptop', device: laptopWindow, phone: false, expect: 'WebGPU' },
    { name: 'android-chrome', device: devices['Pixel 7'], phone: true, expect: 'WebGPU' },
    { name: 'iphone-safari', device: iphone, phone: true, expect: 'WebGL 2' },
    {
        name: 'iphone-chrome',
        device: { ...iphone, userAgent: iphone.userAgent.replace(/Version\/[\d.]+/, 'CriOS/159.0.0.0') },
        phone: true,
        expect: 'WebGL 2'
    },
    {
        name: 'mac-safari',
        device: {
            ...laptopWindow,
            userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.1 Safari/605.1.15'
        },
        phone: false,
        expect: 'WebGL 2'
    }
];

const readout = (page) => page.textContent('#debug');
const settle = (ms) => new Promise((r) => setTimeout(r, ms));

// Waits until no scene file has arrived for `quiet` ms, so the finer detail
// levels are in before a picture is taken (at most `limit` ms).
async function untilSceneQuiet(state, quiet = 2000, limit = 20000) {
    const start = Date.now();
    while (Date.now() - start < limit) {
        if (Date.now() - state.lastScene >= quiet) return;
        await settle(250);
    }
}

async function checkProfile(browser, profile) {
    const context = await browser.newContext(profile.device);
    const page = await context.newPage();
    const state = { lastScene: Date.now(), sceneFiles: 0, badFiles: [], errors: [] };
    page.on('pageerror', (e) => state.errors.push(String(e).slice(0, 200)));
    page.on('response', (r) => {
        const path = new URL(r.url()).pathname;
        if (!/\/scene[^/]*\//.test(path)) return;
        state.lastScene = Date.now();
        state.sceneFiles++;
        if (r.status() >= 400) state.badFiles.push(`${r.status()} ${path}`);
    });
    page.on('requestfailed', (r) => {
        if (/\/scene[^/]*\//.test(new URL(r.url()).pathname)) state.badFiles.push(`failed ${r.url()}`);
    });

    await page.goto(address);
    await page.waitForFunction(() => document.getElementById('debug').textContent.includes('first view'), null, { timeout: 120000 });
    await untilSceneQuiet(state);

    const text = await readout(page);
    const [renderer, quality] = text.split(' · ');
    const canvas = await page.evaluate((phone) => {
        const c = document.querySelector('#viewer canvas');
        // the viewer's full resolution: the display's pixel ratio, capped so the
        // screen's shorter side is at most 1080 pixels on a phone, 2160 elsewhere
        const full = Math.min(devicePixelRatio, (phone ? 1080 : 2160) / Math.min(screen.width, screen.height));
        return { width: c.width, height: c.height, expected: Math.floor(c.clientWidth * full) };
    }, profile.phone);

    const checks = [
        [`renderer ${renderer}`, renderer === profile.expect, `expected ${profile.expect}`],
        [`quality ${quality}`, quality === 'default quality', 'expected default quality'],
        [`canvas ${canvas.width}x${canvas.height}`, canvas.width >= canvas.expected * 0.98, `expected ${canvas.expected} wide`],
        [`${state.sceneFiles} scene files`, state.sceneFiles > 0 && !state.badFiles.length, state.badFiles.join(', ')],
        ['no page errors', !state.errors.length, state.errors.join(' | ')]
    ];

    const shots = [];
    const shoot = async (view) => {
        const file = `${profile.name}-${view}.png`;
        await page.screenshot({ path: join(outDir, file) });
        shots.push({ view, file });
    };
    await shoot('start');
    if (await page.isVisible('#walk-start')) {
        await page.click('#walk-start');
        await settle(2500);
        await untilSceneQuiet(state);
        await shoot('walk-first');
        while (await page.isEnabled('#walk-next')) {
            await page.click('#walk-next');
            await settle(2200);
        }
        await untilSceneQuiet(state);
        await shoot('walk-last');
    }
    await context.close();
    return { profile, text, checks, shots };
}

mkdirSync(outDir, { recursive: true });
const browser = await chromium.launch({
    headless: true,
    args: ['--enable-unsafe-webgpu', '--enable-gpu', '--use-angle=metal', '--ignore-gpu-blocklist']
});
const results = [];
for (const profile of PROFILES) {
    const result = await checkProfile(browser, profile);
    results.push(result);
    const failed = result.checks.filter(([, ok]) => !ok);
    console.log(`${failed.length ? 'FAIL' : 'ok  '} ${profile.name.padEnd(15)} ${result.checks.map(([label]) => label).join(' · ')}`);
    for (const [label, , why] of failed) console.log(`       ${label}: ${why}`);
}
await browser.close();

// Side-by-side page: one row per view, one column per device.
const views = [...new Set(results.flatMap((r) => r.shots.map((s) => s.view)))];
const cell = (r, view) => {
    const shot = r.shots.find((s) => s.view === view);
    return shot ? `<td><img src="${shot.file}" loading="lazy"></td>` : '<td>-</td>';
};
const html = `<!doctype html><meta charset="utf-8"><title>Device check</title>
<style>body{font:14px system-ui;margin:16px;background:#111;color:#eee}table{border-collapse:collapse}
td,th{padding:6px;vertical-align:top;text-align:left}img{height:420px;display:block}.bad{color:#f66}</style>
<h1>Device check</h1><p>${address}<br>${new Date().toString()}</p>
<table><tr><th></th>${results.map((r) => `<th>${r.profile.name}<br><small>${r.text}</small><br>${r.checks
    .map(([label, ok, why]) => `<small class="${ok ? '' : 'bad'}">${ok ? '' : 'FAIL '}${label}${ok ? '' : `: ${why}`}</small>`)
    .join('<br>')}</th>`).join('')}</tr>
${views.map((view) => `<tr><th>${view}</th>${results.map((r) => cell(r, view)).join('')}</tr>`).join('\n')}</table>`;
writeFileSync(join(outDir, 'index.html'), html);
console.log(`Pictures side by side: ${join(outDir, 'index.html')}`);
process.exit(results.some((r) => r.checks.some(([, ok]) => !ok)) ? 1 : 0);
