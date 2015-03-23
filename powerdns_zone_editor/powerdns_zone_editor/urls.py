from django.views.generic import TemplateView
from django.conf.urls import patterns, include, url
from django.contrib import admin

from client import views

urlpatterns = patterns('',
    url('^login/', 'django.contrib.auth.views.login', {'template_name': 'client/login.html'}),
    url('^logout/', 'django.contrib.auth.views.logout'),
    url(r'^api/zones/(?P<zone_id>[^/]+)/revisions/(?P<pk>[^/]+)$', views.ZoneRevisionView.as_view(), name='zone-revision'),
    url(r'^api/zones/(?P<pk>[^/]+)/revisions$', views.ZoneRevisionListView.as_view(), name='zone-revision-list'),
    url(r'^api/zones/(?P<pk>[^/]+)$', views.ZoneView.as_view(), name='zone-detail'),
    url(r'^api/zones/$', views.ZoneListView.as_view(), name='zone-list'),
    url(r'^api/user$', views.UserView.as_view(), name='user-detail'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^$', views.ClientView.as_view(), name='client'),
)
