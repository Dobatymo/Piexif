import os
import struct
import unittest

from piexif._dump import dump
from piexif._webp import (
    get_exif,
    get_file_header,
    insert,
    insert_exif_into_chunks,
    merge_chunks,
    remove,
    set_vp8x,
    split,
)


def chunk(fourcc, data):
    return {
        "fourcc": fourcc,
        "length_bytes": struct.pack("<L", len(data)),
        "data": data,
    }


def webp(chunks):
    payload = merge_chunks(chunks)
    return b"RIFF" + struct.pack("<L", len(payload) + 4) + b"WEBP" + payload


class WebpExifChunkTests(unittest.TestCase):
    def setUp(self):
        self.chunks = [
            chunk(b"VP8X", b"\x00" * 10),
            chunk(b"EXIF", b"old"),
            chunk(b"EXIF", b"old2"),
            chunk(b"VP8 ", b""),
        ]

    def test_insert_replaces_all_exif_chunks_without_mutating_input(self):
        original = [dict(value) for value in self.chunks]

        result = insert_exif_into_chunks(self.chunks, b"new")

        self.assertEqual(self.chunks, original)
        self.assertEqual(
            [value["data"] for value in result if value["fourcc"] == b"EXIF"],
            [b"new"],
        )

    def test_remove_removes_all_exif_chunks(self):
        result = remove(webp(self.chunks))

        self.assertIsNone(get_exif(result))


class WebpCanvasTests(unittest.TestCase):
    def setUp(self):
        path = os.path.join(os.path.dirname(__file__), "images", "animated_canvas.webp")
        with open(path, "rb") as source:
            self.original = source.read()

    def check_canvas(self, original, result):
        before, after = split(original), split(result)
        self.assertEqual(after[0]["data"][4:10], before[0]["data"][4:10])
        self.assertEqual(
            [c for c in after if c["fourcc"] == b"ANMF"],
            [c for c in before if c["fourcc"] == b"ANMF"],
        )

    def test_insert_preserves_animation_canvas(self):
        exif = dump({})[6:]
        result = insert(self.original, exif)
        self.check_canvas(self.original, result)
        self.assertEqual(get_exif(result), exif)

    def test_remove_preserves_animation_canvas(self):
        for source in (self.original, insert(self.original, dump({})[6:])):
            result = remove(source)
            self.check_canvas(self.original, result)
            self.assertIsNone(get_exif(result))

    def test_preserves_canvas_larger_than_frame_bounds(self):
        chunks = split(self.original)
        # A canvas may include background beyond every frame's bounds.
        canvas = struct.pack("<I", 499)[:3] + struct.pack("<I", 599)[:3]
        chunks[0]["data"] = chunks[0]["data"][:4] + canvas
        result = set_vp8x(chunks)
        self.assertEqual(result[0]["data"][4:10], canvas)

    def test_insert_preserves_animation_alpha(self):
        result = insert(self.original, dump({})[6:])
        self.assertEqual(ord(split(result)[0]["data"][:1]) & 0x10, 0x10)

    def test_remove_preserves_animation_alpha(self):
        for source in (self.original, insert(self.original, dump({})[6:])):
            result = remove(source)
            self.assertEqual(ord(split(result)[0]["data"][:1]) & 0x10, 0x10)

    def check_animation_edits(self, filename):
        path = os.path.join(os.path.dirname(__file__), "images", filename)
        with open(path, "rb") as source:
            original = source.read()
        exif = dump({})[6:]
        inserted = insert(original, exif)
        self.assertEqual(get_exif(inserted), exif)
        for result in (inserted, remove(original), remove(inserted)):
            self.check_canvas(original, result)
            # Only the EXIF presence flag may change.
            self.assertEqual(
                ord(split(result)[0]["data"][:1]) & ~0x08,
                ord(split(original)[0]["data"][:1]) & ~0x08,
            )
        self.assertIsNone(get_exif(remove(original)))
        self.assertIsNone(get_exif(remove(inserted)))

    def test_animation_with_varying_frame_bounds(self):
        self.check_animation_edits("pil_animated2.webp")

    def test_animation_with_nested_alpha_chunks(self):
        self.check_animation_edits("pil_animated3.webp")

    def test_simple_webp_has_no_exif(self):
        for filename, fourcc in (("tool1.webp", b"VP8 "), ("pil2.webp", b"VP8L")):
            path = os.path.join(os.path.dirname(__file__), "images", filename)
            with open(path, "rb") as source:
                chunks = [
                    chunk for chunk in split(source.read()) if chunk["fourcc"] == fourcc
                ]
            self.assertEqual(len(chunks), 1)
            data = get_file_header(chunks) + merge_chunks(chunks)
            self.assertIsNone(get_exif(data))
