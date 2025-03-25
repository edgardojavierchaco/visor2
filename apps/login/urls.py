from config.urls import path
from .views import *

app_name='logueo'

urlpatterns=[
    path('',LoginFormView.as_view(),name='login'),
    path('logout/',LogoutView.as_view(next_page='/publico/'),name='logout'),
]