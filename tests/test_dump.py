import unittest

from piexif._dump import dump
from piexif._exif import ExifIFD, GPSIFD, ImageIFD


class DumpValidationTests(unittest.TestCase):
    def test_invalid_rational_type(self):
        exif_dict = {"GPS": {GPSIFD.GPSLatitude: "51,30,0"}}
        with self.assertRaises(ValueError):
            dump(exif_dict)
