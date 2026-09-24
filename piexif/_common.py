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
    if data[0:4] == b"Exif":
        return "exif"
    return None


def split_into_segments(data):
    """Slices JPEG meta data into a list from JPEG binary data."""
    if data[0:2] != b"\xff\xd8":
        raise InvalidImageDataError("Given data isn't JPEG.")

    head = 2
    segments = [b"\xff\xd8"]
    while 1:
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
    f = open(filename, "rb")
    data = f.read(6)

    if data[0:2] != b"\xff\xd8":
        raise InvalidImageDataError("Given data isn't JPEG.")

    head = data[2:6]
    HEAD_LENGTH = 4
    exif = None
    while len(head) == HEAD_LENGTH:
        length = struct.unpack(">H", head[2:4])[0]

        if head[:2] == b"\xff\xe1":
            segment_data = f.read(length - 2)
            if segment_data[:4] != b"Exif":
                head = f.read(HEAD_LENGTH)
                continue
            exif = head + segment_data
            break
        elif head[0:1] == b"\xff":
            f.read(length - 2)
            head = f.read(HEAD_LENGTH)
        else:
            break

    f.close()
    return exif


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
    for segment in segments:
        if segment[:2] == b"\xff\xe1" and segment[4:10] == b"Exif\x00\x00":
            if not found and exif is not None:
                merged.append(exif)
            found = True
        else:
            merged.append(segment)

    if not found and exif:
        position = 2 if merged[1][:2] == b"\xff\xe0" else 1
        merged.insert(position, exif)
    return b"".join(merged)
