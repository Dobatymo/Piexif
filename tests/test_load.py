import os
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

    def test_rejects_truncated_interop_ifd(self):
        for endian, marker in (("<", b"II"), (">", b"MM")):
            for pointer in (39, 40, 0xFFFFFFFF):
                data = marker + struct.pack(endian + "HIH", 42, 8, 1)
                data += struct.pack(endian + "HHII", 34665, 4, 1, 26)
                data += b"\x00" * 4
                data += struct.pack(endian + "HHHII", 1, 40965, 4, 1, pointer)
                with self.assertRaises(InvalidImageDataError) as caught:
                    load(data)
                self.assertEqual(str(caught.exception), "Invalid IFD offset.")

    def test_rejects_huge_corrupt_value(self):
        data = b"Exif\x00\x00II\x2a\x00\x08\x00\x00\x00"
        data += struct.pack("<H", 1)
        data += struct.pack("<HHI4s", 256, 4, 0xFFFFFFFF,
                            struct.pack("<I", 26))
        data += b"\x00\x00\x00\x00"
        with self.assertRaises(InvalidImageDataError) as caught:
            load(data)
        self.assertEqual(str(caught.exception), "Exif value exceeds the image data.")

    def check_ascii_value(self, payload, expected, trailing=b""):
        for endian, marker in (("<", b"II"), (">", b"MM")):
            value = (payload.ljust(4, b"X") if len(payload) <= 4
                     else struct.pack(endian + "I", 26))
            data = marker + struct.pack(endian + "HIH", 42, 8, 1)
            data += struct.pack(endian + "HHI4s", 270, 2, len(payload), value)
            data += b"\x00" * 4
            if len(payload) > 4:
                data += payload
            data += trailing
            self.assertEqual(load(data)["0th"][270], expected)

    def test_ascii_without_terminator_inline(self):
        for payload in (b"A", b"AB", b"ABC", b"ABCD"):
            self.check_ascii_value(payload, payload, b"unrelated\x00")

    def test_ascii_without_terminator_at_offset(self):
        for trailing in (b"", b"\x00", b"unrelated\x00"):
            self.check_ascii_value(b"2021:08:06 16:10:41",
                                   b"2021:08:06 16:10:41", trailing)

    def test_ascii_terminator_preserves_existing_behavior(self):
        for payload in (b"\x00", b"A\x00", b"AB\x00\x00", b"long\x00value\x00\x00"):
            self.check_ascii_value(payload, payload[:-1], b"unrelated")

    def test_ascii_zero_count_does_not_read_inline_padding(self):
        self.check_ascii_value(b"", b"")

    def test_ascii_rejects_out_of_bounds_value(self):
        for count, pointer in ((5, 26), (0xFFFFFFFF, 26), (5, 0xFFFFFFFF)):
            data = b"II" + struct.pack("<HIH", 42, 8, 1)
            data += struct.pack("<HHII", 270, 2, count, pointer)
            data += b"\x00" * 4 + b"ABCD"
            with self.assertRaises(InvalidImageDataError):
                load(data)

    def test_load_simple_webp_without_exif(self):
        path = os.path.join(os.path.dirname(__file__), "images", "pil2.webp")
        with open(path, "rb") as source:
            data = source.read()
        expected = {"0th": {}, "Exif": {}, "GPS": {}, "Interop": {},
                    "1st": {}, "thumbnail": None}
        self.assertEqual(load(data), expected)
        self.assertEqual(load(path), expected)
