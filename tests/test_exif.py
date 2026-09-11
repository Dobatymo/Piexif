import unittest

from piexif._dump import dump
from piexif._exif import ImageIFD
from piexif._load import load


class ExifTagTests(unittest.TestCase):
    def test_dump_negative_timezone_offset(self):
        exif_dict = {"0th": {ImageIFD.TimeZoneOffset: -5}}
        exif_bytes = dump(exif_dict)
        self.assertEqual(
            load(exif_bytes)["0th"][ImageIFD.TimeZoneOffset], -5
        )
