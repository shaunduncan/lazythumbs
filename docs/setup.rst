Setup
=====

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

