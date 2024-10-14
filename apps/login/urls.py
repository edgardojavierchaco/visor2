from config.urls import path
from .views import *

app_name='logueo'

urlpatterns=[
    path('',LoginFormView.as_view(),name='login'),    
    path('logout/',CustomLogoutView.as_view(),name='logout'),
    
]