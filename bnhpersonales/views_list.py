from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView
from django.db.models import Count, Prefetch

from .models import Personas, RegistroActividades


###################################
# LISTADO DE PERSONAS
###################################
class PersonasListView(LoginRequiredMixin, ListView):

    model = Personas
    template_name = 'bnh/personas/list.html'
    context_object_name = 'personas'
    paginate_by = 25

    def get_queryset(self):

        actividades_qs = (
            RegistroActividades.objects
            .select_related(
                'modalidad',
                'niveles',
                'ceic',
                'sit_revista',
                'cond_actividad'
            )
            .order_by('-f_desde')
        )

        return (
            Personas.objects
            .filter(usuario_creacion=self.request.user)
            .select_related(
                'sexo',
                'provincia',
                'localidad',
                'codigo_area'
            )
            .prefetch_related(
                Prefetch(
                    'actividades',
                    queryset=actividades_qs
                )
            )
            .annotate(
                total_actividades=Count('actividades')
            )
            .order_by('-fecha_creacion')
        )

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        queryset = self.get_queryset()

        context['total_personas'] = queryset.count()

        context['total_actividades'] = (
            RegistroActividades.objects
            .filter(usuario_creacion=self.request.user)
            .count()
        )

        return context


###################################
# DETALLE PERSONA
###################################
class PersonaDetailView(LoginRequiredMixin, DetailView):

    model = Personas
    template_name = 'bnh/personas/detail.html'
    context_object_name = 'persona'

    def get_queryset(self):

        actividades_qs = (
            RegistroActividades.objects
            .select_related(
                'modalidad',
                'niveles',
                'ceic',
                'sit_revista',
                'cond_actividad'
            )
            .order_by('-f_desde')
        )

        return (
            Personas.objects
            .filter(usuario_creacion=self.request.user)
            .select_related(
                'sexo',
                'provincia',
                'localidad',
                'codigo_area'
            )
            .prefetch_related(
                Prefetch(
                    'actividades',
                    queryset=actividades_qs
                )
            )
        )