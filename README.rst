Piexif fork
===========

This is a maintained fork of Piexif. Install the fork distribution with::

    pip install piexif-fork

The distribution is named ``piexif-fork``, but it still provides the existing
``piexif`` Python module, so existing ``import piexif`` code can continue to
use it.

See `issues.md <issues.md>`_ for fork issue tracking and planned work.

Original Piexif README
======================

Piexif
======

|Build Status| |Windows Build| |Coverage Status| |docs|


To simplify exif manipulations with Python. Writing, reading, and more... Piexif is pure Python. To everywhere with Python.


Document: http://piexif.readthedocs.org/en/latest/

Online demo: http://piexif-demo.appspot.com/demo

Install
-------

'easy_install'::

    $ easy_install piexif

or 'pip'::

    $ pip install piexif

or download .zip, extract it. Put 'piexif' directory into your environment.

Why Choose Piexif
-----------------

- Pure Python. So, it runs everywhere where Python runs.
- Easy exif manipulations. Read, write, remove...
- Documented. http://piexif.readthedocs.org/en/latest/

How to Use
----------

The standard API provides five functions.

- *load(filename)* - Get exif data as *dict*.
- *dump(exif_dict)* - Get exif as *bytes*.
- *insert(exif_bytes, filename)* - Insert exif into JPEG, WebP, or PNG.
- *remove(filename)* - Remove exif from JPEG, WebP, or PNG.
- *transplant(filename, filename)* - Transplant exif from JPEG to JPEG.

Loading, insertion, removal, and transplantation also have explicit byte/file variants:
``load_bytes()`` / ``load_file()``, ``insert_bytes()`` / ``insert_file()``,
``remove_bytes()`` / ``remove_file()``, and
``transplant_bytes()`` / ``transplant_file()``. Byte variants always treat their
input as image data; file variants always treat it as a path.

For ``io.BytesIO`` output, supply an empty buffer positioned at zero. Writers
do not clear or truncate it; they rewind it after writing. To reuse a buffer,
call ``seek(0)`` and ``truncate(0)`` before passing it again.

The advanced API supports nested directory lists:

- *load_ifds(input_data, key_is_name=False, load_jpeg_data=False)* - Read directory metadata, optionally including JPEG streams.
- *dump_ifds(ifds)* - Serialize directory lists and attached JPEG streams to Exif bytes.

``load_ifds_bytes()`` and ``load_ifds_file()`` select the input kind explicitly
and accept the same options as ``load_ifds()``.

Preservation
------------

This fork aims to preserve supported metadata values through ``load()`` and
``dump()``, and unchanged image data and unrelated metadata during EXIF
insertion, removal and transplantation. Rebuilt EXIF is not guaranteed to be
byte-identical. See `preservation goals and limitations <doc/about.rst#preservation-goals-in-this-fork>`_.

Example
-------

::

    exif_dict = piexif.load("foo1.jpg")
    for ifd in ("0th", "Exif", "GPS", "1st"):
        for tag in exif_dict[ifd]:
            print(piexif.TAGS[ifd][tag]["name"], exif_dict[ifd][tag])

With PIL(Pillow)
----------------

::

    from PIL import Image
    import piexif

    im = Image.open(filename)
    exif_dict = piexif.load(im.info["exif"])
    # process im and exif_dict...
    w, h = im.size
    exif_dict["0th"][piexif.ImageIFD.XResolution] = (w, 1)
    exif_dict["0th"][piexif.ImageIFD.YResolution] = (h, 1)
    exif_bytes = piexif.dump(exif_dict)
    im.save(new_file, "jpeg", exif=exif_bytes)

Environment
-----------

Tested on Python 2.7, 3.5+ and PyPy3. Piexif would run even on IronPython. Piexif is OS independent and can run on Google App Engine.

License
-------

This software is released under the MIT license, see LICENSE.txt.

.. |Build Status| image:: https://api.travis-ci.org/hMatoba/Piexif.svg?branch=master
   :target: https://travis-ci.org/hMatoba/Piexif
.. |Windows Build| image:: https://ci.appveyor.com/api/projects/status/github/hMatoba/Piexif?branch=master&svg=true
   :target: https://ci.appveyor.com/project/hMatoba/piexif
.. |Coverage Status| image:: https://coveralls.io/repos/hMatoba/Piexif/badge.svg?branch=master
   :target: https://coveralls.io/r/hMatoba/Piexif?branch=master
.. |docs| image:: https://readthedocs.org/projects/piexif/badge/?version=latest
   :target: https://readthedocs.org/projects/piexif/
