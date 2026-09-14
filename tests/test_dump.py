import unittest

from piexif._dump import dump
from piexif._exceptions import InvalidImageDataError
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

    def test_invalid_numeric_values(self):
        cases = [
            ("Exif", ExifIFD.BrightnessValue, (4294966933, 100)),
            ("Exif", ExifIFD.BrightnessValue, (-2147483649, 100)),
            ("0th", ImageIFD.XResolution, (-1, 100)),
            ("0th", ImageIFD.ImageWidth, 4294967296),
            ("0th", ImageIFD.Orientation, 65536),
            ("0th", ImageIFD.Orientation, -1),
            ("0th", ImageIFD.TimeZoneOffset, 32768),
            ("GPS", GPSIFD.GPSAltitudeRef, 256),
            ("Exif", ExifIFD.ShutterSpeedValue, "0.00080000"),
            ("Exif", ExifIFD.MaxApertureValue, "2.0"),
            ("Exif", ExifIFD.FocalLength, "50.0"),
            ("Exif", ExifIFD.FocalLengthIn35mmFilm, "50.0"),
        ]
        for ifd, tag, value in cases:
            with self.assertRaises(InvalidImageDataError) as caught:
                dump({ifd: {tag: value}})
            self.assertIn(str(tag), str(caught.exception))
            self.assertIn(ifd, str(caught.exception))

    def test_signed_brightness_roundtrip(self):
        for value in ((-363, 100), (-2147483648, 1), (2147483647, 1)):
            exif = dump({"Exif": {ExifIFD.BrightnessValue: value}})
            self.assertEqual(load(exif)["Exif"][ExifIFD.BrightnessValue], value)
