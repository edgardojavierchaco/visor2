from django.urls import path
from .api.views import IndicatorView
from .views_dashboard import DashboardIndicatorsView

app_name='indica'

urlpatterns = [
    ############
    # API JSON
    ############
    path("indicators/", IndicatorView.as_view()),
    
    ############
    # DASHBOARD
    ############
    path("dashboard/", DashboardIndicatorsView.as_view(), name="dashboard"),
]