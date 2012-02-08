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

# TODO
# bug: cache does not respect img dimensions. consider using the "_get_thumbnail_filename" for caching.
# doc: settings
# feat: cache headers outbound
# feat: regen on cache hit, fs miss

def img_cache_key(img_path, geometry, action):
    """
    returns a cache key suitable for storing thumbnail metadata. We need a key
    that represents both the action taken and the target geometry of the newly
    created image. We currently only support 'thumbnail' as an action but in
    the future there will be actions like 'crop' and 'filter'.

    :param img_path: path to image relative to settings.THUMBNAIL_SOURCE
    :param geometry: WxH string representing image dimensions, eg "30x50".
    :param action: string representing the action taken, eg "thumbnail"
    """
    return "lazythumbs:%s:%s:%s" % (action, geometry, img_path)

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
    geometry = '%sx%s' % (width, height)
    img_path = os.path.join(settings.THUMBNAIL_SOURCE_PATH, img_path)

    cache_key = img_cache_key(img_path, geometry, 'thumbnail')

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
            tb = ThumbnailBackend()
            options = tb.default_options
            options['crop'] = 'left'

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
            # we don't have to worry about filesystem collisions (and
            # subsequent file corruption) since django's storage abstraction
            # layer handles all that for us (thanks django).
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
