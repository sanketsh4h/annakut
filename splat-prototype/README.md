# Annakut 3D darshan: splat prototype

A phone-friendly web page that shows a Gaussian splat scan with tappable,
bilingual (English / Gujarati) hotspots.

- **Default scene:** the 2025 Annakut, version 2 (`site/last-year-v2.json`,
  `site/scene-last-year-v2/`, 34 MB). Version 1 cropped to a 3D boundary round
  the display (below), so the hall's walls, ceiling and floor and the haze
  round the display are gone: 848,702 splats are left. Same turn and pan
  limits as v1; the zoom is set from the screen (the display fills 75% of it
  farthest out, and can be brought 4 times closer).
- **Version 1** (`?config=last-year-v1`, `site/scene-last-year-v1/`, 34 MB):
  the same 15 photos as v0, trained with
  depth from dense stereo and a monocular depth model, levelled with the
  phones' gravity sensors, and cleaned of faint and very large splats
  (865,000 splats are left), with the hall still round it. The camera is held to
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
browsers only allow WebGPU on `https://` pages. Over HTTPS, Chromium browsers
(Chrome, Edge, Brave, Android phones) use WebGPU where they support it.
Browsers on Safari's engine stay on WebGL 2: that is every browser on an
iPhone or iPad, and Safari on a Mac. On an iPhone, Safari's WebGPU drew the
scan with heavy brushstroke streaks that the same view with WebGL 2 did not
have. `?webgpu` turns it back on for testing.

The small readout at the bottom left shows which renderer is in use, the
quality level the viewer chose for the device, the frame rate while the scene
is moving, and how long the first view took. Tap it to step through quality
levels.

