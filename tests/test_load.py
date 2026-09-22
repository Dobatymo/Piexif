import os
import struct
import unittest

import piexif

from piexif._exceptions import InvalidImageDataError
from piexif._dump import dump
from piexif._load import _ExifReader, load, load_ifds


class LoadValidationTests(unittest.TestCase):
    def test_public_loader_entry_points(self):
        data = self.mrc_data(">", b"MM")
        self.assertIs(piexif.load, load)
        self.assertIs(piexif.load_ifds, load_ifds)
        self.assertIsInstance(load(data), dict)
        self.assertIsInstance(load_ifds(data), list)
        self.assertEqual(load_ifds(data, True), load_ifds(data, key_is_name=True))

    def mrc_data(self, endian, marker, kind=4, following=76):
        data = marker + struct.pack(endian + "HIH", 42, 8, 2)
        data += struct.pack(endian + "HHII", 254, 4, 1, 18)
        data += struct.pack(endian + "HHII", 330, kind, 1, 38) + b"\x00" * 4
        for offset, order, next_ifd in ((38, 1, following), (76, 2, 0)):
            data += struct.pack(endian + "H", 2)
            data += struct.pack(endian + "HHII", 254, 4, 1, 16)
            data += struct.pack(endian + "HHII", 34732, 4, 2, offset + 30)
            data += struct.pack(endian + "III", next_ifd, 1, order)
        return data

    def test_mrc_long_and_ifd_pointer_chains(self):
        for endian, marker in (("<", b"II"), (">", b"MM")):
            for kind in (4, 13):
                data = self.mrc_data(endian, marker, kind)
                loaded = load_ifds(data)
                self.assertEqual(len(loaded), 1)
                self.assertEqual(loaded[0]["subifds"], [[
                    {"tags": {254: 16, 34732: (1, 1)}, "subifds": []},
                    {"tags": {254: 16, 34732: (1, 2)}, "subifds": []}]])

    def test_mrc_rejects_cycles_and_invalid_offsets(self):
        for endian, marker in (("<", b"II"), (">", b"MM")):
            for following in (38, 0xFFFFFFFF):
                data = self.mrc_data(endian, marker, following=following)
                self.assertNotIn("IFDs", load(data))
                with self.assertRaises(InvalidImageDataError):
                    load_ifds(data)
            self.assertNotIn("IFDs", load(self.mrc_data(endian, marker)[:75]))
            with self.assertRaises(InvalidImageDataError):
                load_ifds(self.mrc_data(endian, marker)[:75])

    def test_load_ifds_is_separate_from_standard_load(self):
        for endian, marker in (("<", b"II"), (">", b"MM")):
            data = self.mrc_data(endian, marker)
            standard = load(data)
            self.assertNotIn("IFDs", standard)
            self.assertEqual(standard["0th"], {254: 18, 330: 38})
            self.assertEqual(standard["1st"], {})
            # Existing positional key_is_name calls keep their meaning.
            named = load(data, True)
            self.assertNotIn("IFDs", named)
            self.assertEqual(named["0th"], {"NewSubfileType": 18, "SubIFDs": 38})
            graph = load_ifds(data, True)
            self.assertEqual(graph[0]["tags"], {"NewSubfileType": 18})
            # The default result still accepts replacement image dictionaries.
            standard["0th"] = {271: b"Replacement"}
            self.assertEqual(load(dump(standard))["0th"], standard["0th"])

    def test_global_parameters_known_tiff_fields(self):
        for endian, marker in (("<", b"II"), (">", b"MM")):
            data = marker + struct.pack(endian + "HIH", 42, 8, 1)
            data += struct.pack(endian + "HHII", 400, 4, 1, 26)
            data += b"\x00" * 4
            data += struct.pack(endian + "H", 2)
            data += struct.pack(endian + "HHI", 274, 3, 1)
            data += struct.pack(endian + "H", 1) + b"\x00" * 2
            data += struct.pack(endian + "HHII", 401, 4, 1, 1)
            data += b"\x00" * 4
            self.assertEqual(load(data)["GlobalParameters"], {274: 1, 401: 1})

    def test_global_parameters_long_and_ifd_pointers(self):
        for endian, marker in (("<", b"II"), (">", b"MM")):
            for kind in (4, 13):
                data = marker + struct.pack(endian + "HIH", 42, 8, 1)
                data += struct.pack(endian + "HHII", 400, kind, 1, 26)
                data += b"\x00" * 4
                data += struct.pack(endian + "HHHII", 1, 401, 4, 1, 1)
                data += b"\x00" * 4
                loaded = load(data)
                self.assertEqual(loaded["0th"][400], 26)
                self.assertEqual(loaded["GlobalParameters"], {401: 1})
                self.assertEqual(load(data, key_is_name=True)["GlobalParameters"],
                                 {"ProfileType": 1})
                encoded = dump(loaded)
                # Writing keeps the existing, valid LONG representation.
                self.assertEqual(struct.unpack_from(">HHI", encoded, 16),
                                 (400, 4, 1))
                self.assertEqual(load(encoded)["GlobalParameters"], {401: 1})

    def test_global_parameters_pointer_bounds(self):
        for endian, marker in (("<", b"II"), (">", b"MM")):
            for kind in (4, 13):
                for pointer in (26, 0xFFFFFFFF):
                    data = marker + struct.pack(endian + "HIH", 42, 8, 1)
                    data += struct.pack(endian + "HHII", 400, kind, 1, pointer)
                    data += b"\x00" * 4
                    with self.assertRaises(InvalidImageDataError) as caught:
                        load(data)
                    self.assertEqual(str(caught.exception), "Invalid IFD offset.")

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

    def check_ascii_value(self, payload, expected, trailing=b"", tag=270):
        for endian, marker in (("<", b"II"), (">", b"MM")):
            value = (payload.ljust(4, b"X") if len(payload) <= 4
                     else struct.pack(endian + "I", 26))
            data = marker + struct.pack(endian + "HIH", 42, 8, 1)
            data += struct.pack(endian + "HHI4s", tag, 2, len(payload), value)
            data += b"\x00" * 4
            if len(payload) > 4:
                data += payload
            data += trailing
            self.assertEqual(load(data)["0th"][tag], expected)

    def test_make_preserves_final_character(self):
        for payload in (b"Apple", b"Apple\x00"):
            self.check_ascii_value(payload, b"Apple", b"unrelated\x00", tag=271)

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
