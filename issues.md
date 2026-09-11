# Fixed upstream and fork issues

## `FocalLength` cannot be set

- Upstream: [hMatoba/Piexif#60](https://github.com/hMatoba/Piexif/issues/60).
- Status: not planned; user error.
- `FocalLength` is an EXIF `RATIONAL` and must be supplied as a numerator and
  denominator tuple, such as `(8, 1)`. In Python 3, `8 / 1` produces the
  invalid float value `8.0`.

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
