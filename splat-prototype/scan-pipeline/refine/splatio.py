"""Load a gsplat .ply (or a trainer checkpoint) onto the GPU (means, quats, scales, opacities, SH)."""
import numpy as np, torch

def load_ckpt(path):
    """A simple_trainer checkpoint (ckpts/ckpt_*.pt), for runs that saved no .ply."""
    sp = torch.load(path, map_location="cuda", weights_only=False)["splats"]
    return dict(means=sp["means"], quats=sp["quats"], scales=torch.exp(sp["scales"]),
                opac=torch.sigmoid(sp["opacities"]), sh=torch.cat([sp["sh0"], sp["shN"]], 1))

def load_ply(path):
    if path.endswith(".pt"): return load_ckpt(path)
    with open(path, "rb") as f:
        props, n = [], 0
        while True:
            l = f.readline().decode().strip()
            if l.startswith("element vertex"): n = int(l.split()[2])
            elif l.startswith("property"): props.append((l.split()[2], "<f4"))
            elif l == "end_header": break
        v = np.frombuffer(f.read(n * 4 * len(props)), dtype=props, count=n)
    g = lambda *k: torch.tensor(np.stack([v[x] for x in k], 1).copy(), device="cuda")
    rest = sorted([p[0] for p in props if p[0].startswith("f_rest_")], key=lambda s: int(s[7:]))
    sh0 = g("f_dc_0", "f_dc_1", "f_dc_2")[:, None]
    shN = g(*rest).reshape(n, 3, -1).transpose(1, 2) if rest else None
    return dict(means=g("x", "y", "z"), quats=g("rot_0", "rot_1", "rot_2", "rot_3"),
                scales=torch.exp(g("scale_0", "scale_1", "scale_2")),
                opac=torch.sigmoid(g("opacity")[:, 0]),
                sh=torch.cat([sh0, shN], 1) if shN is not None else sh0)
