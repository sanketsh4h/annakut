# Annakut 3D darshan: splat prototype

A phone-friendly web page that shows a Gaussian splat scan with tappable,
bilingual (English / Gujarati) hotspots. It is a proof that the website side of
the plan works; the scene in it is a stand-in, not the Annakut.

- **Scene:** "Knock Community Hall" by scbenoit, CC BY 4.0
  (<https://superspl.at/scene/0ff2e6dc>), taken from the PlayCanvas engine
  examples. 1.9 million splats.
- **Hotspot text and photos:** copied from `../Annakut Project/modal-data.json`.
  Their positions are placeholders pinned to features of the sample building.
- **Viewer:** PlayCanvas [SuperSplat Viewer](https://github.com/playcanvas/supersplat-viewer)
  1.43.1 on engine 2.24.0, both MIT.

## Run it

```bash
npm install
node scripts/serve.mjs
```

The server prints two addresses: `http://localhost:4173` for this computer and
a `Same Wi-Fi` address to open on a phone connected to the same network.

Over plain `http://` on Wi-Fi a phone uses the WebGL 2 renderer, because
browsers only allow WebGPU on `https://` pages. Once the site is hosted over
HTTPS, phones that support WebGPU switch to it automatically.

The small readout at the bottom left shows which renderer is in use, the
quality level the viewer chose for the device, the frame rate while the scene
is moving, and how long the first view took. Tap it to step through quality
levels.

### Test switches

Add these to the address, for example `http://localhost:4173/?webgl&stats`.

| Switch | Effect |
| --- | --- |
| `?webgl` | Force the WebGL 2 renderer |
| `?budget=1` | Cap the scene at this many million splats |
| `?stats` | Show the engine's performance graphs |
| `?lang=gu` | Start in Gujarati |
| `?place` | Hotspot placement mode (below) |
| `?cam=px,py,pz,tx,ty,tz,fov` | Try a starting camera position and target |
| `?config=test-scan` | Load `site/test-scan.json` instead of `hotspots.json` (another scene) |

## Layout

```
site/                 everything that gets deployed (plain static files)
  index.html          page shell and import map
  app.js              viewer setup, hotspots, info sheet, language toggle
  styles.css
  hotspots.json       scene file, starting view, hotspot positions and text
  images/             hotspot photos (1024 px JPEGs)
  scene/              the streamed scene: lod-meta.json plus chunk folders
  test-scan.json      scene description for the pipeline test scan
  scene-test/         the pipeline test scan
  vendor/             viewer and engine files copied from node_modules
scripts/
  serve.mjs           local static server
  vendor.mjs          refreshes site/vendor after a package upgrade
  build-scene.sh      turns one trained splat into site/scene
scan-pipeline/        reference copy of the gpu machine's scan scripts
```

`site/` has no build step. Any static host (Vercel, Netlify, GitHub Pages) can
serve the folder as it is.

## Swapping in the real scan

Shoot the photos by `CAPTURE-CHECKLIST.md` first.

1. Train the splat on the gpu machine and copy the `.ply` here (see
   `~/sshah_workspace/projects/pipeline/README.md` on that machine).
2. Clean it up in the SuperSplat editor: remove floaters, crop the background.
3. Convert it to the streamed format. A fresh scan comes out tilted, so pass
   the `rotate` angles that the pipeline's `scene_frame.py` prints:

   ```bash
   ROTATE=179.4,-36.2,170.8 sh scripts/build-scene.sh path/to/annakut.ply
   ```

   This writes `site/scene/` with four detail levels (100%, 50%, 25%, 10%).
   The viewer shows the 10% level first and refines within a splat budget it
   picks for the device. Leave `ROTATE` out if the splat was already levelled
   in the editor.

4. Re-place the hotspots (next section) and update `initialCamera` and
   `credit` in `site/hotspots.json`.

## Placing hotspots

Open the page with `?place`. Move the camera to the view a visitor should get
for a hotspot, then tap the exact spot in the scene. Each tap adds a line with
the 3D `position` and the `camera` viewpoint; paste those two fields into the
matching entry in `site/hotspots.json`. "Record current view" gives an
`initialCamera` for the starting view.

Note that a tap on the scene also re-centres the camera on that point. That is
the viewer's normal behaviour, and it applies to visitors too.

## The pipeline test scan

`http://localhost:4173/?config=test-scan` shows a scan made end to end with our
own pipeline on 2026-11-11: 128 sample photos (South Building, from the COLMAP
project) -> COLMAP poses -> gsplat training on the TITAN V (2,000,000 splats)
-> `build-scene.sh` -> `site/scene-test/` (68 MB). It was not cleaned in the
SuperSplat editor, so it has haze in the sky and loose splats away from where
the photos were taken. The licence of the sample photos was not checked; keep this
scene for testing and do not publish it.

`scan-pipeline/` is a reference copy of the scripts and notes that live on the
gpu machine in `~/sshah_workspace/projects/pipeline/`. Its README has the
steps, timings, and the pose problem the test caught.

Since 2026-11-12 this copy is ahead of the gpu machine's: it adds power logging
(`powerlog.sh`, called by both scripts). The machine was off at the time, so
copy it over before the next run, from `scan-pipeline/`:

```bash
scp 01-poses.sh 02-train.sh powerlog.sh README.md gpu:sshah_workspace/projects/pipeline/
```

A scene description can set `"fitPortrait": false` to stop the page stepping
the camera back on upright phones. `test-scan.json` does, because a raw scan
only looks right from near where the photos were taken.

## What was checked, and what was not

Checked in a desktop browser, including at phone size (375 x 812):

- The scene streams and renders with both WebGPU and WebGL 2.
- All 10 hotspots track their points; tapping one flies the camera there and
  opens the sheet; previous / next, close and reset view work.
- The language toggle switches titles, body text and interface labels.
- Portrait and landscape layouts.

Not checked:

- Numbers from a real phone. The page was opened on one phone over Wi-Fi and
  worked, but frame rate, memory and load time were not recorded, and only
  that one device was tried.
- Hosting over HTTPS, and loading over mobile data.
- The Gujarati interface labels in `app.js` (`STRINGS.gu`) were written for
  this prototype and need a native reader's review.

Known gaps:

- Data use: this sample is 52 MB on disk, and a phone-sized session downloaded
  about 36 MB of it. The first view needs only the 3.2 MB lowest level.
- Hotspot markers stay visible when the point is behind another object.
- The starting view is fitted to the screen shape once, at load. Rotating the
  phone afterwards keeps the current camera.
- The camera can orbit anywhere, including behind the scene. The old site
  limited the orbit to the front.
- The camera can zoom straight through surfaces; the viewer has no collision.
