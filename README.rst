Summary
#######

Lazythumbs acts as a PIL proxy for images stored in
MEDIA_ROOT. It looks for the requested image and, if found,
generates a new image and writes it to the filesystem at MEDIA_ROOT/lt_cache.
If the request resulted in a 404, the 404 response is cached to avoid getting
hammered by repeated requests for images that don't exist.

Lazythumbs can be utilized from within a Django project's templates, or
from without through the image request API. Images are produced and cached
from their sources on-demand.

Setup
#####

* add `lazythumbs` to INSTALLED_APPS

* configure with Django settings:

 * **LAZYTHUMBS_404_CACHE_TIMEOUT** seconds before a 404'd thumbnail request is retried (required)
 * **LAZYTHUMBS_CACHE_TIMEOUT** seconds a lazythumb image remains cached by browsers (required)
 * **LAZYTHUMBS_DUMMY** whether or not the lazythumb template tag just uses placekitten. (default: `False`)
 * **LAZYTHUMBS_URL** url prefix for lazythumb requests. used by template tag. usually MEDIA_URL or ''. (default: `/`)
 * **LAZYTHUMBS\_EXTRA_URLS** dictionary mapping of source urls to url prefixes for lazythumb requests. used by template tag

* add to urls.py

.. code-block:: python

    (r'^lt/', include('lazythumbs.urls'))

Usage
#####

* ask for a tiny kitten

.. code-block:: text

    mysite.com/lt/lt_cache/thumbnail/20/20/kitten.jpg/

* use in a template

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

* delay the size until the layout is known, for responsive designs

.. code-block:: html

    <script type="text/javascript" src="{{ STATIC_URL }}lib/lazythumbs/js/lazythumbs.js"></script>

    {% lazythumb img_file thumbnail 'responsive' as img %}
        <img {% img_attrs img %} alt="{{img_file.name}}" />
    {% endlazythumb %}

Supported Actions
#################

* **scale** scale image to desired dimensions (no attention paid to ratio)
* **thumbnail** scale in a single dimension (eg "80" or "x48")
* **resize** thumbnail then center crop to desired dimensions

The Template Tag
################

As its first argument the template tag accepts either a string or an object
(and Variables pointing to either). If the argument is an object (say, an
ImageFile) lazythumbs will introspect and hunt for width, height, and path
properties at various levels under various names. This lets us compute ahead of
time the intended width/height of the new image and provide it to the template
context. This is nice: you can speed up page rendering by having your img tags
use preset dimensions but you won't have to take the time to actually compute
and save the new image at template render time. Django's ImageFile will hit the
filesystem to get dimensions but caches them in memory: you'll only have to pay
that cost once in your process.

API
###

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

Responsive Images
#################

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
^^^^^^^^^^^^^^^^^^^^

You'll want to take some care with how you size the images in your layout. Here are some tips that
have come in handy in our experience.

Static Sizes
''''''''''''

At some breakpoints, it makes the most sense to specify static dimensions with concrete values to width
and height.

.. code-block:: css

    @media (max-width: 399px) {
        img.lead-photo {
            width: 380px;
            height: 250px;
        }
    }

Responsive Ratio Enforcement
''''''''''''''''''''''''''''

It often comes up that you want to keep a good ratio for your photos, for example 4:3, but you also
want to adapt the size to the space available in a display, rather than snapping them at certain break
points.

This is really difficult to do, as there is no direct way to specify it in CSS, but there is a trick we
recommend to achieve a ratio enforcement. In this example, we'll specify a width and the percentage of
that width to enforce the height to keep at. We'll fill the available width in whatever container the
image appears, and adjust the height to maintain a 4:3 ratio.

.. code-block: html

    <figure class=photo>
        <div class=elastic></div>
        {% lazythumb img_file thumbnail 'responsive' as img %}
            <img {% img_attrs img %} alt="{{img_file.name}}" />
        {% endlazythumb %}
    </figure>

.. code-block: css

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

Meta
####

lazythumbs is in many ways a combination of `sorl-thumbnail <https://github.com/sorl/sorl-thumbnail>`_
and `thumpy <http://bits.btubbs.com/thumpy>`_ and owes its existence to them both.

lazythumbs was written by nathaniel k smith <nathanielksmith@gmail.com> for
`cmg digital&strategy <http://cmgdigital.com/>`_ and is licensed under the terms of the
MIT license.