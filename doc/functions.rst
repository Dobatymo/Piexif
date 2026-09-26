=========
Functions
=========

.. warning:: Piexif checks whether values can be encoded, but does not check that metadata describes the actual image. For example, XResolution can be written as 0 even if the intended resolution is 300.
.. warning:: To edit exif tags and values appropriately, read official document from P167-. http://www.cipa.jp/std/documents/e/DC-008-2012_E.pdf
.. note:: This document is written for using Piexif on Python 3.x.


The standard API, ``load()``, returns metadata dictionaries. The advanced API,
``load_ifds()``, returns nested directory lists. Both are supported;
the advanced API does not replace or deprecate the standard API.
Use ``dump()`` for standard dictionaries and ``dump_ifds()`` for directory lists.

load
----
.. py:function:: piexif.load(filename, key_is_name=False)

   Returns a dictionary containing ``0th``, ``Exif``, ``GPS``, ``Interop``,
   ``1st`` and ``thumbnail``. Missing IFDs have empty dictionaries;
   ``thumbnail`` contains the JPEG thumbnail bytes or ``None`` if none was
   found in ``1st``. A global-parameters IFD adds ``GlobalParameters``.
   Use ``load_ifds()`` for a list of primary directories with nested
   auxiliary IFDs and optional JPEG data. See Nested directory lists below.

   :param str filename: JPEG, WebP, or TIFF
   :param bool key_is_name: If True, use tag names (for example, "Make") instead of numeric tag IDs (271) inside each IFD dictionary. Defaults to False. IFD names, values, and thumbnail data are unchanged. Keep False when passing the result to ``dump()``, which expects numeric tag IDs.
   :return: Standard metadata dictionary.
   :rtype: dict

load_bytes
----------
.. py:function:: piexif.load_bytes(data, key_is_name=False)

   Reads JPEG, WebP, TIFF, or Exif bytes. The argument is always treated as
   in-memory data and is never opened as a filename. Use this function when
   processing untrusted input.

load_file
---------
.. py:function:: piexif.load_file(filename, key_is_name=False)

   Reads metadata from a filename. The argument is always treated as a path.

Standalone metadata bytes may start with the complete six-byte ``Exif\x00\x00``
prefix or directly with a TIFF header. The EXIF prefix is required for JPEG
APP1 identification; PNG and WebP metadata payloads use the TIFF header directly.

``load()`` retains automatic detection, including ambiguous byte strings.
Bytes with an incomplete or incorrect EXIF prefix are unrecognized and may be
interpreted as filenames by auto-detecting APIs. Explicit byte loaders reject
them. New code should use ``load_bytes()`` for in-memory data and ``load_file()``
for paths.

Malformed TIFF headers raise ``InvalidImageDataError``: the header must contain
eight bytes, a valid byte-order marker, and the classic TIFF magic value 42.
JPEG file loading also raises ``InvalidImageDataError`` for invalid or truncated
segment lengths encountered while searching for EXIF. It stops when EXIF is
found, image scan data begins, or the end-of-image marker is reached; it does
not validate the entire JPEG image.

::

    exif_dict = piexif.load("foo.jpg")
    thumbnail = exif_dict.pop("thumbnail")
    if thumbnail is not None:
        with open("thumbnail.jpg", "wb+") as f:
            f.write(thumbnail)    
    for ifd_name in exif_dict:
        print("\n{0} IFD:".format(ifd_name))
        for key in exif_dict[ifd_name]:
            try:
                print(key, exif_dict[ifd_name][key][:10])
            except:
                print(key, exif_dict[ifd_name][key])

.. py:function:: piexif.load(data, key_is_name=False)

   Reads image or EXIF bytes and returns the same structure as loading a
   filename: standard metadata dictionaries.

   :param bytes data: JPEG, WebP, TIFF, or Exif
   :param bool key_is_name: If True, use tag names (for example, "Make") instead of numeric tag IDs (271) inside each IFD dictionary. Defaults to False. IFD names, values, and thumbnail data are unchanged. Keep False when passing the result to ``dump()``, which expects numeric tag IDs.
   :return: Standard metadata dictionary.
   :rtype: dict

