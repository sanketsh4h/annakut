#!/usr/bin/env python3
"""Stage 1 from video: turn a walk-round video (plus a few still photos) into
the photo set the rest of the pipeline expects.

    python3 scan-pipeline/video_to_frames.py OUT VIDEO [VIDEO ...] --stills DIR

What it does:

  1. Reads every video once at --analysis-fps and gives each frame a sharpness
     score and a measure of how far the picture moved since the frame before.
  2. Cuts each video into stretches of equal movement (not equal time) and
     keeps the sharpest frame of each stretch. Standing still adds no frames;
     walking faster adds more.
  3. Writes those frames as JPEGs at full size.
  4. Reads the gravity vector from each still photo, then crops and resizes the
     still to the video's shape so every image in the scan has one size.

It writes, ready to copy to the scan folder on the gpu machine:

  OUT/images/           v01_000123.jpg ... (video frames), still_IMG_1234.jpg ...
  OUT/groups/*.txt      which images share a camera (01-poses.sh reads these)
  OUT/extra-pairs.txt   each still paired with every image (01-poses.sh, MATCHER=sequential)
  OUT/gravity.json      gravity per still, for refine/level.py
  OUT/frames.csv        every analysed frame: time, sharpness, movement, kept or not

Needs ffmpeg and ffprobe on the PATH (Mac: brew install ffmpeg), numpy and
Pillow. HEIC stills are converted with macOS's sips.

--dry-run does steps 1 and 2 only and prints the report: a quick check, on
site, of whether a video is usable.
"""
import argparse
import csv
import json
import os
import platform
import shutil
import struct
import subprocess
import sys
import tempfile
import time

import numpy as np
from PIL import Image

THUMB_W = 320        # width of the picture used to measure movement
CHECK = (64, 36)     # tiny copy of each analysed frame, to verify the extraction
MIN_PEAK = 0.04      # phase-correlation peak below this: the shift is not trusted
DEADBAND = 0.0006    # movement per frame pair below this (0.2 px of THUMB_W) counts as none
MAX_PAIR = 0.25      # movement per frame pair is capped at this share of the width
SOFT_RATIO = 0.5     # a kept frame under this share of its neighbours' sharpness is "soft"
FAST_GAP = 0.30      # kept frames further apart than this share of the width: "fast"
HDR_TRANSFERS = {"arib-std-b67": "HLG", "smpte2084": "PQ"}


def die(msg):
    sys.exit("video_to_frames: " + msg)


def tool(name):
    path = shutil.which(name) or (f"/opt/homebrew/bin/{name}" if os.path.exists(f"/opt/homebrew/bin/{name}") else None)
    if not path:
        die(f"{name} not found. On the Mac: brew install ffmpeg")
    return path


def mmss(t):
    return f"{int(t // 60):02d}:{int(t % 60):02d}"


# ---------------------------------------------------------------- video ---

def probe(path):
    out = subprocess.run([tool("ffprobe"), "-v", "error", "-select_streams", "v:0",
                          "-show_streams", "-show_format", "-of", "json", path],
                         capture_output=True, text=True)
    if out.returncode != 0 or not json.loads(out.stdout or "{}").get("streams"):
        die(f"cannot read a video stream from {path}: {out.stderr.strip()}")
    info = json.loads(out.stdout)
    s = info["streams"][0]
    rot = 0
    for sd in s.get("side_data_list", []):
        if "rotation" in sd:
            rot = int(round(float(sd["rotation"])))
    if "rotate" in s.get("tags", {}):
        rot = int(s["tags"]["rotate"])
    w, h = int(s["width"]), int(s["height"])
    if abs(rot) % 180 == 90:  # ffmpeg turns the frames upright; this is the size it outputs
        w, h = h, w
    num, den = (s.get("avg_frame_rate") or "0/1").split("/")
    fps = float(num) / float(den) if float(den) else 0.0
    dur = float(s.get("duration") or info.get("format", {}).get("duration") or 0)
    return dict(path=path, name=os.path.basename(path), w=w, h=h, fps=fps, duration=dur,
                codec=s.get("codec_name", "?"), hdr=HDR_TRANSFERS.get(s.get("color_transfer", "")))


