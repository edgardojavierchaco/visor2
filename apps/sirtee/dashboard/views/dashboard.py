from django.views.generic import TemplateView

from apps.sirtee.dashboard.services.indicadores import (
    DashboardSIRTEE
)

from apps.sirtee.security.mixins import (
    SirteePermissionMixin
)



class DashboardView(
    SirteePermissionMixin,
    TemplateView
):


    template_name = (
        "sirtee/dashboard/index.html"
    )


    def get_context_data(
        self,
        **kwargs
    ):

        context = super().get_context_data(
            **kwargs
        )


        context.update(
            DashboardSIRTEE.resumen()
        )


        return context