load_ifds
---------
.. py:function:: piexif.load_ifds(input_data, key_is_name=False, load_jpeg_data=False)

   Reads all supported image directories and their auxiliary IFDs as a nested
   list. Accepts the same filenames and image/Exif bytes as ``load()``.
   The return type is always a list; ``load()`` always returns a dictionary.

   :param input_data: JPEG, WebP, TIFF filename or image/Exif bytes.
   :param bool key_is_name: Use tag names instead of numeric IDs. Keep False when passing the result to ``dump_ifds()``.
   :param bool load_jpeg_data: Extract JPEGInterchangeFormat streams into per-directory ``jpeg_data`` bytes. Defaults to False. This controls payload extraction, not file I/O; TIFF input is still read in full.
   :return: Nonempty primary-directory list; see Nested directory lists below.
   :rtype: list


load_ifds_bytes
---------------
.. py:function:: piexif.load_ifds_bytes(data, key_is_name=False, load_jpeg_data=False)

   Reads nested directories from image or Exif bytes. ``data`` must be bytes
   and is never opened as a filename. Options and results match ``load_ifds()``.

::

    directories = piexif.load_ifds_bytes(image_bytes, load_jpeg_data=True)

load_ifds_file
--------------
.. py:function:: piexif.load_ifds_file(filename, key_is_name=False, load_jpeg_data=False)

   Reads nested directories from a filename, regardless of its name. Options
   and results match ``load_ifds()``. ``load_ifds()`` retains automatic input
   detection for existing callers.

::

    directories = piexif.load_ifds_file("source.tif", load_jpeg_data=True)

dump
----

.. py:function:: piexif.dump(exif_dict)

   Returns EXIF bytes from dictionaries with numeric tag IDs. These bytes can
   be passed to ``insert()``; they are not a complete TIFF or JPEG image file.

   :param exif_dict: Standard Exif dictionaries with numeric tag IDs.
   :return: Exif
   :rtype: bytes

::

    import io
    from PIL import Image
    import piexif

    o = io.BytesIO()
    thumb_im = Image.open("foo.jpg")
    thumb_im.thumbnail((50, 50), Image.ANTIALIAS)
    thumb_im.save(o, "jpeg")
    thumbnail = o.getvalue()

    zeroth_ifd = {piexif.ImageIFD.Make: u"Canon",
                  piexif.ImageIFD.XResolution: (96, 1),
                  piexif.ImageIFD.YResolution: (96, 1),
                  piexif.ImageIFD.Software: u"piexif"
                  }
    exif_ifd = {piexif.ExifIFD.DateTimeOriginal: u"2099:09:29 10:10:10",
                piexif.ExifIFD.LensMake: u"LensMake",
                piexif.ExifIFD.Sharpness: 65535,
                piexif.ExifIFD.LensSpecification: ((1, 1), (1, 1), (1, 1), (1, 1)),
                }
    gps_ifd = {piexif.GPSIFD.GPSVersionID: (2, 0, 0, 0),
               piexif.GPSIFD.GPSAltitudeRef: 1,
               piexif.GPSIFD.GPSDateStamp: u"1999:99:99 99:99:99",
               }
    first_ifd = {piexif.ImageIFD.Make: u"Canon",
                 piexif.ImageIFD.XResolution: (40, 1),
                 piexif.ImageIFD.YResolution: (40, 1),
                 piexif.ImageIFD.Software: u"piexif"
                 }
    
    exif_dict = {"0th":zeroth_ifd, "Exif":exif_ifd, "GPS":gps_ifd, "1st":first_ifd, "thumbnail":thumbnail}
    exif_bytes = piexif.dump(exif_dict)
    im = Image.open("foo.jpg")
    im.thumbnail((100, 100), Image.ANTIALIAS)
    im.save("out.jpg", exif=exif_bytes)

