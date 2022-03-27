"""SocialDistribution URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls import url
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from rest_framework.urlpatterns import format_suffix_patterns

from myapp import views


urlpatterns = [
    #
    #   Accounts
    #
    path('accounts/', include('accounts.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    #
    #   Feed
    #
    #path('', include('myapp.urls', 'postList')),
    #
    #   Admin
    #
    path('admin/', admin.site.urls),
    path('', include('myapp.urls')),
    #
    #   API
    #
    path('service/authors/', views.AuthorsAPIView.as_view(), name='service-authors'),
    path('service/authors/<str:uuid>', views.AuthorAPIView.as_view(), name='service-author'),
    path('service/authors/<str:author>/followers', views.FollowersAPIView.as_view(), name='service-followers'),
    path('service/authors/<str:author>/followers/<str:another_author>', views.FollowerAPIView.as_view(), name='service-follower'),
    # TODO write the FollowRequest
    path('service/authors/<str:author>/posts/<slug:pk>', views.PostAPIView.as_view(), name='service-post'),
    path('service/authors/<str:author>/posts/', views.PostsAPIView.as_view(), name='service-posts'),
    path('service/authors/<str:author>/posts/<slug:pk>/image', views.ImagePostAPIView.as_view(), name='service-image_post'),
    path('service/authors/<str:author>/posts/<slug:post>/comments', views.CommentsAPIView.as_view(), name='service-comments'),
    # TODO like api - 1
    path('service/authors/<str:author>/posts/<slug:post>/likes', views.LikesAPIView.as_view(), name='service-likes'),
    # TODO like api - 3
    path('service/authors/<str:author>/liked', views.LikedAPIView.as_view(), name='service-liked'),
    path('service/authors/<str:author>/inbox', views.InboxAPIView.as_view(), name='service-Inbox'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
