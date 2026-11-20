// Annakut 3D darshan: a streamed Gaussian splat with bilingual hotspots.
//
// The scene is drawn by PlayCanvas's SuperSplat Viewer running headless
// (`ui: false`): it owns the canvas, camera controls and streaming. Everything
// you see on top (hotspot buttons, the info sheet, the language toggle) is
// plain HTML in this file, driven through the viewer's documented handle.
//
// Useful URL switches while testing:
//   ?webgl      force the WebGL 2 renderer (default is WebGPU where available)
//   ?budget=1   cap the splat budget, in millions
//   ?stats      show the engine's performance graphs
//   ?lang=gu    start in Gujarati
//   ?place      hotspot placement mode: tap the scene to get coordinates
//   ?cam=px,py,pz,tx,ty,tz[,fov]   try a starting camera position and target
//   ?config=name   load site/name.json instead of the default scene, for
//                  example ?config=hotspots for the sample scene

import { createViewer } from '@playcanvas/supersplat-viewer/viewer';
import { defaultSettings } from '@playcanvas/supersplat-viewer/settings';
import { Mat4, Picker, Vec3 } from 'playcanvas';

// The scene the page opens with: site/<name>.json. Scene descriptions and
// their folders are versioned (last-year-v0, last-year-v1, ...), so putting a
// better model live is a change to this one line.
const DEFAULT_CONFIG = 'last-year-v0';

const params = new URLSearchParams(location.search);
const $ = (id) => document.getElementById(id);

const STRINGS = {
    en: {
        title: 'Annakut Darshan',
        reset: 'Reset view',
        loading: 'Loading 3D scene…',
        hint: 'Drag to look around · pinch to zoom · tap a glowing point',
        hintPlain: 'Drag to look around · pinch to zoom',
        prev: 'Previous',
        next: 'Next',
        close: 'Close',
        quality: 'quality',
        idle: 'idle',
        failed: 'This device or browser could not start the 3D viewer.'
    },
    gu: {
        title: 'અન્નકૂટ દર્શન',
        reset: 'મૂળ દૃશ્ય',
        loading: '3D દૃશ્ય લોડ થઈ રહ્યું છે…',
        hint: 'ફેરવવા માટે ખેંચો · ઝૂમ માટે પિંચ કરો · ઝબકતા બિંદુ પર ટૅપ કરો',
        hintPlain: 'ફેરવવા માટે ખેંચો · ઝૂમ માટે પિંચ કરો',
        prev: 'પાછળ',
        next: 'આગળ',
        close: 'બંધ કરો',
        quality: 'quality',
        idle: 'idle',
        failed: 'આ ઉપકરણ અથવા બ્રાઉઝર પર 3D વ્યૂઅર શરૂ થઈ શક્યું નથી.'
    }
};

// localStorage can throw in private windows; the page must work without it.
const store = {
    get(key) {
        try {
            return localStorage.getItem(key);
        } catch {
            return null;
        }
    },
    set(key, value) {
        try {
            localStorage.setItem(key, value);
        } catch {
            /* not saved; fine */
        }
    }
};

let lang = params.get('lang') || store.get('annakut-lang') || 'en';
if (!STRINGS[lang]) lang = 'en';

const t = (key) => STRINGS[lang][key];
// Picks the current language from a { en, gu } pair, falling back to English.
const tr = (pair) => (pair && (pair[lang] ?? pair.en)) || '';
const round3 = (n) => Math.round(n * 1000) / 1000;

// The viewer applies a camera's field of view to the longer side of the
// screen. A starting view authored on a wide screen would therefore crop the
// sides of the scene on a phone held upright, so step the camera back until
// about the same width is in view (capped, so the scene doesn't get tiny).
//
// With `square` (a scene description's "fitSquare": true) the starting view
// is taken to be framed for a square screen, and the camera steps back on
// wide screens as well as tall ones, until the shorter side shows what the
// square did. Use it when the subject is about as tall as it is wide.
function fitToScreen(pose, square) {
    const aspect = window.innerWidth / window.innerHeight;
    if (aspect >= 1 && !square) return pose;
    const back = square ? Math.min(Math.max(aspect, 1 / aspect), 2.2) : Math.min(1 / aspect, 2);
    const position = pose.position.map((p, i) => round3(pose.target[i] + (p - pose.target[i]) * back));
    return { ...pose, position };
}

function showError(error) {
    console.error(error);
    $('loading').classList.add('done');
    const box = $('error');
    box.textContent = `${t('failed')} (${error?.message || error})`;
    box.hidden = false;
}

