import numbers
import struct
import sys

from ._common import (
    _is_image_data,
    get_exif_seg,
    read_exif_from_file,
    split_into_segments,
)
from ._exceptions import InvalidImageDataError
from ._exif import TAGS, TYPES, ExifIFD, ImageIFD, _IFD_POINTERS
from piexif import _webp
from piexif import _png

LITTLE_ENDIAN = b"\x49\x49"
try:
    STRING_TYPES = (basestring,)
except NameError:
    STRING_TYPES = (str,)


def load(input_data, key_is_name=False):
    """
    py:function:: piexif.load(input_data, key_is_name=False)

    Read JPEG, WebP, TIFF or Exif metadata from a filename or bytes.
    The standard API returns 0th/Exif/GPS/Interop/1st dictionaries,
    thumbnail bytes or None, and GlobalParameters when present.
    Additional pages and SubIFDs are not traversed; use load_ifds() for the
    advanced nested directory-list API.

    :param input_data: JPEG, WebP, TIFF filename or image/Exif bytes
    :param bool key_is_name: Use tag names instead of numeric IDs. dump()
        requires numeric IDs.
    :return: Standard metadata dictionary
    :rtype: dict
    """
    if isinstance(input_data, bytes) and _is_image_data(input_data):
        return load_bytes(input_data, key_is_name)
    return load_file(input_data, key_is_name)


def load_bytes(data, key_is_name=False):
    """Read metadata from complete image or Exif bytes.

    Unlike ``load()``, this function never treats the byte string as a
    filename. Use it for untrusted or in-memory input.
    """
    if not isinstance(data, bytes):
        raise TypeError("load_bytes() requires bytes.")
    return _load(data, key_is_name, False, data_is_bytes=True)


def load_file(filename, key_is_name=False):
    """Read metadata from a filename; never interpret its value as image data."""
    if not isinstance(filename, STRING_TYPES + (bytes,)):
        raise TypeError("load_file() requires a filename.")
    return _load(filename, key_is_name, False, data_is_bytes=False)


def load_ifds(input_data, key_is_name=False, load_jpeg_data=False):
    """
    py:function:: piexif.load_ifds(input_data, key_is_name=False, load_jpeg_data=False)

    The advanced API reads metadata as a nonempty list of primary directories.
    Each image directory has "tags" and "subifds" (a list of child chains).
    Exif, GPS and GlobalParameters nodes belong to their image directory;
    Interop belongs to its Exif node. Auxiliary nodes also contain "tags".
    With load_jpeg_data=True, JPEGInterchangeFormat streams are returned as
    "jpeg_data" bytes on their image directories, not necessarily thumbnails.
    Shared directories use the same dictionary object. Structural pointer
    tags are replaced by these relationships and rebuilt by dump_ifds().
    JPEG offset/length tags (513/514) are omitted even when data is not loaded.
    An image without EXIF returns [{"tags": {}, "subifds": []}].

    :param input_data: JPEG, WebP, TIFF filename or image/Exif bytes
    :param bool key_is_name: Use tag names instead of numeric IDs. dump_ifds()
        requires numeric IDs. Directory structure and sharing are unchanged.
    :param bool load_jpeg_data: Extract JPEGInterchangeFormat payloads from
        all image directories. Defaults to False; does not limit file I/O.
    :return: Nested directory list, accepted directly by dump_ifds()
    :rtype: list

    Unknown tags and pixel data other than opted-in JPEG streams are not returned.
    This is not a lossless TIFF file reader or pixel-offset relocator.
    """
    return _load(input_data, key_is_name, True, load_jpeg_data)


def load_ifds_bytes(data, key_is_name=False, load_jpeg_data=False):
    """Read nested directories from bytes; never interpret data as a filename."""
    if not isinstance(data, bytes):
        raise TypeError("load_ifds_bytes() requires bytes.")
    return _load(data, key_is_name, True, load_jpeg_data, data_is_bytes=True)


def load_ifds_file(filename, key_is_name=False, load_jpeg_data=False):
    """Read nested directories from a filename; never interpret it as bytes."""
    if not isinstance(filename, STRING_TYPES + (bytes,)):
        raise TypeError("load_ifds_file() requires a filename.")
    return _load(filename, key_is_name, True, load_jpeg_data, data_is_bytes=False)