def read_frames(cmd, nbytes):
    """Run ffmpeg and yield its raw frames one buffer at a time."""
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        while True:
            buf = proc.stdout.read(nbytes)
            if len(buf) < nbytes:
                break
            yield buf
    finally:
        proc.stdout.close()
        err = proc.stderr.read().decode(errors="replace")
        proc.stderr.close()
        if proc.wait() != 0 and "videotoolbox" not in err.lower():
            die("ffmpeg failed while reading the video:\n" + err[-2000:])


def hwaccel():
    return ["-hwaccel", "videotoolbox"] if platform.system() == "Darwin" else []


def sharpness(g):
    """Variance of the Laplacian: high for crisp detail, low for blur."""
    a = g.astype(np.int16)
    lap = 4 * a[1:-1, 1:-1] - a[:-2, 1:-1] - a[2:, 1:-1] - a[1:-1, :-2] - a[1:-1, 2:]
    return float(lap.astype(np.float32).var())


class Shift:
    """How far the picture moved between two frames, as a share of its width.

    Phase correlation on a 2 x 2 grid of tiles. A sideways step moves all four
    tiles the same way; walking toward the display moves them apart. The median
    of the four distances covers both."""

    def __init__(self, th, tw):
        self.th, self.tw = th // 2, tw // 2
        self.full_w = tw
        self.win = np.outer(np.hanning(self.th), np.hanning(self.tw)).astype(np.float32)
        self.prev = None

    def _fft(self, thumb):
        out = []
        for y in (0, self.th):
            for x in (0, self.tw):
                t = thumb[y:y + self.th, x:x + self.tw]
                out.append(np.fft.rfft2((t - t.mean()) * self.win))
        return out

    def _peak(self, A, B):
        R = A * np.conj(B)
        R /= np.abs(R) + 1e-6
        r = np.fft.irfft2(R, s=(self.th, self.tw))
        py, px = np.unravel_index(int(np.argmax(r)), r.shape)
        c = r[py, px]

        def sub(lo, hi):  # parabola through the peak and its two neighbours
            d = lo - 2 * c + hi
            return 0.0 if abs(d) < 1e-9 else float(np.clip(0.5 * (lo - hi) / d, -0.5, 0.5))

        dy = py + sub(r[py - 1, px], r[(py + 1) % self.th, px])
        dx = px + sub(r[py, px - 1], r[py, (px + 1) % self.tw])
        if dy > self.th / 2:
            dy -= self.th
        if dx > self.tw / 2:
            dx -= self.tw
        return float(np.hypot(dx, dy)), float(c)

    def step(self, thumb):
        """Movement since the last call, or None when it could not be measured."""
        cur = self._fft(thumb)
        prev, self.prev = self.prev, cur
        if prev is None:
            return 0.0
        dists = [d for d, c in (self._peak(a, b) for a, b in zip(cur, prev)) if c >= MIN_PEAK]
        if len(dists) < 2:
            return None
        return float(np.median(dists)) / self.full_w


