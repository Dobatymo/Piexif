import os
import struct
import tempfile
import unittest

import piexif
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
        with open("tests/images/tool1.webp", "rb") as source:
            self.chunks = [
                value for value in split(source.read()) if value["fourcc"] != b"EXIF"
            ]
        self.chunks[1:1] = [
            chunk(b"EXIF", b"old"),
            chunk(b"EXIF", b"old2"),
        ]

    def test_loads_bare_and_prefixed_exif_without_riff_padding(self):
        descriptor, path = tempfile.mkstemp(suffix=".webp")
        os.close(descriptor)
        self.addCleanup(os.remove, path)
        for endian, marker in (("<", b"II"), (">", b"MM")):
            for value in (b"abcd\x00", b"abcde\x00"):
                tiff = marker + struct.pack(endian + "HIH", 42, 8, 1)
                tiff += struct.pack(endian + "HHII", 271, 2, len(value), 26)
                tiff += b"\x00" * 4 + value
                for prefix in (b"", b"Exif\x00\x00"):
                    data = webp(
                        [
                            chunk(b"VP8X", b"\x08" + b"\x00" * 9),
                            chunk(b"JUNK", b"odd"),
                            chunk(b"EXIF", prefix + tiff),
                        ]
                    )
                    self.assertEqual(get_exif(data), tiff)
                    with open(path, "wb") as output:
                        output.write(data)
                    for reader, source in (
                        (piexif.load_bytes, data),
                        (piexif.load_file, path),
                    ):
                        self.assertEqual(reader(source)["0th"], {271: value[:-1]})
                    for reader, source in (
                        (piexif.load_ifds_bytes, data),
                        (piexif.load_ifds_file, path),
                    ):
                        self.assertEqual(reader(source)[0]["tags"], {271: value[:-1]})

    def test_padding_and_bad_exif_prefixes_cannot_hide_invalid_metadata(self):
        # The field declares six bytes; the last byte is missing from the TIFF.
        tiff = b"MM" + struct.pack(">HIHHHII", 42, 8, 1, 271, 2, 6, 26)
        tiff += b"\x00" * 4 + b"abcde"
        descriptor, path = tempfile.mkstemp(suffix=".webp")
        os.close(descriptor)
        self.addCleanup(os.remove, path)
        payloads = (tiff, b"Exif\x00\x00" + tiff, b"Exif\x00\x00")
        payloads += tuple(
            prefix + tiff + b"\x00" for prefix in (b"ExifXX", b"Exif\x00X")
        )
        for payload in payloads:
            data = webp(
                [chunk(b"VP8X", b"\x08" + b"\x00" * 9), chunk(b"EXIF", payload)]
            )
            with open(path, "wb") as output:
                output.write(data)
            for reader, source in (
                (piexif.load_bytes, data),
                (piexif.load_file, path),
                (piexif.load_ifds_bytes, data),
                (piexif.load_ifds_file, path),
            ):
                with self.assertRaises(piexif.InvalidImageDataError):
                    reader(source)

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

    def test_missing_webp_image_header_is_rejected(self):
        for chunks in ([], [chunk(b"JUNK", b"")], [chunk(b"EXIF", dump({})[6:])]):
            for reader in (get_exif, piexif.load_bytes, piexif.load_ifds_bytes):
                with self.assertRaises(ValueError):
                    reader(webp(chunks))

    def test_simple_webp_ignores_exif_chunks(self):
        for image_chunk in (chunk(b"VP8 ", b"image"), chunk(b"VP8L", b"image")):
            data = webp([image_chunk, chunk(b"EXIF", dump({})[6:])])
            self.assertIsNone(get_exif(data))
            self.assertEqual(piexif.load_bytes(data)["0th"], {})

    def test_vp8x_exif_flag_must_match_exif_chunks(self):
        exif = chunk(b"EXIF", dump({})[6:])
        for chunks in (
            [chunk(b"VP8X", b"\x00" + b"\x00" * 9), exif],
            [chunk(b"VP8X", b"\x08" + b"\x00" * 9)],
        ):
            data = webp(chunks)
            for reader in (get_exif, piexif.load_bytes, piexif.load_ifds_bytes):
                with self.assertRaises(ValueError):
                    reader(data)

    def test_edits_preserve_trailing_empty_unknown_chunk(self):
        empty = chunk(b"JUNK", b"")
        original = webp(self.chunks + [empty])
        exif = dump({})[6:]
        inserted = insert(original, exif)
        removed = remove(inserted)
        self.assertEqual(get_exif(inserted), exif)
        self.assertIsNone(get_exif(removed))
        image_chunks = [value for value in self.chunks if value["fourcc"] == b"VP8 "]
        for data in (original, inserted, removed):
            chunks = split(data)
            self.assertEqual(
                [value for value in chunks if value["fourcc"] == b"JUNK"], [empty]
            )
            self.assertEqual(
                [value for value in chunks if value["fourcc"] == b"VP8 "], image_chunks
            )

    def test_truncated_chunks_are_rejected(self):
        data = (
            b"RIFF"
            + struct.pack("<L", 13)
            + b"WEBP"
            + b"JUNK"
            + struct.pack("<L", 8)
            + b"x"
        )
        for reader in (split, get_exif):
            with self.assertRaises(ValueError):
                reader(data)

    def test_invalid_vp8_frame_is_rejected(self):
        with self.assertRaises(ValueError):
            set_vp8x([chunk(b"VP8 ", b"not a VP8 frame")])


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

    def test_xmp_chunk_survives_exif_edits(self):
        packet = b'<x:xmpmeta xmlns:x="adobe:ns:meta/" />'
        chunks = split(self.original)
        xmp_chunk = chunk(b"XMP ", packet)
        chunks.append(xmp_chunk)
        source = webp(set_vp8x(chunks))

        inserted = insert(source, dump({})[6:])
        self.assertEqual(
            [value for value in split(inserted) if value["fourcc"] == b"XMP "],
            [xmp_chunk],
        )
        self.assertEqual(ord(split(inserted)[0]["data"][:1]) & 0x04, 0x04)

        removed = remove(inserted)
        self.assertEqual(
            [value for value in split(removed) if value["fourcc"] == b"XMP "],
            [xmp_chunk],
        )
        self.assertEqual(ord(split(removed)[0]["data"][:1]) & 0x04, 0x04)

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
