"""Generate the four original transparent PNG assets (Pillow + numpy; no matplotlib needed)."""
import math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = os.path.join(os.path.dirname(__file__), "..", "assets")
os.makedirs(OUT, exist_ok=True)
SS = 2  # supersample factor for smooth edges


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def blob_mask(w, h, seed, wobble):
    """Organic closed curve as an anti-aliased L mask."""
    rng = np.random.default_rng(seed)
    th = np.linspace(0, 2 * math.pi, 400)
    r = np.ones_like(th)
    for k, amp in zip((2, 3, 4, 5), wobble):
        r += amp * np.sin(k * th + rng.uniform(0, 2 * math.pi))
    r = r / r.max()
    cx, cy = w / 2, h / 2
    pts = [(cx + 0.46 * w * ri * math.cos(t), cy + 0.46 * h * ri * math.sin(t)) for ri, t in zip(r, th)]
    m = Image.new("L", (w * SS, h * SS), 0)
    ImageDraw.Draw(m).polygon([(x * SS, y * SS) for x, y in pts], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(1.2 * SS)).resize((w, h), Image.LANCZOS)
    return m


def gradient_blob(path, w, h, c1, c2, seed, wobble, alpha, angle=35):
    m = blob_mask(w, h, seed, wobble)
    yy, xx = np.mgrid[0:h, 0:w]
    a = math.radians(angle)
    t = ((xx - w / 2) * math.cos(a) + (yy - h / 2) * math.sin(a)) / (0.5 * (w * abs(math.cos(a)) + h * abs(math.sin(a))))
    t = np.clip((t + 1) / 2, 0, 1)
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    for i in range(3):
        rgb[..., i] = (c1[i] + (c2[i] - c1[i]) * t).astype(np.uint8)
    mask = (np.array(m, dtype=np.float32) * alpha).astype(np.uint8)
    img = Image.fromarray(np.dstack([rgb, mask]), "RGBA")
    img.save(path)


def make_helix(path, W=900, H=1800):
    """Stylised protein ribbon (alpha helix) in green gradients, drawn back-to-front."""
    img = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    turns, steps_per_turn = 5.2, 90
    n = int(turns * steps_per_turn)
    amp = 0.36 * W * SS
    cx = W * SS / 2
    top, bot = 0.07 * H * SS, 0.93 * H * SS
    pitch = (bot - top) / turns
    band = pitch * 0.34
    dark, light = hex2rgb("14301F"), hex2rgb("B5E7C6")
    mid, pri = hex2rgb("10B981"), hex2rgb("2F8F5B")
    segs = []
    for i in range(n):
        t0, t1 = 2 * math.pi * i / steps_per_turn, 2 * math.pi * (i + 1) / steps_per_turn
        y0, y1 = top + pitch * t0 / (2 * math.pi), top + pitch * t1 / (2 * math.pi)
        x0, x1 = cx + amp * math.sin(t0), cx + amp * math.sin(t1)
        z = math.cos((t0 + t1) / 2)  # +1 = facing viewer
        segs.append((z, x0, y0, x1, y1))
    segs.sort(key=lambda s: s[0])  # back first
    for z, x0, y0, x1, y1 in segs:
        u = (z + 1) / 2  # 0 back .. 1 front
        col = lerp(lerp(light, mid, u), pri, max(0, u - 0.55) / 0.45 * 0.9)
        edge = lerp(col, dark, 0.35)
        poly = [(x0, y0 - band), (x1, y1 - band), (x1, y1 + band), (x0, y0 + band)]
        d.polygon(poly, fill=col + (255,), outline=edge + (255,))
    img = img.filter(ImageFilter.GaussianBlur(0.6 * SS)).resize((W, H), Image.LANCZOS)
    img.save(path)


def make_strand(path, W=2400, H=700):
    """Flowing amino-acid chain: a thin curve with 'beads on a string'."""
    img = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def curve(x):  # x in 0..1
        return 0.5 + 0.30 * math.sin(x * 2 * math.pi * 1.5 + 0.6) + 0.10 * math.sin(x * 2 * math.pi * 3.1)

    pts = [(int((0.03 + 0.94 * i / 600) * W * SS), int(curve(0.03 + 0.94 * i / 600 * 1.0) * H * SS)) for i in range(601)]
    d.line(pts, fill=hex2rgb("10B981") + (150,), width=int(7 * SS), joint="curve")
    pal = [hex2rgb(c) for c in ("2F8F5B", "10B981", "B5E7C6", "DDF1E3")]
    nb = 34
    for k in range(nb):
        x = 0.03 + 0.94 * k / (nb - 1)
        y = curve(x)
        r = (26 + 7 * math.sin(k * 1.7)) * SS
        px, py = x * W * SS, y * H * SS
        col = pal[k % 4]
        d.ellipse([px - r, py - r, px + r, py + r], fill=col + (235,), outline=hex2rgb("2F8F5B") + (255,), width=int(3 * SS))
    img = img.filter(ImageFilter.GaussianBlur(0.5 * SS)).resize((W, H), Image.LANCZOS)
    img.save(path)


if __name__ == "__main__":
    gradient_blob(os.path.join(OUT, "blob_a.png"), 1600, 1400, hex2rgb("DDF1E3"), hex2rgb("6CCB95"), 7, (0.10, 0.08, 0.05, 0.03), 0.80)
    gradient_blob(os.path.join(OUT, "blob_b.png"), 1000, 1000, hex2rgb("B5E36B"), hex2rgb("10B981"), 21, (0.06, 0.12, 0.05, 0.04), 0.55, angle=120)
    make_helix(os.path.join(OUT, "helix.png"))
    make_strand(os.path.join(OUT, "strand.png"))
    print("assets written to", os.path.abspath(OUT))
