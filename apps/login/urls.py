from config.urls import path
from .views import *
from .views_reset_cuil import ResetPasswordCUILView, ConfirmResetCUILView

app_name='logueo'

urlpatterns=[
    path('',LoginFormView.as_view(),name='login'),    
    path('logout/',CustomLogoutView.as_view(),name='logout'),

    # RESET
    path('reset-cuil/', ResetPasswordCUILView.as_view(), name='reset_cuil'),
    path('confirm-reset-cuil/', ConfirmResetCUILView.as_view(), name='confirm_reset_cuil'),
]
