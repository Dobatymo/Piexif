import struct
import unittest

from piexif._dump import dump
from piexif._exceptions import InvalidImageDataError
from piexif._exif import ExifIFD, GPSIFD, ImageIFD, InteropIFD
from piexif._load import load


class DumpValidationTests(unittest.TestCase):
    def test_nested_ifds_have_null_next_pointers(self):
        cases = [
            {"Exif": {ExifIFD.ExifVersion: b"0230"}},
            {"GPS": {GPSIFD.GPSAltitudeRef: 0}},
            {"Interop": {InteropIFD.InteroperabilityIndex: b"R98"}},
            {"Exif": {ExifIFD.DateTimeOriginal: b"2026:09:14 12:34:56"},
             "GPS": {GPSIFD.GPSLatitude: ((1, 1), (2, 1), (3, 1))},
             "Interop": {InteropIFD.InteroperabilityIndex: b"R98"}},
        ]
        for source in cases:
            exif = dump(source)
            loaded = load(exif)
            tiff = exif[6:]
            pointers = []
            if "Exif" in source or "Interop" in source:
                pointers.append(loaded["0th"][ImageIFD.ExifTag])
            if "GPS" in source:
                pointers.append(loaded["0th"][ImageIFD.GPSTag])
            if "Interop" in source:
                pointers.append(loaded["Exif"][ExifIFD.InteroperabilityTag])
            for pointer in pointers:
                count = struct.unpack_from(">H", tiff, pointer)[0]
                end = pointer + 2 + count * 12
                self.assertEqual(tiff[end:end + 4], b"\x00" * 4)
                for pos in range(pointer + 2, end, 12):
                    tag, kind, length, offset = struct.unpack_from(">HHII", tiff, pos)
                    size = length * (8 if kind == 5 else 1)
                    if kind in (2, 5, 7) and size > 4:
                        self.assertGreaterEqual(offset, end + 4)
            for ifd, values in source.items():
                for tag, value in values.items():
                    self.assertEqual(loaded[ifd][tag], value)

    def test_interop_without_exif(self):
        interop = {InteropIFD.InteroperabilityIndex: b"R98"}
        for siblings in ({}, {"0th": {ImageIFD.Make: b"Camera"},
                              "GPS": {GPSIFD.GPSAltitudeRef: 0}}):
            source = dict(siblings, Interop=interop)
            exif = dump(source)
            self.assertEqual(exif, dump(dict(source, Exif={})))
            loaded = load(exif)
            self.assertEqual(loaded["Interop"], interop)
            self.assertIn(ImageIFD.ExifTag, loaded["0th"])
            self.assertIn(ExifIFD.InteroperabilityTag, loaded["Exif"])
            for ifd, values in siblings.items():
                for tag, value in values.items():
                    self.assertEqual(loaded[ifd][tag], value)
            self.assertEqual(source, dict(siblings, Interop=interop))
            self.assertEqual(interop, {InteropIFD.InteroperabilityIndex: b"R98"})

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

    def test_components_configuration_roundtrip(self):
        value = b"\x01\x02\x03\x00"
        exif = dump({"Exif": {ExifIFD.ComponentsConfiguration: value}})
        self.assertEqual(load(exif)["Exif"][ExifIFD.ComponentsConfiguration], value)

    def test_components_configuration_rejects_tuple(self):
        with self.assertRaises(InvalidImageDataError) as caught:
            dump({"Exif": {ExifIFD.ComponentsConfiguration: (1, 2, 3, 0)}})
        self.assertIn(str(ExifIFD.ComponentsConfiguration), str(caught.exception))
        self.assertIn("Exif", str(caught.exception))

    def test_scene_type_roundtrip(self):
        value = b"\x01"
        exif = dump({"Exif": {ExifIFD.SceneType: value}})
        self.assertEqual(load(exif)["Exif"][ExifIFD.SceneType], value)

    def test_scene_type_rejects_integer(self):
        with self.assertRaises(InvalidImageDataError) as caught:
            dump({"Exif": {ExifIFD.SceneType: 1}})
        self.assertIn(str(ExifIFD.SceneType), str(caught.exception))
        self.assertIn("Exif", str(caught.exception))

    def test_signed_brightness_roundtrip(self):
        for value in ((-363, 100), (-2147483648, 1), (2147483647, 1)):
            exif = dump({"Exif": {ExifIFD.BrightnessValue: value}})
            self.assertEqual(load(exif)["Exif"][ExifIFD.BrightnessValue], value)
