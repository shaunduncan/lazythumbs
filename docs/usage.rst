Usage
=====

Direct URL
----------

.. code-block:: text

    mysite.com/lt/lt_cache/thumbnail/20/20/kitten.jpg/

In a template using the 'lazythumb' template tag
------------------------------------------------

.. code-block:: html

    {% load lazythumb %}
    {% lazythumb img_file scale '80x80' as img %}
        <img {% img_attrs img %} alt="{{img_file.name}}" />
    {% endlazythumb %}
    {% lazythumb img_file resize '80x60' as img %}
        <img {% img_attrs img %} alt="{{img_file.name}}" />
    {% endlazythumb %}
    {% lazythumb img_file thumbnail '80' as img %}
        <img {% img_attrs img %} alt="{{img_file.name}}" />
    {% endlazythumb %}

As its first argument the template tag accepts either a string or an object.
If the argument is an object (say, an ImageFile)
lazythumbs will introspect and hunt for width, height, and path properties at
various levels under various names. This lets us compute ahead of time the
intended width/height of the new image and provide it to the template context.
This is nice: you can speed up page rendering by having your img tags use preset
dimensions but you won't have to take the time to actually compute and save the
new image at template render time.

Django's ImageFile will hit the filesystem to get dimensions but caches them in
memory: you'll only have to pay that cost once in your process.

.. note::

   For responsive designs, you can size the image responsively by using
   the size ``'responsive'``.

   See :ref:`responsive_images` for more information.

### Additional Options

Any keyword arguments passed after the width/height string are treated as
options that can be passed to the LazyThumbRenderer. For example:

.. code-block:: html

    {% lazythumb img_file mresize '80x80' force_scale='true' as img %}
        <img {% img_attrs img %} alt="{{img_file.name}}" />
    {% endlazythumb %}

In this example, ``force_scale`` is the additional option. Normally the
LazyThumbRenderer does not size images that are smaller than the requested
dimensions. However, the ``force_scale`` option, if set to ``'true'`` will
cause lazythumbs to scale the image even if it is smaller and could distort
the image.

.. note::

    Word of caution: many vendors have a requirement that photos should not be
    scaled upwards. Use the ``force_scale`` only if you know that this will not
    be an issue.

    In the case of ``mresize`` in the tag above, the tag adds matting to
    achieve the desired image size, so does not distort the image size if it
    is smaller.

Another option available is 'ratio'. See :ref:`responsive_images` for more
information.