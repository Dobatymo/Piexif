import struct
import zlib

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
    return chunks


def _chunk(chunk_type, payload):
    body = chunk_type + payload
    return (
        struct.pack(">L", len(payload))
        + body
        + struct.pack(">L", zlib.crc32(body) & 0xFFFFFFFF)
    )


def get_exif(data):
    for chunk_type, chunk in _chunks(data):
        if chunk_type == b"eXIf":
            length = struct.unpack(">L", chunk[:4])[0]
            return chunk[8 : 8 + length]
    return None


def insert(data, exif):
    replacement = _chunk(b"eXIf", exif[6:])
    result = []
    inserted = False
    for chunk_type, chunk in _chunks(data):
        if chunk_type == b"eXIf":
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
    return PNG_SIGNATURE + b"".join(
        chunk for chunk_type, chunk in _chunks(data) if chunk_type != b"eXIf"
    )