The 0thIFD and 1stIFD dictionaries should be constructed using the properties of *piexif.ImageIFD*. Use the properties of *piexif.ExifIFD* for the ExifIFD dictionary, *piexif.GPSIFD* for the GPSIFD dictionary, and *piexif.InteropIFD* for the InteroperabilityIFD dictionary.

For the standard dictionary API, ``dump()`` manages pointers to auxiliary dictionaries:
ExifTag (34665), GPSTag (34853) and GlobalParametersIFD (400) in the root image
directory (``0th``), and
InteroperabilityTag (40965) in ``Exif``. Pointers are rebuilt for the IFDs being
written; callers do not need to calculate their offsets.
The standard writer pads directory blocks so every IFD starts at an even
TIFF-relative offset. Padding may change serialized bytes without changing
metadata values.

The ``thumbnail`` value is JPEG bytes or ``None``. Supplying JPEG bytes adds or
replaces the thumbnail only when a ``1st`` dictionary is also supplied.
Without ``1st``, ``dump()`` ignores ``thumbnail``; it does not create a directory.
Omitting ``thumbnail`` or setting it to ``None`` removes the thumbnail. For
the standard dictionary API, ``1st`` is omitted when no thumbnail
is written. Thumbnail offset and length tags (513/514) are rebuilt by the writer.

dump_ifds
---------
.. py:function:: piexif.dump_ifds(ifds)

   Serializes the nested directory list returned by ``load_ifds()``. Directory
   links and offsets to supplied JPEG data are rebuilt. JPEG data is copied
   unchanged, without thumbnail normalization or a 64,000-byte limit.

   :param list ifds: Nonempty primary-directory list with numeric tag IDs.
   :return: Exif bytes, not a complete TIFF or JPEG image file.
   :rtype: bytes

   The result may exceed JPEG APP1 capacity and therefore may not be insertable
   into a JPEG. This is not a format-aware TIFF-to-JPEG conversion.

Nested directory lists
~~~~~~~~~~~~~~~~~~~~~~

The default ``load()`` and standard dictionary ``dump()`` behavior is unchanged.
Default loading reads 0th/1st image directories and the supported auxiliary
IFDs of 0th. It does not retain later pages or SubIFD targets.

``load_ifds()`` returns a nonempty list of
primary image directories. There is no outer ``IFDs`` key and no 0th/1st
aliases. Every directory has a ``tags`` dictionary; image directories also
have ``subifds``, a list of child chains. Each child chain is itself a
nonempty list of image directories. For example::

    directories = piexif.load_ifds("source.tif")
    main_tags = directories[0]["tags"]
    exif_tags = directories[0]["Exif"]["tags"]  # if Exif exists
    exif_bytes = piexif.dump_ifds(directories)

A complete illustrative layout is::

    [
        {
            "tags": {piexif.ImageIFD.Make: b"Camera"},
            "Exif": {
                "tags": {piexif.ExifIFD.ExifVersion: b"0230"},
                "Interop": {"tags": {piexif.InteropIFD.InteroperabilityIndex: b"R98"}},
            },
            "GPS": {"tags": {piexif.GPSIFD.GPSAltitudeRef: 0}},
            "GlobalParameters": {"tags": {401: 1}},
            "subifds": [
                [{"tags": {piexif.ImageIFD.ImageWidth: 100}, "subifds": []}],
            ],
        },
        {"tags": {}, "subifds": [], "jpeg_data": jpeg_bytes},
    ]

Only present auxiliary IFDs are returned; JPEG data additionally requires
``load_jpeg_data=True``. An image without
EXIF returns ``[{"tags": {}, "subifds": []}]``. When constructing input for
``dump_ifds()``, ``tags`` is required; ``subifds`` may be omitted when empty.
Exif, GPS and GlobalParameters belong to their image directory, including
additional pages and SubIFDs. Interop belongs inside Exif. Auxiliary nodes
contain ``tags`` and any supported nested auxiliary node, not image chains.

