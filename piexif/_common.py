import struct

from ._exceptions import InvalidImageDataError


def _is_image_data(data):
    if data[0:2] == b"\xff\xd8":
        return "jpeg"
    if data[0:2] in (b"\x49\x49", b"\x4d\x4d"):
        return "tiff"
    if data[0:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if data[0:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[0:6] == b"Exif\x00\x00":
        return "exif"
    return None


def split_into_segments(data):
    """Slices JPEG meta data into a list from JPEG binary data."""
    if data[0:2] != b"\xff\xd8":
        raise InvalidImageDataError("Given data isn't JPEG.")

    head = 2
    segments = [b"\xff\xd8"]
    while 1:
        segment_start = head
        while data[head : head + 2] == b"\xff\xff":
            head += 1
        segments[-1] += data[segment_start:head]

        if data[head : head + 2] == b"\xff\xda":
            segments.append(data[head:])
            break
        else:
            length = struct.unpack(">H", data[head + 2 : head + 4])[0]
            endPoint = head + length + 2
            seg = data[head:endPoint]
            segments.append(seg)
            head = endPoint

        if head >= len(data):
            raise InvalidImageDataError("Wrong JPEG data.")
    return segments


def read_exif_from_file(filename):
    """Slices JPEG meta data into a list from JPEG binary data."""
    with open(filename, "rb") as f:
        if f.read(2) != b"\xff\xd8":
            raise InvalidImageDataError("Given data isn't JPEG.")

        while True:
            if f.read(1) != b"\xff":
                break
            marker = f.read(1)
            while marker == b"\xff":
                marker = f.read(1)
            if not marker or marker in (b"\xd9", b"\xda"):
                break
            # TEM, restart markers, and SOI have no length field.
            if marker == b"\x01" or b"\xd0" <= marker <= b"\xd8":
                continue

            length_bytes = f.read(2)
            if len(length_bytes) != 2:
                raise InvalidImageDataError("Truncated JPEG segment length.")
            length = struct.unpack(">H", length_bytes)[0]
            if length < 2:
                raise InvalidImageDataError("Invalid JPEG segment length.")

            segment_data = f.read(length - 2)
            if len(segment_data) != length - 2:
                raise InvalidImageDataError("Truncated JPEG segment.")
            if marker == b"\xe1" and segment_data[:6] == b"Exif\x00\x00":
                return b"\xff" + marker + length_bytes + segment_data

    return None


def get_exif_seg(segments):
    """Returns Exif from JPEG meta data list"""
    for seg in segments:
        if seg[0:2] == b"\xff\xe1" and seg[4:10] == b"Exif\x00\x00":
            return seg
    return None


def merge_segments(segments, exif=b""):
    """Replace Exif while preserving all unrelated JPEG segments.

    An empty byte string leaves the data unchanged; None removes Exif.
    """
    if exif == b"":
        return b"".join(segments)

    merged = []
    found = False
    trailing_fill = b""
    for segment in segments:
        if segment[:2] == b"\xff\xe1" and segment[4:10] == b"Exif\x00\x00":
            segment_length = struct.unpack(">H", segment[2:4])[0] + 2
            if not found and exif is not None:
                merged.append(exif + segment[segment_length:])
            else:
                trailing_fill += segment[segment_length:]
            found = True
        else:
            merged.append(trailing_fill + segment)
            trailing_fill = b""

    if trailing_fill:
        if merged:
            merged[-1] += trailing_fill
        else:
            merged.append(trailing_fill)

    if not found and exif:
        position = 2 if merged[1][:2] == b"\xff\xe0" else 1
        merged.insert(position, exif)
    return b"".join(merged)
