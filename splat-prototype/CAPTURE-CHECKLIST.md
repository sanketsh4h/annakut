# Annakut capture checklist

For photographing the 21 ft x 14 ft (6.4 m x 4.3 m) display so it can be turned
into the 3D scene. Target: **450-650 sharp, evenly lit photos in about 40
minutes**, then a 30-minute check before you leave.

The display will be taken down, so there is one chance. The two things that
ruin a scan and cannot be fixed afterwards are **blurry photos** and **parts
that were never photographed**.

## A few days before

- [ ] **Rehearse once at home.** Shoot a table of objects the same way, then
      run the "Before you leave" check below. Each step of that check was run
      on 2026-11-11, but never together as one on-site routine.
- [ ] Ask the organisers for 45-60 minutes with nobody near the display and the
      lighting left alone, after the arranging is finished.
- [ ] Ask the gpu machine's owner to have it switched on that day. Without it
      there is no on-site check.
- [ ] Pack: camera or phone, spare battery or power bank, 10 GB free storage,
      lens cloth, a step stool, the Mac and its charger, a phone hotspot.

## Camera settings

The pipeline assumes **one camera, one zoom setting, every photo the same
shape**, and it was only tested with JPEG files.

- [ ] One camera or phone for the whole shoot. Do not mix devices.
- [ ] No zooming. On a phone stay on the main 1x lens; never pinch to zoom and
      do not let it switch to the ultra-wide or macro lens.
- [ ] Every photo in **landscape**. No upright shots.
- [ ] Save as **JPEG** (iPhone: Settings > Camera > Formats > Most Compatible).
- [ ] 12 megapixels is plenty. Higher modes only make files bigger.
- [ ] Fixed exposure for the whole shoot: set it so the brightest dishes and
      metal are not washed out, then lock it. A manual camera app does this
      best; otherwise use the camera's exposure lock.
- [ ] Fixed white balance (a preset, not auto).
- [ ] **No flash.** It moves with you, so every photo would be lit differently.
- [ ] Off: HDR, night mode, portrait mode, Live Photos, filters, beauty modes.
- [ ] Shutter 1/125 s or faster if you can set it. On a dedicated camera, about
      f/8 so near and far dishes are both in focus.
- [ ] Clean the lens.

If the hall is dim, add steady lamps that stay in one place. Do not slow the
shutter and hope.

## Prepare the display

Anything that changes between photos turns into haze or ghosts.

- [ ] Arranging is finished. Nothing is added, moved or removed until you are
      done, not even one dish.
- [ ] Nobody stands near or behind the display. A helper keeping people behind
      you is worth having.
- [ ] Fans and vents that move garlands or cloth: off.
- [ ] Blinking or colour-changing lights: off, or set to steady.
- [ ] Diyas and incense: unlit while shooting if that is acceptable. Flames and
      smoke will not reconstruct.
- [ ] No sunbeams that will move in the next hour; close curtains if needed.
- [ ] Check your own shadow does not fall on the display from where you will
      walk.

## Shooting

Walk, do not pivot. Each photo is taken from a new position, one small sidestep
(about a foot) from the last, so that neighbouring photos share most of their
content. Hold still for each shot. Aim at the display, not straight ahead.

Go around every side you can reach. If the back is against a wall, cover the
front and wrap fully around both ends.

```
                 wall or backdrop
        +------------------------------+
        |           display            |   21 ft wide, 14 ft deep
        +------------------------------+
   C   .  .  .  .  .  .  .  .  .  .  .  .   C    near:   about 3 ft out
  B  .    .    .    .    .    .    .    .    B   middle: about 6 ft out
 A .        .        .        .        .      A  far:    whole display in frame
```

| Pass | Where | Heights | Step | Photos |
| --- | --- | --- | --- | --- |
| A, far | far enough back that the whole display fits with room to spare | eye level, then high | 2 ft | about 70 |
| B, middle | about 6 ft from the edge | low (waist), eye level, high | 1 ft | about 180 |
| C, near | about 3 ft from the edge | eye level, high | under 1 ft | about 160 |
| Details | each hotspot item | as needed | walk in gradually | about 100 |

- [ ] **High means looking down** at roughly 45 degrees from the step stool or
      with arms raised. The tops of the dishes are most of what a visitor
      sees, and the back rows are only visible from above.
