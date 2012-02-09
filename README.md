# lazythumbs

### render-on-request thumbnails for django, powered by sorl-thumbnail

## usage

* add to INSTALLED\_APPS
* configure:
 * **THUMBNAIL\_SOURCE** path to look in for requested images
 * **THUMBNAIL\_PREFIX** path to prepend to generated thumbnail files relative to THUMBNAIL\_SOURCE
 * **THUMBNAIL\_CACHE\_TIMEOUT** how long before a thumbnail gets regenerated
 * **THUMBNAIL\_CACHE\_404\_TIMEOUT** how long before a 404'd thumbnail request is retried
 * **THUMBNAIL\_PROGRESSIVE** whether to render progressive jpegs or not
 * **THUMBNAIL\_DEFAULT\_WIDTH** default width of rendered thumbnails in pixels
 * **THUMBNAIL\_DEFAULT\_HEIGHT** default height of rendered thumbnails in pixels

* add to urls.py

        (r'^lt/', include('lazythumbs.urls'))
        
* ask for a tiny kitten

        mysite.com/lt/thumb/kitten.jpg/20/20/

## summary

lazythumbs acts as a thumbnailing proxy for images stored in
THUMBNAIL\_SOURCE. It looks for the requested image and, if found,
generates a thumbnail and writes it to the filesystem at THUMBNAIL\_SOURCE/THUMBNAIL\_PREFIX/. 
The path to the generated
thumbnail is cached, as is whether or not the request resulted in a 404 or not
(to avoid getting hammered by repeated requests for images that don't exist).

At a high level, the flow for getting a thumbnail is:

    GET /lt/thumbs/kitten.jpg/48/48/
    THUMBNAIL_SOURCE/kitten.jpg path in cache?
        was it a 404?
            return a a 404.
        else
            does the thumbnail still exist on the fs?
                serve it
            else
                generate, save, and serve it
    else
        THUMBNAIL_SOURCE/kitten.jpg exist on filesystem?
            generate, save, serve thumbnail and cache path
        else
            return, cache 404

In the future actions besides thumbnail can be supported though slight
refactoring and the addition of new views.

## meta

lazythumbs was written by nathaniel k smith <nathanielksmith@gmail.com> for
[cmg digital&strategy](http://cmgdigital.com/) and is licensed under the terms of the
MIT license.
