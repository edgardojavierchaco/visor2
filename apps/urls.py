from config.urls import path
from .views import videoteca

app_name='videoteca'

urlpatterns=[
    path('videos/',videoteca,name='videos'),    
]