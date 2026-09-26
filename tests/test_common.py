import io
import os
import struct
import tempfile
import unittest

import piexif

from piexif._common import (
    get_exif_seg,
    merge_segments,
    read_exif_from_file,
    split_into_segments,
)
from piexif._remove import remove_bytes


def segment(marker, payload):
    return marker + struct.pack(">H", len(payload) + 2) + payload


class OutputValidationTests(unittest.TestCase):
    def test_unsupported_removal_preserves_files(self):
        descriptor, source = tempfile.mkstemp()
        os.close(descriptor)
        self.addCleanup(os.remove, source)
        descriptor, destination = tempfile.mkstemp()
        with os.fdopen(descriptor, "wb") as output:
            output.write(b"existing destination")
        self.addCleanup(os.remove, destination)
        exif = piexif.dump({})
        for remove in (piexif.remove, piexif.remove_file):
            for data in (b"", b"not an image", exif, exif[6:]):
                with open(source, "wb") as output:
                    output.write(data)
                for target in (None, destination):
                    with self.assertRaises(piexif.InvalidImageDataError):
                        remove(source, target)
                    with open(source, "rb") as original:
                        self.assertEqual(original.read(), data)
                    with open(destination, "rb") as original:
                        self.assertEqual(original.read(), b"existing destination")


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
        self.assertEqual(
            merge_segments(segments, self.new),
            b"".join(self.other + [self.new, self.tail]),
        )

    def test_duplicate_exif_replaced_once(self):
        segments = self.other + [self.old, self.old, self.tail]
        self.assertEqual(
            merge_segments(segments, self.new),
            b"".join(self.other + [self.new, self.tail]),
        )

    def test_remove_all_exif_preserves_other_segments(self):
        segments = self.other + [self.old, self.old, self.tail]
        self.assertEqual(
            merge_segments(segments, None), b"".join(self.other + [self.tail])
        )

    def test_replace_exif_preserves_trailing_fill_bytes(self):
        segments = [b"\xff\xd8", self.old + b"\xff\xff", self.tail]
        expected = b"".join([b"\xff\xd8", self.new + b"\xff\xff", self.tail])
        self.assertEqual(merge_segments(segments, self.new), expected)

    def test_remove_exif_preserves_trailing_fill_bytes(self):
        segments = [b"\xff\xd8", self.old + b"\xff\xff", self.tail]
        expected = b"".join([b"\xff\xd8", b"\xff\xff", self.tail])
        self.assertEqual(merge_segments(segments, None), expected)

    def test_remove_bytes_preserves_trailing_fill_bytes(self):
        source = b"\xff\xd8" + self.old + b"\xff\xff" + self.tail
        output = io.BytesIO()
        remove_bytes(source, output)
        self.assertEqual(output.getvalue(), b"\xff\xd8" + b"\xff\xff" + self.tail)

    def test_default_preserves_original_bytes(self):
        segments = [b"\xff\xd8", self.app0, self.old, self.tail]
        expected = b"".join(segments)
        self.assertEqual(merge_segments(segments), expected)


class SplitSegmentsTests(unittest.TestCase):
    def test_file_reader_rejects_invalid_segment_lengths(self):
        exif = piexif.dump({"0th": {piexif.ImageIFD.Make: b"camera"}})
        descriptor, filename = tempfile.mkstemp()
        os.close(descriptor)
        self.addCleanup(os.remove, filename)
        for segment_data in (
            b"\xff\xe1",
            b"\xff\xe1\x00",
            b"\xff\xe1\x00\x00",
            b"\xff\xe1\x00\x01",
            b"\xff\xe1" + struct.pack(">H", len(exif) + 102) + exif,
            b"\xff\xfe\x00\x05ab",
        ):
            with open(filename, "wb") as output:
                output.write(b"\xff\xd8" + segment_data)
            for reader in (piexif.load_file, piexif.load_ifds_file):
                with self.assertRaises(piexif.InvalidImageDataError):
                    reader(filename)

    def test_file_reader_handles_lengthless_markers(self):
        exif = segment(b"\xff\xe1", piexif.dump({}))
        descriptor, filename = tempfile.mkstemp()
        os.close(descriptor)
        self.addCleanup(os.remove, filename)
        for metadata in (b"", exif):
            with open(filename, "wb") as output:
                output.write(
                    b"\xff\xd8\xff\x01"
                    + segment(b"\xff\xe0", b"")
                    + metadata
                    + b"\xff\xd9"
                )
            self.assertEqual(read_exif_from_file(filename), metadata or None)

    def test_file_reader_ignores_incomplete_exif_identifiers(self):
        lookalikes = b"".join(
            segment(b"\xff\xe1", payload)
            for payload in (b"ExifXXjunk", b"Exif\x00Xjunk", b"Exif", b"Exif\x00")
        )
        exif = segment(
            b"\xff\xe1", piexif.dump({"0th": {piexif.ImageIFD.Make: b"camera"}})
        )
        tail = b"\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00\xff\xd9"
        descriptor, filename = tempfile.mkstemp()
        os.close(descriptor)
        self.addCleanup(os.remove, filename)
        for valid_exif in (b"", exif):
            source = b"\xff\xd8" + lookalikes + valid_exif + tail
            with open(filename, "wb") as output:
                output.write(source)
            self.assertEqual(read_exif_from_file(filename), valid_exif or None)
            self.assertEqual(piexif.load_file(filename), piexif.load_bytes(source))

    def _source_with_fill_bytes(self):
        app0 = segment(b"\xff\xe0", b"JFIF\x00")
        exif = segment(b"\xff\xe1", b"Exif\x00\x00data")
        tail = b"\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00\xff\x00\xff\xd9"
        source = b"\xff\xd8\xff\xff" + app0 + b"\xff\xff\xff" + exif + tail
        return source, app0, exif

    def test_marker_fill_bytes_are_preserved(self):
        source, app0, exif = self._source_with_fill_bytes()

        segments = split_into_segments(source)

        self.assertEqual(b"".join(segments), source)
        self.assertEqual(get_exif_seg(segments), exif)
        self.assertEqual(segments[0], b"\xff\xd8\xff\xff")
        self.assertEqual(segments[1], app0 + b"\xff\xff\xff")
        replacement = segment(b"\xff\xe1", b"Exif\x00\x00new")
        self.assertEqual(
            merge_segments(segments, replacement), source.replace(exif, replacement)
        )

    def test_file_reader_accepts_marker_fill_bytes(self):
        source, _app0, exif = self._source_with_fill_bytes()
        descriptor, filename = tempfile.mkstemp()
        try:
            with os.fdopen(descriptor, "wb") as f:
                f.write(source)
            self.assertEqual(read_exif_from_file(filename), exif)
        finally:
            os.remove(filename)
