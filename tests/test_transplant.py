import io
import unittest

from PIL import Image

from piexif._common import split_into_segments
from piexif._dump import dump
from piexif._exif import ImageIFD
from piexif._load import load
from piexif._transplant import transplant


class TransplantTests(unittest.TestCase):
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
