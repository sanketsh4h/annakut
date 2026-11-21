"""Crop a gsplat .ply to the display and drop floaters, working in the levelled frame.

   python clean_ply.py <data-dir> level.json <in.ply> <out.ply> [--box x0,y0,z0,x1,y1,z1]
                       [--min-opacity 0.02] [--max-scale 0.6] [--max-ratio 40]

Box (levelled coordinates, before the viewer's translation) defaults to the display:
x -4.6..6.1, y -1.0..4.6, z -4.3..4.0 (a margin of about 1 unit round the dense
cloud's 0.5-99.5 percentile extent). Removes splats outside it, splats fainter than
--min-opacity, splats whose largest axis is over --max-scale units, and needles
(largest/smallest axis over --max-ratio while larger than 0.05 units).
--box none keeps everything; --shape-box limits the size and needle tests to a region.
Writes the same .ply format (still in gsplat's normalised frame).
"""
import argparse, json, os, sys
import numpy as np
ap = argparse.ArgumentParser()
ap.add_argument("data_dir"); ap.add_argument("level"); ap.add_argument("inp"); ap.add_argument("out")
ap.add_argument("--box", default="-4.6,-1.0,-4.3,6.1,4.6,4.0")
ap.add_argument("--min-opacity", type=float, default=0.02)
ap.add_argument("--max-scale", type=float, default=0.6)
ap.add_argument("--max-ratio", type=float, default=40)
ap.add_argument("--shape-box", default="", help="apply --max-scale/--max-ratio only inside this box "
                "(x0,y0,z0,x1,y1,z1, levelled); outside it only faint splats go")
a = ap.parse_args()
L = np.array(json.load(open(a.level))["R_level"])
with open(a.inp, "rb") as f:
    header = []
    while True:
        l = f.readline(); header.append(l)
        if l.strip() == b"end_header": break
    props = [h.split()[2].decode() for h in header if h.startswith(b"property")]
    n = int([h for h in header if h.startswith(b"element vertex")][0].split()[2])
    v = np.frombuffer(f.read(n * 4 * len(props)), dtype=[(p, "<f4") for p in props], count=n)
P = np.stack([v["x"], v["y"], v["z"]], 1) @ L.T
def within(box):
    if box in ("", "none"): return np.ones(len(P), bool)
    b = np.array([float(x) for x in box.split(",")]); return np.all((P >= b[:3]) & (P <= b[3:]), 1)
inbox = within(a.box)
shaped = within(a.shape_box)
op = 1 / (1 + np.exp(-v["opacity"]))
s = np.exp(np.stack([v["scale_0"], v["scale_1"], v["scale_2"]], 1)); smax, smin = s.max(1), s.min(1)
bad_shape = (smax > a.max_scale) | ((smax / np.maximum(smin, 1e-9) > a.max_ratio) & (smax > 0.05))
keep = inbox & (op >= a.min_opacity) & ~(bad_shape & shaped)
print(json.dumps({"in": n, "kept": int(keep.sum()), "outside_box": int((~inbox).sum()),
                  "faint": int((op < a.min_opacity).sum()), "too_big": int((smax > a.max_scale).sum()),
                  "needles": int(((smax / np.maximum(smin, 1e-9) > a.max_ratio) & (smax > 0.05)).sum())}))
hdr = b"".join(header).replace(f"element vertex {n}".encode(), f"element vertex {int(keep.sum())}".encode())
with open(a.out, "wb") as f:
    f.write(hdr); f.write(v[keep].tobytes())
