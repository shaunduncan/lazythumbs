from django.conf.urls.defaults import patterns

urlpatterns = patterns('',
    (r'thumb/(\d+)/(\d+)/([^/].+)/$', 'lazythumbs.views.thumbnail'),
    (r'thumb/([^/].+)/$', 'lazythumbs.views.default_thumbnail'),
)