def analyse(clip, afps, score_w):
    """One pass over a video: sharpness, cumulative movement and a tiny copy per frame."""
    sw = min(score_w, clip["w"]) // 2 * 2
    sh = int(round(clip["h"] * sw / clip["w"])) // 2 * 2
    th = int(round(THUMB_W * sh / sw)) // 2 * 2
    vf = f"fps={afps:g},scale={sw}:{sh}:flags=area,format=gray"
    base = [tool("ffmpeg"), "-v", "error", "-nostdin"]
    tail = ["-i", clip["path"], "-an", "-sn", "-vf", vf, "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    sharp, motion, checks, unsure = [], [], [], 0
    t0 = time.time()
    for accel in ([hwaccel(), []] if hwaccel() else [[]]):
        shift, last, next_note = Shift(th, THUMB_W), 0.0, 0.1
        for buf in read_frames(base + accel + tail, sw * sh):
            g = np.frombuffer(buf, np.uint8).reshape(sh, sw)
            im = Image.fromarray(g)
            sharp.append(sharpness(g))
            m = shift.step(np.asarray(im.resize((THUMB_W, th), Image.BOX), np.float32))
            if m is None:  # nothing to lock on to (blur, blank wall): assume the pace held
                m, unsure = last, unsure + 1
            m = 0.0 if m < DEADBAND else min(m, MAX_PAIR)
            last = m
            motion.append(m)
            checks.append(np.asarray(im.resize(CHECK, Image.BOX)))
            done = len(sharp) / afps / clip["duration"] if clip["duration"] else 0
            if done >= next_note:
                print(f"    {min(done, 1):4.0%}  {time.time() - t0:5.0f} s", flush=True)
                next_note += 0.1
        if sharp:
            break
    if not sharp:
        die(f"no frames could be read from {clip['path']}")
    clip.update(sharp=np.array(sharp), travel=np.cumsum(motion), pair=np.array(motion),
                checks=np.stack(checks), unsure=unsure, afps=afps, seconds=time.time() - t0)


def choose(clips, count, min_step):
    """Per clip: equal-movement stretches, sharpest frame of each."""
    total = sum(float(c["travel"][-1]) for c in clips)
    if total <= 0:
        for c in clips:
            c["picks"] = np.array([int(np.argmax(c["sharp"]))])
        return 0.0, True
    step = total / count
    limited = step < min_step
    if limited:
        step = min_step
    for c in clips:
        length = float(c["travel"][-1])
        n = max(1, int(round(length / step)))
        bins = np.minimum((c["travel"] / (length / n if length else 1)).astype(int), n - 1)
        picks = []
        for b in np.unique(bins):
            idx = np.flatnonzero(bins == b)
            picks.append(int(idx[np.argmax(c["sharp"][idx])]))
        c["picks"] = np.array(sorted(picks))
    return step, limited


def stretches(times, gap):
    """Group times that are close together into (start, end, count) ranges."""
    out = []
    for t in times:
        if out and t - out[-1][1] <= gap:
            out[-1][1] = t
            out[-1][2] += 1
        else:
            out.append([t, t, 1])
    return out


def judge(clip):
    """Flag kept frames that are blurred next to their neighbours, and jumps."""
    p, s = clip["picks"], clip["sharp"]
    soft = np.zeros(len(p), bool)
    for k in range(len(p)):
        near = np.r_[s[p[max(0, k - 7):k]], s[p[k + 1:k + 8]]]
        soft[k] = len(near) >= 4 and s[p[k]] < SOFT_RATIO * np.median(near)
    clip["soft"] = soft
    gaps = np.diff(clip["travel"][p])
    clip["fast"] = [float(p[k + 1]) / clip["afps"] for k in np.flatnonzero(gaps > FAST_GAP)]
    clip["still_s"] = float((clip["pair"][1:] == 0).sum()) / clip["afps"]


def extract(clip, tag, out_images):
    """Second pass: write the chosen frames at full size."""
    picks = [int(n) for n in clip["picks"]]
    vf = f"fps={clip['afps']:g},select='" + "+".join(f"eq(n,{n})" for n in picks) + "',scale=out_range=pc:out_color_matrix=bt601"
    tmp = tempfile.mkdtemp(prefix="v2f-", dir=os.path.dirname(out_images))
    try:
        err = ""
        for accel in ([hwaccel(), []] if hwaccel() else [[]]):
            for sync in (["-fps_mode", "passthrough"], ["-vsync", "0"]):
                r = subprocess.run([tool("ffmpeg"), "-v", "error", "-nostdin", *accel, "-i", clip["path"],
                                    "-an", "-sn", "-vf", vf, *sync, "-q:v", "2",
                                    os.path.join(tmp, "%06d.jpg")], capture_output=True, text=True)
                err = r.stderr
                got = sorted(os.listdir(tmp))
                if r.returncode == 0 and len(got) == len(picks):
                    break
                for f in got:
                    os.remove(os.path.join(tmp, f))
                got = []
            if got:
                break
        if len(got) != len(picks):
            die(f"expected {len(picks)} frames from {clip['name']}, ffmpeg wrote {len(got)}:\n{err[-2000:]}")
        names = []
        for f, n in zip(got, picks):
            name = f"{tag}_{n:06d}.jpg"
            os.replace(os.path.join(tmp, f), os.path.join(out_images, name))
            names.append(name)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    # Verify: each written frame must look like the frame that was scored.
    wrong = 0
    for name, n in zip(names, picks):
        im = Image.open(os.path.join(out_images, name))
        im.draft("L", (CHECK[0] * 4, CHECK[1] * 4))
        a = np.asarray(im.convert("L").resize(CHECK, Image.BOX), np.float32).ravel()
        lo, hi = max(0, n - 2), min(len(clip["checks"]), n + 3)
        cc = [np.corrcoef(a, clip["checks"][j].astype(np.float32).ravel())[0, 1] for j in range(lo, hi)]
        cc = np.nan_to_num(np.array(cc))
        wrong += cc[n - lo] < 0.8 or cc.max() - cc[n - lo] > 0.02
    if wrong > max(1, len(picks) // 20):
        die(f"{wrong} of {len(picks)} frames written from {clip['name']} do not match the frames "
            "that were scored. The two passes over the video disagree; do not use this output.")
    clip["mismatch"] = wrong
    return names


# --------------------------------------------------------------- stills ---

def apple_gravity(makernote):
    """The iPhone's gravity vector (Apple MakerNote tag 8), as refine/gravity.py reads it."""
    mn = makernote
    if not mn or not mn.startswith(b"Apple iOS"):
        return None
    bo = ">" if mn[12:14] == b"MM" else "<"
    for i in range(struct.unpack(bo + "H", mn[14:16])[0]):
        tag, typ, cnt, off = struct.unpack(bo + "HHII", mn[16 + 12 * i:28 + 12 * i])
        if tag == 8 and typ == 10 and cnt == 3:
            v = struct.unpack(bo + "6i", mn[off:off + 24])
            return [v[0] / v[1], v[2] / v[3], v[4] / v[5]]
    return None


def list_stills(args):
    out = []
    for a in args:
        if os.path.isdir(a):
            out += [os.path.join(a, f) for f in sorted(os.listdir(a))
                    if f.lower().endswith((".jpg", ".jpeg", ".heic", ".heif")) and not f.startswith(".")]
        elif os.path.isfile(a):
            out.append(a)
        else:
            die(f"no such still photo or folder: {a}")
    return out


def add_stills(paths, out_images, w, h, tmpdir):
    """Crop and resize each still to w x h, and collect gravity and lens groups."""
    gravity, groups, notes = {}, {}, []
    for path in paths:
        stem = os.path.splitext(os.path.basename(path))[0]
        src = path
        if path.lower().endswith((".heic", ".heif")):
            if not shutil.which("sips"):
                die(f"{path} is HEIC and sips (macOS) is not here; convert the stills to JPEG first")
            src = os.path.join(tmpdir, stem + ".jpg")
            subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "95", path, "--out", src],
                           check=True, capture_output=True)
        im = Image.open(src)
        ex = im.getexif()
        ifd = ex.get_ifd(0x8769)
        orient = ex.get(0x0112, 1)
        if orient not in (1, 3) or im.width < im.height:
            notes.append(f"{os.path.basename(path)}: shot upright, left out (shoot stills in landscape)")
            continue
        g = apple_gravity(ifd.get(0x927C))
        im = im.convert("RGB")
        if orient == 3:
            # The phone was held the other way up. Turn the picture upright, as ffmpeg
            # does for the video, and turn the gravity vector with it: half a turn
            # about the lens axis (the phone's z) flips its x and y.
            im = im.rotate(180)
            if g:
                g = [-g[0], -g[1], g[2]]
        if im.width * h > im.height * w:  # still is wider than the video frame
            cw, ch = int(round(im.height * w / h)), im.height
        else:
            cw, ch = im.width, int(round(im.width * h / w))
        x0, y0 = (im.width - cw) // 2, (im.height - ch) // 2
        im = im.crop((x0, y0, x0 + cw, y0 + ch)).resize((w, h), Image.LANCZOS)
        name = f"still_{stem}.jpg"
        im.save(os.path.join(out_images, name), quality=95, subsampling=0)  # no EXIF: no GPS leaves the Mac
        f35 = ifd.get(0xA405)
        groups.setdefault(f"stills-{int(f35)}mm" if f35 else "stills", []).append(name)
        if g:
            gravity[name] = g
        else:
            notes.append(f"{os.path.basename(path)}: no gravity data (not an untouched iPhone photo); kept as a view only")
    return gravity, groups, notes


