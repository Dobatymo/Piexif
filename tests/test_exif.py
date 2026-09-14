import struct
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

    def test_camera_label(self):
        self.assertEqual(ImageIFD.CameraLabel, 51105)
        value = b"Camera A"
        encoded = dump({"0th": {ImageIFD.CameraLabel: value}})
        self.assertEqual(struct.unpack(">HHI", encoded[16:24]), (51105, 2, 9))
        self.assertEqual(load(encoded)["0th"][51105], value)

    def test_raw_to_preview_gain(self):
        self.assertEqual(ImageIFD.RawToPreviewGain, 51112)
        value = 1.25
        encoded = dump({"0th": {ImageIFD.RawToPreviewGain: value}})
        self.assertEqual(struct.unpack(">HHI", encoded[16:24]), (51112, 12, 1))
        self.assertEqual(load(encoded)["0th"][51112], value)
