#from django.urls import path
from config.urls import path
from apps.users.views import LoginFormView

app_name='users'

urlpatterns=[
    path('login/', LoginFormView.as_view(), name='login'),
]
