# lazythumbs

### render-on-request thumbnails for django

## usage

* add to INSTALLED\_APPS
* configure:
 * **LAZYTHUMBS\_404\_CACHE\_TIMEOUT** how long before a 404'd thumbnail request is retried
 * **LAZYTHUMBS\_CACHE\_TIMEOUT** how long before a thumbnail gets regenerated
 * **LAZYTHUMBS\_DUMMY** whether or not the lazythumb template tag just uses placekitten
 * **LAZYTHUMBS\_URL** url prefix for lazythumb requests. used by template tag. (usually MEDIA\_URL or '')
 * **LAZYTHUMBS\_EXTRA_URLS** dictionary mapping of source urls to url prefixes for lazythumb requests. used by template tag

* add to urls.py

        (r'^lt/', include('lazythumbs.urls'))

* ask for a tiny kitten

        mysite.com/lt/lt_cache/thumbnail/20x20/kitten.jpg/

* use in a template

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

        <script type="text/javascript" src="{{ STATIC_URL }}lib/lazythumbs/js/lazythumbs.js"></script>

        {% lazythumb img_file thumbnail 'responsive' as img %}
            <img {% img_attrs img %} alt="{{img_file.name}}" />
        {% endlazythumb %}

## summary

lazythumbs acts as a PIL proxy for images stored in
MEDIA\_ROOT. It looks for the requested image and, if found,
generates a new image and writes it to the filesystem at MEDIA\_ROOT/lt\_cache.
If the request resulted in a 404 this is recorded in cache to avoid getting
hammered by repeated requests for images that don't exist.


## supported actions

* **scale** scale image to desired dimensions (no attention paid to ratio)
* **thumbnail** scale in a single dimension (eg "80" or "x48")
* **resize** thumbnail then center crop to desired dimensions

## the template tag

as its first argument the template tag accepts either a string or an object
(and Variables pointing to either). If the argument is an object (say, an
ImageFile) lazythumbs will introspect and hunt for width, height, and path
properties at various levels under various names. This lets us compute ahead of
time the intended width/height of the new image and provide it to the template
context. This is nice: you can speed up page rendering by having your img tags
use preset dimensions but you won't have to take the time to actually compute
and save the new image at template render time. Django's ImageFile will hit the
filesystem to get dimensions but caches them in memory: you'll only have to pay
that cost once in your process.

## meta

lazythumbs is in many ways a combination of [sorl-thumbnail](https://github.com/sorl/sorl-thumbnail)
and [thumpy](http://bits.btubbs.com/thumpy) and owes its existence to them both.

lazythumbs was written by nathaniel k smith <nathanielksmith@gmail.com> for
[cmg digital&strategy](http://cmgdigital.com/) and is licensed under the terms of the
MIT license.