List order determines next-directory pointers. Child chains and named auxiliary
nodes determine their pointer tags. Loading removes those structural pointer
tags from ``tags``; dumping rebuilds them from the structure, ignoring any
stale supplied numeric values. To remove an auxiliary IFD, delete its named
key. An explicit ``{"tags": {}}`` preserves an empty auxiliary IFD.
The writer emits each IFD at an even offset.

Shared directories use the same dictionary object, including on named-tag
loading. They are serialized once. Distinct directory dictionaries remain
distinct even if their tags share an object or have equal contents. A shared
image directory must have the same successor in every chain in which it occurs,
including termination. Edits to shared suffixes must therefore remain
consistent. The writer rejects conflicting successors, cycles, incompatible
uses of one directory as different IFD types, and malformed structures.

With ``key_is_name=True``, only tag keys change to names such as ``"Make"``
instead of numeric IDs such as ``271``. Structure and sharing are unchanged.
``dump_ifds()`` requires numeric tag IDs; use ``key_is_name=False`` for editing.

JPEG data belongs to the directory containing ``jpeg_data`` and moves with it.
Any image directory, including a primary image or SubIFD, may have its own
payload; these streams are not necessarily thumbnails. To retain them::

    directories = piexif.load_ifds("source.tif", load_jpeg_data=True)
    exif_bytes = piexif.dump_ifds(directories)

Only streams described by JPEGInterchangeFormat/JPEGInterchangeFormatLength
(513/514) are extracted, not JPEG-compressed strips or tiles. A zero or absent
513 means no stream. With extraction enabled, present nonzero offset/length
pairs must be in bounds. The loader does not decode JPEG pixels.

``dump_ifds()`` does not create implicit directories. Replacing ``jpeg_data``
replaces its bytes. Removing that key or setting it to ``None`` clears that
directory's 513/514 tags, retaining its other metadata and relationships.
Both tags are omitted on loading, even with extraction disabled, and rebuilt
only for supplied data when writing. Thus a default metadata-only load followed
by dumping does not preserve these streams or leave their old pointers behind.
The writer checks JPEG headers but does not decode pixels, strip APP segments,
or apply the standard thumbnail size limit. Other directories' data is independent.

Selecting a conventional Exif thumbnail is an explicit standard-API operation.
Choose an appropriate directory from a load with ``load_jpeg_data=True`` and
copy both its tags and JPEG data into a standard metadata dictionary::

    exif_dict["1st"] = selected_directory["tags"].copy()
    exif_dict["thumbnail"] = selected_directory["jpeg_data"]
    exif_bytes = piexif.dump(exif_dict)

The standard writer applies its usual thumbnail normalization and size limit.
The caller must select suitable tags and image data; neither API filters
TIFF-specific tags or enforces format-specific placement rules.

``dump_ifds()`` does not modify caller lists or dictionaries. ``insert()`` remains
unchanged: it embeds the serialized EXIF bytes, not this Python structure.

This is a supported-metadata round trip, not a lossless TIFF file round trip.
Unknown tags are omitted; original field types, offsets and padding need not
be preserved. Pixel strips, tiles, old JPEG tables, opaque MakerNotes and
other external/private pointers are not relocated. Only the explicitly loaded
or supplied ``jpeg_data`` payloads are copied. Moving TIFF metadata into a
JPEG does not automatically filter incompatible tags or convert image data.

insert
------

For ``insert()``, ``remove()``, and ``transplant()``, callers must supply an
empty ``io.BytesIO`` output buffer positioned at zero, such as ``io.BytesIO()``.
This contract also applies to their explicit byte/file variants. The functions
write at the current position without clearing or truncating the buffer, then
rewind it to zero for reading. Before reusing a buffer, the caller must reset it
with ``output.seek(0)`` and ``output.truncate(0)``.

