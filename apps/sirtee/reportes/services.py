from django.db.models import Count


from apps.sirtee.models.intervenciones import Intervencion



def reporte_tecnico_intervenciones(
    queryset=None
):


    if queryset is None:

        queryset = Intervencion.objects.all()



    return queryset.select_related(

        "empresa",

        "hallazgo",

        "estado",

        "tipo",

        "prioridad",

    )