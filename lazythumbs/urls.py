from django.conf.urls.defaults import patterns
from lazythumbs.views import LazyThumbRenderer

urlpatterns = patterns('',
    # we'll cleanse the liberal .+ in the view.
    (r'(\w+)/(\d+x\d+|\d+)/(.+)$', LazyThumbRenderer.as_view()),
)