# ----------------------------------------------------------------- main ---

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out", help="output folder (must not already hold images)")
    ap.add_argument("videos", nargs="+", help="video files, in the order they were shot")
    ap.add_argument("--stills", nargs="+", default=[], metavar="PATH",
                    help="still photos (files or folders) taken in the same session, for gravity")
    ap.add_argument("--count", type=int, default=600, help="frames to keep across all videos (default 600)")
    ap.add_argument("--min-step", type=float, default=0.02,
                    help="never keep frames closer than this share of the frame width (default 0.02)")
    ap.add_argument("--analysis-fps", type=float, default=10, help="frames per second to score (default 10)")
    ap.add_argument("--score-width", type=int, default=1920, help="width frames are scored at (default 1920)")
    ap.add_argument("--camera-per-clip", action="store_true",
                    help="give each video its own camera (use when lens or zoom differs between videos)")
    ap.add_argument("--hdr", choices=["stop", "keep"], default="stop",
                    help="what to do with an HDR video: stop (default), or keep its flat colours")
    ap.add_argument("--dry-run", action="store_true", help="analyse and report only; write no images")
    a = ap.parse_args()

    images = os.path.join(a.out, "images")
    if not a.dry_run and os.path.isdir(images) and os.listdir(images):
        die(f"{images} already holds files. Choose a new output folder.")

    clips = [probe(v) for v in a.videos]
    shapes = {(c["w"], c["h"]) for c in clips}
    if len(shapes) > 1:
        die("the videos differ in shape (" + ", ".join(f"{c['name']} {c['w']}x{c['h']}" for c in clips)
            + "). The pipeline needs one shape for the whole scan.")
    w, h = shapes.pop()
    if w < h:
        die(f"{clips[0]['name']} is upright ({w}x{h}). Shoot in landscape.")
    for c in clips:
        if c["hdr"] and a.hdr == "stop":
            die(f"{c['name']} is HDR ({c['hdr']}). Its frames come out with flat, washed-out colours.\n"
                "  Best: record again with HDR video off (iPhone: Settings > Camera > Record Video).\n"
                "  Or pass --hdr keep to go on with the flat colours.")
    stills = list_stills(a.stills)

    for i, c in enumerate(clips, 1):
        afps = min(a.analysis_fps, c["fps"]) if c["fps"] else a.analysis_fps
        print(f"video {i}: {c['name']}  {c['w']}x{c['h']}  {c['fps']:.2f} fps  {c['codec']}  "
              f"{mmss(c['duration'])}  {c['hdr'] or 'SDR'}", flush=True)
        analyse(c, afps, a.score_width)
        print(f"    scored {len(c['sharp'])} frames in {c['seconds']:.0f} s", flush=True)

    step, limited = choose(clips, a.count, a.min_step)
    kept = sum(len(c["picks"]) for c in clips)
    print()
    if step == 0:
        print("WARNING: the camera never moved. One frame kept per video; this cannot make a 3D model.")
    else:
        print(f"keeping {kept} frames; neighbours share about {max(0, 1 - step):.0%} of the picture "
              f"(one frame every {step:.1%} of the frame width)")
        if limited:
            print(f"  fewer than the {a.count} asked for: the videos hold only this much movement "
                  f"at the closest spacing allowed (--min-step {a.min_step:g})")
        if step > 0.2:
            print(f"  WARNING: that is sparse. Raise --count to about {int(kept * step / 0.14)} "
                  "so neighbours share 85% or more.")
    for i, c in enumerate(clips, 1):
        judge(c)
        t = c["picks"] / c["afps"]
        print(f"video {i}: {len(c['picks'])} frames kept, {c['still_s']:.0f} s standing still skipped")
        soft = stretches(t[c["soft"]], 3.0)
        if soft:
            print(f"  soft ({int(c['soft'].sum())} kept frames are blurred next to their neighbours; "
                  "reshoot these stretches if they matter):")
            print("    " + ", ".join(f"{mmss(s)}-{mmss(e)} ({n})" if n > 1 else mmss(s) for s, e, n in soft))
        if c["fast"]:
            print("  fast (the picture jumped between kept frames; neighbours may not connect):")
            print("    " + ", ".join(mmss(x) for x in c["fast"]))
        if c["unsure"] > 0.1 * len(c["sharp"]):
            print(f"  note: movement could not be measured on {c['unsure']} of {len(c['sharp'])} frames "
                  "(blur or blank areas); spacing there follows the pace just before")

    if a.dry_run:
        print("\ndry run: nothing written")
        return

    os.makedirs(images, exist_ok=True)
    groups, rows = {}, []
    for i, c in enumerate(clips, 1):
        tag = f"v{i:02d}"
        print(f"writing frames of video {i} ...", flush=True)
        names = extract(c, tag, images)
        groups.setdefault(f"video-{tag}" if a.camera_per_clip else "video", []).extend(names)
        by_index = dict(zip((int(n) for n in c["picks"]), zip(names, c["soft"])))
        for n in range(len(c["sharp"])):
            name, soft = by_index.get(n, ("", False))
            rows.append([i, c["name"], n, f"{n / c['afps']:.2f}", f"{c['sharp'][n]:.1f}",
                         f"{c['travel'][n]:.4f}", name, int(bool(soft))])
    frame_names = [n for g in groups.values() for n in g]

    gravity, still_names = {}, []
    if stills:
        with tempfile.TemporaryDirectory() as tmp:
            gravity, sgroups, notes = add_stills(stills, images, w, h, tmp)
        groups.update(sgroups)
        still_names = [n for g in sgroups.values() for n in g]
        for n in notes:
            print("  " + n)

    with open(os.path.join(a.out, "frames.csv"), "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["video", "file", "index", "time_s", "sharpness", "travel", "kept_as", "soft"])
        wr.writerows(rows)
    gdir = os.path.join(a.out, "groups")
    shutil.rmtree(gdir, ignore_errors=True)
    for stale in ("extra-pairs.txt", "gravity.json"):
        if os.path.exists(os.path.join(a.out, stale)):
            os.remove(os.path.join(a.out, stale))
    if len(groups) > 1:
        os.makedirs(gdir)
        for key, names in groups.items():
            with open(os.path.join(gdir, key + ".txt"), "w") as f:
                f.write("\n".join(names) + "\n")
    if still_names:
        with open(os.path.join(a.out, "extra-pairs.txt"), "w") as f:
            for k, s in enumerate(still_names):
                for other in frame_names + still_names[k + 1:]:
                    f.write(f"{s} {other}\n")
    if gravity:
        with open(os.path.join(a.out, "gravity.json"), "w") as f:
            json.dump(gravity, f, indent=1)

    size = sum(os.path.getsize(os.path.join(images, n)) for n in os.listdir(images)) / 1e9
    print(f"\nwrote {len(frame_names)} frames and {len(still_names)} stills to {images} ({size:.1f} GB)")
    print(f"cameras: {', '.join(f'{k} ({len(v)})' for k, v in groups.items())}")
    if len(gravity) >= 3:
        print(f"gravity: {len(gravity)} stills -> gravity.json")
    else:
        print(f"WARNING: gravity from only {len(gravity)} stills. refine/level.py needs several that agree; "
              "without them, level with scan-pipeline/scene_frame.py (assumes the camera was held level).")
    print(f"\nnext:  rsync -a {a.out.rstrip('/')}/ gpu:sshah_workspace/projects/<scan>/\n"
          "       ssh gpu 'MATCHER=sequential bash ~/sshah_workspace/projects/pipeline/01-poses.sh "
          "~/sshah_workspace/projects/<scan>'")


if __name__ == "__main__":
    main()
