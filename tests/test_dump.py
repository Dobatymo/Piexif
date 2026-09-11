import unittest

from piexif._dump import dump
from piexif._exif import ExifIFD, GPSIFD, ImageIFD
from piexif._load import load


class DumpValidationTests(unittest.TestCase):
    def test_invalid_rational_type(self):
        exif_dict = {"GPS": {GPSIFD.GPSLatitude: "51,30,0"}}
        with self.assertRaises(ValueError):
            dump(exif_dict)

    def test_as_shot_neutral_rational_roundtrip(self):
        value = ((1000, 1693), (1000, 990), (1000, 1442))
        exif = dump({"0th": {ImageIFD.AsShotNeutral: value}})
        self.assertEqual(load(exif)["0th"][ImageIFD.AsShotNeutral], value)

    def test_as_shot_neutral_short_roundtrip(self):
        value = (100, 200, 300)
        exif = dump({"0th": {ImageIFD.AsShotNeutral: value}})
        self.assertEqual(load(exif)["0th"][ImageIFD.AsShotNeutral], value)
