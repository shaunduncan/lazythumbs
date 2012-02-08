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
# doc: settings

def img_cache_key(img_path, width, height, action):
    """
    returns a cache key suitable for storing thumbnail metadata. We need a key
    that represents both the action taken and the target geometry of the newly
    created image.

    :param img_path: path to image relative to settings.THUMBNAIL_SOURCE
    :param width: target width in pixels for new image
    :param height: target height in pixels for new image
    :param action: string representing the action taken, eg "thumbnail"
    :returns: a cache key
    """
    return "lazythumbs:%s:%sx%s:%s" % (action, width, height, img_path)

def generate_thumbnail_from_path(img_path, width, height, crop='left'):
    """
    create and save to the filesystem a thumbnail based on the provided path to
    a source image.

    side effect: writes to the filesystem.

    :param img_path: path to an image stored on the filesystem
    :param width: integer width in pixels
    :param height: integer height in pixels
    :param crop: one of (top|left|bottom|right|center). Defaults to 'left'.
    :returns: a tuple (path_to_thumbnail, raw_image_data)
    """
    geometry = '%sx%s' % (width, height)
    tb = ThumbnailBackend()
    options = tb.default_options
    options['crop'] = crop

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

    return thumbnail_path, thumbnail_raw

def thumbnail(request, img_path, width, height):
    """
    Generate a thumbnail from img_path using the supplied width and height.
    a request for upscaling will generate a "thumbnail" but just leave the
    image at its existing dimensions. Responds with an image/jpeg. Defaults to
    a "resize and crop" with a left crop by default.

    :param request: HttpRequest object
    :param img_path: image filesystem path relative to THUMBNAIL_SOURCE
    :param width: integer width in pixels
    :param height: integer height in pixels
    """
    def four_oh_four():
        resp = HttpResponse(status=404, content_type='image/jpeg')
        resp['Cache-Control'] = 'public,max-age=%s' % settings.THUMBNAIL_404_CACHE_TIMEOUT
        return resp

    def two_hundred(data):
        resp = HttpResponse(data, content_type='image/jpeg')
        resp['Cache-Control'] = 'public,max-age=%s' % settings.THUMBNAIL_CACHE_TIMEOUT
        return resp

    geometry = '%sx%s' % (width, height)
    img_path = os.path.join(settings.THUMBNAIL_SOURCE_PATH, img_path)

    cache_key = img_cache_key(img_path, width, height, 'thumbnail')

    img_meta = cache.get(cache_key)

    if img_meta: #, then we've processed this already. see if it exists.
        img_meta = json.loads(img_meta)
        if img_meta.get('was_404'): #, then nothing to do. still a 404.
            return four_oh_four()
        # check and see if img is in cache but not filesystem.
        thumbnail_path = img_meta['thumbnail_path']
        if os.path.exists(thumbnail_path): #, then read and return
            thumbnail = ImageFile(thumbnail_path, default.storage)
            thumbnail_raw = thumbnail.read()
        else: # regnerate the image
            _, thumbnail_raw = generate_thumbnail_from_path(img_path, width, height)

        return two_hundred(thumbnail_raw)
    else:
        # we need to process this file: either create a thumbnail or 404.
        if (os.path.exists(img_path)): #, then we can process it.
            thumbnail_path, thumbnail_raw = generate_thumbnail_from_path(img_path, width, height)

            # cache path to written thumbnail
            img_meta = {'thumbnail_path':thumbnail_path, 'was_404':False}
            cache.set(cache_key, json.dumps(img_meta), settings.THUMBNAIL_CACHE_TIMEOUT)

            return two_hundred(thumbnail_raw)
        else:
            # img_path doesn't exist, so return 404.
            img_meta_json = json.dumps({'thumbnail_path':'', 'was_404':True})
            expires = settings.THUMBNAIL_404_CACHE_TIMEOUT
            cache.set(cache_key, img_meta_json, expires)
            return four_oh_four()

def default_thumbnail(request, img_path):
    """
    simple wrapper around thumbnail that passes
    settings.THUMBNAIL_DEFAULT_WIDTH and settings.THUMBNAIL_DEFAULT_HEIGHT

    :param img_path: image filesystem path relative to THUMBNAIL_SOURCE
    """
    width = settings.THUMBNAIL_DEFAULT_WIDTH
    height = settings.THUMBNAIL_DEFAULT_HEIGHT
    return thumbnail(request, img_path, width, height)