.. py:function:: piexif.insert(exif_bytes, filename)

   Inserts exif into JPEG, WebP, or PNG.

   :param bytes exif_bytes: Exif as bytes
   :param str filename: JPEG, WebP, or PNG

::

    exif_bytes = piexif.dump(exif_dict)
    piexif.insert(exif_bytes, "foo.jpg")

.. py:function:: piexif.insert(exif_bytes, data, output)

   Inserts exif into JPEG, WebP, or PNG.

   :param bytes exif_bytes: Exif as bytes
   :param bytes data: JPEG, WebP, or PNG data
   :param io.BytesIO output: output data

insert_bytes
------------
.. py:function:: piexif.insert_bytes(exif_bytes, data, new_file=None)

   Inserts Exif into JPEG, WebP, or PNG bytes. ``data`` must be bytes and is
   never opened as a filename. Supply ``new_file`` as an output filename or
   ``io.BytesIO`` buffer; omitting it raises ``ValueError``.

::

    output = io.BytesIO()
    piexif.insert_bytes(exif_bytes, image_bytes, output)

insert_file
-----------
.. py:function:: piexif.insert_file(exif_bytes, filename, new_file=None)

   Inserts Exif into a JPEG, WebP, or PNG file. ``filename`` is always treated
   as a path, regardless of its name. Omitting ``new_file`` replaces the input
   file. Supply an output filename or ``io.BytesIO`` buffer to write elsewhere.

::

    piexif.insert_file(exif_bytes, "source.png", "updated.png")

``insert()`` retains automatic input detection. Use ``insert_bytes()`` or
``insert_file()`` when the input kind is known explicitly.

remove
------
.. py:function:: piexif.remove(filename)

   Removes exif data from JPEG, WebP, or PNG.

   :param str filename: JPEG, WebP, or PNG

::

    piexif.remove("foo.jpg")

.. py:function:: piexif.remove(data, output)

   Removes exif data from JPEG, WebP, or PNG.

   :param bytes data: JPEG, WebP, or PNG data
   :param io.BytesIO output: output data

``remove_bytes(data, output)`` is the explicit safe byte-input form and never
opens ``data`` as a filename. ``remove_file(filename, output=None)`` is the
explicit filesystem form. ``remove()`` retains its historical auto-detection;
use the explicit functions for untrusted input.

transplant
----------
.. py:function:: piexif.transplant(filename1, filename2)

   Copies exif data from filename1 to filename2.

   :param str filename1: JPEG
   :param str filename2: JPEG

::

    piexif.transplant("exif_src.jpg", "foo.jpg")

.. py:function:: piexif.transplant(exif_src, image_src, output)

   Transplant exif from exif_src to image_src.

   :param bytes exif_src: JPEG data
   :param bytes image_src: JPEG data
   :param io.BytesIO output: output data

transplant_bytes
----------------
.. py:function:: piexif.transplant_bytes(exif_src, image, new_file=None)

   Copies Exif from one JPEG byte string to another. Both inputs must be
   bytes and are never opened as filenames. Supply ``new_file`` as an output
   filename or ``io.BytesIO`` buffer; omitting it raises ``ValueError``.
   The source JPEG must contain Exif.

::

    output = io.BytesIO()
    piexif.transplant_bytes(source_bytes, image_bytes, output)

transplant_file
---------------
.. py:function:: piexif.transplant_file(exif_src, image, new_file=None)

   Copies Exif between two JPEG filenames. Both inputs are always treated as
   paths. Omitting ``new_file`` replaces ``image``; an output filename or
   ``io.BytesIO`` buffer writes elsewhere. The source JPEG must contain Exif.

::

    piexif.transplant_file("source.jpg", "destination.jpg")

``transplant()`` retains independent automatic detection for each input,
including calls that mix a filename with JPEG bytes.
