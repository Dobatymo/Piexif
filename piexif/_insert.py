import io
import struct
import sys

from ._common import _is_image_data, merge_segments, split_into_segments
from ._exceptions import InvalidImageDataError
from piexif import _webp
from piexif import _png


def insert(exif, image, new_file=None):
    """
    py:function:: piexif.insert(exif_bytes, filename)

    Insert exif into JPEG, WebP, or PNG, detecting bytes or a filename.

    :param bytes exif_bytes: Exif as bytes
    :param str filename: JPEG, WebP, or PNG
    """
    return _insert(exif, image, new_file, None)


def insert_bytes(exif, data, new_file=None):
    """Insert Exif into image bytes; never interpret data as a filename.

    new_file must be an output filename or io.BytesIO buffer.
    """
    if not isinstance(data, bytes):
        raise TypeError("insert_bytes() requires bytes.")
    return _insert(exif, data, new_file, True)


def insert_file(exif, filename, new_file=None):
    """Insert Exif into a filename, replacing it when new_file is omitted."""
    return _insert(exif, filename, new_file, False)


def _insert(exif, image, new_file, data_is_bytes):
    if exif[0:6] != b"\x45\x78\x69\x66\x00\x00":
        raise ValueError("Given data is not exif data")

    if data_is_bytes is None:
        # Avoid comparing Unicode filenames with binary signatures on Python 2.
        maybe_image = sys.version_info >= (3, 0, 0) or isinstance(image, str)
        data_is_bytes = maybe_image and _is_image_data(image) in ("jpeg", "webp", "png")

    if data_is_bytes:
        image_data = image
    else:
        with open(image, "rb") as f:
            image_data = f.read()
    file_type = _is_image_data(image_data)

    if file_type == "jpeg":
        exif = b"\xff\xe1" + struct.pack(">H", len(exif) + 2) + exif
        segments = split_into_segments(image_data)
        new_data = merge_segments(segments, exif)
    elif file_type == "webp":
        exif = exif[6:]
        new_data = _webp.insert(image_data, exif)
    elif file_type == "png":
        new_data = _png.insert(image_data, exif)
    else:
        raise InvalidImageDataError("Given data is neither JPEG, WebP, nor PNG.")

    if isinstance(new_file, io.BytesIO):
        new_file.write(new_data)
        new_file.seek(0)
    elif new_file:
        with open(new_file, "wb+") as f:
            f.write(new_data)
    elif not data_is_bytes:
        with open(image, "wb+") as f:
            f.write(new_data)
    else:
        raise ValueError("Give a 3rd argument to 'insert' to output file")
