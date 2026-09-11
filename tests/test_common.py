import struct
import unittest

from piexif._common import merge_segments


def segment(marker, payload):
    return marker + struct.pack(">H", len(payload) + 2) + payload


class MergeSegmentsTests(unittest.TestCase):
    def setUp(self):
        self.app0 = segment(b"\xff\xe0", b"JFIF\x00original")
        self.xmp = segment(b"\xff\xe1", b"http://ns.adobe.com/xap/1.0/\x00xmp")
        self.icc = segment(b"\xff\xe2", b"ICC_PROFILE\x00profile")
        self.old = segment(b"\xff\xe1", b"Exif\x00\x00old")
        self.new = segment(b"\xff\xe1", b"Exif\x00\x00new")
        self.tail = b"\xff\xdascan-data\xff\xd9"
        self.other = [b"\xff\xd8", self.app0, self.xmp, self.icc]

    def test_insert_preserves_other_segments(self):
        segments = self.other + [self.tail]
        expected = self.other[:2] + [self.new] + self.other[2:] + [self.tail]
        self.assertEqual(merge_segments(segments, self.new), b"".join(expected))

    def test_replace_exif_after_other_metadata(self):
        segments = self.other + [self.old, self.tail]
        self.assertEqual(merge_segments(segments, self.new),
                         b"".join(self.other + [self.new, self.tail]))

    def test_duplicate_exif_replaced_once(self):
        segments = self.other + [self.old, self.old, self.tail]
        self.assertEqual(merge_segments(segments, self.new),
                         b"".join(self.other + [self.new, self.tail]))

    def test_remove_all_exif_preserves_other_segments(self):
        segments = self.other + [self.old, self.old, self.tail]
        self.assertEqual(merge_segments(segments, None),
                         b"".join(self.other + [self.tail]))

    def test_default_preserves_original_bytes(self):
        segments = [b"\xff\xd8", self.app0, self.old, self.tail]
        expected = b"".join(segments)
        self.assertEqual(merge_segments(segments), expected)
