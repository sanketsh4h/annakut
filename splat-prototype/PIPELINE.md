# From photos to the live 3D view: the pipeline

Written 2026-11-20. This is the method that made the model the site loads
today (`last-year-v2`, the 2025 Annakut from 15 iPhone photos), written so it
can be run again on a new set of photos.

It has six stages:

| | Stage | Where it runs | Time for the 2025 display |
| --- | --- | --- | --- |
| 1 | Photos: shoot, convert, read the phone's gravity sensor | Mac | minutes |
| 2 | Camera positions (COLMAP) | gpu machine | minutes for 15 photos |
| 3 | Depth targets: dense stereo, then monocular depth for the gaps | gpu machine, GTX 1080 | 10 to 15 min |
| 4 | Train the Gaussian splat (gsplat, with a depth loss) | gpu machine, TITAN V | 28 min |
| 5 | Enhance: remove floaters, level, crop to the display's boundary | gpu machine, then Mac | a few minutes |
| 6 | Web scene: streamed build, the viewer, the angle caps, the rotating view, the phone and laptop check | Mac, then a real phone | about 5 min to build, 3 min to check |

Why this method: three were tested side by side (splat, NeRF mesh, COLMAP
mesh; `3D-METHODS-FINDINGS.md`). The splat looked most like the photos, NeRF
was dropped, and the splat is what the site shows.

**What the pipeline can and cannot do.** Every step either pins down shape
that some photo saw, or removes splats. None of them adds detail. On photos
held back from training, the enhanced model scores the same as the plain one
(14 to 15 dB PSNR). What makes the page look better is the clean-up, the
levelling, the boundary and the limited view. Anything no photo saw stays
bad; only more photos fix that (stage 1).

## Where the pieces are

| What | Where |
| --- | --- |
| Video to photo set (stage 1b) | `scan-pipeline/video_to_frames.py` |
| Scripts for stages 2 to 5, as they were run | `scan-pipeline/refine/` (this repo) |
| Pose and plain-training scripts, power log | `scan-pipeline/` |
| Scene build script | `scripts/build-scene.sh` |
| Viewer, angle caps, rotating view | `site/app.js`, `site/last-year-v2.json` (stage 6b to 6d) |
| Phone and laptop check | `scripts/device-check.mjs` (stage 6e) |
| Tool versions and set-up on the gpu machine | `scan-pipeline/ENVIRONMENT.md` |
| Full results and every number | `last-year-3d/splat-v0/FINDINGS.md`, `last-year-3d/splat-v1/FINDINGS.md` (not in the repo) |
| Photos, trained and levelled `.ply` files | `last_year_annakut/` (never committed: GPS, people, size) |
| Training runs and depth data | gpu machine, `~/sshah_workspace/projects/annakut-2025-splat-v1/` |

On the gpu machine each scan has a project folder, called `$S` below:

```
$S/images/      the photos, as JPEGs
$S/images_2     a link to images/ (the trainer asks for it: ln -s images $S/images_2)
$S/sparse/0/    camera positions (stage 2)
$S/mvs/         dense stereo (stage 3)
$S/depth/       depth targets (stage 3)
$S/tools/       a copy of scan-pipeline/refine/
$S/runs/<name>/ one folder per training run
$S/logs/
```

Every gpu command needs `source ~/sshah_workspace/env/activate.sh` first. The
machine is shared, so long jobs ran under `taskset -c 0-3 nice -n 19` with 2
threads. gsplat runs on the TITAN V only (`CUDA_VISIBLE_DEVICES=0`); COLMAP's
dense stereo ran on the GTX 1080 (`gpu_index 1`).

## 1. Photos

Shoot by `CAPTURE-CHECKLIST.md`. The 2025 photos broke most of its rules (15
photos, two lenses, several zoom levels), and the result shows it. The three
gaps that cost the most, in order:

1. The sides. Past about 45° to either side the food turns into streaks.
2. From above. No photo looks down, so top views stretch.
3. Close, low passes along the front trays. The front strip was seen by two
   photos and breaks up from every other position.

Also keep people out of frame. One person standing at the left edge of three
photos is still in the model.

Convert HEIC to JPEG on the Mac (the JPEGs keep the GPS position, so they
stay out of the repo too):

```bash
mkdir -p images && for f in *.HEIC; do sips -s format jpeg -s formatOptions 95 "$f" --out "images/${f%.HEIC}.jpg"; done
```

Read each photo's gravity vector. An iPhone stores the direction of "down" in
every photo, and stage 5 uses it to level the model:

