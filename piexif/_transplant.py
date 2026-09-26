import io

from ._common import _is_image_data, get_exif_seg, merge_segments, split_into_segments


def transplant(exif_src, image, new_file=None):
    """
    py:function:: piexif.transplant(filename1, filename2)

    Transplant exif from filename1 to filename2.

    :param str filename1: JPEG
    :param str filename2: JPEG
    """
    return _transplant(exif_src, image, new_file, None)


def transplant_bytes(exif_src, image, new_file=None):
    """Copy Exif between JPEG byte strings; an output filename or buffer is required."""
    if not isinstance(exif_src, bytes) or not isinstance(image, bytes):
        raise TypeError("transplant_bytes() requires bytes for both inputs.")
    return _transplant(exif_src, image, new_file, True)


def transplant_file(exif_src, image, new_file=None):
    """Copy Exif between JPEG filenames, replacing image when no output is given."""
    return _transplant(exif_src, image, new_file, False)


def _transplant(exif_src, image, new_file, data_is_bytes):
    src_is_bytes = (
        _is_image_data(exif_src) == "jpeg" if data_is_bytes is None else data_is_bytes
    )
    if src_is_bytes:
        src_data = exif_src
    else:
        with open(exif_src, "rb") as f:
            src_data = f.read()
    segments = split_into_segments(src_data)
    exif = get_exif_seg(segments)
    if exif is None:
        raise ValueError("not found exif in input")

    image_is_bytes = (
        _is_image_data(image) == "jpeg" if data_is_bytes is None else data_is_bytes
    )
    if image_is_bytes:
        image_data = image
    else:
        with open(image, "rb") as f:
            image_data = f.read()
    segments = split_into_segments(image_data)
    new_data = merge_segments(segments, exif)

    if isinstance(new_file, io.BytesIO):
        new_file.write(new_data)
        new_file.seek(0)
    elif new_file:
        with open(new_file, "wb+") as f:
            f.write(new_data)
    elif not image_is_bytes:
        with open(image, "wb+") as f:
            f.write(new_data)
    else:
        raise ValueError("Give a 3rd argument to 'transplant' to output file")
