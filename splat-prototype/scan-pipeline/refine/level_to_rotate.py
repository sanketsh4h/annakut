"""Turn level.py's result into the settings splat-transform needs to level a trained splat.

   python level_to_rotate.py level.json [--centre-x 0.75] [--ground -1.6] [--centre-z 0]

level.json holds R_level, the rotation from gsplat's normalised frame to a levelled one
(+Y up, audience on +Z). The website's frame is that frame moved so the display's middle
is at x = 0 and the floor at y = 0:

   viewer = R_level @ point + translate,   translate = (-centre_x, -ground, -centre_z)

--centre-x, --ground and --centre-z are read off the levelled model (floor.py plots it):
the x of the display's middle, the height of the floor, and (optionally) a z to move to 0.

splat-transform reads and writes a .ply turned 180 degrees about Z from the frame its
-r and -t work in, so the rotation to give it is R_level @ diag(-1, -1, 1), as Euler
angles in degrees with R = Rz(c) @ Ry(b) @ Rx(a). The translate is given as it is.
Written 2026-11-20 and checked against the 2025 Annakut's saved values: its level.json
gives -r 47.1311,-43.2295,-149.6335, and its levelled .ply matches R_level and
-t -0.75,1.6,0 in this form.
"""
import argparse, json
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("level")
ap.add_argument("--centre-x", type=float, default=0.0)
ap.add_argument("--ground", type=float, default=0.0)
ap.add_argument("--centre-z", type=float, default=0.0)
a = ap.parse_args()

R = np.array(json.load(open(a.level))["R_level"]) @ np.diag([-1.0, -1.0, 1.0])
b = -np.arcsin(np.clip(R[2, 0], -1, 1))
x = np.arctan2(R[2, 1], R[2, 2])
c = np.arctan2(R[1, 0], R[0, 0])
rotate = ",".join(f"{np.degrees(v):.4f}" for v in (x, b, c))
translate = ",".join(f"{v + 0.0:g}" for v in (-a.centre_x, -a.ground, -a.centre_z))
print(json.dumps({"rotate": rotate, "translate": translate}))
print(f"node_modules/.bin/splat-transform -w model.ply -r {rotate} -t {translate} level.ply")
