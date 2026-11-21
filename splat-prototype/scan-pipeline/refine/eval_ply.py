"""Score a splat .ply on photos, the way simple_trainer's eval does.

   python eval_ply.py <data-dir> <ply> IMG_a.jpg [IMG_b.jpg ...] [--out dir]

Same cameras (gsplat Parser/Dataset: factor 2, undistorted), same renderer settings
(SH 3, classic rasterisation, near 0.01) and the same metrics (torchmetrics PSNR and
SSIM with data_range 1, LPIPS AlexNet with normalize=True) as the trainer, so a cleaned
or cropped model can be compared with the trainer's own held-out numbers.
"""
import json, os, sys
import numpy as np, torch
sys.path.insert(0, os.environ["GSPLAT_EXAMPLES"]); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from datasets.colmap import Parser, Dataset  # noqa
from torchmetrics.image import PeakSignalNoiseRatio, StructuralSimilarityIndexMeasure
from torchmetrics.image.lpip import LearnedPerceptualImagePatchSimilarity
from splatio import load_ply  # noqa
from gsplat import rasterization

args = sys.argv[1:]; out = None
if "--out" in args:
    i = args.index("--out"); out = args[i + 1]; del args[i:i + 2]
data_dir, ply, names = args[0], args[1], args[2:]
p = Parser(data_dir, factor=2, normalize=True, test_every=8)
ds = Dataset(p, split="val"); ds.indices = np.array([p.image_names.index(n) for n in names])
m = load_ply(ply); deg = int(np.sqrt(m["sh"].shape[1])) - 1
psnr = PeakSignalNoiseRatio(data_range=1.0).cuda(); ssim = StructuralSimilarityIndexMeasure(data_range=1.0).cuda()
lpips = LearnedPerceptualImagePatchSimilarity(net_type="alex", normalize=True).cuda()
res = {}
for k, n in enumerate(names):
    d = ds[k]; gt = d["image"].cuda()[None] / 255.0; Hh, Ww = gt.shape[1:3]
    vm = torch.linalg.inv(d["camtoworld"].cuda())[None]
    img, _, _ = rasterization(m["means"], m["quats"], m["scales"], m["opac"], m["sh"], vm, d["K"].cuda()[None], Ww, Hh,
                              sh_degree=deg, near_plane=0.01, far_plane=1e10, rasterize_mode="classic")
    img = img.clamp(0, 1); a, b = img.permute(0, 3, 1, 2), gt.permute(0, 3, 1, 2)
    res[n] = dict(psnr=psnr(a, b).item(), ssim=ssim(a, b).item(), lpips=lpips(a, b).item())
    if out:
        os.makedirs(out, exist_ok=True)
        import imageio.v2 as io
        io.imwrite(f"{out}/{n[:-4]}-photo-vs-render.jpg", (torch.cat([gt, img], 2)[0].cpu().numpy() * 255).astype(np.uint8), quality=90)
mean = {k: float(np.mean([r[k] for r in res.values()])) for k in ["psnr", "ssim", "lpips"]}
print(json.dumps({"ply": ply, "mean": mean, "per_photo": res}, indent=1))
