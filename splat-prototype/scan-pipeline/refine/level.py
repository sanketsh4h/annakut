"""Find true 'up' in gsplat's normalised frame from the iPhone gravity vectors.

   python level.py <data-dir> gravity.json [out.json]

Each photo's Apple MakerNote holds the gravity direction in the phone's own axes.
The mapping from phone axes to the camera's (OpenCV: x right, y down, z forward)
is one of 48 signed axis permutations; the right one makes all 15 photos agree
on one world direction, so it is chosen by the smallest spread. Also gives the
audience's 'front' (mean camera viewing direction, made horizontal) and the
rotation that puts up on +Y and the audience on +Z.
"""
import itertools, json, os, sys
import numpy as np
sys.path.insert(0, os.environ["GSPLAT_EXAMPLES"])
from datasets.colmap import Parser  # noqa: E402

p = Parser(sys.argv[1], factor=2, normalize=True, test_every=8)
grav = json.load(open(sys.argv[2]))
names = [n for n in p.image_names if n in grav]
A = np.array([grav[n] for n in names]); A /= np.linalg.norm(A, axis=1, keepdims=True)
Rc2w = np.array([p.camtoworlds[p.image_names.index(n)][:3, :3] for n in names])
best = None
for perm in itertools.permutations(range(3)):
    for signs in itertools.product([1, -1], repeat=3):
        M = np.zeros((3, 3))
        for i, (j, s) in enumerate(zip(perm, signs)):
            M[i, j] = s  # camera axis i = s * phone axis j
        g = np.einsum("nij,jk,nk->ni", Rc2w, M, A)  # world gravity per photo
        mean = g.mean(0); mean /= np.linalg.norm(mean)
        spread = np.degrees(np.arccos(np.clip(g @ mean, -1, 1)))
        if best is None or spread.mean() < best[0]:
            best = (spread.mean(), M, mean, spread)
spr, M, down, spread = best
up = -down  # the vector points along gravity (down); flipped below if the cameras say otherwise
fwd = Rc2w[:, :, 2].mean(0)  # mean viewing direction
if up @ (-Rc2w[:, :, 1].mean(0)) < 0:  # camera 'up' (-y) should roughly agree with world up
    up = -up
f = fwd - (fwd @ up) * up; f /= np.linalg.norm(f)
# viewer-ready frame: +Y up, audience on +Z, i.e. looking toward -Z
y = up; z = -f; x = np.cross(y, z)
R = np.stack([x, y, z])  # rows: new axes in normalised coordinates
pitch = np.degrees(np.arcsin(np.clip(np.einsum("ni,i->n", Rc2w[:, :, 2], up), -1, 1)))
res = {"phone_to_camera": M.tolist(), "up_normalised": up.tolist(), "front_normalised": (-z).tolist(),
       "R_level": R.tolist(), "mean_spread_deg": float(spr),
       "per_photo_spread_deg": dict(zip(names, np.round(spread, 2).tolist())),
       "camera_pitch_deg": dict(zip(names, np.round(pitch, 1).tolist()))}
print(json.dumps(res, indent=1))
if len(sys.argv) > 3:
    json.dump(res, open(sys.argv[3], "w"), indent=1)
