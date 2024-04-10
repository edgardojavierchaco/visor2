from config.urls import path
from .views import LoginFormView

app_name='logueo'

urlpatterns=[
    path('',LoginFormView.as_view(),name='login'),
]