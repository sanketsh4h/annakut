"""Works out how to stand a trained splat upright for the website, and a
starting camera view.

    python scene_frame.py <scan-dir> [--raw]

COLMAP reconstructs a scene with an arbitrary tilt. This reads the camera poses,
takes "up" as the average of the cameras' own up directions (so it assumes most
photos were taken with the camera held level), and prints JSON with:

  rotate         Euler angles for `splat-transform -r`, which stand the splat upright
  initialCamera  a starting view (one of the real photo positions) for hotspots.json

By default it assumes the splat came from gsplat's simple_trainer.py, which
trains in a normalised copy of the COLMAP frame. Pass --raw for a splat trained
directly in the COLMAP frame (Brush).
"""
import contextlib
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.environ["GSPLAT_EXAMPLES"])
from datasets.colmap import Parser  # noqa: E402

scan = os.path.abspath(sys.argv[1])
raw = "--raw" in sys.argv[2:]
with contextlib.redirect_stdout(sys.stderr):  # the reader's own messages are not part of the JSON
    parser = Parser(data_dir=scan, factor=1, normalize=not raw, test_every=8)
c2w = np.asarray(parser.camtoworlds, dtype=np.float64)  # OpenCV: x right, y down, z forward
points = np.asarray(parser.points, dtype=np.float64)

# The website viewer shows splat data rotated half a turn about Z, and
# splat-transform's -r works in that displayed frame, so do the maths there.
FLIP = np.diag([-1.0, -1.0, 1.0])
centres = c2w[:, :3, 3] @ FLIP.T
ups = -c2w[:, :3, 1] @ FLIP.T
forwards = c2w[:, :3, 2] @ FLIP.T
pts = points @ FLIP.T


def unit(v):
    return v / np.linalg.norm(v)


up = unit(ups.mean(axis=0))
heading = forwards.mean(axis=0)
heading -= up * heading.dot(up)  # keep the horizontal part
if np.linalg.norm(heading) < 0.2:  # cameras circle the subject: any heading will do
    heading = np.cross(up, [1.0, 0.0, 0.0])
heading = unit(heading)
# New axes: Y is up, the average viewing direction runs along -Z.
z_axis = -heading
x_axis = unit(np.cross(up, z_axis))
R = np.stack([x_axis, up, z_axis])

# splat-transform composes its Euler angles as Rz @ Ry @ Rx.
ey = np.arcsin(np.clip(-R[2, 0], -1.0, 1.0))
ex = np.arctan2(R[2, 1], R[2, 2])
ez = np.arctan2(R[1, 0], R[0, 0])

centres, forwards, pts = centres @ R.T, forwards @ R.T, pts @ R.T
focus = np.median(pts, axis=0)
# Start from the real photo position nearest the middle of all camera positions.
pick = int(np.argmin(np.linalg.norm(centres - np.median(centres, axis=0), axis=1)))
position = centres[pick]
distance = max(float((focus - position).dot(forwards[pick])), 0.5)
target = position + forwards[pick] * distance

tilt = float(np.degrees(np.arccos(np.clip(up.dot([0.0, 1.0, 0.0]), -1.0, 1.0))))
spread = float(np.degrees(np.arccos(np.clip(ups @ up / np.linalg.norm(ups, axis=1), -1, 1))).mean())
print(json.dumps({
    "frame": "COLMAP (raw)" if raw else "gsplat normalised",
    "rotate": [round(float(np.degrees(a)), 3) for a in (ex, ey, ez)],
    "initialCamera": {
        "position": [round(float(v), 3) for v in position],
        "target": [round(float(v), 3) for v in target],
        "fov": 60,
    },
    "photos": int(len(c2w)),
    "tiltCorrectedDegrees": round(tilt, 1),
    "cameraUpSpreadDegrees": round(spread, 1),
    "sceneSize": [round(float(v), 2) for v in (np.percentile(pts, 95, axis=0) - np.percentile(pts, 5, axis=0))],
}, indent=2))
