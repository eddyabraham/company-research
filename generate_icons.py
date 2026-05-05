"""
One-time script to generate PWA icons (static/icons/).
Run: python generate_icons.py
"""
import struct
import zlib
from pathlib import Path


def make_png(size: int) -> bytes:
    """Create an orange bar-chart icon as a valid PNG."""
    BG = (234, 88, 12)   # #ea580c
    FG = (255, 255, 255)

    pixels = [BG] * (size * size)

    def rect(x0, y0, x1, y1):
        for y in range(max(0, y0), min(size, y1)):
            for x in range(max(0, x0), min(size, x1)):
                pixels[y * size + x] = FG

    s = size / 192  # scale relative to 192px design

    bar_w  = int(26 * s)
    gap    = int(14 * s)
    bottom = int(150 * s)
    x0     = (size - (bar_w * 3 + gap * 2)) // 2

    # three bars: left (short), middle (tall), right (medium)
    rect(x0,                  int(100 * s), x0 + bar_w,                  bottom)
    rect(x0 + bar_w + gap,    int(68  * s), x0 + bar_w * 2 + gap,        bottom)
    rect(x0 + bar_w * 2 + gap * 2, int(84 * s), x0 + bar_w * 3 + gap * 2, bottom)

    # build PNG bytes
    def chunk(tag: bytes, data: bytes) -> bytes:
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    raw = b"".join(
        b"\x00" + bytes(ch for px in pixels[y * size:(y + 1) * size] for ch in px)
        for y in range(size)
    )
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


if __name__ == "__main__":
    out = Path("static/icons")
    out.mkdir(parents=True, exist_ok=True)
    for size in (192, 512):
        path = out / f"icon-{size}.png"
        path.write_bytes(make_png(size))
        print(f"  {path}  ({path.stat().st_size:,} bytes)")
    print("Done.")
