""" primary work of this app is done in the views. """
import json
import os

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse

from sorl.thumbnail import default
from sorl.thumbnail.base import ThumbnailBackend
from sorl.thumbnail.images import ImageFile
from sorl.thumbnail.parsers import parse_geometry

def img_cache_key(img_path):
    """ returns a cache key suitable for storing thumbnail metadata. """
    return "lazythumbs:%s" % img_path

def thumbnail(request, img_path, width, height):
    """
    Generate a thumbnail from img_path using the supplied width and height.
    a request for upscaling will generate a "thumbnail" but just leave the
    image at its existing dimensions. Responds with an image/jpeg.

    :param request: HttpRequest object
    :param img_path: path to an image stored on the filesystem
    :param width: integer width in pixels
    :param height: integer height in pixels
    """
    response = HttpResponse(content_type='image/jpeg')

    img_path = os.path.join(settings.THUMBNAIL_SOURCE_PATH, img_path)
    cache_key = img_cache_key(img_path)

    img_meta = cache.get(cache_key)

    if img_meta:
        # we've processed this already. see if it exists or should be a 404.
        img_meta = json.loads(img_meta)
        if not img_meta.get('was_404'):
            # generated thumbnail exists on filesystem,
            # read and return it.
            thumbnail_path = img_meta['path']
            thumbnail = ImageFile(thumbnail_path, default.storage)
            response.content = thumbnail.read()
            return response
        else:
            # no thumbnail (because img_path doesn't exist.) just continue to
            # return a 404.
            response.status_code = 404
            return response
    else:
        # we need to process this file: either generate a thumbnail or conclude
        # 404.
        if (os.path.exists(img_path)): #, then we can process it.
            geometry = '%sx%s' % (width, height)
            tb = ThumbnailBackend()
            options = tb.default_options

            # source is an ImageFile; a sorl-thumbnail abstraction for image
            # files on the fs. source_img is an Image; a wrapper around
            # in-memory PIL (or whatever engine) image data.
            source = ImageFile(img_path, default.storage)
            source_img = default.engine.get_image(source)
            source.set_size(default.engine.get_image_size(source_img))

            thumbnail_path = tb._get_thumbnail_filename(source, geometry, options)
            thumbnail = ImageFile(thumbnail_path, default.storage)

            # create the thumbnail in memory
            ratio = default.engine.get_image_ratio(source)
            geometry = parse_geometry(geometry, ratio)
            thumbnail_img = default.engine.create(source_img, geometry, options)

            # extract its raw data
            f = options['format']
            q = options['quality']
            prog = options.get('progressive', settings.THUMBNAIL_PROGRESSIVE)
            thumbnail_raw = default.engine._get_raw_data(thumbnail_img, f, q, progressive=prog)

            # save raw data to filesystem
            thumbnail.write(thumbnail_raw)

            # put raw data in response
            response.content = thumbnail_raw

            # cache path to written thumbnail
            img_meta = {'path':thumbnail_path, 'was_404':False}
            cache.set(cache_key, json.dumps(img_meta), settings.THUMBNAIL_CACHE_TIMEOUT)

            return response
        else:
            # img_path doesn't exist, so return 404.
            img_meta_json = json.dumps({'path':'', 'was_404':True})
            expires = settings.THUMBNAIL_404_CACHE_TIMEOUT
            cache.set(cache_key, img_meta_json, expires)
            response.status_code = 404
            return response

def default_thumbnail(request, img_path):
    width = settings.THUMBNAIL_DEFAULT_WIDTH
    height = settings.THUMBNAIL_DEFAULT_HEIGHT
    return thumbnail(request, img_path, width, height)