def _load(input_data, key_is_name, full_ifds, load_jpeg_data=False, data_is_bytes=None):
    exif_dict = {
        "0th": {},
        "Exif": {},
        "GPS": {},
        "Interop": {},
        "1st": {},
        "thumbnail": None,
    }
    exifReader = _ExifReader(input_data, data_is_bytes)
    if exifReader.tiftag is None:
        if full_ifds:
            return [{"tags": {}, "subifds": []}]
        return exif_dict

    if exifReader.tiftag[0:2] == LITTLE_ENDIAN:
        exifReader.endian_mark = "<"
    else:
        exifReader.endian_mark = ">"

    pointer = struct.unpack(exifReader.endian_mark + "L", exifReader.tiftag[4:8])[0]
    if full_ifds:
        return exifReader.get_image_ifds(pointer, key_is_name, load_jpeg_data)
    zeroth_ifd = exifReader.get_ifd_dict(pointer, "0th")
    first_ifd_pointer = zeroth_ifd.pop("first_ifd_pointer")
    first_ifd = {}
    if first_ifd_pointer != b"\x00\x00\x00\x00":
        pointer = struct.unpack(exifReader.endian_mark + "L", first_ifd_pointer)[0]
        first_ifd = exifReader.get_ifd_dict(pointer, "1st")
    exif_dict["0th"] = zeroth_ifd
    exif_dict["1st"] = first_ifd
    if ImageIFD.ExifTag in zeroth_ifd:
        pointer = zeroth_ifd[ImageIFD.ExifTag]
        exif_dict["Exif"] = exifReader.get_ifd_dict(pointer, "Exif")
    if ImageIFD.GPSTag in zeroth_ifd:
        pointer = zeroth_ifd[ImageIFD.GPSTag]
        exif_dict["GPS"] = exifReader.get_ifd_dict(pointer, "GPS")
    if ImageIFD.GlobalParametersIFD in zeroth_ifd:
        pointer = zeroth_ifd[ImageIFD.GlobalParametersIFD]
        exif_dict["GlobalParameters"] = exifReader.get_ifd_dict(
            pointer, "GlobalParameters"
        )
    if ExifIFD.InteroperabilityTag in exif_dict["Exif"]:
        pointer = exif_dict["Exif"][ExifIFD.InteroperabilityTag]
        exif_dict["Interop"] = exifReader.get_ifd_dict(pointer, "Interop")
    if (
        ImageIFD.JPEGInterchangeFormat in first_ifd
        and ImageIFD.JPEGInterchangeFormatLength in first_ifd
    ):
        start = first_ifd[ImageIFD.JPEGInterchangeFormat]
        end = start + first_ifd[ImageIFD.JPEGInterchangeFormatLength]
        exif_dict["thumbnail"] = exifReader.tiftag[start:end]
    if key_is_name:
        exif_dict = _get_key_name_dict(exif_dict)
    return exif_dict


