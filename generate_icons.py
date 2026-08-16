"""One-off script: generates PWA icon assets into static/icons/ from the app's brand colors."""
import os

from PIL import Image, ImageDraw

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE_DIR, "static", "icons")
os.makedirs(OUT_DIR, exist_ok=True)

SUPERSAMPLE = 1024
STOPS = [(0.0, (124, 111, 240)), (0.45, (108, 92, 231)), (1.0, (160, 102, 224))]


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def gradient_color(t):
    for (t0, c0), (t1, c1) in zip(STOPS, STOPS[1:]):
        if t0 <= t <= t1:
            local_t = (t - t0) / (t1 - t0) if t1 > t0 else 0
            return lerp(c0, c1, local_t)
    return STOPS[-1][1]


def make_base_icon(size, corner_radius_ratio, draw_piece=True):
    img = Image.new("RGB", (size, size))
    px = img.load()
    max_d = (size - 1) * 2
    for y in range(size):
        for x in range(size):
            t = (x + y) / max_d
            px[x, y] = gradient_color(t)

    mask = Image.new("L", (size, size), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.rounded_rectangle([0, 0, size - 1, size - 1], radius=int(size * corner_radius_ratio), fill=255)

    bg = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    bg.paste(img, (0, 0), mask)

    if draw_piece:
        piece = build_puzzle_piece(size)
        bg.alpha_composite(piece)

    return bg


def build_puzzle_piece(size):
    """White jigsaw-piece silhouette with a bump (top) and notch (right), centered."""
    layer = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(layer)

    m = size * 0.30
    body = [m, m, size - m, size - m]
    d.rounded_rectangle(body, radius=size * 0.05, fill=255)

    bump_r = size * 0.10
    bump_cx = size / 2
    bump_cy = m
    d.ellipse([bump_cx - bump_r, bump_cy - bump_r, bump_cx + bump_r, bump_cy + bump_r], fill=255)

    notch_r = size * 0.095
    notch_cx = size - m
    notch_cy = size / 2
    d.ellipse(
        [notch_cx - notch_r, notch_cy - notch_r, notch_cx + notch_r, notch_cy + notch_r],
        fill=0,
    )

    piece = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    white = Image.new("RGBA", (size, size), (255, 255, 255, 255))
    piece.paste(white, (0, 0), layer)
    return piece


def save_resized(base, sizes, prefix, corner_radius_ratio):
    for s in sizes:
        icon = make_base_icon(SUPERSAMPLE, corner_radius_ratio).resize((s, s), Image.LANCZOS)
        icon.save(os.path.join(OUT_DIR, f"{prefix}-{s}.png"))
        print(f"wrote {prefix}-{s}.png")


if __name__ == "__main__":
    save_resized(None, [192, 512], "icon", corner_radius_ratio=0.18)
    save_resized(None, [180], "apple-touch-icon", corner_radius_ratio=0.0)
    os.rename(os.path.join(OUT_DIR, "apple-touch-icon-180.png"), os.path.join(OUT_DIR, "apple-touch-icon.png"))

    maskable = make_base_icon(SUPERSAMPLE, corner_radius_ratio=0.0)
    maskable.resize((512, 512), Image.LANCZOS).save(os.path.join(OUT_DIR, "icon-512-maskable.png"))
    print("wrote icon-512-maskable.png")

    favicon_sizes = [16, 32, 48]
    favicon_imgs = [
        make_base_icon(SUPERSAMPLE, corner_radius_ratio=0.18).resize((s, s), Image.LANCZOS)
        for s in favicon_sizes
    ]
    favicon_imgs[0].save(
        os.path.join(BASE_DIR, "static", "favicon.ico"),
        format="ICO",
        sizes=[(s, s) for s in favicon_sizes],
    )
    print("wrote favicon.ico")