- [ ] Pass A matters for phones: the page starts further back on an upright
      screen, and the scene only looks clean from near where photos were taken.
- [ ] Change height or distance **gradually**: take four or five linking photos
      as you move from one pass to the next instead of jumping.
- [ ] For each hotspot item, walk in over 8-10 photos from the middle pass to
      close up. Never jump straight to a close-up.
- [ ] Keep something distinctive in every frame (a murti, a decoration, the
      edge of the table). A frame filled with identical bowls can be placed in
      the wrong spot; that is the kind of mistake the test run caught.
- [ ] Shoot in order, as one continuous walk. Do not delete anything on the
      camera.
- [ ] After each pass, zoom in on five or six photos on the screen. If they are
      soft, redo that pass now.
- [ ] Stay under about 700 photos. More makes the processing much slower, not
      better.
- [ ] Last, take a separate, nicely framed photo of each hotspot item for its
      information card. These do not go into the 3D scan, so any angle or
      orientation is fine.

## Shooting on video instead

Added 2026-11-21. A slow walk on video, plus about a dozen still photos, can
replace the 450-650 stills. `scan-pipeline/video_to_frames.py` picks the
sharpest frames and prepares the stills (`PIPELINE.md`, stage 1b). **This
route has not been run on a real video yet. Shoot the home rehearsal both
ways and compare before relying on it.** Everything under "Prepare the
display" still applies, and so do the passes in the table above: video makes
them faster, it does not replace them.

### iPhone 17 Pro settings for the video

Menu names are from Apple's iPhone User Guide for iOS 26. They were not
checked on a phone.

In **Settings > Camera**:

| Setting | Set to | Why |
| --- | --- | --- |
| Record Video | 4K at 60 fps | 60 fps keeps each frame's exposure short, which is less blur |
| Record Video > HDR Video | off | HDR frames come out flat and washed out; the script stops on them |
| Record Video > Auto FPS | off | Otherwise it drops to 30 or 24 fps in dim light, with a longer, blurrier exposure |
| Record Video > Enhanced Stabilization | off | It crops and warps every frame differently |
| Record Video > Lock Camera | on | No switching to another lens while recording |
| Record Video > Lock White Balance | on | Colour stays the same through a clip |
| Formats | High Efficiency; Apple ProRes off | ProRes files are huge, and Apple Log looks flat |
| Macro Control | on | Shows the macro button in the Camera app, so it can be turned off there |
| Preserve Settings | Macro Control, Exposure Adjustment on | The choices below survive closing the app |

In the **Camera app**, before each clip:

- [ ] Video mode, **1x**, landscape. Hold the phone the same way up all day.
- [ ] Action mode off. Torch off.
- [ ] If the macro button (a flower) shows, tap it so it is off.
- [ ] Stand where the pass starts and aim at the middle of the display. Touch
      and hold the screen until **AE/AF Lock** shows. This fixes exposure and
      focus for the clip.
- [ ] If bright dishes or metal look washed out, drag the sun slider down a
      little.
- [ ] Record **one clip per pass** (far, middle, near, each height). Focus is
      locked at the distance where the clip started, so a clip that changes
      distance goes soft.

Apple's Camera app has no switch for its ordinary video stabilisation and no
shutter setting. If the rehearsal shows blur or frames that do not line up,
use a manual camera app (Blackmagic Camera is free): fix the shutter at 1/120
s or faster, fix ISO and white balance, turn stabilisation off, leave
autofocus on, and record 4K HEVC in the ordinary (Rec. 709) colour mode, not
Log or HDR. Its menus were not checked for this guide.

### How to walk

- [ ] **Slowly: about half a foot per second.** One pass along the 21 ft
      front takes over a minute. Faster than that blurs in hall lighting.
- [ ] Step, pause for a moment, step. The script keeps the sharpest frame of
      each stretch, and those come from the pauses.
- [ ] Sidestep, do not pivot on the spot, and aim at the display.
- [ ] Wrap round both ends, and do the high pass looking down at about 45
      degrees. Those are the views last year's model lacked.
- [ ] Walk in to each hotspot item slowly as part of a clip; no sudden moves.
- [ ] About 10 minutes of video in all is plenty (about 4.5 GB at 4K 60).

### The still photos

About 12 ordinary photos give the pipeline the direction of "down" (the
phone stores it in every photo, not in video). Take them in the same
session, spread along the passes, each with the phone held still.

In **Settings > Camera**:

