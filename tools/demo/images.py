"""Image metadata for the Seeker demo (spec 8.4 and 9.3): the compiler strips it, the scanner fails any that's left.

Metadata here is anything that can say where, when, on what or by whom a picture was made: EXIF, XMP, IPTC, ICC
profiles (they name the device), comments, text chunks, thumbnails, and data hidden after the image's end (a phone's
motion-photo video or a maker's trailer). Every format works from an allow-list: only the parts drawing the picture
needs are kept, and everything else is dropped. `metadata()` names everything `strip()` would drop, so the scanner
fails exactly what the compiler would take out.
"""

import struct
import zlib

PNG_SIG = b"\x89PNG\r\n\x1a\n"
# The chunks a PNG needs to draw, and the colour ones that hold no text. Everything else (tEXt, zTXt, iTXt, eXIf,
# tIME, iCCP, and any private chunk) is dropped.
PNG_KEEP = {b"IHDR", b"PLTE", b"IDAT", b"IEND", b"tRNS", b"gAMA", b"cHRM", b"sRGB", b"sBIT", b"bKGD", b"pHYs",
            b"acTL", b"fcTL", b"fdAT"}
AFTER_END = "data after the end"


class ImageError(ValueError):
    """An image that can't be read as the type it claims."""


def kind_of(data):
    if data.startswith(PNG_SIG):
        return "png"
    if data[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


# Each reader returns (the kept bytes, the names of what it dropped).

# ---------------------------------------------------------------- PNG

def _png(data):
    pos, out, dropped = len(PNG_SIG), [PNG_SIG], []
    while True:
        if pos + 8 > len(data):
            raise ImageError("PNG: no IEND" if pos >= len(data) else "PNG: cut short")
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        end = pos + 12 + length
        if end > len(data):
            raise ImageError("PNG: chunk past the end")
        if kind in PNG_KEEP:
            out.append(data[pos:end])
        else:
            dropped.append(kind.decode("latin-1"))
        pos = end
        if kind == b"IEND":
            break
    if pos < len(data):
        dropped.append(AFTER_END)
    return b"".join(out), dropped


# ---------------------------------------------------------------- JPEG

# Markers kept: SOF0 to SOF15 but DHT (C4), JPG (C8) and DAC (CC); DHT, DAC, DQT, DRI; SOS with its scan data.
JPEG_SOF = {m for m in range(0xC0, 0xD0) if m not in (0xC4, 0xC8, 0xCC)}
JPEG_TABLES = {0xC4, 0xCC, 0xDB, 0xDD}
JPEG_NAMES = {0xE0: "APP0 (JFIF extension or thumbnail)", 0xE1: "APP1 (EXIF or XMP)", 0xE2: "APP2 (ICC)",
              0xED: "APP13 (IPTC)", 0xFE: "comment"}


def _jpeg_name(marker):
    if marker in JPEG_NAMES:
        return JPEG_NAMES[marker]
    if 0xE0 <= marker <= 0xEF:
        return "APP%d" % (marker - 0xE0)
    return "segment FF%02X" % marker


def _jfif_plain(raw):
    """A JFIF APP0 cut down to its density fields, with no thumbnail; None when it isn't JFIF at all."""
    body = raw[4:]
    if not body.startswith(b"JFIF\x00") or len(body) < 14:
        return None
    return b"\xff\xe0" + struct.pack(">H", 16) + body[:12] + b"\x00\x00"


def _jpeg_scan_end(data, pos):
    """The position of the marker that ends the entropy-coded data starting at pos (RSTn markers are inside it)."""
    while True:
        i = data.find(b"\xff", pos)
        if i < 0 or i + 1 >= len(data):
            raise ImageError("JPEG: scan data runs past the end")
        nxt = data[i + 1]
        if nxt == 0x00 or 0xD0 <= nxt <= 0xD7 or nxt == 0xFF:
            pos = i + 1 if nxt == 0xFF else i + 2
            continue
        return i


def _jpeg(data):
    pos, out, dropped = 2, [b"\xff\xd8"], []
    while True:
        if pos >= len(data):
            raise ImageError("JPEG: no end of image")
        if data[pos] != 0xFF:
            raise ImageError("JPEG: bad marker")
        while pos < len(data) and data[pos] == 0xFF:
            pos += 1
        if pos >= len(data):
            raise ImageError("JPEG: cut short")
        marker = data[pos]
        pos += 1
        if marker == 0xD9:
            out.append(b"\xff\xd9")
            break
        if marker == 0xD8 or 0xD0 <= marker <= 0xD7 or marker == 0x01:
            raise ImageError("JPEG: marker FF%02X out of place" % marker)
        if pos + 2 > len(data):
            raise ImageError("JPEG: cut short")
        length = struct.unpack(">H", data[pos:pos + 2])[0]
        if length < 2 or pos + length > len(data):
            raise ImageError("JPEG: segment past the end")
        raw = bytes([0xFF, marker]) + data[pos:pos + length]
        pos += length
        if marker == 0xDA:
            end = _jpeg_scan_end(data, pos)
            out.append(raw + data[pos:end])
            pos = end
        elif marker in JPEG_SOF or marker in JPEG_TABLES:
            out.append(raw)
        elif marker == 0xE0 and _jfif_plain(raw) is not None:
            plain = _jfif_plain(raw)
            out.append(plain)
            if plain != raw:
                dropped.append("JFIF thumbnail")
        else:
            dropped.append(_jpeg_name(marker))
    if pos < len(data):
        dropped.append(AFTER_END)
    return b"".join(out), dropped


# ---------------------------------------------------------------- GIF

GIF_LOOPS = (b"NETSCAPE2.0", b"ANIMEXTS1.0")


def _gif(data):
    if len(data) < 13:
        raise ImageError("GIF: cut short")
    flags = data[10]
    pos = 13 + (3 * (2 << (flags & 7)) if flags & 0x80 else 0)
    if pos > len(data):
        raise ImageError("GIF: cut short")
    out, dropped = [data[:pos]], []

    def sub_blocks(p):
        while True:
            if p >= len(data):
                raise ImageError("GIF: cut short")
            size = data[p]
            p += 1 + size
            if size == 0:
                return p

    while True:
        if pos >= len(data):
            raise ImageError("GIF: no trailer")
        intro = data[pos]
        if intro == 0x3B:
            out.append(b"\x3b")
            pos += 1
            break
        if intro == 0x21:
            if pos + 1 >= len(data):
                raise ImageError("GIF: cut short")
            label = data[pos + 1]
            end = sub_blocks(pos + 2)
            raw = data[pos:end]
            # A graphic control block is always 4 bytes; a loop block is the 11-byte name, then 3 bytes (1, count).
            if label == 0xF9 and len(raw) == 8 and raw[2] == 4:
                out.append(raw)
            elif label == 0xFF and len(raw) == 19 and raw[2] == 11 and raw[3:14] in GIF_LOOPS and raw[14:16] == b"\x03\x01":
                out.append(raw)
            else:
                dropped.append({0xFE: "comment", 0x01: "plain-text block", 0xFF: "application block",
                                0xF9: "graphic control block of an odd size"}.get(label, "extension %02X" % label))
            pos = end
        elif intro == 0x2C:
            if pos + 10 > len(data):
                raise ImageError("GIF: cut short")
            flags = data[pos + 9]
            p = pos + 10 + (3 * (2 << (flags & 7)) if flags & 0x80 else 0) + 1
            end = sub_blocks(p)
            out.append(data[pos:end])
            pos = end
        else:
            raise ImageError("GIF: bad block")
    if pos < len(data):
        dropped.append(AFTER_END)
    return b"".join(out), dropped


# ---------------------------------------------------------------- WebP

WEBP_KEEP = {b"VP8 ", b"VP8L", b"VP8X", b"ALPH", b"ANIM", b"ANMF"}
WEBP_FRAME_KEEP = {b"VP8 ", b"VP8L", b"ALPH"}


def _webp_chunks(data, pos, stop):
    while pos < stop:
        if pos + 8 > stop:
            raise ImageError("WebP: cut short")
        kind, length = struct.unpack("<4sI", data[pos:pos + 8])
        if pos + 8 + length > stop:
            raise ImageError("WebP: chunk past the end")
        yield kind, data[pos + 8:pos + 8 + length]
        pos += 8 + length + (length & 1)


def _webp_chunk(kind, body):
    return kind + struct.pack("<I", len(body)) + body + (b"\x00" if len(body) & 1 else b"")


def _webp(data):
    if len(data) < 12:
        raise ImageError("WebP: cut short")
    stop = 8 + struct.unpack("<I", data[4:8])[0]
    if stop > len(data):
        raise ImageError("WebP: RIFF size past the end")
    out, dropped = [], []
    for kind, body in _webp_chunks(data, 12, stop):
        name = kind.decode("latin-1").strip()
        if kind not in WEBP_KEEP:
            dropped.append(name)
            continue
        if kind == b"VP8X":  # clear the ICC, EXIF and XMP flags: those chunks never survive
            if len(body) < 1:
                raise ImageError("WebP: VP8X cut short")
            body = bytes([body[0] & ~0x2C & 0xFF]) + body[1:]
        elif kind == b"ANMF":  # a frame: 16 bytes of placing, then its own chunks, kept by their own list
            if len(body) < 16:
                raise ImageError("WebP: ANMF cut short")
            inner = []
            for sub, sub_body in _webp_chunks(body, 16, len(body)):
                if sub in WEBP_FRAME_KEEP:
                    inner.append(_webp_chunk(sub, sub_body))
                else:
                    dropped.append("frame " + sub.decode("latin-1").strip())
            body = body[:16] + b"".join(inner)
        out.append(_webp_chunk(kind, body))
    if stop < len(data):
        dropped.append(AFTER_END)
    whole = b"WEBP" + b"".join(out)
    return b"RIFF" + struct.pack("<I", len(whole)) + whole, dropped


# ---------------------------------------------------------------- both ways in

READ = {"png": _png, "jpeg": _jpeg, "gif": _gif, "webp": _webp}


def _read(data):
    kind = kind_of(data)
    if kind is None:
        raise ImageError("not a PNG, JPEG, GIF or WebP image")
    return READ[kind](data)


def strip(data):
    """The image with everything but what drawing it needs removed. Raises ImageError for an unreadable image."""
    return _read(data)[0]


def metadata(data):
    """What strip() would drop, as sorted names; empty when the image is clean."""
    return sorted(set(_read(data)[1]))


def png(width, height, rgb, text=None):
    """A small solid PNG, with one text chunk when asked (for tests)."""
    raw = b"".join(b"\x00" + bytes(rgb) * width for _ in range(height))

    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)

    out = PNG_SIG + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    if text:
        out += chunk(b"tEXt", text.encode("latin-1"))
    return out + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")
