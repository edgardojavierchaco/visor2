from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Prefetch, Q, Value, CharField
from django.views.generic import ListView, DetailView

from apps.consultasge.models_padron import CapaUnicaOfertas

from .models import Personas, RegistroActividades
from .domain.access import get_user_cueanexos


# =========================================================
# LISTADO PERSONAS
# =========================================================
class PersonasListView(LoginRequiredMixin, ListView):
    model = Personas
    template_name = "bnh/personas/list.html"
    context_object_name = "personas"
    paginate_by = 25

    # =====================================================
    # CACHE CUEANEXOS
    # =====================================================
    def dispatch(self, request, *args, **kwargs):

        self.cueanexos_usuario = (get_user_cueanexos(
                request.user
            )
        )

        return super().dispatch(
            request,
            *args,
            **kwargs
        )

    # =====================================================
    # QUERYSET
    # =====================================================
    def get_queryset(self):

        actividades_qs = (

            RegistroActividades.objects

            .filter(
                cueanexo__in=self.cueanexos_usuario
            )

            .select_related(
                "modalidad",
                "niveles",
                "ceic",
                "sit_revista",
                "cond_actividad"
            )

            .order_by("-f_desde")
        )

        queryset = (

            Personas.objects

            .filter(
                actividades__cueanexo__in=self.cueanexos_usuario
            )

            .distinct()

            .select_related(
                "sexo",
                "provincia",
                "localidad",
                "codigo_area"
            )

            .prefetch_related(
                Prefetch(
                    "actividades",
                    queryset=actividades_qs
                )
            )

            .annotate(
                total_actividades=Count(
                    "actividades",
                    filter=Q(
                        actividades__cueanexo__in=self.cueanexos_usuario
                    ),
                    distinct=True
                )
            )

            .order_by("-fecha_creacion")
        )

        return queryset

    # =====================================================
    # CONTEXTO
    # =====================================================
    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        
        actividades = RegistroActividades.objects.filter(
            cueanexo__in=self.cueanexos_usuario
        )

        context["total_personas"] = (
            context["paginator"].count
        )

        context["total_actividades"] = (
            actividades.count()
        )

        context["total_activos"] = (
            actividades
            .filter(estado="ACTIVO")
            .values("persona")
            .distinct()
            .count()
        )

        context["total_pasivos"] = (
            actividades
            .exclude(estado="ACTIVO")
            .values("persona")
            .distinct()
            .count()
        )

        return context


# =========================================================
# DETALLE PERSONA
# =========================================================
class PersonaDetailView(
    LoginRequiredMixin,
    DetailView
):

    model = Personas

    template_name = "bnh/personas/detail.html"

    context_object_name = "persona"

    def dispatch(self, request, *args, **kwargs):

        self.cueanexos_usuario = get_user_cueanexos(
            request.user
        )

        return super().dispatch(
            request,
            *args,
            **kwargs
        )

    def get_queryset(self):

        actividades_qs = (
            RegistroActividades.objects
            .filter(
                cueanexo__in=self.cueanexos_usuario
            )
            .select_related(
                "modalidad",
                "niveles",
                "ceic",
                "sit_revista",
                "cond_actividad",
            )
            .order_by("-f_desde")
        )

        return (
            Personas.objects
            .filter(
                actividades__cueanexo__in=self.cueanexos_usuario
            )
            .distinct()
            .select_related(
                "sexo",
                "provincia",
                "localidad",
                "codigo_area",
            )
            .prefetch_related(
                Prefetch(
                    "actividades",
                    queryset=actividades_qs,
                )
            )
            .annotate(
                total_actividades=Count(
                    "actividades",
                    filter=Q(
                        actividades__cueanexo__in=self.cueanexos_usuario
                    ),
                    distinct=True,
                )
            )
        )