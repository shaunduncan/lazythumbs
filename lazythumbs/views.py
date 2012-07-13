from cStringIO import StringIO
from hashlib import md5
import errno
import logging
import os
import re
import types

from django.conf import settings
from django.core.cache import cache
from django.core.files.storage import FileSystemStorage
from django.core.files.base import ContentFile
from django.core.exceptions import SuspiciousOperation
from django.http import HttpResponse
from django.views.generic.base import View
from PIL import Image

from lazythumbs.util import geometry_parse, get_format

logger = logging.getLogger('lazythumbs')

def action(fun):
    """
    Decorator used to denote an instance method as an action: a function
    that takes a path to an image, performs PIL on it, and returns raw image
    data.
    """
    fun.is_action = True
    return fun


class LazyThumbRenderer(View):
    """
    Perform requested image render operations and handle fs logic and caching
    of 404s. Maps a requested action (currently 'thumbnail' and 'resize' are
    supported) to a matching method named after the action prefixed with
    'action_'. Once the argument signatures are relaxed one can implement new
    image transformations simply by subclassing this view and adding "action_"
    methods that return raw image data as a string.
    """
    def __init__(self):
        self.fs = FileSystemStorage()
        self._allowed_actions = [a.__name__
            for a in (getattr(self, a, None) for a in dir(self))
            if type(a) == types.MethodType and getattr(a, 'is_action', False)
        ]


    def get(self, request, action, geometry, source_path):
        """
        Perform action routing and handle sanitizing url input. Handles caching the path to a rendered image to
        django.cache and saves the new image on the filesystem. 404s are cached to
        save time the next time the missing image is requested.

        :param request: HttpRequest
        :param action: some action, eg thumbnail or resize
        :param geometry: a string of either '\dx\d' or just '\d'
        :param source_path: the fs path to the image to be manipulated
        :returns: an HttpResponse with an image/{format} content_type
        """

        # reject naughty paths and actions
        if source_path.startswith('/'):
            logger.info("%s: blocked bad path" % source_path)
            return self.four_oh_four()
        if re.match('\.\./', source_path):
            logger.info("%s: blocked bad path" % source_path)
            return self.four_oh_four()
        if action not in self._allowed_actions:
            logger.info("%s: bad action requested: %s" % (source_path, action))
            return self.four_oh_four()

        try:
            width, height = geometry_parse(action, geometry, ValueError)
        except ValueError, e:
            logger.info('corrupted geometry "%s" for action "%s"' % (geometry, action))
            return self.four_oh_four()

        width = int(width) if width is not None else None
        height = int(height) if height is not None else None

        rendered_path = request.path[1:]

        cache_key = self.cache_key(source_path, action, width, height)
        was_404 = cache.get(cache_key)

        if was_404 == 1:
            return self.four_oh_four()

        img_format = get_format(rendered_path)
        # TODO this tangled mess of try/except is hideous... but such is
        # filesystem io? No it can be cleaned up by splitting it out
        try:
            # does rendered file already exist?
            raw_data = self.fs.open(rendered_path).read()
        except IOError:
            if was_404 == 0:
                # then it *was* here last time. if was_404 had been None then
                # it makes sense for rendered image to not exist yet: we
                # probably haven't seen it, or it dropped out of cache.
                logger.info('rendered image previously on fs missing. regenerating')
            try:
                pil_img = getattr(self, action)(
                    width=width,
                    height=height,
                    img_path=source_path
                )
                # this code from sorl-thumbnail
                buf = StringIO()
                # TODO we need a better way of choosing options based on size and format
                params = {
                    'format': get_format(rendered_path),
                    'quality': 80,
                }

                if params['format'] == "JPEG" and pil_img.mode == 'P':
                    # Cannot save mode 'P' image as JPEG without converting first
                    # (This can happen if we have a GIF file without an extension and don't scale it)
                    pil_img = pil_img.convert()

                try:
                    pil_img.save(buf, **params)
                except IOError:
                    logger.exception("pil_img.save(%r)" % params)
                    # TODO reevaluate this except when we make options smarter
                    logger.info("Failed to create new image %s . Trying without options" % rendered_path)
                    pil_img.save(buf, format=img_format)
                raw_data = buf.getvalue()
                buf.close()
                try:
                    self.fs.save(rendered_path, ContentFile(raw_data))
                except OSError, e:
                    if e.errno == errno.EEXIST:
                        pass # race condition, another WSGI worker wrote file or directory first
                    else:
                        logger.exception("saving converted image")
                        raise

            except (IOError, SuspiciousOperation, ValueError), e:
                # we've now failed to find a rendered path as well as the
                # original source path. this is a 404.
                logger.info('404: %s' % e)
                cache.set(cache_key, 1, settings.LAZYTHUMBS_404_CACHE_TIMEOUT)
                return self.four_oh_four()

        cache.set(cache_key, 0, settings.LAZYTHUMBS_CACHE_TIMEOUT)

        return self.two_hundred(raw_data, img_format)

    @action
    def resize(self, width, height, img_path=None, img=None):
        """
        Thumbnail and crop. Thumbnails along larger dimension and then center
        crops to meet desired dimension.

        :param width: desired width in pixels. required.
        :param height: desired height in pixels. required.
        :param img_path: a path to an image on the filesystem
        :param img: a PIL Image object
        :returns: a PIL Image object
        """
        img = img or self.get_pil_from_path(img_path)
        if not img:
            raise ValueError('unable to determine find img given args')

        source_width = img.size[0]
        source_height = img.size[1]

        if width >= source_width and height >= source_height:
            return img

        img = self.thumbnail(
            width = width if source_width < source_height else None,
            height = height if source_height <= source_width else None,
            img = img
        )

        # see if we even have to crop
        if img.size == (width, height):
            return img

        left = (img.size[0] - width) / 2
        top = (img.size[1] - height) / 2
        right = left + width
        bottom = top + height

        return img.crop((left, top, right, bottom))

    @action
    def thumbnail(self, width=None, height=None, img_path=None, img=None):
        """
        Scale in one dimension retaining image ratio in the other. Either width
        or height is required.

        :param width: desired width in pixels. mutually exclusive with height.
        :param height: desired height in pixels. mutually exclusive with width
        :param img_path: a path to an image on the filesystem
        :param img: a PIL Image object
        :returns: a PIL Image object
        """
        img = img or self.get_pil_from_path(img_path)
        if not img:
            raise ValueError('unable to determine find img given args')
        if width and height or width is None and height is None:
            raise ValueError('thumbnail requires width XOR height; got (%s, %s)' % (width, height))

        source_width = img.size[0]
        source_height = img.size[1]
        scale = lambda a,b,c: int(int(a) * float(b) / float(c))

        # we are guaranteed to have either height or width which lets us take
        # some validation shortcuts here.
        width = width or scale(source_width, height, source_height)
        height = height or scale(source_height, width, source_width)

        if width >= source_width or height >= source_height:
            return img

        return self.scale(width, height, img=img)

    def scale(self, width, height, img_path=None, img=None):
        """
        Scale to desired dimensions paying no attention to ratio.

        :param width: desired width in pixels. required.
        :param height: desired height in pixels. required.
        :param img_path: a path to an image on the filesystem
        :param img: a PIL Image object
        :returns: a PIL Image object
        """
        img = img or self.get_pil_from_path(img_path)
        if not img:
            raise ValueError('unable to determine find img given args')

        if width > img.size[0]:
            width = img.size[0]

        if height > img.size[1]:
            height = img.size[1]

        # PIL is really bad at scaling GIFs. This helps a little with the quality.
        # (http://python.6.n6.nabble.com/Poor-Image-Quality-When-Resizing-a-GIF-tp2099779.html)
        if img.mode == "P":
            img = img.convert(mode="RGB", dither=Image.NONE)

        return img.resize((width, height), Image.ANTIALIAS)

    def get_pil_from_path(self, img_path):
        """
        given some path relative to MEDIA_ROOT, create a PIL Image and
        return it.

        :param img_path: a path to an image file relative to MEDIA_ROOT
        :raises IOError: if image is not found
        :return: PIL.Image
        """
        return Image.open(os.path.join(settings.MEDIA_ROOT, img_path))

    def cache_key(self, img_path, action, width, height):
        """
        Compute a unique cache key for an image operation. Takes width, height,
        fs path, and desired action into account.

        :param img_path: fs path to a source image
        :param action: string representing image manipulation to occur
        :param width: integer width in pixels
        :param height: integer height in pixels
        """
        hashed = self.hash_(img_path, action, width, height)
        return 'lazythumbs:%s' % hashed

    def hash_(self, img_path, action, width, height):
        """
        Generate an md5 hash for an image operation. Takes width, height,
        fs path, and desired action into account.

        :param img_path: fs path to a source image
        :param action: string representing image manipulation to occur
        :param width: integer width in pixels
        :param height: integer height in pixels
        """
        hashed = md5('%s:%s:%s:%s' % (img_path, action, width, height))
        return hashed.hexdigest()

    def two_hundred(self, img_data, img_format):
        """
        Generate a 200 image response with raw image data, Cache-Control set,
        and an image/{img_format} content-type.

        :param img_data: raw image data as a string
        """
        resp = HttpResponse(img_data, content_type='image/%s' % img_format.lower())
        resp['Cache-Control'] = 'public,max-age=%s' % settings.LAZYTHUMBS_CACHE_TIMEOUT
        return resp

    def four_oh_four(self):
        """
        Generate a 404 response with an image/jpeg content_type. Sets a
        Cache-Control header for caches like Akamai (browsers will ignore it
        since it's a 4xx.
        """
        resp = HttpResponse(status=404, content_type='image/jpeg')
        resp['Cache-Control'] = 'public,max-age=%s' % settings.LAZYTHUMBS_404_CACHE_TIMEOUT
        return resp
