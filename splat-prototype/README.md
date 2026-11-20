# Annakut 3D darshan: splat prototype

A phone-friendly web page that shows a Gaussian splat scan with tappable,
bilingual (English / Gujarati) hotspots.

- **Default scene:** the 2025 Annakut, version 1 (`site/last-year-v1.json`,
  `site/scene-last-year-v1/`, 34 MB). The same 15 photos as v0, trained with
  depth from dense stereo and a monocular depth model, levelled with the
  phones' gravity sensors, and cleaned of faint and very large splats
  (865,000 splats are left). The camera is held to
  ±75 degrees to either side and 0 to 75 degrees above level
  (`viewLimits`, below). From the front it looks like the photos; towards the
  edges of that window it smears, because no photo saw the display from there.
  It has no hotspots yet.
- **Version 0** stays available at `?config=last-year-v0`
  (`site/scene-last-year-v0/`, 36 MB): the raw baseline, tilted about 13
  degrees, not cleaned, with no view limits.
- **Sample scene:** `?config=hotspots` shows "Knock Community Hall" by
  scbenoit, CC BY 4.0 (<https://superspl.at/scene/0ff2e6dc>), taken from the
  PlayCanvas engine examples. 1.9 million splats. It carries the 10 hotspots.
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
| `?config=hotspots` | Load `site/hotspots.json` (the sample scene) instead of the default scene. Any `site/<name>.json` works: `?config=test-scan`, `?config=last-year-v0` |
| `?nolimits` | Ignore the scene's `viewLimits`, for authoring hotspots and views outside the visitor's window |

## Layout

```
site/                 everything that gets deployed (plain static files)
  index.html          page shell and import map
  app.js              viewer setup, hotspots, info sheet, language toggle;
                      DEFAULT_CONFIG names the scene the page opens with
  styles.css
  last-year-v1.json   the default scene: the 2025 Annakut, version 1
  scene-last-year-v1/ its streamed scene: lod-meta.json plus chunk folders
  last-year-v0.json   version 0, with scene-last-year-v0/
  hotspots.json       the sample scene: scene file, starting view, hotspot
                      positions and text
  images/             hotspot photos (1024 px JPEGs)
  scene/              the sample's streamed scene
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

## Putting a new model live

Each model gets its own versioned pair, and old versions stay in place:
`site/last-year-v1.json` with `site/scene-last-year-v1/`, and so on.

1. Convert the splat into a new folder (step 3 below), giving the output
   folder as the second argument:

   ```bash
   ROTATE=... sh scripts/build-scene.sh path/to/model.ply site/scene-last-year-v2
   ```

   A model that needs moving as well as turning (v1 does: the ground goes to
   height 0 and the display's middle to x = 0) is levelled with
   splat-transform first, then built without `ROTATE`. For a model trained
   like v1:

   ```bash
   node_modules/.bin/splat-transform -w model.ply -r 47.1311,-43.2295,-149.6335 -t -0.75,1.6,0 level.ply
   sh scripts/build-scene.sh level.ply site/scene-last-year-v2
   ```

2. Copy the current `site/last-year-v1.json` to `site/last-year-v2.json` and
   point its `scene` at the new folder. Check the starting view at
   `?config=last-year-v2` and adjust `initialCamera` and `viewLimits` if the
   model sits differently.
3. Change `DEFAULT_CONFIG` in `site/app.js` to `'last-year-v2'`. That one line
   is what makes it the page visitors get.

Never commit a source `.ply` (`.gitignore` blocks them): they are over
GitHub's 100 MB file limit. The photos stay out of the repo too, because they
carry GPS positions.

## Making a scene from a new scan

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
   `credit` in the scene description. A `credit` without a `url` shows as
   plain text.

## Limiting the view

A scene description can hold the camera to the views the model can stand
behind. Without `viewLimits` (the sample scene, the test scan) the camera
orbits freely, as before.

From `last-year-v1.json`:

```json
"viewLimits": {
  "yaw": [-75, 75],
  "pitch": [0, 75],
  "ground": 0,
  "focusBox": { "min": [-4.0, 0.82, -3.0], "max": [4.0, 5.0, 3.0] },
  "distance": [1.5, 16]
}
```

In v1 the ground (0) is an estimate: the hall floor is not in the model, so
it was placed from the display's 14 ft height, about 0.6 m below the front
table top. The focus box stops at the table top (0.82), so in practice the
camera never goes lower than that: below it the model has nothing to show.
Setting `focusBox.min[1]` to 0 would let the camera down to the floor.

| Field | Meaning |
| --- | --- |
| `yaw` | Degrees the camera may swing round the point it orbits. 0 looks toward -Z (straight at the display from the audience side); negative is toward the visitor's left. Keep both ends between -180 and 180. |
| `pitch` | Degrees above that point's horizon: 0 is level, 90 straight down. |
| `ground` | Height (Y) of the floor in the scene. |
| `focusBox` | Box the orbited point stays in while panning (and after a tap re-centres the view). |
| `distance` | Closest and farthest zoom, measured from the orbited point. The farthest is raised automatically if the starting view (after the screen-shape step-back) is farther. |

The camera cannot get below the ground: it never goes below the point it
orbits (so the lowest `pitch` is raised to 0 when `ground` is set), and that
point never goes below `ground`. Yaw and pitch are measured round the orbited
point, which moves when the visitor pans or taps something; the window is
always "this far round whatever you are looking at".

How it works: the viewer's orbit camera is PlayCanvas's `OrbitController`,
which has these limits built in but left open. `app.js` imports the same class
and sets them each time the viewer attaches it to a pose (load, reset, hotspot
fly-to). A limited scene also turns off the viewer's keyboard and gamepad
input, whose WASD, arrow, `2` and `3` keys switch to unlimited fly and walk
modes. Visitors drag, pinch and tap, and the Reset view button stays.

## Placing hotspots

Open the page with `?place`. Move the camera to the view a visitor should get
for a hotspot, then tap the exact spot in the scene. Each tap adds a line with
the 3D `position` and the `camera` viewpoint; paste those two fields into the
matching entry of the scene description's `hotspots` list. "Record current
view" gives an `initialCamera` for the starting view.

The Annakut scene has an empty `hotspots` list. The 10 entries in
`site/hotspots.json` are placed on the sample building, so their text and
photos can be copied over, but each needs a new `position` and `camera`.

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

`"fitSquare": true` does the opposite: the starting view is taken to be framed
for a square screen, and the camera steps back on wide screens as well as
upright ones, so a subject about as tall as it is wide stays whole on every
screen shape. `last-year-v1.json` and `last-year-v0.json` use it to keep the
whole display in view.

## What was checked, and what was not

Checked in a desktop browser, including at phone size (375 x 812):

- Both scenes stream and render with both WebGPU and WebGL 2.
- The Annakut's starting view shows the whole display upright (375 x 812),
  sideways (812 x 375) and on a desktop window (1280 x 800).
- On the sample scene, all 10 hotspots track their points; tapping one flies
  the camera there and opens the sheet; previous / next, close and reset view
  work.
- The language toggle switches titles, body text and interface labels.
- Portrait and landscape layouts.

Checked for v1 and the view limits (2026-11-19, the same desktop browser):

- The default page opens v1. Its starting view shows the whole display, level,
  at 375 x 812 (WebGPU), 812 x 375 (WebGL 2, `?webgl`) and in the desktop pane
  (WebGPU and WebGL 2).
- Mouse drags stop at exactly 75 degrees to each side, at 75 degrees above
  level, and at level. The mouse wheel stops at the closest and farthest
  distance (1.5 and 16).
- Panning (tested with input fed straight to the camera, since the test
  browser cannot make a right-button or two-finger drag) stops the orbited
  point at the table top, and over a random walk of turns, pans and zooms
  the camera never went below it.
- Reset view returns to the starting view, and the limits hold after it.
- The sample scene (`?config=hotspots`) is unchanged: no limits, 10
  hotspots, fly-to, the sheet, next and reset view work.

Not checked:

- Numbers from a real phone. The page was opened on one phone over Wi-Fi and
  worked, but frame rate, memory and load time were not recorded, and only
  that one device was tried.
- Hosting over HTTPS, and loading over mobile data.
- Pinch zoom and two-finger pan with real fingers. The limits work on the
  camera itself, whatever the input, but no touch screen was used.
- Load times for v1: the test machine was busy with other work at the time
  (first view 14 to 29 seconds, against 0.5 to 0.7 seconds for the same page
  on an idle machine earlier that evening).
- The Gujarati interface labels in `app.js` (`STRINGS.gu`) were written for
  this prototype and need a native reader's review.

Known gaps:

- Data use: the Annakut scene is 34 MB on disk (v0: 36 MB) and a
  phone-sized session that zoomed in downloaded all of v0. The sample is 52 MB on disk, and a
  phone-sized session downloaded about 36 MB of it. The first view needs only
  the lowest level (about 4 MB for the Annakut, 3.2 MB for the sample).
- v1 is clean round the display but still smears towards the edges of its
  view window: past about 45 degrees to the side or above, the food on the
  tiers turns into streaks. No photo was taken from there. Some loose splats
  from the hall ceiling remain above the canopy.
- The person who stood at the left edge of three photos is still in v1, as a
  dark, streaky figure beside the display when seen from the left. The boxes
  that were meant to leave them out of training were drawn too small (they
  miss the legs in two photos).
- Version 0 (`?config=last-year-v0`) is not cleaned: loose splats from the
  hall's ceiling, floor and walls show around the display, and a person who
  stood at the left edge of three photos appears as a faint figure there.
- Hotspot markers stay visible when the point is behind another object.
- The starting view is fitted to the screen shape once, at load. Rotating the
  phone afterwards keeps the current camera.
- The camera can zoom through surfaces inside the `distance` limit; the
  viewer has no collision. Scenes without `viewLimits` can still orbit
  anywhere, including behind the scene.
