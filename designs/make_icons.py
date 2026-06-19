"""Generate 4 mockup app icons for Echo Dutch (1024x1024)."""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math, os

SIZE = 1024
OUT = os.path.join(os.path.dirname(__file__), "icons")
os.makedirs(OUT, exist_ok=True)

DUTCH_ORANGE = (255, 105, 0)
DUTCH_ORANGE_DARK = (233, 78, 15)
DUTCH_ORANGE_LIGHT = (255, 140, 66)
DUTCH_RED = (174, 28, 40)
DUTCH_BLUE = (33, 70, 139)
WHITE = (255, 255, 255)
OFFWHITE = (252, 246, 235)

HELV = "/System/Library/Fonts/HelveticaNeue.ttc"
SF = "/System/Library/Fonts/SFCompact.ttf"
SF_NS = "/System/Library/Fonts/SFNS.ttf"


def gradient_bg(c1, c2, vertical=False):
    """Create a gradient background image."""
    img = Image.new("RGB", (SIZE, SIZE), c1)
    px = img.load()
    for y in range(SIZE):
        for x in range(SIZE):
            t = (y if vertical else (x + y) / 2) / SIZE
            r = int(c1[0] * (1 - t) + c2[0] * t)
            g = int(c1[1] * (1 - t) + c2[1] * t)
            b = int(c1[2] * (1 - t) + c2[2] * t)
            px[x, y] = (r, g, b)
    return img