| Setting | Set to | Why |
| --- | --- | --- |
| Formats | High Efficiency or Most Compatible | The script reads both |
| Formats > Photo Mode | 24 MP (12 MP is enough) | |
| Formats > ProRAW & Resolution Control | off | |
| Main Camera (or Fusion Camera) > Default Lens | 1x (24 mm) | One lens setting for all the stills |
| Preserve Settings | Live Photo, Night Mode on | Keeps both turned off once you turn them off |

In the **Camera app**:

- [ ] Photo mode, **1x** (not 1.2x or 1.5x), **landscape**. Upright stills
      are left out.
- [ ] Live Photo off. Flash off. Photographic Style: Standard.
- [ ] Night mode off: if its button turns yellow, tap it and slide to Off.
- [ ] No Portrait mode, no zooming.
- [ ] Each still should show a good part of the display, like a frame of the
      video would.

Copy the videos and stills to the Mac by cable (Image Capture or Photos) or
AirDrop. Messaging apps recompress the video and strip the data the
pipeline needs from the photos.

### Check the video before you leave

1. Blur and pace, about as long as the video itself:

   ```bash
   python3 scan-pipeline/video_to_frames.py /tmp/none VIDEO1.MOV VIDEO2.MOV --dry-run
   ```

   It lists `soft` stretches (blurred) and `fast` stretches (the picture
   jumped) by time in each video. Reshoot those stretches as a new clip.

2. Coverage: make a small set, shrink it, and run the same check as "Before
   you leave" below, from its step 2, with `MATCHER=sequential` in front of
   `bash`:

   ```bash
   python3 scan-pipeline/video_to_frames.py check VIDEO1.MOV VIDEO2.MOV --stills STILLS_FOLDER --count 200 && sips -Z 1600 check/images/*.jpg >/dev/null
   ```

   Send the whole `check/` folder, not only its images (`rsync -a check/
   gpu:sshah_workspace/projects/annakut-check/`).

## Before you leave

A fast coverage check on every third photo, shrunk. It answers one question:
did all the photos connect into one model with no holes?

1. Copy the photos to the Mac. In Terminal, from the folder holding them:

   ```bash
   mkdir -p check && ls | grep -iE "\.jpe?g$" | awk "NR % 3 == 0" | while read -r f; do sips -Z 1600 "$f" --out check/ >/dev/null; done; ls check | wc -l
   ```

   It prints how many photos went into `check/`.

2. Send them to the gpu machine and compute the camera positions (about 10-15
   minutes for 200 photos; that figure is an estimate):

   ```bash
   ssh gpu 'mkdir -p ~/sshah_workspace/projects/annakut-check/images' && scp check/* gpu:sshah_workspace/projects/annakut-check/images/ && ssh gpu 'bash ~/sshah_workspace/projects/pipeline/01-poses.sh ~/sshah_workspace/projects/annakut-check'
   ```

3. Read the last lines it prints:
   - [ ] `separate models: 1`. More than 1 means part of the shoot did not
         connect to the rest.
   - [ ] `Registered images` equals the number of photos you sent.

4. If either is off, list the photos that were not placed:

   ```bash
   ssh gpu 'source ~/sshah_workspace/env/activate.sh; S=~/sshah_workspace/projects/annakut-check; mkdir -p $S/txt; colmap model_converter --input_path $S/sparse/0 --output_path $S/txt --output_type TXT >/dev/null 2>&1; ls $S/images | grep -vxF -f <(awk "!/^#/ && NF==10 {print \$10}" $S/txt/images.txt)'
   ```

   The file names show which stretch of the walk is missing. Go back, shoot
   linking photos between that stretch and its neighbours, add them, and
   repeat from step 1. (This command's parts were tested separately, not yet
   as a whole on the gpu machine; the rehearsal is the place to prove it.)

5. If there is time, make the 4-minute quick splat and look at it for holes and
   doubled objects (see `scan-pipeline/README.md`).

Passing this check means the photos connect. It does not guarantee the final
quality; that only shows after the full run.

## Afterwards

- [ ] Keep every original photo, unedited: no cropping, renaming, rotating,
      filters or lens corrections.
- [ ] Back them up before doing anything else.
- [ ] Full run: copy all the originals into
      `~/sshah_workspace/projects/annakut/images/` on the gpu machine and
      follow `scan-pipeline/README.md`.
