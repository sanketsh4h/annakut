"""Monocular depth (Depth-Anything-V2-Small) aligned to the dense-stereo points.

   python mono_depth.py <data-dir> <depth.npz from prep_depth.py> <out.npz>

For each photo (undistorted exactly as the trainer sees it) the model gives relative
inverse depth. It is fitted to that photo's own MVS points (from the same npz, so a
held-out run never sees depth made with its held-out photos) as 1/z = a*d + b, by
least squares with two rounds of dropping the worst 20%. Pixels where a*d + b is not
positive, or the depth is beyond 4x the farthest MVS point, are left empty (0).
Saved at a quarter of the training resolution as depth_<photo>; the per-photo fit
error is printed and stored. v1_train.py uses it only where MVS has no point.
"""
import json, os, sys
import numpy as np, torch
sys.path.insert(0, os.environ["GSPLAT_EXAMPLES"])
from datasets.colmap import Parser, Dataset  # noqa
from transformers import AutoImageProcessor, AutoModelForDepthEstimation

data_dir, dense_npz, out = sys.argv[1:4]
p = Parser(data_dir, factor=2, normalize=True, test_every=8)
ds = Dataset(p, split="val"); ds.indices = np.arange(len(p.image_names))
D = np.load(dense_npz); P = D["points"].astype(np.float64)
mid = "depth-anything/Depth-Anything-V2-Small-hf"
proc = AutoImageProcessor.from_pretrained(mid); model = AutoModelForDepthEstimation.from_pretrained(mid).cuda().eval()
res, report = {}, {}
for k, name in enumerate(p.image_names):
    d = ds[k]; img = d["image"].numpy().astype(np.uint8); H, W = img.shape[:2]
    with torch.no_grad():
        inp = proc(images=img, return_tensors="pt").to("cuda")
        pred = model(**inp).predicted_depth[None]          # relative inverse depth
        h4, w4 = H // 4, W // 4
        rel = torch.nn.functional.interpolate(pred, size=(h4, w4), mode="bilinear", align_corners=False)[0, 0].cpu().numpy()
    K = d["K"].numpy().astype(np.float64); w2c = np.linalg.inv(d["camtoworld"].numpy().astype(np.float64))
    pc = (w2c[:3, :3] @ P[D[f"idx_{name}"]].T).T + w2c[:3, 3]
    uv = (K @ pc.T).T; uv = uv[:, :2] / uv[:, 2:3]; z = pc[:, 2]
    u4 = (uv[:, 0] / 4).astype(int); v4 = (uv[:, 1] / 4).astype(int)
    ok = (u4 >= 0) & (u4 < w4) & (v4 >= 0) & (v4 < h4) & (z > 0)
    u4, v4, z = u4[ok], v4[ok], z[ok]
    # one target per cell: median MVS inverse depth
    cell = v4 * w4 + u4; order = np.argsort(cell); cell, inv = cell[order], 1 / z[order]
    uniq, start = np.unique(cell, return_index=True)
    inv_c = np.array([np.median(a) for a in np.split(inv, start[1:])]); rel_c = rel.reshape(-1)[uniq]
    sel = np.ones(len(uniq), bool)
    for _ in range(3):
        A = np.c_[rel_c[sel], np.ones(sel.sum())]; (a, b), *_ = np.linalg.lstsq(A, inv_c[sel], rcond=None)
        err = np.abs(a * rel_c + b - inv_c) / inv_c
        sel = err <= np.quantile(err[sel], 0.8)
    pred_inv = a * rel + b
    zmax = 4 / inv_c.min()
    depth = np.where(pred_inv > 0, 1 / np.maximum(pred_inv, 1e-9), 0); depth[depth > zmax] = 0
    med = float(np.median(err)); report[name] = {"a": float(a), "b": float(b), "median_rel_err": med,
                                                  "mvs_cells": int(len(uniq)), "filled": float((depth > 0).mean())}
    res[f"depth_{name}"] = depth.astype(np.float32)
    print(f"{name}: fit on {len(uniq):6d} cells, median relative error {med:.1%}, filled {(depth > 0).mean():.0%}", flush=True)
np.savez_compressed(out, report=json.dumps(report), **res)
print("saved", out)
