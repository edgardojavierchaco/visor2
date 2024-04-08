from config.urls import path
from apps.login.views import *
from django.contrib.auth.views import LogoutView

app_name='acceso'

urlpatterns=[
    path('',LoginFormView.as_view(),name='acceso_login'),
    path('logout/',LogoutView.as_view(next_page='/cards/'),name='logout')
    ]
