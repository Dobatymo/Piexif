import io

from ._common import *
from ._common import _is_image_data
from piexif import _webp

def remove(src, new_file=None):
    """
    py:function:: piexif.remove(filename)

    Remove exif from JPEG.

    :param str filename: JPEG
    """
    if _is_image_data(src):
        return _remove(src, new_file, False)
    return _remove(src, new_file, True)


def remove_bytes(data, new_file=None):
    """Remove metadata from in-memory JPEG or WebP bytes without opening them."""
    if not isinstance(data, bytes) or not _is_image_data(data):
        raise ValueError("Given data is neither JPEG nor WebP.")
    return _remove(data, new_file, False)


def remove_file(filename, new_file=None):
    """Remove metadata from a filename; the input is always treated as a path."""
    return _remove(filename, new_file, True)


def _remove(src, new_file, output_is_file):
    if not output_is_file:
        src_data = src
    else:
        with open(src, 'rb') as f:
            src_data = f.read()
    file_type = _is_image_data(src_data)

    if file_type == "jpeg":
        segments = split_into_segments(src_data)
        exif = get_exif_seg(segments)
        if exif:
            new_data = src_data.replace(exif, b"")
        else:
            new_data = src_data
    elif file_type == "webp":
        try:
            new_data = _webp.remove(src_data)
        except ValueError:
            new_data = src_data
        except e:
            print(e.args)
            raise ValueError("Error occurred.")

    if isinstance(new_file, io.BytesIO):
        new_file.write(new_data)
        new_file.seek(0)
    elif new_file:
        with open(new_file, "wb+") as f:
            f.write(new_data)
    elif output_is_file:
        with open(src, "wb+") as f:
            f.write(new_data)
    else:
        raise ValueError("Give a second argument to 'remove' to output file")