def concept_1_mouth_waves():
    """Mouth + sound waves on Dutch orange."""
    img = Image.new("RGB", (SIZE, SIZE), DUTCH_ORANGE)
    d = ImageDraw.Draw(img, "RGBA")
    cx, cy = SIZE // 2, SIZE // 2

    # Sound waves (3 arcs each side, fading)
    for side in (-1, 1):
        for i, alpha in enumerate([220, 150, 80]):
            r = 220 + i * 90
            bbox = [cx - r, cy - r, cx + r, cy + r]
            start = -25 if side == 1 else 155
            end = 25 if side == 1 else 205
            d.arc(bbox, start, end, fill=(255, 255, 255, alpha), width=22)

    # Mouth shape (stylized open lips, oval)
    mw, mh = 360, 180
    d.ellipse([cx - mw // 2, cy - mh // 2, cx + mw // 2, cy + mh // 2], fill=WHITE)
    # Inner darker oval (mouth opening)
    iw, ih = 260, 90
    d.ellipse([cx - iw // 2, cy - ih // 2, cx + iw // 2, cy + ih // 2],
              fill=DUTCH_ORANGE_DARK)
    # Tongue hint
    tw, th = 140, 50
    d.ellipse([cx - tw // 2, cy - th // 2 + 18, cx + tw // 2, cy + th // 2 + 18],
              fill=(255, 90, 90))

    # NL badge bottom right
    try:
        f = ImageFont.truetype(HELV, 56, index=8)  # bold
    except Exception:
        f = ImageFont.truetype(HELV, 56)
    d.text((SIZE - 130, SIZE - 110), "NL", font=f, fill=(255, 255, 255, 210))

    img.save(os.path.join(OUT, "concept1_mouth_waves.png"))
    print("✓ concept 1")


def concept_2_tulip_mouth():
    """Tulip silhouette doubling as opening lips."""
    img = gradient_bg(DUTCH_ORANGE_LIGHT, DUTCH_ORANGE_DARK)
    d = ImageDraw.Draw(img, "RGBA")
    cx, cy = SIZE // 2, SIZE // 2 - 40

    # Three tulip petals (white)
    # Center petal
    petal = []
    for t in [i / 60 for i in range(61)]:
        # parametric tulip-petal-like shape
        ang = math.pi * t
        r = 280 * (math.sin(ang)) ** 0.7
        x = cx + r * (0.35 * math.cos(ang * 2 - math.pi / 2))
        y = cy - 240 + 480 * (1 - math.sin(ang))
        petal.append((x, y))
    d.polygon(petal, fill=WHITE)

    # Side petals - simulate as ellipses
    d.pieslice([cx - 320, cy - 240, cx - 20, cy + 200],
               start=-110, end=20, fill=WHITE)
    d.pieslice([cx + 20, cy - 240, cx + 320, cy + 200],
               start=160, end=290, fill=WHITE)

    # Gap between petals (suggesting open mouth)
    d.polygon([(cx - 30, cy - 60), (cx + 30, cy - 60),
               (cx + 50, cy + 80), (cx - 50, cy + 80)],
              fill=DUTCH_ORANGE_DARK)

    # Sound waves curling out of the gap
    for i, alpha in enumerate([200, 130, 70]):
        r = 60 + i * 50
        d.arc([cx - r, cy - 30 - r, cx + r, cy - 30 + r],
              210, 330, fill=(255, 255, 255, alpha), width=14)

    # Stem
    d.rectangle([cx - 12, cy + 200, cx + 12, cy + 420], fill=WHITE)
    # Leaf
    d.ellipse([cx + 10, cy + 280, cx + 180, cy + 360], fill=(255, 240, 220))

    img.save(os.path.join(OUT, "concept2_tulip_mouth.png"))
    print("✓ concept 2")


def concept_3_letter_e():
    """Big É letter with sound-wave accent."""
    img = Image.new("RGB", (SIZE, SIZE), DUTCH_ORANGE)
    d = ImageDraw.Draw(img, "RGBA")

    # Subtle radial darker spot at corners
    for r in range(SIZE, 0, -8):
        a = int(40 * (r / SIZE) ** 2)
        if a < 1:
            continue
        d.ellipse([SIZE - r, SIZE - r, SIZE + r, SIZE + r],
                  outline=None, fill=(0, 0, 0, 0))

    # Big É - use thick custom-drawn E so we don't depend on font É glyph
    cx, cy = SIZE // 2, SIZE // 2 + 60
    w = 540
    h = 600
    bar = 110  # horizontal bar thickness
    stem = 130  # vertical stem thickness

    # vertical
    d.rectangle([cx - w // 2, cy - h // 2, cx - w // 2 + stem, cy + h // 2],
                fill=WHITE)
    # top bar
    d.rectangle([cx - w // 2, cy - h // 2, cx + w // 2, cy - h // 2 + bar],
                fill=WHITE)
    # middle bar (shorter)
    d.rectangle([cx - w // 2, cy - bar // 2, cx + w // 2 - 80,
                 cy + bar // 2], fill=WHITE)
    # bottom bar
    d.rectangle([cx - w // 2, cy + h // 2 - bar, cx + w // 2, cy + h // 2],
                fill=WHITE)

    # Accent: 3 concentric sound-wave dots above the E
    ax, ay = cx, cy - h // 2 - 110
    for i, (rad, alpha) in enumerate([(28, 255), (60, 170), (95, 100)]):
        d.ellipse([ax - rad, ay - rad, ax + rad, ay + rad],
                  outline=(255, 255, 255, alpha), width=14)
    # filled center dot
    d.ellipse([ax - 22, ay - 22, ax + 22, ay + 22], fill=WHITE)

    # NL flag stripes bottom-left (tiny)
    sx, sy, sw, sh = 80, SIZE - 130, 130, 60
    d.rectangle([sx, sy, sx + sw, sy + sh // 3], fill=DUTCH_RED)
    d.rectangle([sx, sy + sh // 3, sx + sw, sy + 2 * sh // 3], fill=OFFWHITE)
    d.rectangle([sx, sy + 2 * sh // 3, sx + sw, sy + sh], fill=DUTCH_BLUE)

    img.save(os.path.join(OUT, "concept3_letter_e.png"))
    print("✓ concept 3")


def concept_4_flag_waves():
    """Dutch flag stripes (custom proportions) + sound waves."""
    img = Image.new("RGB", (SIZE, SIZE), DUTCH_ORANGE)
    d = ImageDraw.Draw(img, "RGBA")

    # Top red stripe
    d.rectangle([0, 0, SIZE, 220], fill=DUTCH_RED)
    # Bottom blue stripe
    d.rectangle([0, SIZE - 220, SIZE, SIZE], fill=DUTCH_BLUE)
    # Middle is already orange (royal House of Orange)

    # 3 concentric sound waves expanding from left
    cx, cy = 280, SIZE // 2
    for i, (rad, alpha) in enumerate([(140, 255), (240, 180), (360, 110), (490, 60)]):
        d.arc([cx - rad, cy - rad, cx + rad, cy + rad],
              -55, 55, fill=(255, 255, 255, alpha), width=28)

    # Origin dot (the "speaker")
    d.ellipse([cx - 50, cy - 50, cx + 50, cy + 50], fill=WHITE)

    img.save(os.path.join(OUT, "concept4_flag_waves.png"))
    print("✓ concept 4")


def make_contact_sheet():
    """2x2 grid of all 4 concepts with labels, for easy comparison."""
    pad = 60
    label_h = 80
    cell = 480
    sheet_w = cell * 2 + pad * 3
    sheet_h = (cell + label_h) * 2 + pad * 3
    sheet = Image.new("RGB", (sheet_w, sheet_h), (245, 243, 240))
    d = ImageDraw.Draw(sheet)
    try:
        f = ImageFont.truetype(HELV, 36, index=8)
    except Exception:
        f = ImageFont.truetype(HELV, 36)
    titles = [
        ("concept1_mouth_waves.png", "1. 嘴 + 音波"),
        ("concept2_tulip_mouth.png", "2. Tulip-mouth"),
        ("concept3_letter_e.png", "3. 大字母 É"),
        ("concept4_flag_waves.png", "4. 國旗音波"),
    ]
    for idx, (fname, title) in enumerate(titles):
        col = idx % 2
        row = idx // 2
        x = pad + col * (cell + pad)
        y = pad + row * (cell + label_h + pad)
        im = Image.open(os.path.join(OUT, fname)).resize((cell, cell), Image.LANCZOS)
        # rounded mask to preview how iOS will round
        mask = Image.new("L", (cell, cell), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, cell, cell],
                                               radius=int(cell * 0.22), fill=255)
        rounded = Image.new("RGB", (cell, cell), (245, 243, 240))
        rounded.paste(im, (0, 0), mask)
        sheet.paste(rounded, (x, y))
        d.text((x, y + cell + 16), title, font=f, fill=(40, 40, 40))
    sheet.save(os.path.join(OUT, "_contact_sheet.png"))
    print("✓ contact sheet")


if __name__ == "__main__":
    concept_1_mouth_waves()
    concept_2_tulip_mouth()
    concept_3_letter_e()
    concept_4_flag_waves()
    make_contact_sheet()
    print(f"\nAll saved to: {OUT}")
