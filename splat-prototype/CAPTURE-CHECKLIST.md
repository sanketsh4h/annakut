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