Every device starts at the viewer's `default` quality. Left to itself the
viewer starts phones at `performance`, which draws at half resolution and
made the scan look blocky and noisy on phones. `app.js` overrides that. The
viewer saves a level picked by tapping the readout in the browser, so a
phone that had `performance` saved from before the fix is reset to `default`
once, on its first visit with it (marked by `annakut-quality-reset` in the
browser's storage). After that the visitor's own choice sticks. If a phone
runs too slowly, tapping round to `performance` is the way back.

### Test switches

Add these to the address, for example `http://localhost:4173/?webgl&stats`.

| Switch | Effect |
| --- | --- |
| `?webgl` | Force the WebGL 2 renderer |
| `?webgpu` | Use WebGPU in Safari's engine too (iPhone, iPad, Safari on a Mac), which otherwise gets WebGL 2 |
| `?budget=1` | Cap the scene at this many million splats |
| `?stats` | Show the engine's performance graphs |
| `?lang=gu` | Start in Gujarati |
| `?place` | Hotspot placement mode (below) |
| `?cam=px,py,pz,tx,ty,tz,fov` | Try a starting camera position and target |
| `?config=hotspots` | Load `site/hotspots.json` (the sample scene) instead of the default scene. Any `site/<name>.json` works: `?config=test-scan`, `?config=last-year-v0` |
| `?nolimits` | Ignore the scene's `viewLimits`, for authoring hotspots and views outside the visitor's window |
| `?walk` | Start in the walk along the display, if the scene has one |

## Layout

```
site/                 everything that gets deployed (plain static files)
  index.html          page shell and import map
  app.js              viewer setup, hotspots, info sheet, language toggle;
                      DEFAULT_CONFIG names the scene the page opens with
  styles.css
  last-year-v2.json   the default scene: the 2025 Annakut, version 2
  scene-last-year-v2/ its streamed scene: lod-meta.json plus chunk folders
  last-year-v1.json   version 1, with scene-last-year-v1/
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
  object-scene.sh     a small object's model from the gpu machine to a
                      page on the local site (PIPELINE.md, short route)
  device-check.mjs    checks a phone and a laptop get the same quality
                      (PIPELINE.md, 6e); needs Playwright
scan-pipeline/        reference copy of the gpu machine's scan scripts
  video_to_frames.py  runs on the Mac: a walk-round video plus a few stills
                      becomes the photo set (PIPELINE.md, 1b)
  object.sh           a small object in one command: camera positions,
                      training, crop (PIPELINE.md, short route)
  depth-targets.sh    depth targets for the trainer in one command (3)
  spacing_study.sh    how far apart frames can be: the test behind the
                      frame caps (1b)
  refine/             the scripts that made the live model: depth targets,
                      training with a depth loss, clean-up, levelling, and
                      the crops for the display (crop_hull.py, 5c) and for a
                      small object (crop_object.py, 5d)
PIPELINE.md           the whole method, photos to the live view, step by step
```

`site/` has no build step. Any static host (Vercel, Netlify, GitHub Pages) can
serve the folder as it is.

## Where it is live

<https://sanketsh4h.github.io/annakut/>, on GitHub Pages.

`.github/workflows/pages.yml` uploads `site/` on every push to `3D-gsplat`
that changes the site, so pushing this branch is what publishes a change. It
takes a few minutes. Only tracked files go up, so `?config=test-scan` does not
work there: its scene folder is not in the repo.

## Putting a new model live

Each model gets its own versioned pair, and old versions stay in place:
`site/last-year-v1.json` with `site/scene-last-year-v1/`, and so on.

1. Convert the splat into a new folder (step 3 below), giving the output
   folder as the second argument:

   ```bash
   ROTATE=... sh scripts/build-scene.sh path/to/model.ply site/scene-last-year-v3
   ```

   A model that needs moving as well as turning (v1 does: the ground goes to
   height 0 and the display's middle to x = 0) is levelled with
   splat-transform first, then built without `ROTATE`. For a model trained
   like v1:

   ```bash
   node_modules/.bin/splat-transform -w model.ply -r 47.1311,-43.2295,-149.6335 -t -0.75,1.6,0 level.ply
   sh scripts/build-scene.sh level.ply site/scene-last-year-v3
   ```

   v2 was then cropped to the display (next section) before the build step.

2. Copy the current `site/last-year-v2.json` to `site/last-year-v3.json` and
   point its `scene` at the new folder. Check the starting view at
   `?config=last-year-v3` and adjust `initialCamera` and `viewLimits` if the
   model sits differently.
3. Change `DEFAULT_CONFIG` in `site/app.js` to `'last-year-v3'`. That one line
   is what makes it the page visitors get.

Never commit a source `.ply` (`.gitignore` blocks them): they are over
GitHub's 100 MB file limit. The photos stay out of the repo too, because they
carry GPS positions.

### Cropping to the display

v2 keeps only what lies inside a 3D boundary round the display, drawn to
follow a sketch of what belongs to the display and what is noise. The
boundary follows the display's stepped shape: low and deep at the front
trays, tall and shallow at the canopy, with the domes on top. It is made from
the display's own clearly reconstructed surfaces (opaque, small splats), cut
into height bands 0.25 units tall; each band's outline seen from above,
grown by 0.25 units, is what that band keeps. The script is
`scan-pipeline/refine/crop_hull.py`, and runs on the levelled `.ply` before
`build-scene.sh` (`PIPELINE.md`, stage 5, has the whole clean-up in order):

```bash
python3 scan-pipeline/refine/crop_hull.py level.ply cropped.ply \
  --box=-4.5,-0.4,-3.95,4.7,5.7,3.95 --box=-2.9,5.7,-3.2,2.9,7.1,-1.3 \
  --fringe-box=-4.75,0.5,-3.75,4.5,5.75,4.0 --keep-box=-0.8,5.5,-2.2,0.8,7.05,-1.35
```

The two `--box` limits are loose, in the viewer's frame: the display, and the
domes above it. They keep the hall walls, ceiling and the cabinet beside the
display out of the boundary.

The `--fringe-box` is a tighter box round the display. Outside it (above the
canopy, under the front table top, at the sides) only small splats right next
to the display's solid surfaces stay: the table's front edge and the domes
stay, the streaks and haze between them go. The centre dome is drawn with the
same thin, faint splats as the streaks round it, so `--keep-box` exempts it.

## Making a scene from a new scan

Shoot the photos by `CAPTURE-CHECKLIST.md` first. It also covers shooting a
video in place of most of the photos (`PIPELINE.md`, stage 1b).

`PIPELINE.md` is the full method that made the live model (depth targets,
training, clean-up, levelling, the crop to the display), followed by the
viewer, the angle caps and the walk. The short version below is the plain
route without the extra training and clean-up steps.

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
| `zoom` | Sets the zoom from the screen instead of `distance` (v2 uses it, below). |

v2 sets its zoom from the screen. Farthest out, the display spans 75% of the
screen in its tighter direction (the height on a landscape screen, the width
on a phone held upright); closest in, it is 4 times larger:

```json
"zoom": {
  "boxes": [
    { "min": [-4.0, 0.2, 2.5], "max": [4.0, 1.0, 3.9] },
    { "min": [-4.5, 0.2, -1.0], "max": [4.5, 1.0, 2.5] },
    { "min": [-4.5, 0.2, -3.5], "max": [4.5, 5.6, -1.0] },
    { "min": [-0.6, 5.6, -2.0], "max": [0.6, 6.9, -1.4] }
  ],
  "fill": 0.75,
  "in": 4
}
```

The boxes describe the display's shape (front table, middle tiers, the back
tiers with the canopy, the centre dome), fitted to what shows on screen. The
page works out the distance at which they span `fill` of the screen, seen from
the starting view's direction, and that is both the farthest zoom and where
the starting view sits. The closest zoom is that distance divided by `in`, so
the point the camera orbits looks `in` times larger; things behind that point
grow a little less. Turning the phone recomputes both, and Reset view goes
back to the farthest zoom for the new screen shape.

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

## Walking along the display

A scene description can offer a walk round the front of the display. The
visitor presses **Walk along the display**, the camera glides to the right
end, and each press of **Move left** takes it one stop further along a
curved path to the left end. **›** steps back, **Full view** (or Reset view,
or Escape) returns to the starting view. Left and right arrow keys step too.

From `last-year-v2.json`:

```json
"walk": {
  "eyeHeight": 1.91,
  "center": [0, -0.7],
  "radius": 6.4,
  "angles": [45, -45],
  "fov": 60,
  "stops": 5,
  "step": 0.6
}
```

| Field | Meaning |
| --- | --- |
| `eyeHeight` | Height (Y) of the camera. The view is level, so whatever is at this height sits halfway up the screen. |
| `center` | X and Z of the point the path curves round. The camera faces it all the way. |
| `radius` | How far the camera stays from that point. |
| `angles` | Where on that circle the walk starts and ends, in degrees: 0 is straight in front of the display, positive is the visitor's right. `[45, -45]` goes right to left. |
| `fov` | Field of view, across the screen's longer side. |
| `stops` | At least this many stops, the two ends included. |
| `step` | No two stops are further apart than this share of the angle in view across the screen, so a narrow screen gets more stops. |

Seen from above, the path is an arc of a circle. With the values above it
runs from the display's front right corner, out to about 1.4 m in front of
the front trays at the middle, and back in to the front left corner. Height,
distance from the centre and field of view stay the same for the whole walk,
so nothing at the centre changes size on the way. A landscape screen gets 5
stops and a phone held upright 7.

`eyeHeight` 1.91 is the eye height of the two seated cut-out figures on the
middle tier, measured in the model by picking points on their faces in
placement mode (left figure 1.915, right figure 1.90). In the model's scale
that is about 1.45 m above the estimated floor, close to a standing
visitor's eye height. "Life size" here means the view of someone standing
there: at the middle stop the cut-out figures are about 3.8 m away.

During the walk a drag slides the camera along the same path (the buttons
then carry on from the nearest stop); tilting, panning and zoom are off.

How it works: the walk is an orbit round `center` with the pitch, the
distance and the orbited point all fixed, so it uses the same
`OrbitController` limits as `viewLimits`, swapped in while the walk is on and
put back after. Each glide is the viewer's own hotspot fly-to, aimed at one
extra annotation whose viewpoint is rewritten for each stop. A glide goes
straight from one stop to the next while the view turns, so between stops
the camera cuts inside the arc by up to about 10 cm.

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

Checked for v2 (2026-11-20): it opens by default at 375 x 812 (WebGPU),
812 x 375 (WebGL 2) and 1000 x 692 (WebGPU), and looks clean from the front,
from both sides and from above. The yaw, pitch and pan limits are the same as
v1's. For the zoom rule, measured on screenshots: at 1000 x 692 the start view
shows the display over 74% of the height (64% of the width); at 375 x 812 over
73% of the width. The mouse wheel stops there going out and at 4 times closer
going in. Turning 375 x 812 to 812 x 375 without reloading, then Reset view,
gives the same framing as loading sideways.

Checked for the walk (2026-11-20, the same desktop browser):

- At 1200 x 800 (WebGPU), 812 x 375 (WebGPU) and 375 x 812 (WebGL 2, in
  Gujarati): the button starts the walk at the right end; each press moves
  one stop left (5 stops on the two wide screens, 7 on the upright phone);
  the camera stays at height 1.91 and 6.4 from the centre at every stop; Move
  left greys out at the last stop; the controls fit the 375 wide screen.
- The cut-out figures' eyes sit at half the screen's height when the camera
  faces them.
- A drag slides along the path and stops at both ends, and the counter
  follows. The mouse wheel does nothing during the walk.
- Full view and Reset view end the walk and return to the starting view, and
  the scene's own limits hold again after it.
- The sample scene (`?config=hotspots`) shows no walk button and its
  hotspots still open.

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

- Most numbers from real phones. One frame rate is recorded: an iPhone 15
  Pro in Safari on the live site, WebGL 2 at `default` quality, ran the v2
  model at 45 to 60 fps while dragging (2026-11-21; PIPELINE.md, 6e, keeps
  the table). Memory and load time were not recorded, and no Android phone
  or older iPhone has been tried.
- Loading over mobile data. The live site is on HTTPS (GitHub Pages) and
  has been opened on that iPhone over Wi-Fi.
- Pinch zoom and two-finger pan with real fingers. The limits work on the
  camera itself, whatever the input, but no touch screen was used.
- Load times for v1: the test machine was busy with other work at the time
  (first view 14 to 29 seconds, against 0.5 to 0.7 seconds for the same page
  on an idle machine earlier that evening).
- The Gujarati interface labels in `app.js` (`STRINGS.gu`) were written for
  this prototype and need a native reader's review.

Known gaps:

- The walk's two end stops look rough. They view the display from 45 degrees
  to the side, from over its front corners, where no photo was taken: the
  front trays smear into streaks and the flat cut-out figures look thin. The
  three to five stops in between look close to the photos. Smaller `angles`
  (say `[30, -30]`) trade the curve for a cleaner picture.
- On a landscape screen the walk's view is about 30 to 42 degrees tall, so
  the top of the display is out of the picture, as it is for someone
  standing that close who does not look up.

- Data use: the Annakut scene is 34 MB on disk (v0: 36 MB) and a
  phone-sized session that zoomed in downloaded all of v0. The sample is 52 MB on disk, and a
  phone-sized session downloaded about 36 MB of it. The first view needs only
  the lowest level (about 4 MB for the Annakut, 3.2 MB for the sample).
- v1 and v2 still smear towards the edges of the view window: past about 45
  degrees to the side or above, the food on the tiers turns into streaks. No
  photo was taken from there. v2's crop removes what lies outside the
  display; streaks inside the boundary (round the domes and the front-right
  trays) remain.
- The person who stood at the left edge of three photos is still in v1, as a
  dark, streaky figure beside the display when seen from the left. The boxes
  that were meant to leave them out of training were drawn too small (they
  miss the legs in two photos).
- Version 0 (`?config=last-year-v0`) is not cleaned: loose splats from the
  hall's ceiling, floor and walls show around the display, and a person who
  stood at the left edge of three photos appears as a faint figure there.
- Hotspot markers stay visible when the point is behind another object.
- The starting view is fitted to the screen shape once, at load. Rotating the
  phone afterwards keeps the current camera (in v2 the zoom limits follow the
  new shape, and Reset view refits).
- The camera can zoom through surfaces inside the `distance` limit; the
  viewer has no collision. Scenes without `viewLimits` can still orbit
  anywhere, including behind the scene.
