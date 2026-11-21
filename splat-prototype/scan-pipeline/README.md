# Photos to splat: the scan pipeline

Run on this machine after `source ~/sshah_workspace/env/activate.sh` is
available (see `~/sshah_workspace/env/README.md`). Each scan gets its own
folder under `~/sshah_workspace/projects/` with the photos in `images/`.

```bash
S=~/sshah_workspace/projects/<scan>

bash pipeline/01-poses.sh $S        # camera poses (COLMAP)
brush $S --total-steps 5000 --export-every 5000 --export-path $S/brush   # quick look, ~4 min
bash pipeline/02-train.sh $S        # final splat (gsplat), ~30 min
python pipeline/scene_frame.py $S   # levelling angles + starting camera for the website
```

Then, on the Mac, copy `$S/gsplat/ply/point_cloud_29999.ply` over and build the
web scene with the `rotate` angles that `scene_frame.py` printed (see the
prototype's README, "Swapping in the real scan").

For frames taken from a video (`video_to_frames.py`, run on the Mac; see
`PIPELINE.md`, stage 1b), use `MATCHER=sequential bash pipeline/01-poses.sh $S`.
It also reads `$S/groups/*.txt` (one camera per file) and `$S/extra-pairs.txt`.

The scripts run at low priority (`renice 15`), because the machine is shared.
COLMAP still uses every CPU thread that is free; `THREADS=4 bash pipeline/01-poses.sh $S`
caps it (slower, but leaves half the CPU alone).

## Power log

`01-poses.sh` and `02-train.sh` log the machine's power draw while they run and
print a summary when they finish. Each run writes a new `logs/power-*.csv` in
the scan folder. To log any other command, such as the quick Brush splat, wrap
it:

```bash
bash pipeline/powerlog.sh run $S/logs/power-brush.csv brush $S --total-steps 5000 --export-every 5000 --export-path $S/brush
```

Everything logged so far, added up in one table:

```bash
bash pipeline/powerlog.sh summary ~/sshah_workspace/projects/*/logs/power-*.csv
```

What the numbers are:

- **Graphics cards: measured**, from `nvidia-smi` every 5 seconds (good to
  about 5 W per card).
- **CPU: estimated** from how busy it was, unless the processor's own energy
  counter is readable (normally root only), in which case it is measured.
- **At the wall: an estimate.** It adds assumed figures for the rest of the
  machine and for power-supply losses; they are listed at the top of
  `powerlog.sh`. A plug-in meter is the only real check.
- Only the time a script or wrapped command runs is logged, not the idle time
  in between, and the readings include anyone else's work on the machine.

Added on 2026-11-12 while this machine was switched off. It was tested on the
Mac with stand-ins for `nvidia-smi`, COLMAP and the trainer; it has not run
against the real cards yet.

## Check the poses before training

COLMAP reporting "all photos registered" is not proof that the poses are right.
Before the long training run:

1. Look at the quick Brush splat. Doubled or ghosted structure means bad poses.
2. After training, read the score line in `logs/5-gsplat.log` and open a few
   images in `gsplat/renders/` (real photo on the left, render on the right).

On the test below, wrong poses gave PSNR 16.5 and visible ghosts; correct poses
gave 22.5 and renders that match the photos.

`01-poses.sh` uses COLMAP's incremental mapper. `MAPPER=global` selects the
faster global mapper, which is what went wrong in the test. Scenes with
repeated, similar-looking parts are the risk.

## Test run, 2026-11-11

South Building sample from the COLMAP project: 128 photos, 3072 x 2304
(`test-south-building/`). It ships with a reference reconstruction, which is
what the poses were checked against (`compare/compare_poses.py`).

| Step | Time | Notes |
| --- | --- | --- |
| Feature extraction | 8 s | both GPUs |
| Exhaustive matching | 122 s | both GPUs, 8,128 photo pairs |
| Mapping, global mapper | 130 s | **wrong:** 53 of 128 cameras misplaced |
| Mapping, incremental mapper | 226 s | 128 of 128 match the reference (max error 0.03% of the camera path) |
| Brush, 5,000 steps | 234 s | 271,000 splats, about 2 GB of GPU memory |
| gsplat MCMC, 30,000 steps | 30 min | 2,000,000 splats, photos at half size, 4.2 GB of GPU memory, 472 MB `.ply` |
| Copy `.ply` to the Mac | 1 min 42 s | over Tailscale |
| Convert to web format (on the Mac) | 7 min | 68 MB, four detail levels |

Held-out photos (16 of the 128, never used for training): PSNR 22.5, SSIM 0.82,
LPIPS 0.17. Loaded in the website prototype at 60 fps on the Mac.

`test-south-building/rejected-global-mapper/` keeps the bad run for comparison.
It can be deleted.

Power was not logged during this test. Worked out afterwards from the run
times and the parts' rated power: about 0.76 kWh for the 4.3 hours the machine
was on (somewhere between 0.6 and 0.96), of which about 0.33 kWh was caused by
the jobs and the rest was the machine idling.

### What this suggests for a 400-700 photo scan (estimates, not measured)

- Matching grows with the square of the photo count: roughly 30 min for 500
  photos and 60 min for 700.
- Incremental mapping grows faster than the photo count; expect somewhere
  between half an hour and a few hours on this CPU.
- Training time depends on steps and photo size, not much on photo count:
  about 30-40 min.
- GPU memory was not close to the TITAN V's 12 GB at 2,000,000 splats.
