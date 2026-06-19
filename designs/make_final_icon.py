"""Echo Dutch — polished final app icon (concept 3 refined).

Modern universal idiom: only one 1024x1024 PNG needed.
Xcode auto-derives all other sizes.
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math, os

SIZE = 1024
OUT = os.path.join(os.path.dirname(__file__), "icons")
os.makedirs(OUT, exist_ok=True)

# Brand palette
ORANGE_TOP = (255, 124, 24)
ORANGE_BOTTOM = (227, 90, 0)
WHITE = (255, 255, 255)
OFFWHITE = (252, 248, 240)
DUTCH_RED = (174, 28, 40)
DUTCH_BLUE = (33, 70, 139)

HELV = "/System/Library/Fonts/HelveticaNeue.ttc"


def radial_gradient_bg(c_center, c_edge):
    """Subtle radial gradient — brighter center, darker corners for depth."""
    img = Image.new("RGB", (SIZE, SIZE), c_center)
    px = img.load()
    cx, cy = SIZE / 2, SIZE / 2
    max_r = math.hypot(cx, cy)
    for y in range(SIZE):
        for x in range(SIZE):
            r = math.hypot(x - cx, y - cy) / max_r
            t = r ** 1.4  # bias gradient toward edges
            R = int(c_center[0] * (1 - t) + c_edge[0] * t)
            G = int(c_center[1] * (1 - t) + c_edge[1] * t)
            B = int(c_center[2] * (1 - t) + c_edge[2] * t)
            px[x, y] = (R, G, B)
    return img


def draw_thick_e(d, cx, cy, w, h, bar, stem, color, shadow=False):
    """Draw a custom-built capital E (cleaner than font glyph at this scale)."""
    layers = [(0, 0, color)]
    if shadow:
        layers = [(8, 14, (0, 0, 0, 50)), (0, 0, color)]

    for dx, dy, col in layers:
        # vertical stem
        d.rectangle(
            [cx - w // 2 + dx, cy - h // 2 + dy,
             cx - w // 2 + stem + dx, cy + h // 2 + dy],
            fill=col,
        )
        # top arm
        d.rectangle(
            [cx - w // 2 + dx, cy - h // 2 + dy,
             cx + w // 2 + dx, cy - h // 2 + bar + dy],
            fill=col,
        )
        # middle arm (slightly shorter than top/bottom — classic E design)
        mid_w = int(w * 0.78)
        d.rectangle(
            [cx - w // 2 + dx, cy - bar // 2 + dy,
             cx - w // 2 + mid_w + dx, cy + bar // 2 + dy],
            fill=col,
        )
        # bottom arm
        d.rectangle(
            [cx - w // 2 + dx, cy + h // 2 - bar + dy,
             cx + w // 2 + dx, cy + h // 2 + dy],
            fill=col,
        )


def draw_sound_wave_accent(d, cx, cy):
    """Replace the É's accent dot with concentric sound waves."""
    # Outer faint wave
    d.ellipse([cx - 110, cy - 110, cx + 110, cy + 110],
              outline=(255, 255, 255, 85), width=12)
    # Middle wave
    d.ellipse([cx - 75, cy - 75, cx + 75, cy + 75],
              outline=(255, 255, 255, 165), width=14)
    # Inner solid dot
    d.ellipse([cx - 38, cy - 38, cx + 38, cy + 38], fill=WHITE)


def draw_nl_corner(d):
    """Small NL flag pill at bottom-right corner."""
    pad = 70
    fw, fh = 150, 95
    x = SIZE - pad - fw
    y = SIZE - pad - fh

    # Rounded white plate behind flag for premium feel
    plate_pad = 14
    d.rounded_rectangle(
        [x - plate_pad, y - plate_pad, x + fw + plate_pad, y + fh + plate_pad],
        radius=18, fill=(255, 255, 255, 235),
    )

    # Dutch flag (3 stripes)
    third = fh // 3
    d.rounded_rectangle([x, y, x + fw, y + third], radius=4, fill=DUTCH_RED)
    d.rectangle([x, y + third, x + fw, y + 2 * third], fill=OFFWHITE)
    d.rounded_rectangle([x, y + 2 * third, x + fw, y + fh], radius=4, fill=DUTCH_BLUE)

    # Hide top + bottom inner corners to look like single rounded card with crisp stripes
    d.rectangle([x, y + 4, x + fw, y + third], fill=DUTCH_RED)
    d.rectangle([x, y + 2 * third, x + fw, y + fh - 4], fill=DUTCH_BLUE)


def make_final():
    img = radial_gradient_bg(ORANGE_TOP, ORANGE_BOTTOM)
    d = ImageDraw.Draw(img, "RGBA")

    # Subtle top-light highlight (soft white blob, blurred via paste)
    hl = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hl)
    hd.ellipse([SIZE * 0.15, -SIZE * 0.25, SIZE * 0.85, SIZE * 0.35],
               fill=(255, 255, 255, 32))
    hl = hl.filter(ImageFilter.GaussianBlur(radius=70))
    img.paste(hl, (0, 0), hl)

    d = ImageDraw.Draw(img, "RGBA")

    # E geometry
    cx = SIZE // 2
    cy = SIZE // 2 + 70  # offset down to leave room for accent above
    w = 520
    h = 580
    bar = 105
    stem = 130

    # Subtle shadow under E for depth
    draw_thick_e(d, cx, cy, w, h, bar, stem, WHITE, shadow=False)

    # Soft drop-shadow behind E
    shadow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    draw_thick_e(sd, cx + 6, cy + 16, w, h, bar, stem, (0, 0, 0, 70))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=14))
    img.paste(shadow, (0, 0), shadow)

    # Redraw the E ON TOP of the shadow
    d = ImageDraw.Draw(img, "RGBA")
    draw_thick_e(d, cx, cy, w, h, bar, stem, WHITE)

    # Accent sound waves
    accent_x = cx
    accent_y = cy - h // 2 - 130
    draw_sound_wave_accent(d, accent_x, accent_y)

    # NL flag corner
    draw_nl_corner(d)

    out = os.path.join(OUT, "AppIcon-1024.png")
    img.save(out, "PNG", optimize=True)
    print(f"✓ {out}")

    # Preview rendering: rounded mask + multiple sizes preview
    preview_sizes = [(1024, "1024 (App Store)"),
                     (180, "180 (iPhone)"),
                     (120, "120 (Spotlight)"),
                     (60, "60 (Settings)"),
                     (40, "40 (Notification)")]
    pad = 50
    total_w = sum(s for s, _ in preview_sizes) + pad * (len(preview_sizes) + 1)
    total_h = 1024 + 160
    sheet = Image.new("RGB", (total_w, total_h), (240, 238, 234))
    sd2 = ImageDraw.Draw(sheet)
    try:
        f = ImageFont.truetype(HELV, 22, index=8)
    except Exception:
        f = ImageFont.truetype(HELV, 22)
    x = pad
    for s, label in preview_sizes:
        im_resized = img.resize((s, s), Image.LANCZOS)
        mask = Image.new("L", (s, s), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            [0, 0, s, s], radius=int(s * 0.225), fill=255
        )
        rounded = Image.new("RGB", (s, s), (240, 238, 234))
        rounded.paste(im_resized, (0, 0), mask)
        sheet.paste(rounded, (x, (1024 - s) // 2 + 80))
        sd2.text((x, total_h - 60), label, font=f, fill=(50, 50, 50))
        x += s + pad
    sheet.save(os.path.join(OUT, "_final_size_preview.png"))
    print(f"✓ size preview")


if __name__ == "__main__":
    make_final()
