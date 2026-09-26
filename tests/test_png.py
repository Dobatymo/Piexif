import io
import os
import struct
import tempfile
import unittest

from PIL import Image

import piexif
from piexif import _png


class PngTests(unittest.TestCase):
    def setUp(self):
        source = io.BytesIO()
        with Image.new("RGB", (2, 3), "red") as image:
            image.save(source, "PNG")
        self.png = source.getvalue()
        descriptor, self.path = tempfile.mkstemp(suffix=".png")
        os.close(descriptor)
        self.addCleanup(os.remove, self.path)

    def test_trailing_bytes_are_ignored_for_exif_and_preserved_when_editing(self):
        exif = piexif.dump({"0th": {piexif.ImageIFD.Orientation: 6}})
        fake_exif = _png._chunk(b"eXIf", exif[6:])
        for trailer in (b"x", b"\xff" * 32, fake_exif):
            original = self.png + trailer
            with open(self.path, "wb") as output:
                output.write(original)
            for source, reader, ifd_reader, insert, remove in (
                (
                    original,
                    piexif.load_bytes,
                    piexif.load_ifds_bytes,
                    piexif.insert_bytes,
                    piexif.remove_bytes,
                ),
                (
                    self.path,
                    piexif.load_file,
                    piexif.load_ifds_file,
                    piexif.insert_file,
                    piexif.remove_file,
                ),
            ):
                self.assertEqual(reader(source)["0th"], {})
                self.assertEqual(ifd_reader(source), [{"tags": {}, "subifds": []}])
                unchanged = io.BytesIO()
                remove(source, unchanged)
                self.assertEqual(unchanged.getvalue(), original)
                inserted = io.BytesIO()
                insert(exif, source, inserted)
                data = inserted.getvalue()
                self.assertTrue(data.endswith(trailer))
                self.assertEqual(piexif.load_bytes(data)["0th"], {274: 6})
                self.assertEqual(piexif.load_ifds_bytes(data)[0]["tags"], {274: 6})
                replaced = io.BytesIO()
                piexif.insert_bytes(piexif.dump({"0th": {274: 1}}), data, replaced)
                self.assertEqual(
                    piexif.load_bytes(replaced.getvalue())["0th"], {274: 1}
                )
                removed = io.BytesIO()
                piexif.remove_bytes(replaced.getvalue(), removed)
                self.assertEqual(removed.getvalue(), original)
                with Image.open(inserted) as image:
                    self.assertEqual(image.tobytes(), b"\xff\x00\x00" * 6)

    def test_truncated_chunks_before_iend_are_still_rejected(self):
        # A truncated IEND, or an oversized IDAT followed by a valid IEND.
        invalid = (
            self.png[:-1],
            self.png[:33] + struct.pack(">I", 1000) + b"IDAT" + self.png[-12:],
        )
        for data in invalid:
            for reader in (piexif.load_bytes, piexif.load_ifds_bytes):
                with self.assertRaises(piexif.InvalidImageDataError):
                    reader(data)
            with self.assertRaises(piexif.InvalidImageDataError):
                piexif.insert_bytes(piexif.dump({}), data, io.BytesIO())
            with self.assertRaises(piexif.InvalidImageDataError):
                piexif.remove_bytes(data, io.BytesIO())
