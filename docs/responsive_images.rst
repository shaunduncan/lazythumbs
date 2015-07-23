.. _responsive_images:

Responsive Images
=================

Lazythumbs includes a useful facility for anyone using responsive layouts to adapt between
a range of display sizes. In these situations, loading images larger than you'll actually be
able to display (for example, on mobile devices) is often unwanted or even damaging in cases of
a limited and high-latency network. Lazythumbs can optimize the image loading for you.

To use this feature, be sure to load the lazythumbs.js script to support the client-side behavior.
When including your images in templates, use the special size 'responsive' to trigger the
injection of a placeholder for the clientside script to use, like so:

.. code-block:: html

    <script type="text/javascript" src="{{ STATIC_URL }}lib/lazythumbs/js/lazythumbs.js"></script>

    {% lazythumb img_file thumbnail 'responsive' as img %}
        <img {% img_attrs img %} alt="{{img_file.name}}" />
    {% endlazythumb %}

The placeholder used will be a 1x1 transparent image, and you'll use CSS to specify an appropriate
size, often differing based on the display size by way of relative sizing or media queries to build
a set of breakpoints.

Adaptive Sizing Tips
--------------------

You'll want to take some care with how you size the images in your layout. Here are some tips that
have come in handy in our experience.

Static Sizes
~~~~~~~~~~~~

At some breakpoints, it makes the most sense to specify static dimensions with concrete values to width
and height.

.. code-block:: css

    @media (max-width: 399px) {
        img.lead-photo {
            width: 380px;
            height: 250px;
        }
    }

Aspect Ratio Enforcement
~~~~~~~~~~~~~~~~~~~~~~~~

It often comes up that you want to keep a good ratio for your photos, for example 4:3, but you also
want to adapt the size to the space available in a display, rather than snapping them at certain break
points.

Using the ``ratio`` keyword
+++++++++++++++++++++++++++

You can use the ``ratio`` keyword:

.. code-block:: html

   {% lazythumb img_file mresize "responsive" ratio="16:9" as img %}
        <img {% img_attrs img %} alt="{{img_file.name}}" />
   {% endlazythumb %}

Using the above, lazythumbs will calculate the available space and
request an image that fills the available width and matches the
specified aspect ratio (here: "16:9").

Using CSS
+++++++++

This is really difficult to do, as there is no direct way to specify it in CSS, but there is a trick we
recommend to achieve a ratio enforcement. In this example, we'll specify a width and the percentage of
that width to enforce the height to keep at. We'll fill the available width in whatever container the
image appears, and adjust the height to maintain a 4:3 ratio.

.. code-block:: html

    <figure class=photo>
        <div class=elastic></div>
        {% lazythumb img_file thumbnail 'responsive' as img %}
            <img {% img_attrs img %} alt="{{img_file.name}}" />
        {% endlazythumb %}
    </figure>

.. code-block:: css

    figure.photo .elastic {
        padding-top: 75%; // This is where the magic happens
    }
    figure.photo img {
        position: absolute;
        top: 0;
        bottom: 0;
        left: 0;
        right: 0;
        margin: 0;
        background: @black;
        height: 100%;
    }

This trick is useful without lazythumbs, of course, but is particularly useful in combination with
responsively loading resized photos to fit a display.

Caveats
-------

* **You must use the ``lazythumbs.js`` javascript library**:
  For responsively-sized images to work, the ``lazythumbs.js`` library must be included in your page.
* **Responsively-sized images may not exactly match the size you've requested**:
  The returned image will (in normal situations) be *at* *least* the requested size but may be slightly larger.
  Images are snapped to various common sizes to ensure that we do not (in exceptional situations)
  generate a new image for every user's request.

