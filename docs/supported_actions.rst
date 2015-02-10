API
===

Overview
--------

Lazythumbs exposes an API to request the generation and caching of an image at
any requested size, using a specified action to adapt the image appropriately.

.. code-block:: text

    mysite.com/lt/lt_cache/thumbnail/20/kitten.jpg/

This example would request a thumbnail of `kitten.jpg` at 20 pixels wide, but
will maintain the ratio of the original image.

.. code-block:: text

    mysite.com/lt/lt_cache/thumbnail/20/kitten.jpg/

                           ^         ^  ^
                           |         |  | The original image filename requested
                           |         |
                           |         | This parameter specifies the width requested
                           |         | For some actions, both width and height can
                           |         | be specified.
                           |
                           | This parameter specifies the action to adapt the
                           | image to the requested size.

For scale and resize actions, both the width and height are requested.

.. code-block:: text

    mysite.com/lt/lt_cache/resize/20/20/kitten.jpg/

                                  ^
                                  | Both the width and height are given in this
                                  | example.

If a version of the image requested has not been produced previously, it will
be created immediately, and cached for future use.

Actions
-------

+---------------+------------+---------------+------------------+
| Action        | Maintains  | Matte when    | Crops?           |
|               | aspect     | undersized ?  |                  |
|               | ratio?     |               |                  |
+===============+============+===============+==================+
| ``scale``     | No         | No            | No               |
|               |            | (stretched)   |                  |
+---------------+------------+---------------+------------------+
| ``thumbnail`` | Yes        | No            | No               |
|               |            | (undersized   |                  |
|               |            | image         |                  |
|               |            | returned)     |                  |
+---------------+------------+---------------+------------------+
| ``resize``    | Yes        | Yes (one      | Yes (only on     |
|               |            | dimension     | largest          |
|               |            | only; if both | dimension,       |
|               |            | are           | otherwise        |
|               |            | undersized,   | resizes)         |
|               |            | the           |                  |
|               |            | undersized    |                  |
|               |            | image is      |                  |
|               |            | returned)     |                  |
+---------------+------------+---------------+------------------+
| ``aresize``   | Yes        | Yes           | Yes (only if     |
|               |            |               | source           |
|               |            |               | orientation      |
|               |            |               | matches          |
|               |            |               | requested)       |
+---------------+------------+---------------+------------------+
| ``mresize``   | Yes        | Yes           | Yes              |
+---------------+------------+---------------+------------------+

``scale``
~~~~~~~~~

Scales image to desired dimensions (no attention paid to ratio).

``thumbnail``
~~~~~~~~~~~~~

Scale in a single dimension (eg "80" or "x48").

``resize``
~~~~~~~~~~

Thumbnail then center crop to desired dimensions.

``aresize``
~~~~~~~~~~~

Aspect ratio-aware resizing.  Thumbnails the image, and then center crops
to the desired dimensions if the source image's orientation matches
that of the requested image size's orientation.

``mresize``
~~~~~~~~~~~

Like ``resize`` above, thumbnail then center crop to desired dimensions,
but rather than returning an undersized image in situations where the
requested image dimensions are larger than the source image, return an
image with matting on all dimensions in which the source image is smaller
than the requested image size.

