from django.contrib.auth import views as auth_views
from django.urls import path

from .views import signup

urlpatterns = [
    path('signup/', signup, name='signup'),
    path('login/', auth_views.LoginView.as_view(), name='login')
]