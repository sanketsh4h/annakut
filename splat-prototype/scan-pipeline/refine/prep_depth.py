"""Turn a COLMAP fused cloud into depth targets in gsplat's own frame.

   python prep_depth.py <data-dir> <fused.ply> <out.npz>

Loads gsplat's Parser exactly as the trainer does (factor 2, normalised world), moves
the fused points into that frame, and for every photo keeps only the points that
photo can see: each point is projected, and a point survives if it is within 2% of
the nearest point in its 4x4-pixel cell (a z-buffer, so surfaces hidden behind
nearer ones are dropped). Saves the points, their colours, and per-photo indices.
"""
import os, sys
import numpy as np
sys.path.insert(0, os.environ["GSPLAT_EXAMPLES"])
from datasets.colmap import Parser  # noqa: E402

def read_fused(path):
    with open(path, "rb") as f:
        props, n = [], 0
        while True:
            l = f.readline().decode().strip()
            if l.startswith("element vertex"): n = int(l.split()[2])
            elif l.startswith("property"):
                t, name = l.split()[1:3]
                props.append((name, {"float": "<f4", "uchar": "u1", "double": "<f8"}[t]))
            elif l == "end_header": break
        v = np.frombuffer(f.read(), dtype=props, count=n)
    return np.stack([v["x"], v["y"], v["z"]], 1).astype(np.float64), np.stack([v["red"], v["green"], v["blue"]], 1)

if __name__ == "__main__":
    data_dir, fused, out = sys.argv[1:4]
    p = Parser(data_dir, factor=2, normalize=True, test_every=8)
    P, rgb = read_fused(fused)
    T = p.transform
    Pn = (T[:3, :3] @ P.T).T + T[:3, 3]
    print(f"{len(Pn):,} fused points; scene_scale {p.scene_scale:.3f}")
    CELL, TOL = 4, 0.02
    per = {}
    for i, name in enumerate(p.image_names):
        cid = p.camera_ids[i]; K = p.Ks_dict[cid]; W, H = p.imsize_dict[cid]
        w2c = np.linalg.inv(p.camtoworlds[i])
        pc = (w2c[:3, :3] @ Pn.T).T + w2c[:3, 3]
        z = pc[:, 2]; front = z > 1e-3
        uv = (K @ pc[front].T).T; uv = uv[:, :2] / uv[:, 2:3]
        idx = np.nonzero(front)[0]
        ok = (uv[:, 0] >= 0) & (uv[:, 0] < W) & (uv[:, 1] >= 0) & (uv[:, 1] < H)
        idx, uv = idx[ok], uv[ok]
        cx = (uv[:, 0] // CELL).astype(np.int64); cy = (uv[:, 1] // CELL).astype(np.int64)
        cell = cy * (W // CELL + 1) + cx
        zmin = np.full(cell.max() + 1, np.inf); np.minimum.at(zmin, cell, z[idx])
        keep = z[idx] <= zmin[cell] * (1 + TOL)
        per[name] = idx[keep].astype(np.int32)
        cover = len(np.unique(cell[keep])) / ((W // CELL) * (H // CELL))
        print(f"{name}: {ok.sum():>9,} in view, {keep.sum():>9,} visible, covers {cover:5.1%} of the photo")
    np.savez_compressed(out, points=Pn.astype(np.float32), rgb=rgb, transform=T,
                        names=np.array(p.image_names), **{f"idx_{k}": v for k, v in per.items()})
    print("saved", out)
