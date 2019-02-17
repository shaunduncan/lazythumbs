from django.conf.urls import url

from lazythumbs.views import LazyThumbRenderer

urlpatterns = [
    # we'll cleanse the liberal .+ in the view.
    url(r'lt_cache/(\w+)/(\d+/\d+|\d+)/(.+)$', LazyThumbRenderer.as_view(), name='lt_slash_sep'),
    url(r'lt_cache/(\w+)/(\d+x\d+)/(.+)$', LazyThumbRenderer.as_view(), name='lt_x_sep'),
    url(r'lt_cache/(\w+)/(x/\d+)/(.+)$', LazyThumbRenderer.as_view(), name='lt_x_width'),
]