```bash
python3 scan-pipeline/refine/gravity.py images/*.jpg | python3 -c "import sys, json; print(json.dumps({l.split()[0]: json.loads(l.split(None, 1)[1]) for l in sys.stdin}, indent=1))" > gravity.json
```

Copy `images/` and `gravity.json` to `$S` on the gpu machine.

### 1b. From a video instead

Added 2026-11-21. One or more videos of a slow walk, plus about a dozen
still photos, in place of several hundred stills. Shoot by
`CAPTURE-CHECKLIST.md`, "Shooting on video instead". On the Mac (it needs
ffmpeg: `brew install ffmpeg`):

```bash
python3 scan-pipeline/video_to_frames.py scan-set pass-a.MOV pass-b.MOV pass-c.MOV --stills stills/
```

Name the videos in the order they were shot. `--stills` takes folders or
files, HEIC or JPEG. It writes a folder that is copied whole to `$S`:

| It writes | What it is |
| --- | --- |
| `images/v01_000123.jpg` ... | The frames it kept, full size, named in shooting order |
| `images/still_IMG_1234.jpg` ... | Each still, cropped and resized to the video's shape, so every image has one size |
| `groups/*.txt` | Which images share a camera: the video frames, and the stills by lens setting. Stage 2 reads these |
| `extra-pairs.txt` | Each still paired with every other image, for stage 2's sequential matching |
| `gravity.json` | Gravity per still, as stage 5 expects it |
| `frames.csv` | Every frame it looked at: time, sharpness, movement, kept or not |

How it picks frames. It scores 10 frames a second for sharpness, and measures
how far the picture moved between them. Each video is cut into stretches of
equal movement, not equal time, and the sharpest frame of each stretch is
kept. Standing still adds nothing; a pause in the walk gives a sharp frame.

| Option | Default | What it does |
| --- | --- | --- |
| `--count` | 600 | Frames to keep across all videos. It prints how much of the picture neighbouring frames share; aim for 85% or more |
| `--min-step` | 0.02 | Never keep frames closer than this share of the frame width. A short video gives fewer than `--count` |
| `--camera-per-clip` | off | Give each video its own camera. Use it if lens or zoom differed between videos |
| `--hdr keep` | stop | An HDR video stops the script, because its frames come out flat. This goes on anyway |
| `--dry-run` | off | Score and report only. The on-site check |

Read what it prints. `soft` lists stretches where even the best frame is
blurred next to its neighbours, and `fast` lists places where the picture
jumped between kept frames. Both are given as times in the video, so that
stretch can be shot again.

The stills carry the gravity data, which video does not have. An upright
still is left out. A still with the phone held the other way up is turned
upright and its gravity vector is turned with it. Without at least three
stills, level with `scan-pipeline/scene_frame.py` instead of stage 5's
`level.py`.

```bash
rsync -a scan-set/ gpu:sshah_workspace/projects/<scan>/
```

## 2. Camera positions

One camera, one zoom setting, all photos the same shape:

```bash
bash ~/sshah_workspace/projects/pipeline/01-poses.sh $S
```

Use the default incremental mapper. The global mapper misplaced 53 of 128
cameras on the test set while reporting success, and an Annakut's many
identical dishes are the same risk (`scan-pipeline/README.md`).

Mixed lenses or zoom levels (the 2025 photos): `01-poses.sh` forces one shared
camera, which is wrong. Run the feature extractor once per lens-and-zoom
group, each group sharing one camera, then match and map as usual. The 2025
photos made 6 groups (35 mm equivalents 14, 18 and 24 on the ultra-wide; 24,
40 and 46 on the main lens), with COLMAP's default SIMPLE_RADIAL camera. All
15 photos were placed, at 1.14 px mean error.

```bash
# once per group, with a text file naming that group's photos
colmap feature_extractor --database_path $S/colmap.db --image_path $S/images \
    --image_list_path $S/group-main-24mm.txt --ImageReader.single_camera 1 --FeatureExtraction.use_gpu 1
# then, once
colmap exhaustive_matcher --database_path $S/colmap.db --FeatureMatching.use_gpu 1
colmap mapper --database_path $S/colmap.db --image_path $S/images --output_path $S/sparse
```

The script that did this for the 2025 photos is on the gpu machine only
(`~/sshah_workspace/projects/annakut-2025/poses-baseline.sh`). The commands
above are written from its description, not copied from it.

**Frames from a video (stage 1b).** Add `MATCHER=sequential`:

```bash
MATCHER=sequential bash ~/sshah_workspace/projects/pipeline/01-poses.sh $S
```

