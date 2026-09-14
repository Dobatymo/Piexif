============
About Piexif
============

What for?
---------

To simplify exif manipulations with Python. Writing, reading, and more...

How to Use
----------

There are only five functions.

- *load(filename)* - Get exif data as *dict*.
- *dump(exif_dict)* - Get exif as *bytes* to save with JPEG.
- *insert(exif_bytes, filename)* - Insert exif into JPEG.
- *remove(filename)* - Remove exif from JPEG.
- *transplant(filename, filename)* - Transplant exif from JPEG to JPEG.

Preservation goals in this fork
-------------------------------

``load()`` followed by ``dump()`` aims to preserve supported metadata values,
not the original EXIF bytes. Dumping rebuilds the EXIF structure, so tag order,
offsets and encoding details may change. For example, an ASCII value read
without a final NUL is written with the required terminator; its parsed value
is preserved. Embedded NULs remain part of the value.

This is not a lossless round trip for arbitrary metadata. Unknown tags may be
omitted, and retaining opaque MakerNote bytes does not guarantee that internal
offsets remain valid after rebuilding EXIF. Preserving every original byte or
repairing all malformed metadata is outside this fork's current scope.

For ``insert()``, ``remove()`` and ``transplant()``, the goal is to preserve
encoded image data and unrelated metadata byte-for-byte wherever the requested
operation does not require changes. Container lengths and EXIF-presence flags
may need updating. These operations do not re-encode pixels; saving an image
through Pillow is a separate operation with its own preservation behavior.

Tests and change descriptions should distinguish metadata-value preservation
from byte preservation rather than claim that all round trips are lossless.

Dependency
----------

Piexif doesn't depend on any third library.

Environment
-----------

Tested on Python 2.7, 3.5+, pypy, and pypy3. Piexif would run even on IronPython. Piexif is OS independent and can run on GoogleAppEngine.

License
-------

The MIT License (MIT)

Copyright (c) 2014, 2015 hMatoba

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
