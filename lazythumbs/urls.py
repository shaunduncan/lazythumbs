try:
    from django.conf.urls import patterns, url
except ImportError:
    from django.conf.urls.defaults import patterns, url  # support Django 1.3

from lazythumbs.views import LazyThumbRenderer

urlpatterns = patterns('',
    # we'll cleanse the liberal .+ in the view.
    url(r'lt_cache/(\w+)/(\d+/\d+|\d+)/(.+)$', LazyThumbRenderer.as_view(), name='lt_slash_sep'),
    url(r'lt_cache/(\w+)/(\d+x\d+)/(.+)$', LazyThumbRenderer.as_view(), name='lt_x_sep'),
    url(r'lt_cache/(\w+)/(x/\d+)/(.+)$', LazyThumbRenderer.as_view(), name='lt_x_width'),
)