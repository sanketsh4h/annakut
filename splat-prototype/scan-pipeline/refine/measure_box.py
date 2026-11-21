"""Where does the display end and the noise begin? Measures a levelled splat.

   python measure_box.py <levelled.ply>                     density along each axis
   python measure_box.py <levelled.ply> --box x0,y0,z0,x1,y1,z1
                                                            count the splats outside a box

Works on the .ply that splat-transform writes after levelling; numbers are in the
viewer's frame (the file's x and y negated: ground y = 0, straight on looks toward -Z).

Without --box it prints, for x, y and z, how many "solid" splats (opacity over 0.5,
largest axis under 0.05 units: surfaces the photos saw clearly) fall in each 0.25-unit
slice, and the range where a slice holds at least --share (default 2%) of the fullest
slice. That range is a first guess at the display's box; read the table before trusting
it, because a wall or ceiling the photos saw well is solid too.

With --box it counts every splat outside the box, by side, and how many of those are
solid. Many splats but few solid ones on a side means haze and streaks; mostly solid
means the box cuts through something real (the 2025 display's table edge dips below
its box, for example).
"""
import argparse
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("inp")
ap.add_argument("--box", default="")
ap.add_argument("--share", type=float, default=0.02)
ap.add_argument("--slice", type=float, default=0.25)
a = ap.parse_args()

with open(a.inp, "rb") as f:
    header = []
    while True:
        l = f.readline(); header.append(l)
        if l.strip() == b"end_header": break
    props = [h.split()[2].decode() for h in header if h.startswith(b"property")]
    n = int([h for h in header if h.startswith(b"element vertex")][0].split()[2])
    v = np.frombuffer(f.read(n * 4 * len(props)), dtype=[(q, "<f4") for q in props], count=n)
P = np.stack([-v["x"], -v["y"], v["z"]], 1).astype(np.float64)       # viewer frame
op = 1 / (1 + np.exp(-v["opacity"].astype(np.float64)))
smax = np.exp(np.stack([v["scale_0"], v["scale_1"], v["scale_2"]], 1).astype(np.float64)).max(1)
solid = (op > 0.5) & (smax < 0.05)
print(f"{n:,} splats, {int(solid.sum()):,} solid")

if not a.box:
    guess = []
    for i, axis in enumerate("xyz"):
        q = P[solid][:, i]
        lo, hi = np.floor(q.min() / a.slice) * a.slice, np.ceil(q.max() / a.slice) * a.slice
        counts, edges = np.histogram(q, bins=int(round((hi - lo) / a.slice)), range=(lo, hi))
        full = np.flatnonzero(counts >= a.share * counts.max())
        guess += [edges[full[0]], edges[full[-1] + 1]]
        print(f"\n{axis}: slices holding at least {a.share:.0%} of the fullest run from {edges[full[0]]:g} to {edges[full[-1] + 1]:g}")
        for c, e in zip(counts, edges):
            if c:
                print(f"  {e:7.2f} {c:8,d} {'#' * int(round(50 * c / counts.max()))}")
    g = [guess[0], guess[2], guess[4], guess[1], guess[3], guess[5]]
    print("\nfirst guess: --box=" + ",".join(f"{x:g}" for x in g))
else:
    b = np.array([float(x) for x in a.box.split(",")])
    left = np.ones(n, bool); total = 0
    sides = [("below", P[:, 1] < b[1]), ("above", P[:, 1] > b[4]), ("left (x low)", P[:, 0] < b[0]),
             ("right (x high)", P[:, 0] > b[3]), ("behind (z low)", P[:, 2] < b[2]), ("in front (z high)", P[:, 2] > b[5])]
    for name, m in sides:                    # a splat outside on two sides counts for the first
        m = m & left; left &= ~m; total += int(m.sum())
        print(f"  {name:18s} {int(m.sum()):8,d}   solid {int((m & solid).sum()):7,d}")
    print(f"  {'outside in all':18s} {total:8,d} of {n:,}")
