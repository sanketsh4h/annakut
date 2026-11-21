"""splat-v1: gsplat's simple_trainer with v1's additions, all switched by environment.

   HOLDOUT="IMG_1524.jpg,IMG_1526.jpg"  held-out photos, as v0's train_split.py ("" = all)
   DENSE=<npz from prep_depth.py>       MVS points: seed the splats, and (with --depth-loss)
                                        replace the 8.9k sparse points as the depth target
   INIT_PTS=400000                      MVS points used as starting splats
   DEPTH_PTS=150000                     MVS points per photo per step for the depth loss
   MASKS=<json>                         boxes (fractions of the photo) left out of the loss
   MONO=<npz from mono_depth.py>        optional: aligned monocular depth, used for the
                                        depth loss where MVS has no point (see mono_depth.py)

It runs tools/simple_trainer_v1.py, a copy of gsplat 1.5.3's simple_trainer.py with two
marked changes: masked pixels of the photo are replaced by the (detached) render before
the loss, so they neither pull nor push; and the depth loss skips points where the
rendered depth is under 0.01 or not finite (empty pixels made it NaN). Held-out scoring
is unchanged (whole photo).
"""
import json, os, runpy, sys
import numpy as np
import cv2
EX = os.environ["GSPLAT_EXAMPLES"]
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, EX)
import datasets.colmap as dc  # noqa: E402

hold = [h for h in os.environ.get("HOLDOUT", "").split(",") if h]
DENSE = os.environ.get("DENSE", "")
INIT_PTS = int(os.environ.get("INIT_PTS", "400000"))
DEPTH_PTS = int(os.environ.get("DEPTH_PTS", "150000"))
MASKS = json.load(open(os.environ["MASKS"])) if os.environ.get("MASKS") else {}
MONO = os.environ.get("MONO", "")
rng = np.random.default_rng(0)

_pinit = dc.Parser.__init__
def _parser_init(self, *a, **k):
    _pinit(self, *a, **k)
    self.dense = None
    if DENSE:
        d = np.load(DENSE)
        assert np.allclose(d["transform"], self.transform, atol=1e-6), "npz made with another normalisation"
        self.dense = {"points": d["points"].astype(np.float64),
                      "idx": {n: d[f"idx_{n}"] for n in self.image_names}}
        sel = rng.choice(len(d["points"]), min(INIT_PTS, len(d["points"])), replace=False)
        # keep COLMAP's sparse points too: where dense stereo failed (the left-front
        # trays with IMG_1524 held out) they are the only seeds and depth targets
        self.sparse_points, self.sparse_indices = self.points, self.point_indices
        self.points = np.concatenate([self.sparse_points, d["points"][sel].astype(np.float64)])
        self.points_rgb = np.concatenate([self.points_rgb, d["rgb"][sel]])
        print(f"[v1] {len(d['points']):,} MVS points; {len(sel):,} plus {len(self.sparse_points):,} sparse seed the splats", flush=True)
    # read fully now: a lazily opened npz breaks in forked data-loader workers
    self.mono = {k: v for k, v in np.load(MONO).items() if k.startswith("depth_")} if MONO else None
dc.Parser.__init__ = _parser_init

_dinit = dc.Dataset.__init__
def _dataset_init(self, parser, split="train", *a, **k):
    _dinit(self, parser, split, *a, **k)
    names = list(parser.image_names)
    assert all(h in names for h in hold), hold
    idx = np.arange(len(names)); test = np.array([n in hold for n in names])
    self.indices = idx if not hold else (idx[~test] if split == "train" else idx[test])
    print(f"[train_split] {split}: {[names[i] for i in self.indices]}", flush=True)
dc.Dataset.__init__ = _dataset_init

_getitem = dc.Dataset.__getitem__
def _getitem_v1(self, item):
    p = self.parser; index = self.indices[item]; name = p.image_names[index]
    use_dense = self.load_depths and p.dense is not None
    if use_dense:
        self.load_depths = False
    try:
        data = _getitem(self, item)
    finally:
        if use_dense:
            self.load_depths = True
    H, W = data["image"].shape[:2]
    if self.split == "train" and name in MASKS:
        cid = p.camera_ids[index]
        h0, w0 = p.mapx_dict[cid].shape if cid in p.mapx_dict else (H, W)
        m = np.ones((h0, w0), np.uint8)
        for x0, y0, x1, y1 in MASKS[name]:
            m[int(y0 * h0):int(np.ceil(y1 * h0)), int(x0 * w0):int(np.ceil(x1 * w0))] = 0
        if cid in p.mapx_dict:
            m = cv2.remap(m, p.mapx_dict[cid], p.mapy_dict[cid], cv2.INTER_NEAREST)
            x, y, w, h = p.roi_undist_dict[cid]; m = m[y:y + h, x:x + w]
        import torch
        data["lossmask"] = torch.from_numpy(m.astype(bool))
    if use_dense:
        import torch
        K = data["K"].numpy().astype(np.float64); c2w = data["camtoworld"].numpy().astype(np.float64)
        ids = p.dense["idx"][name]
        if len(ids) > DEPTH_PTS:
            ids = rng.choice(ids, DEPTH_PTS, replace=False)
        w2c = np.linalg.inv(c2w)
        pts = np.concatenate([p.dense["points"][ids], p.sparse_points[p.sparse_indices.get(name, np.zeros(0, int))]])
        pc = (w2c[:3, :3] @ pts.T).T + w2c[:3, 3]
        uv = (K @ pc.T).T; uv = uv[:, :2] / uv[:, 2:3]; z = pc[:, 2]
        ok = (uv[:, 0] >= 0) & (uv[:, 0] < W) & (uv[:, 1] >= 0) & (uv[:, 1] < H) & (z > 0)
        uv, z = uv[ok], z[ok]
        if p.mono is not None and f"depth_{name}" in p.mono:
            # aligned monocular depth where MVS has no point within 8 px
            md = p.mono[f"depth_{name}"]; mh, mw = md.shape
            have = np.zeros((mh, mw), bool)
            have[(uv[:, 1] * mh / H).astype(int).clip(0, mh - 1), (uv[:, 0] * mw / W).astype(int).clip(0, mw - 1)] = True
            have = cv2.dilate(have.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
            ys, xs = np.nonzero(~have & (md > 0))
            take = rng.choice(len(ys), min(len(ys), DEPTH_PTS // 3), replace=False) if len(ys) else []
            ys, xs = ys[take], xs[take]
            uv = np.concatenate([uv, np.stack([(xs + 0.5) * W / mw, (ys + 0.5) * H / mh], 1)])
            z = np.concatenate([z, md[ys, xs]])
        data["points"] = torch.from_numpy(uv).float()
        data["depths"] = torch.from_numpy(z).float()
    return data
dc.Dataset.__getitem__ = _getitem_v1

import torch, torch.utils.data as tud  # noqa: E402
torch.set_num_threads(2)
_DL = tud.DataLoader
class _CappedDL(_DL):
    def __init__(self, *a, **k):
        if k.get("num_workers", 0) > 2:
            k["num_workers"] = 2
        super().__init__(*a, **k)
tud.DataLoader = _CappedDL
torch.utils.data.DataLoader = _CappedDL
os.chdir(EX)
script = os.path.join(HERE, "simple_trainer_v1.py")
sys.argv = [script] + sys.argv[1:]
runpy.run_path(script, run_name="__main__")
