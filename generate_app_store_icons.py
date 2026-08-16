"""One-off: generates high-resolution, store-ready icon assets (1024x1024 opaque
source for iOS/Android/Windows/macOS packaging tools) reusing the brand icon
generator already in generate_icons.py."""
import os

from generate_icons import make_base_icon, SUPERSAMPLE

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE_DIR, "store_assets")
os.makedirs(OUT_DIR, exist_ok=True)

# App Store Connect requires a 1024x1024 icon with NO alpha channel (fully opaque).
icon_rgba = make_base_icon(SUPERSAMPLE, corner_radius_ratio=0.18)
icon_rgb = icon_rgba.convert("RGB")  # drops alpha, flattens onto black -- fix below
# Flatten onto white instead of black so any transparent corners (there are none at
# ratio 0.18 since the shape fills the frame, but be safe) read correctly.
from PIL import Image
flattened = Image.new("RGB", icon_rgba.size, (255, 255, 255))
flattened.paste(icon_rgba, mask=icon_rgba.split()[3])
flattened.save(os.path.join(OUT_DIR, "icon-1024.png"))
print("wrote store_assets/icon-1024.png (App Store / general source icon)")

# Android adaptive icon foreground: same mark, no rounding/background baked in,
# since Android applies its own mask shape at runtime.
adaptive_fg = make_base_icon(SUPERSAMPLE, corner_radius_ratio=0.0)
adaptive_fg.save(os.path.join(OUT_DIR, "icon-adaptive-foreground-1024.png"))
print("wrote store_assets/icon-adaptive-foreground-1024.png (Android adaptive icon foreground)")

# Play Store listing icon: 512x512, 32-bit PNG with alpha allowed.
play_icon = make_base_icon(SUPERSAMPLE, corner_radius_ratio=0.18).resize((512, 512), Image.LANCZOS)
play_icon.save(os.path.join(OUT_DIR, "icon-play-store-512.png"))
print("wrote store_assets/icon-play-store-512.png (Play Store listing icon)")