class _ExifReader(object):
    def get_image_ifds(self, root, key_is_name=False, load_jpeg_data=False):
        nodes, active = {}, set()
        stack = [(root, "Image", False)]
        while stack:
            pointer, kind, leaving = stack.pop()
            if leaving:
                active.remove(pointer)
                continue
            if not isinstance(pointer, numbers.Integral) or pointer < 8:
                raise InvalidImageDataError("Invalid IFD offset.")
            if pointer in active:
                raise InvalidImageDataError("Cyclic IFD graph.")
            if pointer in nodes:
                if nodes[pointer]["kind"] != kind:
                    raise InvalidImageDataError(
                        "IFD referenced with incompatible types."
                    )
                continue
            tags = self.get_ifd_dict(pointer, kind)
            links = {}
            for tag, name in _IFD_POINTERS.get(kind, ()):
                if tag in tags:
                    links[name] = tags.pop(tag)
            following, children = 0, ()
            if kind == "Image":
                count = struct.unpack_from(
                    self.endian_mark + "H", self.tiftag, pointer
                )[0]
                end = pointer + 2 + count * 12
                if end + 4 > len(self.tiftag):
                    raise InvalidImageDataError("Invalid image IFD size.")
                following = struct.unpack_from(
                    self.endian_mark + "L", self.tiftag, end
                )[0]
                if ImageIFD.SubIFDs in tags:
                    children = tags.pop(ImageIFD.SubIFDs)
                    if not isinstance(children, tuple):
                        children = (children,)
                    if not children or any(not p for p in children):
                        raise InvalidImageDataError("Invalid SubIFDs offset.")
                    for index in range(count):
                        tag, value_type = struct.unpack_from(
                            self.endian_mark + "HH",
                            self.tiftag,
                            pointer + 2 + index * 12,
                        )
                        if tag == ImageIFD.SubIFDs and value_type not in (
                            TYPES.Long,
                            TYPES.Ifd,
                        ):
                            raise InvalidImageDataError("Invalid SubIFDs pointer type.")
            node = {"tags": tags}
            if kind == "Image":
                node["subifds"] = []
                start = tags.pop(ImageIFD.JPEGInterchangeFormat, None)
                length = tags.pop(ImageIFD.JPEGInterchangeFormatLength, None)
                if load_jpeg_data and start not in (None, 0) and length is not None:
                    if (
                        not isinstance(start, numbers.Integral)
                        or not isinstance(length, numbers.Integral)
                        or start < 8
                        or length < 0
                        or start + length > len(self.tiftag)
                    ):
                        raise InvalidImageDataError(
                            "Invalid JPEG data offset or length."
                        )
                    node["jpeg_data"] = self.tiftag[start : start + length]
            nodes[pointer] = {
                "kind": kind,
                "node": node,
                "next": following,
                "subifds": children,
                "links": links,
            }
            active.add(pointer)
            stack.append((pointer, kind, True))
            targets = [(child, "Image") for child in children]
            targets.extend((target, name) for name, target in links.items())
            if following:
                targets.append((following, "Image"))
            for target, target_kind in reversed(targets):
                stack.append((target, target_kind, False))

        chains = {}

        def chain(pointer):
            if pointer not in chains:
                result = []
                chains[pointer] = result
                while pointer:
                    result.append(nodes[pointer]["node"])
                    pointer = nodes[pointer]["next"]
            else:
                result = chains[pointer]
            return result

        for entry in nodes.values():
            node = entry["node"]
            if entry["kind"] == "Image":
                node["subifds"] = [chain(child) for child in entry["subifds"]]
            for name, target in entry["links"].items():
                node[name] = nodes[target]["node"]
            if key_is_name:
                node["tags"] = {
                    TAGS[entry["kind"]][tag]["name"]: value
                    for tag, value in node["tags"].items()
                }
        return chain(root)

    def __init__(self, data, data_is_bytes=None):
        # None auto-detects; True selects bytes and False selects a filename.
        # Prevents "UnicodeWarning: Unicode equal comparison failed" warnings on Python 2
        maybe_image = sys.version_info >= (3, 0, 0) or isinstance(data, str)

        data_type = (
            _is_image_data(data) if maybe_image and data_is_bytes is not False else None
        )
        if data_type == "jpeg":
            segments = split_into_segments(data)
            app1 = get_exif_seg(segments)
            if app1:
                self.tiftag = app1[10:]
            else:
                self.tiftag = None
        elif data_type == "tiff":
            self.tiftag = data
        elif data_type == "webp":
            self.tiftag = _webp.get_exif(data)
        elif data_type == "png":
            self.tiftag = _png.get_exif(data)
        elif data_type == "exif":
            self.tiftag = data[6:]
        elif data_is_bytes:
            raise InvalidImageDataError(
                "Given data is neither JPEG, TIFF, WebP, nor PNG."
            )
        else:
            with open(data, "rb") as f:
                file_type = _is_image_data(f.read(12))
                if file_type in ("tiff", "webp", "png"):
                    f.seek(0)
                    file_data = f.read()
            if file_type == "jpeg":
                app1 = read_exif_from_file(data)
                if app1:
                    self.tiftag = app1[10:]
                else:
                    self.tiftag = None
            elif file_type == "tiff":
                self.tiftag = file_data
            elif file_type == "webp":
                self.tiftag = _webp.get_exif(file_data)
            elif file_type == "png":
                self.tiftag = _png.get_exif(file_data)
            else:
                raise InvalidImageDataError(
                    "Given file is neither JPEG, TIFF, WebP, nor PNG."
                )

    def get_ifd_dict(self, pointer, ifd_name, read_unknown=False):
        ifd_dict = {}
        if pointer < 0 or pointer + 2 > len(self.tiftag):
            raise InvalidImageDataError("Invalid IFD offset.")
        tag_count = struct.unpack(
            self.endian_mark + "H", self.tiftag[pointer : pointer + 2]
        )[0]
        offset = pointer + 2
        # Only the entry table is required for nested IFDs. The trailing
        # next-IFD pointer is meaningful for the 0th IFD and may be absent
        # from compact nested IFD data.
        required_end = offset + tag_count * 12
        if ifd_name == "0th":
            required_end += 4
        if required_end > len(self.tiftag):
            raise InvalidImageDataError("Invalid IFD size.")
        if ifd_name in ["0th", "1st"]:
            t = "Image"
        else:
            t = ifd_name
        for x in range(tag_count):
            pointer = offset + 12 * x
            tag = struct.unpack(
                self.endian_mark + "H", self.tiftag[pointer : pointer + 2]
            )[0]
            value_type = struct.unpack(
                self.endian_mark + "H", self.tiftag[pointer + 2 : pointer + 4]
            )[0]
            value_num = struct.unpack(
                self.endian_mark + "L", self.tiftag[pointer + 4 : pointer + 8]
            )[0]
            value = self.tiftag[pointer + 8 : pointer + 12]
            v_set = (value_type, value_num, value, tag)
            if tag in TAGS[t]:
                ifd_dict[tag] = self.convert_value(v_set)
            elif read_unknown:
                ifd_dict[tag] = (v_set[0], v_set[1], v_set[2], self.tiftag)
            # else:
            #    pass

        if ifd_name == "0th":
            pointer = offset + 12 * tag_count
            ifd_dict["first_ifd_pointer"] = self.tiftag[pointer : pointer + 4]
        return ifd_dict

    def convert_value(self, val):
        data = None
        t = val[0]
        length = val[1]
        value = val[2]

        type_size = {
            TYPES.Byte: 1,
            TYPES.Ascii: 1,
            TYPES.Short: 2,
            TYPES.Long: 4,
            TYPES.Ifd: 4,
            TYPES.Rational: 8,
            TYPES.SByte: 1,
            TYPES.Undefined: 1,
            TYPES.SShort: 2,
            TYPES.SLong: 4,
            TYPES.SRational: 8,
            TYPES.Float: 4,
            TYPES.DFloat: 8,
        }.get(t)
        if type_size is None:
            raise InvalidImageDataError(
                "Exif might be wrong. Got incorrect value type to decode."
            )
        value_size = length * type_size
        if value_size > 4:
            pointer = struct.unpack(self.endian_mark + "L", value)[0]
            if pointer > len(self.tiftag) or value_size > len(self.tiftag) - pointer:
                raise InvalidImageDataError("Exif value exceeds the image data.")
        elif value_size > 4 or length < 0:
            raise InvalidImageDataError("Invalid Exif value size.")

        if t == TYPES.Byte:  # BYTE
            if length > 4:
                pointer = struct.unpack(self.endian_mark + "L", value)[0]
                data = struct.unpack(
                    "B" * length, self.tiftag[pointer : pointer + length]
                )
            else:
                data = struct.unpack("B" * length, value[0:length])
        elif t == TYPES.Ascii:  # ASCII
            if length > 4:
                pointer = struct.unpack(self.endian_mark + "L", value)[0]
                data = self.tiftag[pointer : pointer + length]
            else:
                data = value[0:length]
            # Some writers omit the terminator; never read beyond the count.
            if data.endswith(b"\x00"):
                data = data[:-1]
        elif t == TYPES.Short:  # SHORT
            if length > 2:
                pointer = struct.unpack(self.endian_mark + "L", value)[0]
                data = struct.unpack(
                    self.endian_mark + "H" * length,
                    self.tiftag[pointer : pointer + length * 2],
                )
            else:
                data = struct.unpack(
                    self.endian_mark + "H" * length, value[0 : length * 2]
                )
        elif t in (TYPES.Long, TYPES.Ifd):  # LONG or IFD offset
            if length > 1:
                pointer = struct.unpack(self.endian_mark + "L", value)[0]
                data = struct.unpack(
                    self.endian_mark + "L" * length,
                    self.tiftag[pointer : pointer + length * 4],
                )
            else:
                data = struct.unpack(self.endian_mark + "L" * length, value)
        elif t == TYPES.Rational:  # RATIONAL
            pointer = struct.unpack(self.endian_mark + "L", value)[0]
            if length > 1:
                data = tuple(
                    (
                        struct.unpack(
                            self.endian_mark + "L",
                            self.tiftag[pointer + x * 8 : pointer + 4 + x * 8],
                        )[0],
                        struct.unpack(
                            self.endian_mark + "L",
                            self.tiftag[pointer + 4 + x * 8 : pointer + 8 + x * 8],
                        )[0],
                    )
                    for x in range(length)
                )
            else:
                data = (
                    struct.unpack(
                        self.endian_mark + "L", self.tiftag[pointer : pointer + 4]
                    )[0],
                    struct.unpack(
                        self.endian_mark + "L", self.tiftag[pointer + 4 : pointer + 8]
                    )[0],
                )
        elif t == TYPES.SByte:  # SIGNED BYTES
            if length > 4:
                pointer = struct.unpack(self.endian_mark + "L", value)[0]
                data = struct.unpack(
                    "b" * length, self.tiftag[pointer : pointer + length]
                )
            else:
                data = struct.unpack("b" * length, value[0:length])
        elif t == TYPES.Undefined:  # UNDEFINED BYTES
            if length > 4:
                pointer = struct.unpack(self.endian_mark + "L", value)[0]
                data = self.tiftag[pointer : pointer + length]
            else:
                data = value[0:length]
        elif t == TYPES.SShort:  # SIGNED SHORT
            if length > 2:
                pointer = struct.unpack(self.endian_mark + "L", value)[0]
                data = struct.unpack(
                    self.endian_mark + "h" * length,
                    self.tiftag[pointer : pointer + length * 2],
                )
            else:
                data = struct.unpack(
                    self.endian_mark + "h" * length, value[0 : length * 2]
                )
        elif t == TYPES.SLong:  # SLONG
            if length > 1:
                pointer = struct.unpack(self.endian_mark + "L", value)[0]
                data = struct.unpack(
                    self.endian_mark + "l" * length,
                    self.tiftag[pointer : pointer + length * 4],
                )
            else:
                data = struct.unpack(self.endian_mark + "l" * length, value)
        elif t == TYPES.SRational:  # SRATIONAL
            pointer = struct.unpack(self.endian_mark + "L", value)[0]
            if length > 1:
                data = tuple(
                    (
                        struct.unpack(
                            self.endian_mark + "l",
                            self.tiftag[pointer + x * 8 : pointer + 4 + x * 8],
                        )[0],
                        struct.unpack(
                            self.endian_mark + "l",
                            self.tiftag[pointer + 4 + x * 8 : pointer + 8 + x * 8],
                        )[0],
                    )
                    for x in range(length)
                )
            else:
                data = (
                    struct.unpack(
                        self.endian_mark + "l", self.tiftag[pointer : pointer + 4]
                    )[0],
                    struct.unpack(
                        self.endian_mark + "l", self.tiftag[pointer + 4 : pointer + 8]
                    )[0],
                )
        elif t == TYPES.Float:  # FLOAT
            if length > 1:
                pointer = struct.unpack(self.endian_mark + "L", value)[0]
                data = struct.unpack(
                    self.endian_mark + "f" * length,
                    self.tiftag[pointer : pointer + length * 4],
                )
            else:
                data = struct.unpack(self.endian_mark + "f" * length, value)
        elif t == TYPES.DFloat:  # DOUBLE
            pointer = struct.unpack(self.endian_mark + "L", value)[0]
            data = struct.unpack(
                self.endian_mark + "d" * length,
                self.tiftag[pointer : pointer + length * 8],
            )
        else:
            raise ValueError(
                "Exif might be wrong. Got incorrect value "
                + "type to decode.\n"
                + "tag: "
                + str(val[3])
                + "\ntype: "
                + str(t)
            )

        if isinstance(data, tuple) and (len(data) == 1):
            return data[0]
        else:
            return data


def _get_key_name_dict(exif_dict):
    new_dict = {"thumbnail": exif_dict["thumbnail"]}
    for name in ("0th", "Exif", "1st", "GPS", "Interop", "GlobalParameters"):
        if name in exif_dict:
            new_dict[name] = {
                TAGS[name][tag]["name"]: value for tag, value in exif_dict[name].items()
            }
    return new_dict
