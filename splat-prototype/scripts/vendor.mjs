#!/usr/bin/env node
// Copies the viewer and engine files the site needs out of node_modules into
// site/vendor, so the site folder is fully self-contained and can be deployed
// as plain static files with no build step.
//
//   node scripts/vendor.mjs      (re-run after upgrading either package)

import { cpSync, mkdirSync, rmSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const nm = (p) => resolve(root, 'node_modules', p);
const out = (p) => resolve(root, 'site/vendor', p);

const files = [
    // PlayCanvas engine (the viewer's peer dependency)
    ['playcanvas/build/playcanvas.min.mjs', 'playcanvas/build/playcanvas.min.mjs'],
    ['playcanvas/scripts/esm/parsers/spz-parser.mjs', 'playcanvas/scripts/esm/parsers/spz-parser.mjs'],
    ['playcanvas/scripts/esm/xr/xr-controllers.mjs', 'playcanvas/scripts/esm/xr/xr-controllers.mjs'],
    ['playcanvas/scripts/esm/xr/xr-navigation.mjs', 'playcanvas/scripts/esm/xr/xr-navigation.mjs'],
    ['playcanvas/LICENSE', 'playcanvas/LICENSE'],

    // SuperSplat Viewer
    ['@playcanvas/supersplat-viewer/dist/viewer.js', 'supersplat-viewer/viewer.js'],
    ['@playcanvas/supersplat-viewer/dist/viewer.css', 'supersplat-viewer/viewer.css'],
    ['@playcanvas/supersplat-viewer/dist/settings.js', 'supersplat-viewer/settings.js'],
    ['@playcanvas/supersplat-viewer/dist/zstd-decoder.wasm', 'supersplat-viewer/zstd-decoder.wasm'],
    ['@playcanvas/supersplat-viewer/dist/gsaf-decoder.wasm', 'supersplat-viewer/gsaf-decoder.wasm'],
    ['@playcanvas/supersplat-viewer/LICENSE', 'supersplat-viewer/LICENSE'],
    ['@playcanvas/supersplat-viewer/THIRD_PARTY_NOTICES.md', 'supersplat-viewer/THIRD_PARTY_NOTICES.md']
];

rmSync(out(''), { recursive: true, force: true });
for (const [from, to] of files) {
    mkdirSync(dirname(out(to)), { recursive: true });
    cpSync(nm(from), out(to));
    console.log(`vendor/${to}`);
}
