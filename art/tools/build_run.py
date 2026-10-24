"""把 6 帧跑步循环原图做成游戏用精灵：抠图 → 按头部对齐 → 统一画布。

AI 生成的各帧头部大小、位置会有轻微漂移，直接播放会"抖头"。
这里用头发（粉色）像素的宽度统一缩放，用头发中心对齐，
再把所有帧放进同样大小的画布，并让最低的脚落在画布底边。

须在 cut_sprites.py 之后运行（会覆盖其输出的 run1~run4）：
    python3 art/tools/build_run.py art/raw/run_sheet.png demo/assets/sprites demo/assets/sprites/jump.png
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).parent))
from cut_sprites import matte  # noqa: E402


def hair_box(rgba):
    """头部区域（上 45%）里粉色头发像素的中心与宽度。"""
    a = rgba[..., 3] > 128
    r, g, b = (rgba[..., i].astype(int) for i in range(3))
    pink = a & (r > 200) & (r - g > 45) & (b > 120) & (b < 225)
    top = int(rgba.shape[0] * 0.45)
    pink[top:] = False
    ys, xs = np.where(pink)
    lo, hi = np.percentile(xs, [3, 97])
    return xs.mean(), ys.mean(), hi - lo


def main(raw, out, ref):
    rgb = np.asarray(Image.open(raw).convert("RGB"))
    H, W, _ = rgb.shape
    fg, alpha = matte(rgb, 16)
    lab, n = ndi.label(fg)
    sizes = ndi.sum(fg, lab, index=np.arange(1, n + 1))
    cells = {}
    for i, sl in enumerate(ndi.find_objects(lab)):
        if sizes[i] < 400:
            continue
        cy, cx = (sl[0].start + sl[0].stop) / 2, (sl[1].start + sl[1].stop) / 2
        cells.setdefault((int(cy / (H / 2)), int(cx / (W / 3))), []).append(i + 1)
    rgba = np.dstack([rgb, (alpha * 255).astype(np.uint8)])

    frames = []
    for r in range(2):
        for c in range(3):
            m = ndi.binary_dilation(np.isin(lab, cells[(r, c)]), iterations=2)
            ys, xs = np.where(m)
            y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
            piece = rgba[y0:y1, x0:x1].copy()
            piece[..., 3] = (piece[..., 3] * m[y0:y1, x0:x1]).astype(np.uint8)
            frames.append(piece)

    # 以现有跳跃帧的头宽为基准，保证跑/跳切换时人物大小不变
    _, _, ref_w = hair_box(np.asarray(Image.open(ref).convert("RGBA")))
    scaled = []
    for f in frames:
        _, _, hw = hair_box(f)
        k = ref_w / hw
        im = Image.fromarray(f, "RGBA")
        im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
        arr = np.asarray(im)
        hx, hy, _ = hair_box(arr)
        scaled.append((im, hx, hy))

    # 统一画布：头发中心对齐到同一点，最低的脚贴底
    left = max(hx for _, hx, _ in scaled)
    right = max(im.width - hx for im, hx, _ in scaled)
    up = max(hy for _, _, hy in scaled)
    down = max(im.height - hy for im, _, hy in scaled)
    cw, ch = int(np.ceil(left + right)) + 2, int(np.ceil(up + down)) + 2
    out = Path(out)
    for i, (im, hx, hy) in enumerate(scaled):
        canvas = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        canvas.alpha_composite(im, (int(round(left - hx)), int(round(up - hy))))
        canvas.save(out / f"run{i + 1}.png", optimize=True)
    print(f"6 帧，画布 {cw}x{ch}，头部锚点 ({left:.0f}, {up:.0f})")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