The default compares every photo with every other, which grows with the
square of the count. Sequential matching compares each frame with the 20
after it in name order (`OVERLAP=20`), looks for places the walk came back to
(loop detection, with a vocabulary file COLMAP downloads once), and then
matches every pair in `$S/extra-pairs.txt`, which ties each still to all the
frames. The script also reads `$S/groups/*.txt` and gives each group its own
camera, which is the per-lens procedure above done for you. Any scan can use
`groups/`; every photo must be named in exactly one file.

Tested 2026-11-21 on the 128-photo South Building sample, split into a
"video" group of 108 and a "stills" group of 20 with extra pairs: 128 of 128
cameras matched the reference (largest position error 0.02% of the camera
path), and both groups came out with the same focal length, as they should
for one real camera. It matched 2,329 pairs where the default matches 8,128.
That sample is photos, not video frames, and too small to show the time
saved.

Check before going on: `colmap model_analyzer --path $S/sparse/0` should list
every photo as registered, and a quick Brush splat
(`scan-pipeline/README.md`) should show no doubled or ghosted structure.

## 3. Depth targets

The trainer gets a depth target per photo so that surfaces land at the right
distance. It comes from two sources.

**Dense stereo** (COLMAP) gives accurate depth wherever two photos agree:

```bash
colmap image_undistorter --image_path $S/images --input_path $S/sparse/0 --output_path $S/mvs --output_type COLMAP --num_threads 2
sed -i "s/^__auto__, .*/__auto__, 14/" $S/mvs/stereo/patch-match.cfg
colmap patch_match_stereo --workspace_path $S/mvs --PatchMatchStereo.max_image_size 2400 \
    --PatchMatchStereo.gpu_index 1 --PatchMatchStereo.geom_consistency 1 --PatchMatchStereo.num_threads 2
colmap stereo_fusion --workspace_path $S/mvs --input_type geometric --output_path $S/mvs/fused.ply \
    --StereoFusion.max_image_size 2400 --StereoFusion.min_num_pixels 2 --StereoFusion.num_threads 2
```

The `14` is how many other photos each photo is compared with: all of them,
for 15 photos. COLMAP's own default is 20, which suits a large shoot.
`min_num_pixels 2` keeps points that only two photos agree on; with few
photos the default of 5 leaves holes. For several hundred photos start from
COLMAP's defaults (depth-map size 1600 was enough on the 128-photo test).
These four commands are `refine/mvs-ho.sh` without its step that removes
held-out photos; the all-photo run itself was made by the mesh pipeline's
script (`mvs-glb-prototype/pipeline/04-mvs-mesh.sh`) with the same settings.

Then turn the fused cloud into per-photo targets in the trainer's own frame,
keeping for each photo only the points that photo can see:

```bash
python $S/tools/prep_depth.py $S $S/mvs/fused.ply $S/depth/all.npz
```

**Monocular depth** fills the gaps (shiny foil, the strip nearest the
camera). Depth-Anything-V2-Small guesses relative depth from one photo, and
the script fits that guess to the photo's own stereo points, so it is only
ever used where stereo has no point within about 8 px:

```bash
CUDA_VISIBLE_DEVICES=1 python $S/tools/mono_depth.py $S $S/depth/all.npz $S/depth/mono-all.npz
```

It downloads the model (25 M parameters, Apache-2.0) from Hugging Face the
first time. The fit error it prints was 1.5 to 5% per photo in 2025.

## 4. Train

