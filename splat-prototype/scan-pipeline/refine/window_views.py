"""Render a splat .ply at the edges of the visitor's window, in the levelled frame.

   python window_views.py <data-dir> level.json <out-dir> <label>=<ply> [<label>=<ply> ...]

Views are set the way the viewer's orbit camera works: a focus point, a yaw round it
(0 = straight on from the audience, negative = visitor's left), an elevation above it
and a distance, with a 60-degree horizontal field of view. Writes one PNG per view and
model, and a sheet with one row per model. Also renders each training photo's own pose
next to the photo, for reference.
"""
import json, os, sys
import numpy as np, torch
from PIL import Image, ImageDraw
from gsplat import rasterization
sys.path.insert(0, os.environ["GSPLAT_EXAMPLES"])
from datasets.colmap import Parser  # noqa
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from splatio import load_ply  # noqa

data_dir, lvl, out = sys.argv[1:4]
models = [a.split("=", 1) for a in sys.argv[4:]]
os.makedirs(out, exist_ok=True)
L = np.array(json.load(open(lvl))["R_level"])           # normalised -> levelled
W, H, FOV = 960, 600, 60.0
# levelled coordinates (before the viewer's translation): display centre, table top
C = np.array([0.75, 1.6, -0.2]); TABLE = -0.78; FRONT = np.array([0.75, TABLE, 1.8])
VIEWS = [  # name, focus, yaw, elevation, distance
    ("start", C, 0, 15, 9.0),
    ("left75", C, -75, 15, 9.0), ("right75", C, 75, 15, 9.0),
    ("up75", C, 0, 75, 9.0), ("level-centre", C, 0, 0, 9.0),
    ("ground-front", FRONT, 0, 0, 5.0),
    ("left75-up45", C, -75, 45, 9.0), ("right75-up45", C, 75, 45, 9.0),
    ("left45", C, -45, 15, 9.0), ("right45", C, 45, 15, 9.0),
]

def render(m, c2w, K, w, h):
    sh = m["sh"]; deg = int(np.sqrt(sh.shape[1])) - 1
    viewmat = torch.tensor(np.linalg.inv(c2w), dtype=torch.float32, device="cuda")[None]
    Kt = torch.tensor(K, dtype=torch.float32, device="cuda")[None]
    img, alpha, _ = rasterization(m["means"], m["quats"], m["scales"], m["opac"], sh, viewmat, Kt, w, h, sh_degree=deg)
    return (img[0].clamp(0, 1).cpu().numpy() * 255).astype(np.uint8), float((alpha[0] < 0.5).float().mean())

def orbit_c2w(focus, yaw, elev, dist):
    # levelled frame: +Y up, audience on +Z. Camera position, looking at the focus.
    y, e = np.radians(yaw), np.radians(elev)
    off = dist * np.array([np.sin(y) * np.cos(e), np.sin(e), np.cos(y) * np.cos(e)])
    pos = focus + off; fwd = (focus - pos) / dist
    right = np.cross(fwd, [0, 1, 0]); right /= np.linalg.norm(right); down = np.cross(fwd, right)
    R_lv = np.stack([right, down, fwd], 1)            # OpenCV camera axes in levelled frame
    c2w = np.eye(4); c2w[:3, :3] = L.T @ R_lv; c2w[:3, 3] = L.T @ pos   # back to normalised
    return c2w

f = (W / 2) / np.tan(np.radians(FOV / 2)); K = np.array([[f, 0, W / 2], [0, f, H / 2], [0, 0, 1]])
p = Parser(data_dir, factor=2, normalize=True, test_every=8)
rows, stats = [], {}
for label, path in models:
    m = load_ply(path); tiles = []
    for name, focus, yaw, elev, dist in VIEWS:
        img, empty = render(m, orbit_c2w(focus, yaw, elev, dist), K, W, H)
        Image.fromarray(img).save(f"{out}/{label}-{name}.jpg", quality=90)
        stats[f"{label}/{name}"] = round(empty, 4); tiles.append((name, img))
    rows.append((label, tiles))
    del m; torch.cuda.empty_cache()
tw, th, COLS = W // 2, H // 2, 5
nr = (len(VIEWS) + COLS - 1) // COLS
sheet = Image.new("RGB", (tw * COLS, (th + 18) * nr * len(rows)), "black"); d = ImageDraw.Draw(sheet)
for r, (label, tiles) in enumerate(rows):
    for c, (name, img) in enumerate(tiles):
        x, y = (c % COLS) * tw, (r * nr + c // COLS) * (th + 18)
        sheet.paste(Image.fromarray(img).resize((tw, th)), (x, y + 18))
        d.text((x + 4, y + 3), f"{label}  {name}  empty {stats[f'{label}/{name}']:.0%}", fill=(255, 255, 0))
sheet.save(f"{out}/sheet.jpg", quality=88)
json.dump(stats, open(f"{out}/empty.json", "w"), indent=1)
print(json.dumps(stats, indent=1))
