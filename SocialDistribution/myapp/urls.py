from django.urls import path, include
from django.conf.urls import url
from django.contrib import admin
from django.contrib.auth import views as auth_views

from . import views
from .views import NewPostView, PostListView, PostDetailView, PostEditView, PostDeleteView, SharedPostView, ShareDetailView, friendRequests, acceptFriendRequest

app_name = 'myapp'
urlpatterns = [
    # ex: /polls/
    # path('feed/', views.feed, name='feed'),
    path('newpost/', NewPostView.as_view(), name='newpost'),
    # path('feed/', views.search),
    path('feed/',PostListView.as_view(), name='postList'),
    path('post/<uuid:pk>',PostDetailView.as_view(), name='postDetail'),
    path('post/edit/<uuid:pk>',PostEditView.as_view(), name='postEdit'),
    path('post/delete/<uuid:pk>',PostDeleteView.as_view(), name='postDelete'),
    path('authors/<str:user_id>', views.profile, name='profile'),
    path('follow', views.follow, name='follow'),
    path('friendRequests', friendRequests, name='friendRequests'),
    path('acceptFriendRequest/<actor_id>', acceptFriendRequest, name='acceptFriendRequest'),
    path('like', views.like, name='like'),
    path('liked/<uuid:post_id>', views.liked, name='liked'),
    path('post/<uuid:pk>/share', SharedPostView.as_view(), name='sharePost'),
    path('post/shared/<uuid:pk>',ShareDetailView.as_view(), name='shareDetail'),
    path('', views.getuser, name='getuser'),
]