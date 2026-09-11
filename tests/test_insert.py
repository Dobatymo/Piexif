import io
import unittest

from PIL import Image

from piexif._common import split_into_segments
from piexif._dump import dump
from piexif._exif import ImageIFD
from piexif._insert import insert
from piexif._load import load


class InsertTests(unittest.TestCase):
    def check_insert(self, existing):
        old_exif = dump({"0th": {ImageIFD.Orientation: 6}})
        new_exif = dump({"0th": {ImageIFD.Orientation: 1}})
        source = io.BytesIO()
        image = Image.new("RGB", (16, 16), "red")
        image.save(source, "JPEG", dpi=(300, 300),
                   exif=old_exif if existing else b"")
        result = io.BytesIO()
        insert(new_exif, source.getvalue(), result)
        before = split_into_segments(source.getvalue())
        after = split_into_segments(result.getvalue())
        without_exif = lambda parts: [part for part in parts
            if not (part[:2] == b"\xff\xe1" and part[4:10] == b"Exif\x00\x00")]
        self.assertEqual(without_exif(before), without_exif(after))
        self.assertEqual(after[1], before[1])
        self.assertEqual(load(result.getvalue())["0th"][274], 1)
        with Image.open(result) as output:
            self.assertEqual(output.info["dpi"], (300, 300))
            self.assertEqual(output.tobytes(), Image.open(io.BytesIO(source.getvalue())).tobytes())

    def test_insert_preserves_jfif(self):
        self.check_insert(False)

    def test_replace_preserves_jfif(self):
        self.check_insert(True)
