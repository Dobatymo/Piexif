# Fixed upstream and fork issues

## Corrupt EXIF can trigger `MemoryError`

- Upstream: [hMatoba/Piexif#55](https://github.com/hMatoba/Piexif/issues/55).
- Reproduction image: https://user-images.githubusercontent.com/1758850/37331204-450a05bc-26de-11e8-90c7-1c0fda00e01c.jpg
- Status: fixed in this fork as parser hardening.
- Malformed EXIF lengths and offsets are now bounds-checked and rejected with
  `InvalidImageDataError`; the parser does not attempt to recover the data.
- Validation with the image attached to the upstream issue: the original
  parser did not finish before being interrupted, while this fork rejected it
  immediately with `InvalidImageDataError`. The image is kept outside the
  repository as a temporary test input.
- The original unknown-tag regression test also used a truncated IFD entry;
  the fixture was corrected to include the required 12-byte entry data.

## `FocalLength` cannot be set

- Upstream: [hMatoba/Piexif#60](https://github.com/hMatoba/Piexif/issues/60).
- Status: not planned; user error.
- `FocalLength` is an EXIF `RATIONAL` and must be supplied as a numerator and
  denominator tuple, such as `(8, 1)`. In Python 3, `8 / 1` produces the
  invalid float value `8.0`.

## Invalid GPS value raises `UnboundLocalError`

- Upstream: [hMatoba/Piexif#67](https://github.com/hMatoba/Piexif/issues/67).
- Status: hardened in this fork.
- Invalid rational values now raise `ValueError` instead of an internal
  `UnboundLocalError`; incorrect GPS types are not converted or supported.

## Negative `TimeZoneOffset` cannot be dumped

- Upstream: [hMatoba/Piexif#135](https://github.com/hMatoba/Piexif/issues/135).
- Status: fixed in this fork.
- `TimeZoneOffset` is a signed-short EXIF value. It was incorrectly declared
  as an unsigned long, so valid negative offsets raised `struct.error`.
- The tag is now declared as `TYPES.SShort`.

## `ExifIFD` string-name lookup

- Upstream: [hMatoba/Piexif#139](https://github.com/hMatoba/Piexif/issues/139).
- Status: not planned; the requested dictionary interface is unnecessary.
- `ExifIFD` is a class containing numeric tag IDs. Dynamic lookup already works
  with `getattr(piexif.ExifIFD, "DateTimeOriginal")`.

## JFIF metadata lost when inserting EXIF

- Upstream: [hMatoba/Piexif#148](https://github.com/hMatoba/Piexif/issues/148).
- Status: fixed in this fork.
- Problem: inserting or transplanting EXIF removed or replaced the JPEG APP0
  segment, losing JFIF metadata such as DPI.
- Fix: preserve unrelated segments byte-for-byte, replace the first EXIF
  segment in place, and remove duplicate EXIF segments. When adding EXIF to
  a JPEG starting with APP0, insert it after APP0.
- The shared helper keeps all bytes unchanged for its default empty argument
  and removes only EXIF segments when passed None.
- Original contribution: [mapillary/Piexif PR #1, "Handle JFIF headers."](https://github.com/mapillary/Piexif/pull/1)
  by hinxx, from [hinxx/handle-jfif](https://github.com/hinxx/Piexif/tree/handle-jfif).
  Its four commits include [b03d1470](https://github.com/mapillary/Piexif/commit/b03d1470aa0eebd1d87915505a191cbedf393fd3),
  which changes EXIF segment merging.
  Hinxx's fix is incomplete: it removes list entries while iterating fixed
  indices, causing IndexError when removing EXIF or replacing duplicate EXIF
  segments. Its default empty argument also removes existing EXIF.
  This implementation builds a new segment list instead.
