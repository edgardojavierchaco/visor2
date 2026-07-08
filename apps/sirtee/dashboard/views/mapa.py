import json

from django.views.generic import TemplateView

from django.core.serializers.json import DjangoJSONEncoder


from apps.sirtee.security.mixins import (
    SirteePermissionMixin
)


from apps.sirtee.dashboard.services.mapa import (
    MapaSIRTEE
)



class DashboardMapaView(
    SirteePermissionMixin,
    TemplateView
):


    template_name = (
        "sirtee/dashboard/mapa.html"
    )



    def get_context_data(
        self,
        **kwargs
    ):


        context = super().get_context_data(
            **kwargs
        )


        context["escuelas_json"] = json.dumps(
            MapaSIRTEE.escuelas_operativas(),
            cls=DjangoJSONEncoder
        )


        context["regiones"] = (
            MapaSIRTEE.regiones()
        )


        context["departamentos"] = (
            MapaSIRTEE.departamentos()
        )


        return context