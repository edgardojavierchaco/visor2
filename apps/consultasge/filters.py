import django_filters

from .models import Consulta


class ConsultaFilter(django_filters.FilterSet):

    class Meta:
        model = Consulta

        fields = ["estado","categoria","region"]