async function main() {
    // ?config=name swaps in another scene description from the same folder.
    const wanted = params.get('config') || '';
    const configName = /^[a-z0-9-]+$/.test(wanted) ? wanted : DEFAULT_CONFIG;
    const config = await (await fetch(`${configName}.json`, { cache: 'no-cache' })).json();
    const hotspots = config.hotspots || [];

    // ----- viewer ----------------------------------------------------------

    const settings = defaultSettings();
    if (config.background) settings.background.color = config.background;
    if (config.initialCamera) settings.cameras = [{ initial: config.initialCamera }];
    // ?cam=px,py,pz,tx,ty,tz[,fov] tries a starting view without editing the scene description.
    const cam = (params.get('cam') || '').split(',').map(Number);
    if (cam.length >= 6 && cam.every(Number.isFinite)) {
        settings.cameras = [{ initial: { position: cam.slice(0, 3), target: cam.slice(3, 6), fov: cam[6] || 60 } }];
    }
    // A raw scan is only clean near where the photos were taken, so a scene
    // can opt out of the step-back with "fitPortrait": false.
    if (config.fitPortrait !== false) {
        settings.cameras = settings.cameras.map((c) => ({ initial: fitToScreen(c.initial, config.fitSquare === true) }));
    }
    // Each hotspot is also a viewer annotation, so the viewer can fly the
    // camera to its authored viewpoint. We draw the hotspots ourselves.
    settings.annotations = hotspots.map((h) => ({
        position: h.position,
        title: h.title.en.slice(0, 60),
        text: '',
        extras: { id: h.id },
        camera: { initial: h.camera }
    }));

    const options = {
        container: $('viewer'),
        settings,
        contentUrl: config.scene,
        ui: false,
        // Without this the viewer starts by slowly circling the scene on its own.
        noanim: true
    };
    if (params.has('webgl')) options.renderer = 'webgl';
    if (params.has('budget')) options.budget = Number(params.get('budget'));
    if (params.has('stats')) options.ministats = true;

    const viewer = await createViewer(options);
    const app = viewer.app;

    // ----- loading ---------------------------------------------------------

    const setProgress = (percent) => {
        $('bar-fill').style.width = `${Math.max(4, Math.min(100, percent))}%`;
    };
    setProgress(viewer.state.progress || 0);
    viewer.events.on('progress:changed', setProgress);

    const whenLoaded = new Promise((resolve) => {
        if (viewer.state.loaded) resolve();
        else viewer.events.once('loaded:changed', resolve);
    });

    // ----- hotspot markers -------------------------------------------------

    const layer = $('markers');
    const markers = hotspots.map((h, index) => {
        const el = document.createElement('button');
        el.type = 'button';
        el.className = 'marker';
        el.innerHTML = '<span class="dot"></span><span class="label"></span>';
        el.addEventListener('click', () => openHotspot(index));
        layer.appendChild(el);
        return {
            el,
            label: el.querySelector('.label'),
            position: new Vec3(h.position[0], h.position[1], h.position[2]),
            visible: false,
            x: NaN,
            y: NaN
        };
    });

    let camera = null;
    const findCamera = () => app.root.findComponents('camera').find((c) => c.enabled && c.entity.enabled) || null;
    const getCamera = () => {
        if (!camera || !camera.entity || !camera.enabled) camera = findCamera();
        return camera;
    };

    // Re-project every hotspot into screen space each frame. The viewer only
    // renders when something changes, but this loop is cheap enough to run
    // always and keeps the buttons glued to the scene while the camera moves.
    const worldToCamera = new Mat4();
    const inCamera = new Vec3();
    const onScreen = new Vec3();
    const placeMarkers = () => {
        const cam = getCamera();
        if (cam) {
            worldToCamera.copy(cam.entity.getWorldTransform()).invert();
            for (const m of markers) {
                // The camera looks down its own -Z axis.
                worldToCamera.transformPoint(m.position, inCamera);
                const inFront = inCamera.z < -cam.nearClip;
                if (inFront) {
                    cam.worldToScreen(m.position, onScreen);
                    const x = Math.round(onScreen.x * 2) / 2;
                    const y = Math.round(onScreen.y * 2) / 2;
                    if (x !== m.x || y !== m.y) {
                        m.x = x;
                        m.y = y;
                        m.el.style.transform = `translate3d(${x}px, ${y}px, 0)`;
                    }
                }
                if (inFront !== m.visible) {
                    m.visible = inFront;
                    m.el.classList.toggle('show', inFront);
                }
            }
        }
        requestAnimationFrame(placeMarkers);
    };

    // ----- info sheet ------------------------------------------------------

    const sheet = $('sheet');
    let current = null;

    const renderSheet = () => {
        if (current === null) return;
        const h = hotspots[current];
        const image = $('sheet-image');
        if (image.getAttribute('src') !== h.image) image.src = h.image;
        image.alt = tr(h.title);
        $('sheet-title').textContent = tr(h.title);
        const subtitle = (h.subtitle && h.subtitle[lang]) || '';
        $('sheet-subtitle').textContent = subtitle;
        $('sheet-subtitle').hidden = !subtitle;
        $('sheet-body').textContent = tr(h.body);
        $('counter').textContent = `${current + 1} / ${hotspots.length}`;
    };

    function openHotspot(index) {
        current = (index + hotspots.length) % hotspots.length;
        viewer.selectAnnotation(current);
        markers.forEach((m, i) => m.el.classList.toggle('active', i === current));
        renderSheet();
        sheet.querySelector('.sheet-scroll').scrollTop = 0;
        sheet.classList.add('open');
        sheet.setAttribute('aria-hidden', 'false');
        document.body.classList.add('sheet-open');
        hideHint();
    }

    function closeSheet() {
        if (current === null) return;
        current = null;
        viewer.selectAnnotation(null);
        markers.forEach((m) => m.el.classList.remove('active'));
        sheet.classList.remove('open');
        sheet.setAttribute('aria-hidden', 'true');
        document.body.classList.remove('sheet-open');
    }

    $('sheet-close').addEventListener('click', closeSheet);
    $('prev').addEventListener('click', () => openHotspot(current - 1));
    $('next').addEventListener('click', () => openHotspot(current + 1));
    window.addEventListener('keydown', (event) => {
        if (current === null) return;
        if (event.key === 'Escape') closeSheet();
        if (event.key === 'ArrowLeft') openHotspot(current - 1);
        if (event.key === 'ArrowRight') openHotspot(current + 1);
    });

    $('reset').addEventListener('click', () => {
        closeSheet();
        if (viewer.state.loaded) viewer.resetCamera();
    });

    // ----- hint ------------------------------------------------------------

    const hint = $('hint');
    let hintTimer = 0;
    function hideHint() {
        clearTimeout(hintTimer);
        hint.classList.remove('show');
    }
    $('viewer').addEventListener('pointerdown', hideHint, { passive: true });

    // ----- language --------------------------------------------------------

    const applyLanguage = () => {
        document.documentElement.lang = lang;
        document.body.dataset.lang = lang;
        $('site-title').textContent = t('title');
        $('reset').textContent = t('reset');
        $('loading-label').textContent = t('loading');
        $('prev-label').textContent = t('prev');
        $('next-label').textContent = t('next');
        $('sheet-close').setAttribute('aria-label', t('close'));
        // A scene without hotspots has no glowing points to mention.
        hint.textContent = t(hotspots.length ? 'hint' : 'hintPlain');
        markers.forEach((m, i) => {
            m.label.textContent = tr(hotspots[i].title);
            m.el.setAttribute('aria-label', tr(hotspots[i].title));
        });
        renderSheet();
    };

    $('lang').addEventListener('click', () => {
        lang = lang === 'en' ? 'gu' : 'en';
        store.set('annakut-lang', lang);
        applyLanguage();
    });

    // ----- test readout (renderer, quality, frame rate) --------------------

    const debug = $('debug');
    const frameTimes = [];
    app.on('framerender', () => {
        const now = performance.now();
        frameTimes.push(now);
        while (frameTimes.length && frameTimes[0] < now - 1000) frameTimes.shift();
    });
    const renderer = app.graphicsDevice.isWebGPU ? 'WebGPU' : 'WebGL 2';
    let firstFrame = '';
    const updateDebug = () => {
        const now = performance.now();
        const fps = frameTimes.filter((time) => time > now - 1000).length;
        const speed = fps > 1 ? `${fps} fps` : t('idle');
        debug.textContent = `${renderer} · ${viewer.state.quality} ${t('quality')} · ${speed}${firstFrame}`;
    };
    setInterval(updateDebug, 500);
    debug.addEventListener('click', () => {
        const levels = viewer.state.qualityAvailable || [];
        if (!levels.length) return;
        viewer.state.quality = levels[(levels.indexOf(viewer.state.quality) + 1) % levels.length];
        updateDebug();
    });

    if (config.credit) {
        $('credit').textContent = config.credit.text;
        // A credit without a "url" is plain text, not a link.
        if (config.credit.url) $('credit').href = config.credit.url;
    }

    // ----- start -----------------------------------------------------------

    applyLanguage();
    updateDebug();

    await whenLoaded;
    // Time from opening the page to the first complete picture of the scene.
    firstFrame = ` · first view ${(performance.now() / 1000).toFixed(1)}s`;
    // Start still, in the authored view, ready for the visitor to drag.
    if (viewer.state.cameraMode !== 'orbit') viewer.state.cameraMode = 'orbit';
    $('loading').classList.add('done');
    document.body.classList.add('ready');
    requestAnimationFrame(placeMarkers);

    hint.hidden = false;
    requestAnimationFrame(() => hint.classList.add('show'));
    hintTimer = setTimeout(hideHint, 7000);

    if (params.has('place')) enablePlaceMode(viewer, getCamera);
}

