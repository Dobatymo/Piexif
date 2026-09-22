import copy
import struct
import unittest

from piexif._dump import dump
from piexif._exceptions import InvalidImageDataError
from piexif._exif import ExifIFD, GPSIFD, ImageIFD, InteropIFD
from piexif._load import load


class DumpValidationTests(unittest.TestCase):
    thumbnail = (b"\xff\xd8\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00"
                 b"\xff\xd9")

    def test_thumbnail_ifd_entries_are_sorted(self):
        raw = dump({"1st": {ImageIFD.XMLPacket: (1,)},
                    "thumbnail": self.thumbnail})[6:]
        first = struct.unpack_from(">I", raw, 10)[0]  # Empty root's next pointer.
        count = struct.unpack_from(">H", raw, first)[0]
        tags = [struct.unpack_from(">H", raw, first + 2 + index * 12)[0]
                for index in range(count)]
        self.assertEqual(tags, [ImageIFD.JPEGInterchangeFormat,
                               ImageIFD.JPEGInterchangeFormatLength,
                               ImageIFD.XMLPacket])

    def test_all_standard_ifds_are_word_aligned(self):
        thumbnail = self.thumbnail
        for length in (4, 5):
            for mask in range(32):
                source = {"0th": {ImageIFD.Make: b"x" * length}}
                options = (("Exif", {ExifIFD.DateTimeOriginal: b"x" * length}),
                           ("GPS", {GPSIFD.GPSMapDatum: b"x" * length}),
                           ("Interop", {InteropIFD.InteroperabilityIndex: b"x" * length}),
                           ("GlobalParameters", {ImageIFD.Software: b"x" * length}))
                for index, (name, tags) in enumerate(options):
                    if mask & (1 << index):
                        source[name] = tags
                if mask & 16:
                    source.update({"1st": {ImageIFD.Make: b"x" * length},
                                   "thumbnail": thumbnail})
                before = copy.deepcopy(source)
                encoded = dump(source)
                raw = encoded[6:]
                stack, seen = [8], set()
                while stack:
                    pointer = stack.pop()
                    self.assertEqual(pointer % 2, 0, (length, mask, pointer))
                    self.assertNotIn(pointer, seen)
                    seen.add(pointer)
                    count = struct.unpack_from(">H", raw, pointer)[0]
                    fields = {}
                    for index in range(count):
                        tag, kind, size, value = struct.unpack_from(
                            ">HHII", raw, pointer + 2 + index * 12)
                        fields[tag] = value
                        if tag in (ImageIFD.GlobalParametersIFD, ImageIFD.ExifTag,
                                   ImageIFD.GPSTag, ExifIFD.InteroperabilityTag):
                            self.assertEqual((kind, size), (4, 1))
                            stack.append(value)
                    following = struct.unpack_from(">I", raw, pointer + 2 + count * 12)[0]
                    if following:
                        stack.append(following)
                    if ImageIFD.JPEGInterchangeFormat in fields:
                        start = fields[ImageIFD.JPEGInterchangeFormat]
                        size = fields[ImageIFD.JPEGInterchangeFormatLength]
                        self.assertEqual(raw[start:start + size], thumbnail)
                result = load(encoded)
                for name, tags in source.items():
                    if name == "thumbnail":
                        self.assertEqual(result[name], tags)
                    else:
                        for tag, value in tags.items():
                            self.assertEqual(result[name][tag], value)
                self.assertEqual(source, before)
                self.assertEqual(dump(result), encoded)

    def test_jpeg_thumbnail_lifecycle(self):
        thumbnail = self.thumbnail
        replacement = thumbnail[:2] + b"\xff\xfe\x00\x09changed" + thumbnail[2:]
        for first in ({}, {ImageIFD.Make: b"Preview"}):
            source = {"0th": {ImageIFD.Make: b"Main"}, "1st": first,
                      "thumbnail": thumbnail}
            before = copy.deepcopy(source)
            result = load(dump(source))
            self.assertEqual(result["thumbnail"], thumbnail)
            self.assertEqual(source, before)
            if first:
                self.assertEqual(result["1st"][ImageIFD.Make], b"Preview")
            result["thumbnail"] = replacement
            result["1st"][ImageIFD.JPEGInterchangeFormat] = 0xFFFFFFFF
            result["1st"][ImageIFD.JPEGInterchangeFormatLength] = 1
            result = load(dump(result))
            self.assertEqual(result["thumbnail"], replacement)
            self.assertEqual(result["1st"][ImageIFD.JPEGInterchangeFormatLength], len(replacement))
            self.assertEqual(load(dump(result))["thumbnail"], replacement)
            for omitted in (False, True):
                candidate = copy.deepcopy(result)
                if omitted:
                    candidate.pop("thumbnail")
                else:
                    candidate["thumbnail"] = None
                before = copy.deepcopy(candidate)
                deleted = load(dump(candidate))
                self.assertIsNone(deleted["thumbnail"])
                self.assertEqual(deleted["1st"], {})
                self.assertEqual(deleted["0th"], source["0th"])
                self.assertEqual(candidate, before)
                self.assertIsNone(load(dump(deleted))["thumbnail"])

    def test_thumbnail_without_first_ifd_is_ignored(self):
        thumbnail = self.thumbnail
        expected = dump({"0th": {ImageIFD.Make: b"Main"}})
        for payload in (thumbnail, b"not a JPEG", b"", None):
            source = {"0th": {ImageIFD.Make: b"Main"}, "thumbnail": payload}
            before = copy.deepcopy(source)
            self.assertEqual(dump(source), expected)
            self.assertEqual(source, before)

    def test_global_parameters_ifd_alignment(self):
        thumbnail = self.thumbnail
        for extra in ({}, {"Exif": {ExifIFD.DateTimeOriginal: b"odd!"},
                           "GPS": {GPSIFD.GPSAltitudeRef: 0},
                           "Interop": {InteropIFD.InteroperabilityIndex: b"R98"}}):
            for with_thumbnail in (False, True):
                source = dict(extra, **{"0th": {ImageIFD.Make: b"even"},
                                        "GlobalParameters": {ImageIFD.ProfileType: 1,
                                                   ImageIFD.Software: b"even"}})
                if with_thumbnail:
                    source.update({"1st": {ImageIFD.Make: b"Preview"},
                                   "thumbnail": thumbnail})
                encoded = dump(source)
                result = load(encoded)
                self.assertEqual(result["0th"][ImageIFD.GlobalParametersIFD] % 2, 0)
                self.assertEqual(result["GlobalParameters"], source["GlobalParameters"])
                if with_thumbnail:
                    count = struct.unpack_from(">H", encoded, 14)[0]
                    following = struct.unpack_from(">I", encoded, 16 + count * 12)[0]
                    self.assertEqual(following % 2, 0)
                    self.assertEqual(result["thumbnail"], thumbnail)
                for name in extra:
                    for tag, value in extra[name].items():
                        self.assertEqual(result[name][tag], value)

    def test_tiff_fx_shared_tiff_fields_roundtrip(self):
        globals_ifd = {ImageIFD.ProfileType: 1,
                       ImageIFD.Orientation: 1,
                       ImageIFD.Software: b"Global software",
                       ImageIFD.XResolution: (300, 1),
                       ImageIFD.Copyright: b"Global copyright"}
        source = {"0th": {ImageIFD.Orientation: 6}, "GlobalParameters": globals_ifd}
        encoded = dump(source)
        loaded = load(encoded)
        self.assertEqual(loaded["GlobalParameters"], globals_ifd)
        self.assertEqual(loaded["0th"][ImageIFD.Orientation], 6)
        self.assertEqual(load(encoded, key_is_name=True)["GlobalParameters"],
                         {"ProfileType": 1, "Orientation": 1,
                          "Software": b"Global software",
                          "XResolution": (300, 1),
                          "Copyright": b"Global copyright"})
        pointer = loaded["0th"][ImageIFD.GlobalParametersIFD]
        tiff = encoded[6:]
        count = struct.unpack_from(">H", tiff, pointer)[0]
        tags = [struct.unpack_from(">H", tiff, pointer + 2 + 12 * i)[0]
                for i in range(count)]
        self.assertEqual(tags, sorted(tags))

    def test_tiff_fx_tags_roundtrip(self):
        values = {ImageIFD.ProfileType: 1, ImageIFD.FaxProfile: 6,
                  ImageIFD.CodingMethods: 0x28,
                  ImageIFD.VersionYear: (49, 57, 57, 57),
                  ImageIFD.ModeNumber: 0}
        image_values = {ImageIFD.StripRowCounts: (100, 200),
                        ImageIFD.ImageLayer: (2, 1)}
        thumbnail = self.thumbnail
        self.assertIsNotNone(thumbnail)
        siblings = {"Exif": {ExifIFD.DateTimeOriginal: b"2026:09:18 12:34:56"},
                    "GPS": {GPSIFD.GPSLatitude: ((1, 1), (2, 1), (3, 1))},
                    "Interop": {InteropIFD.InteroperabilityIndex: b"R98"},
                    "1st": {ImageIFD.Make: b"Thumbnail camera"},
                    "thumbnail": thumbnail}
        for extra in ({}, siblings):
            source = dict(extra, **{"0th": image_values, "GlobalParameters": values})
            encoded = dump(source)
            loaded = load(encoded)
            for ifd, supplied in source.items():
                if ifd == "thumbnail":
                    self.assertEqual(loaded[ifd], supplied)
                else:
                    for tag, value in supplied.items():
                        self.assertEqual(loaded[ifd][tag], value)
            tiff = encoded[6:]
            count = struct.unpack_from(">H", tiff, 8)[0]
            tags = [struct.unpack_from(">H", tiff, 10 + i * 12)[0]
                    for i in range(count)]
            self.assertEqual(tags, sorted(tags))
            pointer = loaded["0th"][ImageIFD.GlobalParametersIFD]
            entries = [struct.unpack_from(">HHI", tiff, pointer + 2 + i * 12)
                       for i in range(5)]
            self.assertEqual(entries, [(401, 4, 1), (402, 1, 1), (403, 4, 1),
                                       (404, 1, 4), (405, 1, 1)])
            self.assertEqual(load(encoded, key_is_name=True)["GlobalParameters"],
                             {"ProfileType": 1, "FaxProfile": 6,
                              "CodingMethods": 40,
                              "VersionYear": (49, 57, 57, 57), "ModeNumber": 0})

    def test_nested_ifds_have_null_next_pointers(self):
        cases = [
            {"Exif": {ExifIFD.ExifVersion: b"0230"}},
            {"GPS": {GPSIFD.GPSAltitudeRef: 0}},
            {"Interop": {InteropIFD.InteroperabilityIndex: b"R98"}},
            {"Exif": {ExifIFD.DateTimeOriginal: b"2026:09:14 12:34:56"},
             "GPS": {GPSIFD.GPSLatitude: ((1, 1), (2, 1), (3, 1))},
             "Interop": {InteropIFD.InteroperabilityIndex: b"R98"}},
        ]
        for source in cases:
            exif = dump(source)
            loaded = load(exif)
            tiff = exif[6:]
            pointers = []
            if "Exif" in source or "Interop" in source:
                pointers.append(loaded["0th"][ImageIFD.ExifTag])
            if "GPS" in source:
                pointers.append(loaded["0th"][ImageIFD.GPSTag])
            if "Interop" in source:
                pointers.append(loaded["Exif"][ExifIFD.InteroperabilityTag])
            for pointer in pointers:
                count = struct.unpack_from(">H", tiff, pointer)[0]
                end = pointer + 2 + count * 12
                self.assertEqual(tiff[end:end + 4], b"\x00" * 4)
                for pos in range(pointer + 2, end, 12):
                    tag, kind, length, offset = struct.unpack_from(">HHII", tiff, pos)
                    size = length * (8 if kind == 5 else 1)
                    if kind in (2, 5, 7) and size > 4:
                        self.assertGreaterEqual(offset, end + 4)
            for ifd, values in source.items():
                for tag, value in values.items():
                    self.assertEqual(loaded[ifd][tag], value)

    def test_interop_without_exif(self):
        interop = {InteropIFD.InteroperabilityIndex: b"R98"}
        for siblings in ({}, {"0th": {ImageIFD.Make: b"Camera"},
                              "GPS": {GPSIFD.GPSAltitudeRef: 0}}):
            source = dict(siblings, Interop=interop)
            exif = dump(source)
            self.assertEqual(exif, dump(dict(source, Exif={})))
            loaded = load(exif)
            self.assertEqual(loaded["Interop"], interop)
            self.assertIn(ImageIFD.ExifTag, loaded["0th"])
            self.assertIn(ExifIFD.InteroperabilityTag, loaded["Exif"])
            for ifd, values in siblings.items():
                for tag, value in values.items():
                    self.assertEqual(loaded[ifd][tag], value)
            self.assertEqual(source, dict(siblings, Interop=interop))
            self.assertEqual(interop, {InteropIFD.InteroperabilityIndex: b"R98"})

    def test_invalid_rational_type(self):
        exif_dict = {"GPS": {GPSIFD.GPSLatitude: "51,30,0"}}
        with self.assertRaises(ValueError):
            dump(exif_dict)

    def test_as_shot_neutral_rational_roundtrip(self):
        value = ((1000, 1693), (1000, 990), (1000, 1442))
        exif = dump({"0th": {ImageIFD.AsShotNeutral: value}})
        self.assertEqual(load(exif)["0th"][ImageIFD.AsShotNeutral], value)

    def test_as_shot_neutral_short_roundtrip(self):
        value = (100, 200, 300)
        exif = dump({"0th": {ImageIFD.AsShotNeutral: value}})
        self.assertEqual(load(exif)["0th"][ImageIFD.AsShotNeutral], value)

    def test_invalid_numeric_values(self):
        cases = [
            ("Exif", ExifIFD.BrightnessValue, (4294966933, 100)),
            ("Exif", ExifIFD.BrightnessValue, (-2147483649, 100)),
            ("0th", ImageIFD.XResolution, (-1, 100)),
            ("0th", ImageIFD.ImageWidth, 4294967296),
            ("0th", ImageIFD.Orientation, 65536),
            ("0th", ImageIFD.Orientation, -1),
            ("0th", ImageIFD.TimeZoneOffset, 32768),
            ("GPS", GPSIFD.GPSAltitudeRef, 256),
            ("GPS", GPSIFD.GPSAltitudeRef, (256,)),
            ("GPS", GPSIFD.GPSLatitude,
             ((1, 1), (2, 1), (2476979795053773, 2251799813685248))),
            ("GPS", GPSIFD.GPSLatitude,
             ((1, 1), (2, 1), (4294967296, 1))),
            ("GPS", GPSIFD.GPSLatitude,
             ((1, 1), (2, 1), (1, 4294967296))),
            ("Exif", ExifIFD.ShutterSpeedValue, "0.00080000"),
            ("Exif", ExifIFD.MaxApertureValue, "2.0"),
            ("Exif", ExifIFD.FocalLength, "50.0"),
            ("Exif", ExifIFD.FocalLengthIn35mmFilm, "50.0"),
        ]
        for ifd, tag, value in cases:
            with self.assertRaises(InvalidImageDataError) as caught:
                dump({ifd: {tag: value}})
            self.assertIn(str(tag), str(caught.exception))
            self.assertIn(ifd, str(caught.exception))

    def test_components_configuration_roundtrip(self):
        value = b"\x01\x02\x03\x00"
        exif = dump({"Exif": {ExifIFD.ComponentsConfiguration: value}})
        self.assertEqual(load(exif)["Exif"][ExifIFD.ComponentsConfiguration], value)

    def test_components_configuration_rejects_tuple(self):
        with self.assertRaises(InvalidImageDataError) as caught:
            dump({"Exif": {ExifIFD.ComponentsConfiguration: (1, 2, 3, 0)}})
        self.assertIn(str(ExifIFD.ComponentsConfiguration), str(caught.exception))
        self.assertIn("Exif", str(caught.exception))

    def test_scene_type_roundtrip(self):
        value = b"\x01"
        exif = dump({"Exif": {ExifIFD.SceneType: value}})
        self.assertEqual(load(exif)["Exif"][ExifIFD.SceneType], value)

    def test_scene_type_rejects_integer(self):
        with self.assertRaises(InvalidImageDataError) as caught:
            dump({"Exif": {ExifIFD.SceneType: 1}})
        self.assertIn(str(ExifIFD.SceneType), str(caught.exception))
        self.assertIn("Exif", str(caught.exception))

    def test_gps_rational_roundtrip(self):
        for seconds in ((11, 10), (4294967295, 4294967294)):
            value = ((25, 1), (3, 1), seconds)
            exif = dump({"GPS": {GPSIFD.GPSLatitude: value}})
            self.assertEqual(load(exif)["GPS"][GPSIFD.GPSLatitude], value)

    def test_signed_brightness_roundtrip(self):
        for value in ((-363, 100), (-2147483648, 1), (2147483647, 1)):
            exif = dump({"Exif": {ExifIFD.BrightnessValue: value}})
            self.assertEqual(load(exif)["Exif"][ExifIFD.BrightnessValue], value)
