from django.conf.urls.defaults import patterns
from lazythumbs.views import LazyThumbRenderer

urlpatterns = patterns('',
    # we'll cleanse the liberal .+ in the view.
    (r'lt_cache/(\w+)/(\d+\/\d+|\d+)/(.+)$', LazyThumbRenderer.as_view()),
)