gsplat 1.5.3, MCMC strategy, through `tools/run.sh` (which logs time, peak
memory and power) and `tools/v1_train.py` (which adds the depth targets and
the masks to gsplat's trainer):

```bash
cd $S
BASE="--data-factor 2 --strategy.cap-max 1000000 --steps-scaler 0.5 --eval-steps 7000 15000 30000 --save-steps 30000 --save-ply --ply-steps 30000 --depth-loss --depth-lambda 0.05"
HOLDOUT= INIT_PTS=0 MASKS=$PWD/tools/people-masks.json DENSE=$PWD/depth/all.npz MONO=$PWD/depth/mono-all.npz \
    bash tools/run.sh final -- $BASE > logs/final.log 2>&1
```

The model is the `.ply` in `runs/final/ply/`. `refine/queue5.sh` is this
command as it was launched in 2025.

| Setting | Value | Why |
| --- | --- | --- |
| Splats | 1,000,000 | 2,000,000 scored no better on held-back photos, at twice the time, memory and download |
| Steps | 15,000 (`--steps-scaler 0.5` halves gsplat's 30,000 and its schedules) | With 15 photos that is already 1,000 passes per photo; 30,000 scored no better. For several hundred photos use the full 30,000 |
| Photo size | half (`--data-factor 2`) | Keeps detail on the far tiers; loading photos is the bottleneck |
| Starting points | COLMAP's sparse points only (`INIT_PTS=0`) | Starting from dense stereo points turned the foreground into streaks and added a milky veil |
| Depth loss | on, weight 0.05 | The one training change that helped, slightly |
| Per-photo colour correction (`--use-bilateral-grid`) | off | Made held-back scores worse |
| `MASKS` | boxes to leave out of the loss, as fractions of each photo | For people. Boxes drawn by eye missed the person's legs and did not work; cover the whole person or use a segmentation model |
| `HOLDOUT` | empty for the final model | Name two photos (`IMG_a.jpg,IMG_b.jpg`) to hold them back and get an honest score |

`simple_trainer_v1.py` is gsplat 1.5.3's `examples/simple_trainer.py`
(Apache-2.0) with two marked changes: masked pixels neither pull nor push,
and the depth loss skips empty pixels, which used to make it fail. `run.sh`
expects `powerlog.sh` at `~/sshah_workspace/projects/pipeline/`.

To check a run, hold two photos back, train, and read
`runs/<name>/stats/val_step*.json`. To score a cleaned or cropped model the
same way: `python tools/eval_ply.py $S model.ply IMG_a.jpg IMG_b.jpg`.

## 5. Enhance: floaters, level, boundary

### 5a. Remove floaters (gpu machine)

```bash
python tools/level.py $S gravity.json tools/level.json
python tools/clean_ply.py $S tools/level.json runs/final/ply/<model>.ply clean/final.ply \
    --box none --min-opacity 0.05 --max-scale 0.3 --max-ratio 1e9
```

`level.py` finds true "up" from the gravity vectors (the 2025 photos agreed
to within 1.5°; without it the model was tilted 13°). `clean_ply.py` then
removes two kinds of splat:

- fainter than 5% opacity. Free: the score does not change.
- longer than 0.3 units (about 23 cm). These are the veil that hangs in
  front of the display in side and top views. They are also the hall's walls
  and ceiling, so the display ends up on the page's dark background.

Tried and rejected: a plain box crop at this stage, and removing long thin
"needle" splats, which carry real food texture.

In 2025 this removed about 136,000 splats (123,693 faint, 12,376 large) and
left 864,936. To see the model from the
edges of the visitor's window before copying it anywhere:
`python tools/window_views.py $S tools/level.json review/ label=clean/final.ply`
(the display's centre is written into that script for the 2025 model; change
`C`, `TABLE` and `FRONT` at its top for another).

### 5b. Level (Mac)

The trained model sits at an arbitrary tilt and position. The site wants +Y
up, the audience on +Z looking toward -Z, the display's middle at x = 0 and
the floor at y = 0. Find the display's middle and the floor in the levelled
frame (`floor.py` plots the dense cloud from the side, front and top with a
grid), then get the settings:

```bash
python tools/floor.py $S $S/mvs/fused.ply tools/level.json review/floor        # gpu machine
python3 scan-pipeline/refine/level_to_rotate.py level.json --centre-x 0.75 --ground -1.6   # Mac
```

Copy `tools/level.json` and `clean/final.ply` to the Mac first. `--centre-x`
is the x of the display's middle and `--ground` the height of the floor, both
read off `floor.py`'s plots.

It prints the `splat-transform` command. For the 2025 display:

```bash
node_modules/.bin/splat-transform -w final.ply -r 47.1311,-43.2295,-149.6335 -t -0.75,1.6,0 level.ply
```

In 2025 the floor was not in the model, so its height is an estimate from the
display's known 14 ft height. The scale came out at about 0.76 m per unit.

### 5c. The boundary between the display and the noise (Mac)

What is left outside the display after 5a is haze, streaks, and bits of hall.
The boundary is built from the model's own "solid" splats: opaque (over 0.5)
and small (largest axis under 0.05 units). Those are surfaces the photos saw
clearly. Floaters and haze are faint or large.

First measure where the display ends:

```bash
python3 scan-pipeline/refine/measure_box.py level.ply
python3 scan-pipeline/refine/measure_box.py level.ply --box=-4.75,0.5,-3.75,4.5,5.75,4.0
```

The first form prints how many solid splats lie in each 0.25-unit slice along
x, y and z, and a first guess at the box where the count drops away. Check it
against the picture: on the 2025 model the guess matched the box chosen by
eye on three sides, was one slice off on two, and two slices low at the
floor. The second form counts what lies outside a box, by side, and how much
of it is solid. Many splats with few solid ones is haze. Mostly solid means
the box is cutting something real.

Then crop:

```bash
python3 scan-pipeline/refine/crop_hull.py level.ply cropped.ply \
  --box=-4.5,-0.4,-3.95,4.7,5.7,3.95 --box=-2.9,5.7,-3.2,2.9,7.1,-1.3 \
  --fringe-box=-4.75,0.5,-3.75,4.5,5.75,4.0 --keep-box=-0.8,5.5,-2.2,0.8,7.05,-1.35
```

| Option | What to give it |
| --- | --- |
| `--box` (repeatable) | Loose limits for which solid splats count as the display. Generous, but not reaching the walls, ceiling or furniture beside it. The second box admits the domes above the canopy without admitting the ceiling next to them |
| `--fringe-box` | The tight box from `measure_box.py`. Outside it, only small splats right next to solid surfaces stay |
| `--keep-box` | A region exempt from the fringe rule, for a real part drawn with thin faint splats. In 2025 the centre dome looked exactly like the streaks round it by every measure, so it had to be named |

How it decides. Heights are cut into bands 0.25 units tall. Each band keeps
the outline, seen from above, of the solid splats near its height, grown by
0.25 units. The display is a staircase, low and deep at the front and tall
and shallow at the back, so the stack of outlines follows the tiers. A single
convex hull was tried first and kept the empty wedge in front of every tier.

It needs `numpy` and `scipy`. It prints how many splats it kept. In 2025:
16,234 of 864,936 removed, 848,702 left. Few, but they were the large ones
covering the hall and the white streaks over the shrine.

Check the result by loading it (stage 6) and looking from the front, both
sides and above for cut edges and for anything real that went missing.

## 6. Web scene: build, viewer, angle caps, rotating view, device check

### 6a. Build the streamed scene

```bash
sh scripts/build-scene.sh cropped.ply site/scene-last-year-v3
```

This is what keeps the render light enough for a phone:

- Four detail levels: 100%, 50%, 25% and 10% of the splats, cut into chunks
  in the compressed SOG format. The 2025 scene is 34 MB in all.
- The viewer downloads the 10% level first (about 4 MB), shows it, and
  refines from there. It picks a splat budget for the device and stays
  within it.
- It uses WebGPU in Chromium browsers where they allow it, and WebGL 2
  everywhere else. Safari's engine (every browser on an iPhone or iPad, and
  Safari on a Mac) gets WebGL 2 on purpose: its WebGPU drew this scan with
  heavy streaks.
- Every device starts at the viewer's "default" quality, full resolution.
  The viewer's own choice for phones is half resolution, which made the scan
  look blocky.
- It only draws a frame when something changes.

To check on a device: the readout at the bottom left shows the renderer, the
quality level, the frame rate and the time to the first view. `?stats` shows
the engine's graphs, `?budget=1` caps the scene at a million splats, `?webgl`
forces WebGL 2. Stage 6e is the full check that a phone shows the same
quality as a laptop.

### 6b. The viewer

The page is PlayCanvas's SuperSplat Viewer 1.43.1 on the PlayCanvas engine
2.24.0 (both MIT), run without its own interface (`ui: false`). The viewer
owns the canvas, the camera and the streaming. Everything on top of it is
plain HTML and one script, with no build step:

| File | What it holds |
| --- | --- |
| `site/index.html` | The page shell, and an import map that points the viewer at its engine |
| `site/app.js` | Starts the viewer, applies the angle caps, runs the walk, draws hotspots and the info sheet, switches language. `DEFAULT_CONFIG` near the top names the scene the page opens with |
| `site/styles.css` | All the styling |
| `site/<name>.json` | One scene description per model (below) |
| `site/scene-<name>/` | That model's streamed scene from 6a |
| `site/vendor/` | The viewer and engine files, copied out of `node_modules` by `node scripts/vendor.mjs` so the folder deploys as it is. Re-run it after upgrading either package |

Run it locally with `npm install` once, then `node scripts/serve.mjs`
(port 4173; it also prints an address for a phone on the same Wi-Fi). Any
scene description loads with `?config=<name>`. Switches for testing, added
to the address:

| Switch | Effect |
| --- | --- |
| `?config=<name>` | Load `site/<name>.json` instead of the default scene |
| `?webgl` | Force the WebGL 2 renderer. Without it, Chromium browsers use WebGPU on `https://` or `localhost` pages |
| `?webgpu` | Use WebGPU in Safari's engine too (it draws streaks there) |
| `?budget=1` | Cap the scene at this many million splats |
| `?stats` | Show the engine's performance graphs |
| `?nolimits` | Ignore the angle caps (6c) |
| `?place` | Tap to read positions off the model, for hotspots and for measuring |
| `?cam=px,py,pz,tx,ty,tz,fov` | Try a starting view without editing the scene description |
| `?walk` | Start in the rotating view (6d) |
| `?lang=gu` | Start in Gujarati |

What `app.js` does when the page opens: reads the scene description, fits
the starting view to the screen's shape, hands the viewer the scene and the
starting camera, waits for the first complete picture, puts the camera in
orbit mode, and applies the caps. With caps on, it also turns off the
viewer's keyboard and gamepad controls, because those switch to free-flying
modes the caps do not cover.

A scene description, in full (this is `site/last-year-v2.json`):

```json
{
  "scene": "scene-last-year-v2/lod-meta.json",
  "background": [0.06, 0.05, 0.05],
  "initialCamera": { "position": [0, 4.56, 7.62], "target": [0, 2.9, -0.2], "fov": 60 },
  "fitSquare": true,
  "viewLimits": { ... },
  "walk": { ... },
  "credit": { "text": "Annakut 2025 · early 3D preview (v2), made from 15 photos" },
  "hotspots": []
}
```

`initialCamera` is a view from the front that shows the whole display.
`fitSquare` says it was framed for a square screen, so the camera steps back
on both tall and wide screens until the shorter side shows the same. The
viewer applies `fov` to the screen's longer side. `hotspots` are tappable
points with text and a photo; none are placed on the Annakut yet (README,
"Placing hotspots").

### 6c. The angle caps

A model made from photos only looks right from near where the photos were
taken. The caps hold the camera inside that region, so a visitor cannot
reach the views that fall apart. For the 2025 model:

```json
"viewLimits": {
  "yaw": [-75, 75],
  "pitch": [0, 75],
  "ground": 0,
  "focusBox": { "min": [-4.0, 0.82, -3.0], "max": [4.0, 5.0, 3.0] },
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
}
```

| Cap | Value | What it means |
| --- | --- | --- |
| `yaw` | -75° to 75° | How far the camera may swing to either side of straight on: a 150° window. Negative is the visitor's left |
| `pitch` | 0° to 75° | How far above level the camera may rise. 0 is level, 90 would be straight down |
| `ground` | 0 | The floor's height. The camera never goes below the point it orbits, and that point never goes below this, so there is no view from underneath |
| `focusBox` | the display, from the table top up | Where the orbited point may go when the visitor pans or taps. Its floor is the table top (0.82), not the ground: below the table top the model has nothing to show |
| `zoom.fill` | 0.75 | Farthest out, the display spans 75% of the screen in its tighter direction. That is also the starting view |
| `zoom.in` | 4 | Closest in, the orbited point looks 4 times larger than at the farthest |
| `zoom.boxes` | four boxes | The display's shape, used to work out the farthest distance for any screen: front table, middle tiers, back tiers with the canopy, centre dome |

A simpler `"distance": [1.5, 16]` (closest and farthest, in scene units) can
replace `zoom`; v1 used it. `zoom` adapts to the screen, so an upright phone
and a desktop both start with the display filling the same share.

**How the values were chosen.** The 150° and 75° window, the ground rule and
"no view from below" were the brief. What the model supports is narrower:

| View | What the 2025 model shows |
| --- | --- |
| Straight on | Close to the photos |
| 30° to the side | Display recognisable, front trays soften |
| 45° to the side or above | Tiers readable, figures recognisable, food smeared into short streaks |
| 75° to the side | The near half is a slanted smear, the far half is missing |
| 75° above | Rows of trays from above, stretched toward the viewer |

So the outer 30° of this window is rough. For a new model, set the caps from
what it shows, not from these numbers. Two ways to look:

- On the gpu machine, before building anything:
  `python tools/window_views.py $S tools/level.json review/ label=model.ply`
  renders the model from the start view, 45° and 75° to each side, 75° up
  and at ground level, in one sheet. The display's centre is written into
  the script (`C`, `TABLE`, `FRONT`, in levelled coordinates before the
  shift of stage 5b); change it for a new display.
- In the browser: load the scene with `?nolimits`, drag to where it starts
  to break up, and read the view with `window.annakut.currentView()` (add
  `?place`).

Put `yaw` and `pitch` where the picture is still acceptable. Set `ground`
to the floor's height from stage 5b, and `focusBox` to the display's box
from stage 5c with its floor at the lowest surface the model really has.

**How the caps work.** The viewer's orbit camera is PlayCanvas's
`OrbitController`, which has ranges for pitch, yaw, zoom and the orbited
point built in, left open by the viewer. `app.js` imports the same class and
sets the ranges every time the viewer attaches the controller to a pose: at
load, on Reset view, on a hotspot fly-to and at each stop of the walk. The
controller then clamps every drag, pan and pinch with its usual smoothing,
so the camera slows into a cap and does not bounce. `?nolimits` turns the
caps off for authoring.

**Checked** on the 2025 model with mouse input: drags stop at exactly 75° to
each side, 75° above and at level; the wheel stops at the farthest and
closest zoom; after a long random run of turns, pans and zooms the camera
never went below the table top. Not checked with real fingers on a touch
screen.

### 6d. The rotating view

The walk carries the visitor round the front of the display on a curved
path, one stop per button press, with the camera facing the centre all the
way:

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

| Setting | How to choose it |
| --- | --- |
| `eyeHeight` | The height the camera holds. The view is level, so whatever is at this height sits halfway up the screen. Measure it by loading `?place&nolimits`, facing the thing that should be at eye level, and picking points on it (tap, or `window.annakut.pickAt(x, y)` in the console). The 2025 value is the eye height of the two seated cut-out figures |
| `center`, `radius` | The point the path curves round, and how far the camera stays from it. Together they set how far in front of the display the visitor stands: here about 1.4 m from the front trays at the middle |
| `angles` | Where the path starts and ends, in the same degrees as `yaw`. Keep them inside what the model supports: at 45° the 2025 model's two end stops already look rough |
| `stops`, `step` | At least `stops` stops; a narrow screen gets more, so that no two stops are further apart than `step` of the angle in view |

It is an orbit with the pitch, distance and orbited point all fixed, so it
uses the same caps mechanism, swapped in while the walk is on. Height,
distance and field of view do not change along the way, so nothing changes
size. README, "Walking along the display", has the rest.

### 6e. Same quality on a phone and a laptop

A model that looks right on a laptop can look far worse on a phone, from
the same files, for reasons that have nothing to do with the model. On
2026-11-21 the 2025 model looked fine on a laptop and "bad, unclear, noisy"
on an iPhone. There were two causes, both in the page, and both are now
handled in `site/app.js`:

- **Half resolution.** Left to itself the viewer starts phones at its
  "performance" quality, which draws the scene at half resolution. `app.js`
  starts every device at "default". A phone keeps a level picked by tapping
  the readout, so `app.js` also resets a saved level below "high" once per
  browser (the `annakut-quality-reset` key in the browser's storage).
- **Safari's WebGPU.** It drew the scan with heavy brushstroke streaks. The
  same view with `?webgl` on the same iPhone was clean. Every browser on an
  iPhone or iPad runs Safari's engine, and so does Safari on a Mac, so those
  get WebGL 2. Chromium browsers keep WebGPU. `?webgpu` turns it back on in
  Safari for testing.

Chrome on a Mac never shows the second problem, which is why the check
below has a step on a real iPhone. Run all three steps for every new model,
and again after upgrading the viewer or the engine (`scripts/vendor.mjs`).

**Step 1. Automatic check, on the Mac.** With `node scripts/serve.mjs`
running:

```bash
node scripts/device-check.mjs "http://localhost:4173/?config=last-year-v3"
```

It opens the page in headless Chromium as a laptop, an Android phone, an
iPhone with Safari, an iPhone with Chrome and Safari on a Mac, each in a
fresh profile. Every one must pass:

| Check | Pass |
| --- | --- |
| Renderer | WebGPU on the laptop and Android; WebGL 2 on both iPhones and Mac Safari |
| Quality | `default` on all five |
| Canvas | Full resolution: the display's pixel ratio, capped at 1080 pixels on a phone's shorter side (2160 elsewhere) |
| Scene files | Every file loads; none fails or returns an error |
| Page errors | None |

It prints one line per device and exits with 1 if anything fails. It also
photographs the start view and the walk's first and last stops on every
device, and writes `index.html` with them side by side (in the system's
temporary folder unless `--out` names one). Look at that page: apart from
the screen's shape, the phone pictures should look like the laptop's. A
blemish that shows on every device at the same view is the model, not the
page; fix it in stage 5 or keep the caps (6c) and the walk (6d) away from
it.

It needs Playwright. On this Mac it is in another project:
`PLAYWRIGHT_PATH=~/Projects/digital_outreach/node_modules node scripts/device-check.mjs ...`.
Elsewhere, `npm install --no-save playwright` and
`npx playwright install chromium` in this folder.

The pictures are all drawn by Chromium, including the Safari rows: those
rows only prove the page picks WebGL 2 for Safari. Safari's own drawing
needs step 3.

**Step 2. Put it on an `https://` address.** A phone cannot reach the Mac's
`node scripts/serve.mjs` reliably: on 2026-11-21 the iPhone's Safari would
not open the Mac's Wi-Fi address and the server saw no visit. Browsers also
only allow WebGPU on `https://`. So the phone check runs on the published
site (6f), or on another `https://` address if one is set up first. GitHub
Pages keeps files for up to 10 minutes (`max-age=600`), so after a push wait
that long, then reload.

**Step 3. Real phone and laptop.** Open the site on an iPhone, on a laptop,
and on an Android phone if one is at hand. On each:

1. Read the readout at the bottom left. It should say `WebGL 2 · default
   quality` on the iPhone and `WebGPU · default quality` on Chrome (laptop or
   Android).
2. Drag for a few seconds and read the frame rate while it moves. Note it
   with the phone's model in the table below.
3. Take the walk and screenshot stop 1, the middle stop and the last stop on
   the phone; compare them with the same stops on the laptop.

Frame rates measured on real phones, while dragging, on the live site:

| Date | Phone | Browser, renderer | Model | Frame rate |
| --- | --- | --- | --- | --- |
| 2026-11-21 | iPhone 15 Pro | Safari, WebGL 2, `default` quality | `last-year-v2` (848,702 splats) | 45 to 60 fps |

If the phone looks worse than the laptop:

| What the phone shows | Cause | What to do |
| --- | --- | --- |
| Readout says `performance`; everything soft and blocky | Half resolution, from a level saved by tapping the readout | Tap the readout round to `default`. If the reset in `app.js` stopped working, fix that |
| Brushstroke or needle-like streaks, but `?webgl` on the same phone is clean | The browser's WebGPU | Keep that browser on WebGL 2: extend `safariEngine` in `app.js` |
| Streaks with `?webgl` too, and the laptop shows them at the same view | The model | Stage 5, or keep the caps and the walk away from that view |
| Streaks with `?webgl` too, but the laptop is clean at the same view | Not seen yet | Compare `?budget=1` and the readout's quality levels; record the phone and browser |
| Old behaviour right after a push | GitHub Pages' cache | Wait 10 minutes and reload |
| Sharp but under about 30 fps while dragging | The phone is short of power | Tap the readout to `performance` to check; if most phones need it, build with fewer splats (6a) |

### 6f. Put it live

1. Run 6e step 1 on `http://localhost:4173/?config=last-year-v3`, and look
   at it yourself at 375 × 812, sideways and on a desktop window.
2. Change `DEFAULT_CONFIG` in `site/app.js` to `'last-year-v3'`.
3. Commit the scene folder, its `.json` and `app.js`, and push `3D-gsplat`.
   The push publishes to <https://sanketsh4h.github.io/annakut/> within a
   minute or two.
4. Run 6e step 3 on the live site, and step 1 again against it:
   `node scripts/device-check.mjs https://sanketsh4h.github.io/annakut/`.

Never commit photos, their JPEG copies, or any `.ply`.

## What is not saved here

- `poses-baseline.sh`, the per-lens pose script for the 2025 photos, is on
  the gpu machine only. Stage 2 describes what it does.
- The mesh pipeline's dense-stereo script, which made the all-photo cloud, is
  in `mvs-glb-prototype/pipeline/`, not in this repo. Stage 3 lists its
  commands and settings.
- `measure_box.py` and `level_to_rotate.py` were written on 2026-11-20 to
  replace steps that were first done by hand. Both were checked against the
  2025 model's saved numbers; neither has been used on a new scan.
- The scripts in `refine/` are as they ran. `mvs-ho.sh` and `queue5.sh` have
  the 2025 project's folder names written into them, and `window_views.py`
  the 2025 display's centre.
- The whole chain has been run once, on one set of 15 photos. It has not been
  run on a full capture of several hundred photos.
- The video route (stage 1b and `MATCHER=sequential`) was written on
  2026-11-21 and has not been run on a real video. `video_to_frames.py` was
  tested on a made-up video with known movement, pauses and blur: it measured
  the movement to within 4%, kept the sharp frames, and flagged the blurred
  stretch. Not tested: a real iPhone file, whether video frames give as good
  a model as stills, and a still taken with the phone the other way up (the
  arithmetic was checked, not a photo). The home rehearsal should shoot the
  same table both ways and compare held-back scores (stage 4).
- `scripts/device-check.mjs` (6e) was written on 2026-11-21 and has been run
  on the 2025 model only, locally and on the live site. Safari's WebGPU
  streaks were seen on one iPhone; why they happen was not found.
