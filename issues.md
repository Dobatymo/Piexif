# Fixed upstream and fork issues

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
