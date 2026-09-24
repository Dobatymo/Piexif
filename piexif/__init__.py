from ._remove import remove, remove_bytes, remove_file
from ._load import load, load_bytes, load_file, load_ifds
from ._dump import dump, dump_ifds
from ._transplant import transplant
from ._insert import insert
from ._exif import TYPES, TAGS, ImageIFD, ExifIFD, GPSIFD, InteropIFD
from ._exceptions import InvalidImageDataError


VERSION = "1.1.3"


__all__ = [
    "remove",
    "remove_bytes",
    "remove_file",
    "load",
    "load_bytes",
    "load_file",
    "load_ifds",
    "dump",
    "dump_ifds",
    "transplant",
    "insert",
    "TYPES",
    "TAGS",
    "ImageIFD",
    "ExifIFD",
    "GPSIFD",
    "InteropIFD",
    "InvalidImageDataError",
    "VERSION",
]
