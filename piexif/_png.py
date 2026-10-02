import binascii
import struct
import zlib

from ._config import config
from ._exceptions import InvalidImageDataError

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _chunks(data):
    if data[:8] != PNG_SIGNATURE:
        raise InvalidImageDataError("Given data isn't PNG.")
    chunks = []
    offset = 8
    while offset < len(data):
        if len(data) - offset < 12:
            raise InvalidImageDataError("Invalid PNG chunk.")
        length = struct.unpack(">L", data[offset : offset + 4])[0]
        end = offset + length + 12
        if end > len(data):
            raise InvalidImageDataError("Invalid PNG chunk length.")
        chunks.append((data[offset + 4 : offset + 8], data[offset:end]))
        offset = end
        if chunks[-1][0] == b"IEND":
            # Preserve the opaque trailer for edits without parsing it as PNG.
            if offset < len(data):
                chunks.append((None, data[offset:]))
            break
    return chunks


def _chunk(chunk_type, payload):
    body = chunk_type + payload
    return (
        struct.pack(">L", len(payload))
        + body
        + struct.pack(">L", zlib.crc32(body) & 0xFFFFFFFF)
    )


def _legacy_exif(chunk):
    length = struct.unpack(">L", chunk[:4])[0]
    payload = chunk[8 : 8 + length]
    try:
        keyword, value = payload.split(b"\x00", 1)
    except ValueError:
        return None
    if keyword == b"exif":
        exif = value
    elif keyword == b"Raw profile type exif":
        lines = value.splitlines()
        try:
            if lines[1] != b"exif":
                return None
            exif_length = int(lines[2])
            exif_hex = b"".join(b"".join(lines[3:]).split())
            if len(exif_hex) != exif_length * 2:
                raise ValueError
            exif = binascii.unhexlify(exif_hex)
        except (IndexError, TypeError, ValueError, binascii.Error):
            raise InvalidImageDataError("Invalid PNG Exif text profile.")
    else:
        return None
    return exif[6:] if exif.startswith(b"Exif\x00\x00") else exif


def get_exif(data):
    allow_legacy_text_exif = config.allow_legacy_png_text_exif
    legacy_exif = None
    for chunk_type, chunk in _chunks(data):
        if chunk_type == b"eXIf":
            length = struct.unpack(">L", chunk[:4])[0]
            return chunk[8 : 8 + length]
        if allow_legacy_text_exif and chunk_type == b"tEXt":
            legacy_exif = _legacy_exif(chunk) or legacy_exif
    return legacy_exif


def insert(data, exif):
    allow_legacy_text_exif = config.allow_legacy_png_text_exif
    replacement = _chunk(b"eXIf", exif[6:])
    result = []
    inserted = False
    for chunk_type, chunk in _chunks(data):
        if chunk_type == b"eXIf" or (
            allow_legacy_text_exif
            and chunk_type == b"tEXt"
            and _legacy_exif(chunk) is not None
        ):
            if not inserted:
                result.append(replacement)
                inserted = True
        else:
            result.append(chunk)
            if chunk_type == b"IHDR" and not inserted:
                result.append(replacement)
                inserted = True
    return PNG_SIGNATURE + b"".join(result)


def remove(data):
    allow_legacy_text_exif = config.allow_legacy_png_text_exif
    return PNG_SIGNATURE + b"".join(
        chunk
        for chunk_type, chunk in _chunks(data)
        if chunk_type != b"eXIf"
        and not (
            allow_legacy_text_exif
            and chunk_type == b"tEXt"
            and _legacy_exif(chunk) is not None
        )
    )
