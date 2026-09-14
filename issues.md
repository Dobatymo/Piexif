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

## Changes to thumbnail metadata are omitted without a thumbnail

- Upstream: [hMatoba/Piexif#80](https://github.com/hMatoba/Piexif/issues/80).
- Status: not planned; user error.
- EXIF dictionaries must use integer tag IDs such as `piexif.ImageIFD.Make`,
  not strings such as `"piexif.ImageIFD.Make"`.
- The example also modifies `1st`, which describes the thumbnail and is omitted
  when no thumbnail is supplied. Use `0th` for primary-image Make and Software.

## `AsShotNeutral` rational values cannot be dumped

- Upstream: [hMatoba/Piexif#86](https://github.com/hMatoba/Piexif/issues/86).
- Status: fixed in this fork.
- Piexif's tag table represented `AsShotNeutral` as `SHORT`,
  while the DNG specification permits both `SHORT` and `RATIONAL` values.
  Rational DNG values now round-trip correctly.

## Truncated DateTimeOriginal without a counted NUL terminator

- Upstream: [hMatoba/Piexif#134](https://github.com/hMatoba/Piexif/issues/134).
- Status: fixed in this fork with bounded support for unterminated ASCII.
- The sample declares 19 bytes for `DateTimeOriginal`, excluding its NUL
  terminator; EXIF specifies 20 bytes including the NUL. The parser now reads
  exactly the declared count and removes one trailing NUL only when present.
  It returns the full timestamp without scanning past the field boundary.
- Existing bounds checks still reject values extending beyond the input.
  Zero-count ASCII values now return empty bytes instead of inline padding.
- Reproduction image: [20_BIKE_C_4_002.jpg](https://issue-report-resources.s3.eu-central-1.amazonaws.com/piexif/20_BIKE_C_4_002.jpg).

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

## Missing CameraLabel and RawToPreviewGain tags

- Upstream: [hMatoba/Piexif#142](https://github.com/hMatoba/Piexif/issues/142).
- Status: fixed in this fork.
- Added `CameraLabel` (51105, ASCII) and `RawToPreviewGain` (51112, DOUBLE)
  to the image tag table and `ImageIFD`. Loading now retains these values,
  and dumping supports them using the existing ASCII and double encoders.

## Animated WebP loses its alpha flag

- Upstream: [hMatoba/Piexif#144](https://github.com/hMatoba/Piexif/issues/144).
- Status: fixed in this fork.
- EXIF insertion and removal preserve the existing `VP8X` alpha flag. Frame
  data remains unchanged, including nested `ALPH` chunks and lossless alpha.
- The issue describes the flag as the animation flag in places; the affected
  flag is the alpha flag.
- `pil_animated3.webp` covers lossy frames with nested `ALPH` chunks. It and
  `pil_animated2.webp` were contributed as test fixtures in the MIT-licensed
  [source commit](https://github.com/skidder/Piexif/commit/5a12974343580d5f6fbbed74966bc56f2859ffe9);
  the license is retained in `LICENSE.txt`.

## Animated WebP canvas dimensions shrink to the last frame

- Upstream: [hMatoba/Piexif#145](https://github.com/hMatoba/Piexif/issues/145).
- Status: fixed in this fork.
- EXIF insertion and removal preserve the existing `VP8X` canvas dimensions
  instead of replacing them with the last `ANMF` frame dimensions. This also
  preserves canvases with background beyond the frames' bounds.
- `pil_animated2.webp` also covers varying frame sizes and offsets.
- Reproduction image: [test.webp.zip](https://github.com/user-attachments/files/16908953/test.webp.zip),
  included as `animated_canvas.webp`. Its author, nico, explicitly placed it
  in the public domain in the [issue comment](https://github.com/hMatoba/Piexif/issues/145#issuecomment-2334111999).

## Out-of-range brightness value raises `struct.error`

- Upstream: [hMatoba/Piexif#147](https://github.com/hMatoba/Piexif/issues/147).
- Status: hardened in this fork.
- `BrightnessValue` (37379) requires a signed rational. The reported unsigned
  numerator exceeds its permitted range; the source image was not provided.
- Invalid tag values rejected by validation or numeric packing now raise
  `InvalidImageDataError` with the tag and IFD, without converting invalid data.

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
