import io
import os
import tempfile
import unittest

from PIL import Image

import piexif

from piexif._common import split_into_segments
from piexif._dump import dump
from piexif._exif import ImageIFD
from piexif._load import load
from piexif._transplant import transplant


class TransplantTests(unittest.TestCase):
    jpeg = b"\xff\xd8\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00\xff\xd9"

    def make_file(self, data):
        descriptor, path = tempfile.mkstemp(prefix="Exif", dir=".")
        self.addCleanup(os.remove, path)
        with os.fdopen(descriptor, "wb") as output:
            output.write(data)
        return os.path.basename(path)

    def test_explicit_transplant_and_legacy_mixed_inputs(self):
        buffer = io.BytesIO()
        piexif.insert_bytes(dump({"0th": {ImageIFD.Orientation: 6}}), self.jpeg, buffer)
        source = buffer.getvalue()
        source_path = self.make_file(source)
        destination_path = self.make_file(self.jpeg)
        for writer, exif_src, image in (
            (piexif.transplant_bytes, source, self.jpeg),
            (piexif.transplant_file, source_path, destination_path),
            (
                piexif.transplant_file,
                source_path.encode("ascii"),
                destination_path.encode("ascii"),
            ),
            (transplant, source_path.encode("ascii"), self.jpeg),
            (transplant, source, destination_path.encode("ascii")),
        ):
            output = io.BytesIO()
            writer(exif_src, image, output)
            self.assertEqual(output.tell(), 0)
            self.assertEqual(output.getvalue(), source)
        with open(destination_path, "rb") as original:
            self.assertEqual(original.read(), self.jpeg)
        piexif.transplant_file(source_path, destination_path)
        self.assertEqual(
            piexif.load_file(destination_path)["0th"][ImageIFD.Orientation], 6
        )
        with open(destination_path, "wb") as original:
            original.write(self.jpeg)
        piexif.transplant_bytes(source, self.jpeg, destination_path)
        with open(destination_path, "rb") as original:
            self.assertEqual(original.read(), source)
        with self.assertRaises(ValueError):
            piexif.transplant_bytes(source, self.jpeg)

    def test_transplant_bytes_never_opens_inputs_as_paths(self):
        buffer = io.BytesIO()
        piexif.insert_bytes(dump({}), self.jpeg, buffer)
        source = buffer.getvalue()
        path = self.make_file(source)
        for exif_src, image in (
            (path.encode("ascii"), self.jpeg),
            (source, path.encode("ascii")),
            (b"", self.jpeg),
            (source, dump({})[6:]),
        ):
            with self.assertRaises(piexif.InvalidImageDataError):
                piexif.transplant_bytes(exif_src, image, path)
            with open(path, "rb") as original:
                self.assertEqual(original.read(), source)

    def test_transplant_preserves_destination_jfif(self):
        exif = dump({"0th": {ImageIFD.Orientation: 6}})
        source, destination, result = io.BytesIO(), io.BytesIO(), io.BytesIO()
        image = Image.new("RGB", (16, 16))
        image.save(source, "JPEG", exif=exif, dpi=(72, 72))
        image.save(destination, "JPEG", dpi=(300, 300))
        transplant(source.getvalue(), destination.getvalue(), result)
        before = split_into_segments(destination.getvalue())
        after = split_into_segments(result.getvalue())
        self.assertEqual(after[1], before[1])
        self.assertEqual(load(result.getvalue())["0th"][274], 6)
        with Image.open(result) as output:
            self.assertEqual(output.info["dpi"], (300, 300))
