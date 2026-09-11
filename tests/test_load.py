import struct
import unittest

from piexif._exceptions import InvalidImageDataError
from piexif._load import _ExifReader, load


class LoadValidationTests(unittest.TestCase):
    def test_accepts_nested_ifd_without_next_pointer(self):
        # Nested IFD data may end after its entry table.
        data = (b"MM\x00\x2a\x00\x00\x00\x08" + b"\x00\x01"
                + b"\xff\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
        reader = _ExifReader(data)
        reader.endian_mark = ">"
        result = reader.get_ifd_dict(8, "Exif", True)
        self.assertEqual(result[0xFFFF][2], b"\x00\x00\x00\x00")

    def test_rejects_huge_corrupt_value(self):
        data = b"Exif\x00\x00II\x2a\x00\x08\x00\x00\x00"
        data += struct.pack("<H", 1)
        data += struct.pack("<HHI4s", 256, 4, 0xFFFFFFFF,
                            struct.pack("<I", 26))
        data += b"\x00\x00\x00\x00"
        with self.assertRaises(InvalidImageDataError) as caught:
            load(data)
        self.assertEqual(str(caught.exception), "Exif value exceeds the image data.")
