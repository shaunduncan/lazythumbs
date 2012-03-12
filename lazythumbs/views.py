from cStringIO import StringIO
from hashlib import md5
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

from lazythumbs.util import geometry_parse

logger = logging.getLogger(__name__)

def action(fun):
    """
    Decorator used to denote an instance method as an action: a function
    that takes a path to an image, performs PIL on it, and returns raw imag
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

    @action
    def resize(self, **kwargs):
        """
        Thumbnail+center crop. Resize along larger dimension and then center crop to
        meet smaller dimension.

        TODO
        """
        img = kwargs.get('img') or self.get_pil_from_path(kwargs['img_path'])

        width = kwargs['width']
        height = kwargs['height']
        source_width = img.size[0]
        source_height = img.size[1]

        if width > source_width or height > source_height:
            return img

        if width == source_width and height == source_height:
            return img

        img = self.thumbnail(**{
            'img': img,
            'width': width if source_width < source_height else None,
            'height': height if source_height <= source_width else None
        })

        # see if we even have to crop
        if img.size == (width, height):
            return img

        left = (img.size[0] - width) / 2
        top = (img.size[1] - height) / 2
        right = left + width
        bottom = top + height

        return img.crop((left, top, right, bottom))

    @action
    def thumbnail(self, **kwargs):
        """
        Scale in one dimension. Either width or height must be provided
        in kwargs.

        TODO
        """
        img = kwargs.get('img') or self.get_pil_from_path(kwargs['img_path'])
        source_width = img.size[0]
        source_height = img.size[1]
        scale = lambda a,b,c: int(int(a) * float(b) / float(c))

        # we are guaranteed to have either height or width which lets us take
        # some validation shortcuts here.
        width = kwargs.get('width') or scale(source_width, kwargs.get('height'), source_height)
        height = kwargs.get('height') or scale(source_height, kwargs.get('width'), source_width)

        if width >= source_width or height >= source_height:
            return img

        return self.scale(**{
            'img': img,
            'width': width,
            'height': height,
        })

    @action
    def scale(self, **kwargs):
        """
        Straight scale. Distortion will occur.

        TODO
        """
        img = kwargs.get('img') or self.get_pil_from_path(kwargs['img_path'])

        width = kwargs['width']
        height = kwargs['height']

        if width > img.size[0]:
            width = img.size[0]

        if height > img.size[1]:
            height = img.size[1]

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

    def get(self, request, action, geometry, source_path):
        """
        Perform action routing and handle sanitizing url input. Handles caching the path to a rendered image to
        django.cache and saves the new image on the filesystem. 404s are cached to
        save time the next time the missing image is requested.

        :param request: HttpRequest
        :param action: some action, eg thumbnail or resize
        :param geometry: a string of either '\dx\d' or just '\d'
        :param source_path: the fs path to the image to be manipulated
        :returns: an HttpResponse with an image/jpeg content_type
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
            logger.info('corrupted geometry "%s" for action "%s"' % (action, geometry))
            return self.four_oh_four()

        width = int(width) if width is not None else None
        height = int(height) if height is not None else None

        rendered_path = self.generate_path(source_path, action, width, height)

        cache_key = self.cache_key(source_path, action, width, height)
        was_404 = cache.get(cache_key)

        if was_404 == 1:
            return self.four_oh_four()

        # TODO this tangled mess of try/except is hideous... but such is
        # filesystem io?
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
                kwargs = dict(width=width, img_path=source_path, height=height)
                pil_img = getattr(self, action)(**kwargs)
                # this code from sorl-thumbnail
                buf = StringIO()
                params = {
                    'format': 'JPEG',
                    'optimize': 1,
                    'progressive': True
                }
                try:
                    pil_img.save(buf, **params)
                except IOError:
                    logger.info('failed to optimize jpeg, removing option')
                    params.pop('optimize')
                    pil_img.save(buf, **params)
                raw_data = buf.getvalue()
                buf.close()
                self.fs.save(rendered_path, ContentFile(raw_data))
            except (IOError, SuspiciousOperation), e:
                # we've now failed to find a rendered path as well as the
                # original source path. this is a 404.
                logger.info('404: %s' % e)
                cache.set(cache_key, 1, settings.LAZYTHUMBS_404_CACHE_TIMEOUT)
                return self.four_oh_four()

        cache.set(cache_key, 0, settings.LAZYTHUMBS_CACHE_TIMEOUT)

        return self.two_hundred(raw_data)

    def generate_path(self, img_path, action, width, height):
        """
        Return the path that the rendered form of this image would be saved to.
        :param img_path: path to an image
        :param action: an action method name
        :param width: desired image width in pixels
        :param height: desired image height in pixels

        :returns: a path to a would-be rendered image
        """
        # TODO this method is only called once but might be useful in a script
        # or elsewhere.
        action_hash = self.hash_(img_path, action, width, height)
        return os.path.join(settings.LAZYTHUMBS_PREFIX, action_hash[0:2],
            action_hash[2:4], action_hash)

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

    def two_hundred(self, img_data):
        """
        Generate a 200 image response with raw image data, Cache-Control set,
        and an image/jpeg content-type.

        :param img_data: raw image data as a string
        """
        resp = HttpResponse(img_data, content_type='image/jpeg')
        resp['Cache-Control'] = 'public,max-age=%s' % settings.LAZYTHUMBS_CACHE_TIMEOUT
        return resp

    def four_oh_four(self):
        """
        Generate a 404 response with an image/jpeg content_type. Sets a
        Cahce-Control header for caches like Akamai (browsers will ignore it
        since it's a 4xx.
        """
        resp = HttpResponse(status=404, content_type='image/jpeg')
        resp['Cache-Control'] = 'public,max-age=%s' % settings.LAZYTHUMBS_404_CACHE_TIMEOUT
        return resp
