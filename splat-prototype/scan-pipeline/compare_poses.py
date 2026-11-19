"""Compares camera positions in two COLMAP text models of the same photos.

    python compare_poses.py <ours>/images.txt <reference>/images.txt

Fits the best scale / rotation / shift between the two (robustly), then reports
how many cameras land in the same place. Only useful when a trusted reference
exists, as it does for the South Building sample.
"""
import sys

import numpy as np


def load(path):
    out = {}
    with open(path) as f:
        lines = [l for l in f if not l.startswith("#")]
    for l in lines[0::2]:
        p = l.split()
        if len(p) < 10:
            continue
        qw, qx, qy, qz, tx, ty, tz = map(float, p[1:8])
        R = np.array([[1 - 2 * (qy * qy + qz * qz), 2 * (qx * qy - qz * qw), 2 * (qx * qz + qy * qw)],
                      [2 * (qx * qy + qz * qw), 1 - 2 * (qx * qx + qz * qz), 2 * (qy * qz - qx * qw)],
                      [2 * (qx * qz - qy * qw), 2 * (qy * qz + qx * qw), 1 - 2 * (qx * qx + qy * qy)]])
        out[p[9]] = (-R.T @ np.array([tx, ty, tz]), R.T[:, 2])  # centre, viewing direction
    return out


def umeyama(X, Y):
    mx, my = X.mean(0), Y.mean(0)
    Xc, Yc = X - mx, Y - my
    U, D, Vt = np.linalg.svd(Yc.T @ Xc / len(X))
    S = np.eye(3)
    if np.linalg.det(U) * np.linalg.det(Vt) < 0:
        S[2, 2] = -1
    R = U @ S @ Vt
    s = np.trace(np.diag(D) @ S) / Xc.var(0).sum()
    return s, R, my - s * R @ mx


a, b = load(sys.argv[1]), load(sys.argv[2])
names = sorted(set(a) & set(b))
A = np.array([a[n][0] for n in names]); B = np.array([b[n][0] for n in names])
dA = np.array([a[n][1] for n in names]); dB = np.array([b[n][1] for n in names])
rng = np.random.default_rng(0)
extent = np.linalg.norm(B.max(0) - B.min(0))
best = None
for _ in range(3000):
    i = rng.choice(len(names), 3, replace=False)
    s, R, t = umeyama(A[i], B[i])
    inl = np.linalg.norm((s * (R @ A.T).T + t) - B, axis=1) < 0.02 * extent
    if best is None or inl.sum() > best.sum():
        best = inl
s, R, t = umeyama(A[best], B[best])
err = np.linalg.norm((s * (R @ A.T).T + t) - B, axis=1) / extent * 100
ang = np.degrees(np.arccos(np.clip(np.sum((R @ dA.T).T * dB, axis=1), -1, 1)))
print(f"photos in both models: {len(names)}")
print(f"cameras within 2% of the reference position: {int((err < 2).sum())} of {len(names)}")
print(f"position error, % of camera path extent: median {np.median(err):.2f}, max {err.max():.2f}")
print(f"viewing direction error, degrees: median {np.median(ang):.2f}, max {ang.max():.2f}")
