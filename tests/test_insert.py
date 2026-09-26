import io
import os
import tempfile
import unittest

from PIL import Image

import piexif

from piexif._common import split_into_segments
from piexif._dump import dump
from piexif._exif import ImageIFD
from piexif._insert import insert
from piexif._load import load


class InsertTests(unittest.TestCase):
    jpeg = b"\xff\xd8\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00\xff\xd9"

    def make_file(self, data, prefix="insert-"):
        descriptor, path = tempfile.mkstemp(prefix=prefix, dir=".")
        self.addCleanup(os.remove, path)
        with os.fdopen(descriptor, "wb") as output:
            output.write(data)
        return path

    def test_explicit_insert_entry_points(self):
        exif = dump({"0th": {ImageIFD.Orientation: 6}})
        image = Image.new("RGB", (2, 3), "red")
        self.addCleanup(image.close)
        for image_format in ("JPEG", "PNG", "WEBP"):
            source = io.BytesIO()
            image.save(source, image_format)
            data = source.getvalue()
            path = self.make_file(data)
            for writer, image_input in (
                (piexif.insert_bytes, data),
                (piexif.insert_file, path),
            ):
                output = io.BytesIO()
                writer(exif, image_input, output)
                self.assertEqual(output.tell(), 0)
                self.assertEqual(
                    load(output.getvalue())["0th"][ImageIFD.Orientation], 6
                )
                with Image.open(io.BytesIO(data)) as before:
                    with Image.open(output) as after:
                        self.assertEqual(before.tobytes(), after.tobytes())
            with open(path, "rb") as original:
                self.assertEqual(original.read(), data)
            piexif.insert_file(exif, path)
            self.assertEqual(load(path)["0th"][ImageIFD.Orientation], 6)
            with open(path, "wb") as original:
                original.write(data)
            piexif.insert_bytes(exif, data, path)
            self.assertEqual(load(path)["0th"][ImageIFD.Orientation], 6)

    def test_insert_file_does_not_detect_format_from_filename(self):
        exif = dump({"0th": {ImageIFD.Orientation: 6}})
        path = self.make_file(self.jpeg, "RIFF0000WEBP")
        filename = os.path.basename(path)
        for name in (filename, filename.encode("ascii")):
            with open(path, "wb") as original:
                original.write(self.jpeg)
            piexif.insert_file(exif, name)
            self.assertEqual(piexif.load_file(name)["0th"][ImageIFD.Orientation], 6)

    def test_insert_bytes_rejects_invalid_input_without_writing(self):
        exif = dump({})
        filename = os.path.basename(self.make_file(self.jpeg)).encode("ascii")
        destination = self.make_file(b"existing destination")
        for data in (filename, b"", b"not an image", exif, exif[6:]):
            with self.assertRaises(piexif.InvalidImageDataError):
                piexif.insert_bytes(exif, data, destination)
            with open(destination, "rb") as original:
                self.assertEqual(original.read(), b"existing destination")
        with self.assertRaises(ValueError):
            piexif.insert_bytes(exif, self.jpeg)

    def check_insert(self, existing):
        old_exif = dump({"0th": {ImageIFD.Orientation: 6}})
        new_exif = dump({"0th": {ImageIFD.Orientation: 1}})
        source = io.BytesIO()
        image = Image.new("RGB", (16, 16), "red")
        image.save(source, "JPEG", dpi=(300, 300), exif=old_exif if existing else b"")
        result = io.BytesIO()
        insert(new_exif, source.getvalue(), result)
        before = split_into_segments(source.getvalue())
        after = split_into_segments(result.getvalue())

        def without_exif(parts):
            return [
                part
                for part in parts
                if not (part[:2] == b"\xff\xe1" and part[4:10] == b"Exif\x00\x00")
            ]

        self.assertEqual(without_exif(before), without_exif(after))
        self.assertEqual(after[1], before[1])
        self.assertEqual(load(result.getvalue())["0th"][274], 1)
        with Image.open(result) as output:
            self.assertEqual(output.info["dpi"], (300, 300))
            self.assertEqual(
                output.tobytes(), Image.open(io.BytesIO(source.getvalue())).tobytes()
            )

    def test_insert_preserves_jfif(self):
        self.check_insert(False)

    def test_replace_preserves_jfif(self):
        self.check_insert(True)
