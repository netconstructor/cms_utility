from django.conf.urls.defaults import *
from django.conf import settings

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^cms_utility/', include('cms_utility.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/(.*)', admin.site.root),
    (r'^$', 'publisher.views.index'),
    
    (r'^options/$', 'publisher.views.cms_settings'),
    (r'^options/get/$', 'publisher.views.get_cms_settings'),
    (r'^options/clear/$', 'publisher.views.clear_cms_settings'),

    (r'^single_upload/$', 'publisher.views.single_upload'),
    (r'^single_upload/file_info/$', 'publisher.views.single_upload_file_info'),
    (r'^batch_upload/$', 'publisher.views.batch_upload'),
    (r'^batch_upload/hierarchy/$', 'publisher.views.batch_upload_hierarchy'),
    
    (r'^media/(?P<path>.*)$', 'django.views.static.serve',
            {'document_root': settings.MEDIA_ROOT}),
)

handler500 = 'publisher.views.server_error'
handler404 = 'publisher.views.page_not_found' 