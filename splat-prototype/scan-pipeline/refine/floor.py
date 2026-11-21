"""Heights of a dense cloud in the levelled frame: find the floor and the display's box.
   python floor.py <data-dir> <fused.ply> level.json <out-prefix>
Writes <out-prefix>.json (levelled points' height histogram, percentiles) and
<out-prefix>-side.png / -front.png / -top.png point plots in the levelled frame."""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.environ["GSPLAT_EXAMPLES"]); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from datasets.colmap import Parser  # noqa
from prep_depth import read_fused  # noqa

data_dir, fused, lvl, out = sys.argv[1:5]
p = Parser(data_dir, factor=2, normalize=True, test_every=8)
L = np.array(json.load(open(lvl))["R_level"])
P, rgb = read_fused(fused)
T = p.transform
Q = (L @ ((T[:3, :3] @ P.T).T + T[:3, 3]).T).T          # levelled, normalised scale
cams = (L @ p.camtoworlds[:, :3, 3].T).T
def plot(i, j, lo, hi, px, name, marks=()):
    Wd, Ht = int((hi[0] - lo[0]) * px), int((hi[1] - lo[1]) * px)
    img = np.full((Ht, Wd, 3), 255, np.uint8)
    x = ((Q[:, i] - lo[0]) * px).astype(int); y = (Ht - 1 - (Q[:, j] - lo[1]) * px).astype(int)
    k = (x >= 0) & (x < Wd) & (y >= 0) & (y < Ht); img[y[k], x[k]] = rgb[k]
    im = Image.fromarray(img); d = ImageDraw.Draw(im)
    for g in range(int(np.ceil(lo[0])), int(hi[0]) + 1):
        X = int((g - lo[0]) * px); d.line([(X, 0), (X, Ht)], fill=(200, 200, 255)); d.text((X + 2, Ht - 12), str(g), fill=(0, 0, 200))
    for g in range(int(np.ceil(lo[1])), int(hi[1]) + 1):
        Y = int(Ht - 1 - (g - lo[1]) * px); d.line([(0, Y), (Wd, Y)], fill=(200, 200, 255)); d.text((2, Y - 12), str(g), fill=(0, 0, 200))
    for c in cams:
        X = int((c[i] - lo[0]) * px); Y = int(Ht - 1 - (c[j] - lo[1]) * px); d.ellipse([X - 4, Y - 4, X + 4, Y + 4], outline=(255, 0, 0), width=2)
    im.save(f"{out}-{name}.png")
r = np.percentile(Q, [0.5, 99.5], axis=0)
lo = np.floor(np.minimum(r[0], cams.min(0)) - 0.5); hi = np.ceil(np.maximum(r[1], cams.max(0)) + 0.5)
plot(2, 1, (lo[2], lo[1]), (hi[2], hi[1]), 80, "side")
plot(0, 1, (lo[0], lo[1]), (hi[0], hi[1]), 80, "front")
plot(0, 2, (lo[0], lo[2]), (hi[0], hi[2]), 80, "top")
h, e = np.histogram(Q[:, 1], bins=80, range=(lo[1], hi[1]))
res = {"n": len(Q), "pct_xyz": {str(q): np.percentile(Q, q, axis=0).round(3).tolist() for q in [0.5, 1, 2, 5, 50, 95, 98, 99, 99.5]},
       "cams_y": cams[:, 1].round(3).tolist(), "cams": cams.round(3).tolist(), "names": p.image_names,
       "hist_y": list(zip(e[:-1].round(3).tolist(), h.tolist()))}
json.dump(res, open(f"{out}.json", "w"), indent=1)
print(json.dumps({k: res[k] for k in ["n", "pct_xyz", "cams_y"]}, indent=1))