// ---------------------------------------------------------------------------
// Placement mode (?place): tap a spot in the scene to get its 3D coordinates
// and the current camera viewpoint, ready to paste into hotspots.json.
// ---------------------------------------------------------------------------
function enablePlaceMode(viewer, getCamera) {
    const app = viewer.app;
    const canvas = app.graphicsDevice.canvas;
    const picker = new Picker(app, 1, 1, true);

    const pickAt = async (x, y) => {
        const cam = getCamera();
        if (!cam) return null;
        picker.resize(canvas.clientWidth, canvas.clientHeight);
        picker.prepare(cam, app.scene);
        const point = await picker.getWorldPointAsync(x, y);
        return point ? [round3(point.x), round3(point.y), round3(point.z)] : null;
    };

    const cameraPosition = () => {
        const p = getCamera().entity.getPosition();
        return [round3(p.x), round3(p.y), round3(p.z)];
    };

    // The current view as a camera pose: where the camera is, and the point
    // of the scene at the centre of the screen.
    const currentView = async () => {
        const cam = getCamera();
        let target = await pickAt(canvas.clientWidth / 2, canvas.clientHeight / 2);
        if (!target) {
            const p = cam.entity.getPosition();
            const f = cam.entity.forward;
            target = [round3(p.x + f.x * 3), round3(p.y + f.y * 3), round3(p.z + f.z * 3)];
        }
        return { position: cameraPosition(), target, fov: round3(cam.fov) };
    };

    const panel = document.createElement('div');
    panel.className = 'place-panel';
    panel.innerHTML = `
        <strong>Placement mode</strong>
        <span>Tap the scene to record a hotspot from the current viewpoint.</span>
        <textarea readonly rows="7"></textarea>
        <div class="place-actions">
            <button type="button" data-action="view">Record current view</button>
            <button type="button" data-action="copy">Copy</button>
            <button type="button" data-action="clear">Clear</button>
        </div>`;
    document.body.appendChild(panel);
    const output = panel.querySelector('textarea');
    const records = [];
    const refresh = () => {
        output.value = records.map((r) => JSON.stringify(r)).join(',\n');
        output.scrollTop = output.scrollHeight;
    };

    panel.addEventListener('click', async (event) => {
        const action = event.target.dataset?.action;
        if (action === 'view') {
            records.push({ initialCamera: await currentView() });
            refresh();
        } else if (action === 'copy') {
            try {
                await navigator.clipboard.writeText(output.value);
            } catch {
                output.select();
            }
        } else if (action === 'clear') {
            records.length = 0;
            refresh();
        }
    });

    // A tap is a short press that barely moves; anything else is a camera drag.
    let down = null;
    const container = viewer.app.graphicsDevice.canvas.parentElement;
    container.addEventListener('pointerdown', (event) => {
        down = { x: event.clientX, y: event.clientY, time: performance.now() };
    }, { passive: true });
    container.addEventListener('pointerup', async (event) => {
        if (!down) return;
        const moved = Math.hypot(event.clientX - down.x, event.clientY - down.y);
        const quick = performance.now() - down.time < 400;
        down = null;
        if (moved > 6 || !quick) return;
        const rect = canvas.getBoundingClientRect();
        const position = await pickAt(event.clientX - rect.left, event.clientY - rect.top);
        if (!position) return;
        const cam = getCamera();
        records.push({ position, camera: { position: cameraPosition(), target: position, fov: round3(cam.fov) } });
        refresh();
    }, { passive: true });

    // Handy from the browser console while authoring.
    window.annakut = { viewer, pickAt, currentView, records };
}

main().catch(showError);
