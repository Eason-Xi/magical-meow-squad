"""把带光晕背景的精灵图抠成透明底，并按网格切成单个精灵。

思路：背景（含柔和光晕）是平滑渐变，精灵有深色描边形成强边缘。
先算梯度，把"低梯度且与图像边框连通"的区域判为背景；被精灵包围的
小块背景（如两腿之间）按颜色接近背景的程度额外剔除。
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi


def matte(rgb, edge_t, enclosed_fn=None):
    f = rgb.astype(np.float32)
    # 每个像素与右/下邻居的最大通道差，作为梯度
    gx = np.abs(np.diff(f, axis=1, append=f[:, -1:])).max(axis=2)
    gy = np.abs(np.diff(f, axis=0, append=f[-1:])).max(axis=2)
    grad = np.maximum(gx, gy)
    grad = np.maximum(grad, ndi.maximum_filter(grad, size=2))
    calm = grad < edge_t
    lab, n = ndi.label(calm)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    bg = np.isin(lab, list(border))
    if enclosed_fn is not None:
        sizes = ndi.sum(np.ones_like(lab), lab, index=np.arange(n + 1))
        means = [ndi.mean(f[..., c], lab, index=np.arange(n + 1)) for c in range(3)]
        extra = [i for i in range(1, n + 1)
                 if i not in border and sizes[i] > 30
                 and enclosed_fn(means[0][i], means[1][i], means[2][i])]
        if extra:
            bg |= np.isin(lab, extra)
    fg = ~bg
    # 去掉孤立噪点，再向内收 1px 去掉光晕残边
    fg = ndi.binary_opening(fg, iterations=1)
    fg = ndi.binary_erosion(fg, iterations=1)
    alpha = ndi.gaussian_filter(fg.astype(np.float32), 0.6)
    alpha = np.clip((alpha - 0.15) / 0.7, 0, 1)
    return fg, alpha


def cut(src, out_dir, rows, cols, names, edge_t, target_h, enclosed_fn=None, scale_by=None):
    rgb = np.asarray(Image.open(src).convert("RGB"))
    H, W, _ = rgb.shape
    fg, alpha = matte(rgb, edge_t, enclosed_fn)
    lab, n = ndi.label(fg)
    objs = ndi.find_objects(lab)
    sizes = ndi.sum(fg, lab, index=np.arange(1, n + 1))
    cells = {}
    for i, sl in enumerate(objs):
        if sizes[i] < 400:
            continue
        cy = (sl[0].start + sl[0].stop) / 2
        cx = (sl[1].start + sl[1].stop) / 2
        key = (min(int(cy / (H / rows)), rows - 1), min(int(cx / (W / cols)), cols - 1))
        cells.setdefault(key, []).append(i + 1)
    rgba = np.dstack([rgb, (alpha * 255).astype(np.uint8)])
    meta = {}
    crops = {}
    for r in range(rows):
        for c in range(cols):
            name = names[r][c]
            if not name or (r, c) not in cells:
                continue
            m = np.isin(lab, cells[(r, c)])
            m = ndi.binary_dilation(m, iterations=2)
            ys, xs = np.where(m)
            y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
            piece = rgba[y0:y1, x0:x1].copy()
            piece[..., 3] = (piece[..., 3] * m[y0:y1, x0:x1]).astype(np.uint8)
            crops[name] = piece
    # 同一张表内统一缩放比例，保证角色各姿势大小一致
    ref_h = max(p.shape[0] for k, p in crops.items() if scale_by is None or k in scale_by)
    s = target_h / ref_h
    for name, piece in crops.items():
        im = Image.fromarray(piece, "RGBA")
        w, h = max(1, round(im.width * s)), max(1, round(im.height * s))
        im = im.resize((w, h), Image.LANCZOS)
        im.save(Path(out_dir) / f"{name}.png", optimize=True)
        meta[name] = [w, h]
    return meta


if __name__ == "__main__":
    raw = Path(sys.argv[1])
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    greenish = lambda r, g, b: g > r + 12 and g > b + 12
    meta = {}
    meta.update(cut(raw / "girl_sheet.png", out, 2, 4,
                    [["run1", "run2", "run3", "run4"], ["jump", "fall", "hurt", "win"]],
                    edge_t=16, target_h=200, enclosed_fn=greenish,
                    scale_by={"run1", "run2", "run3", "run4"}))
    meta.update(cut(raw / "mobs_sheet.png", out, 2, 3,
                    [["jelly", "pudding", "king"], ["cat_idle", "cat_cheer", "cat_worry"]],
                    edge_t=16, target_h=240, scale_by={"king"}))
    print(json.dumps(meta, ensure_ascii=False))
