# Splat scanning environment

Tools for turning photos into a Gaussian splat on this machine (TITAN V 12 GB +
GTX 1080 8 GB). Everything lives in this folder. Nothing was installed
system-wide and nothing needed sudo; deleting the folder removes it all.

## Use it

```bash
source ~/sshah_workspace/env/activate.sh
```

That puts `colmap`, `brush`, `python` (3.12 with PyTorch and gsplat) on the
PATH for the current shell.

## What is installed

| Tool | Version | Where | Runs on |
| --- | --- | --- | --- |
| COLMAP | 4.2.1, CUDA build | `splat/` (conda-forge) | both cards |
| PyTorch | 2.14.1 + cu126 | `splat/` (pip) | both cards |
| gsplat | 1.5.3, built here | `src/gsplat` -> `splat/` | TITAN V only |
| fused-ssim, fused-bilagrid | pinned commits, built here | `splat/` | TITAN V only |
| Brush | 0.3.0 release binary | `brush/` | TITAN V by default |
| CUDA compiler | 12.9 | `splat/` | - |

The gsplat trainer scripts are in `src/gsplat/examples` (`$GSPLAT_EXAMPLES`
after activating).

## Things to know

- **Use CUDA 12, not 13.** CUDA 13 dropped both of these cards. PyTorch 2.14
  with cu126 is the last PyTorch that ships builds for them, so do not
  `pip install -U torch` in this environment. `setup/constraints.txt` pins it.
- **gsplat runs on the TITAN V only.** Its GPU code uses a CUDA feature that
  needs compute capability 7.0; the GTX 1080 is 6.1. Train with
  `CUDA_VISIBLE_DEVICES=0`. `activate.sh` sets `TORCH_CUDA_ARCH_LIST=7.0` for
  the same reason.
- **One local patch to gsplat.** `src/gsplat/setup.py` compiles with
  `-std=c++20` instead of `-std=c++17`, because PyTorch 2.14's headers need
  C++20. `setup/02-install-torch-gsplat.sh` applies it.
- **Brush** is started through the `brush/brush` wrapper, which points Vulkan
  at the NVIDIA driver. Without it Brush may pick a software renderer.

## Check that it works

```bash
bash ~/sshah_workspace/env/setup/verify.sh
```

Takes about a minute and needs no photos. It runs PyTorch on both cards,
renders and backpropagates with gsplat, loads the trainer script, runs COLMAP
feature extraction and matching in GPU and CPU mode, and trains a tiny scene
with Brush. Last run: 2026-11-11, 6 of 6 passed (`logs/verify.log`).

A full run on real photos (COLMAP poses, Brush, gsplat training) was done on
2026-11-11 with the scripts in `~/sshah_workspace/projects/pipeline/`. See the
README there for the steps, timings and one pitfall with COLMAP's global
mapper.

## Rebuild from scratch

```bash
bash setup/01-create-env.sh              # micromamba env: COLMAP, CUDA compiler
bash setup/02-install-torch-gsplat.sh    # PyTorch, gsplat, trainer packages
```

Brush is not scripted: it is the `brush-app-x86_64-unknown-linux-gnu` archive
from the v0.3.0 release at https://github.com/ArthurBrussee/brush/releases,
unpacked into `brush/`, plus the small `brush/brush` wrapper.

## Layout

```
activate.sh     source this
splat/          the conda environment (15 GB)
micromamba/     the package manager that created it
src/gsplat/     gsplat 1.5.3 source and trainer scripts
brush/          Brush binary and wrapper
setup/          install and verify scripts
logs/           install and verify logs
cache/          pip / torch caches and verify scratch files (safe to delete)
```
