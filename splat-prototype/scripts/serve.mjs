#!/usr/bin/env node
// Tiny static server for testing the site on this computer and on phones on
// the same Wi-Fi.  No dependencies.
//
//   node scripts/serve.mjs [port]      (default 4173)
//
// Requests from other devices are printed as "[visit] ..." lines, so it is
// easy to see whether a phone got through. This computer's own are not.

import { createReadStream, statSync } from 'node:fs';
import { createServer } from 'node:http';
import { networkInterfaces } from 'node:os';
import { dirname, extname, join, normalize, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../site');
const port = Number(process.env.PORT || process.argv[2] || 4173);

const types = {
    '.html': 'text/html; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.js': 'text/javascript; charset=utf-8',
    '.mjs': 'text/javascript; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.wasm': 'application/wasm',
    '.webp': 'image/webp',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon',
    '.md': 'text/plain; charset=utf-8'
};

const send = (res, status, body = '') => {
    res.writeHead(status, { 'content-type': 'text/plain; charset=utf-8' });
    res.end(body);
};

const ownAddresses = () => Object.values(networkInterfaces()).flat().map((net) => net?.address);
const devices = new Set();
const logVisit = (req, res) => {
    const from = (req.socket.remoteAddress || '').replace(/^::ffff:/, '');
    if (from === '127.0.0.1' || from === '::1' || ownAddresses().includes(from)) return;
    if (!devices.has(from)) {
        devices.add(from);
        console.log(`[visit] new device ${from}: ${req.headers['user-agent'] || 'unknown browser'}`);
    }
    res.on('close', () => {
        const time = new Date().toTimeString().slice(0, 8);
        const result = res.writableFinished ? res.statusCode : 'cut off';
        console.log(`[visit] ${time} ${from} ${result} ${req.url}`);
    });
};

createServer((req, res) => {
    logVisit(req, res);
    if (req.method !== 'GET' && req.method !== 'HEAD') return send(res, 405, 'Method not allowed');

    let path;
    try {
        path = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
    } catch {
        return send(res, 400, 'Bad request');
    }

    // Never serve anything outside the site folder.
    let file = normalize(join(root, path));
    if (file !== root && !file.startsWith(root + sep)) return send(res, 403, 'Forbidden');

    let stat;
    try {
        stat = statSync(file);
        if (stat.isDirectory()) {
            file = join(file, 'index.html');
            stat = statSync(file);
        }
    } catch {
        return send(res, 404, 'Not found');
    }

    // Always revalidate, so edits show up on reload but unchanged scene chunks
    // come back as a cheap 304 instead of a re-download.
    const modified = new Date(Math.floor(stat.mtimeMs / 1000) * 1000);
    const since = Date.parse(req.headers['if-modified-since'] || '');
    const headers = {
        'cache-control': 'no-cache',
        'last-modified': modified.toUTCString()
    };
    if (!Number.isNaN(since) && since >= modified.getTime()) {
        res.writeHead(304, headers);
        return res.end();
    }

    res.writeHead(200, {
        ...headers,
        'content-type': types[extname(file).toLowerCase()] || 'application/octet-stream',
        'content-length': stat.size
    });
    if (req.method === 'HEAD') return res.end();
    createReadStream(file).pipe(res);
}).listen(port, '0.0.0.0', () => {
    console.log(`Serving ${root}`);
    console.log(`  This computer:  http://localhost:${port}`);
    for (const list of Object.values(networkInterfaces())) {
        for (const net of list || []) {
            if (net.family === 'IPv4' && !net.internal) {
                console.log(`  Same Wi-Fi:     http://${net.address}:${port}`);
            }
        }
    }
});
