from django.conf.urls import url

from wordstream import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^plot/$', views.plot, name='plot'),
    url(r'^download/$', views.download, name='download'),
    url(r'^(?P<keyword>\w+)/tweets/$', views.tweets, name='tweets')
]
