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
lazythumbs will introspect and hunt for width, height, and path properties at various levels under various names.
This lets us compute ahead of time the intended width/height of the new image
and provide it to the template context.
This is nice: you can speed up page rendering by having your img tags use preset dimensions
but you won't have to take the time to actually compute and save the new image at template render time.

Django's ImageFile will hit the filesystem to get dimensions but caches them in memory:
you'll only have to pay that cost once in your process.

.. note::

   For responsive designs, you can size the image responsively by using
   the size ``'responsive'``.

   See :ref:`responsive_images` for more information.

