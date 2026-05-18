from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib import messages
from django.views.generic import (
    ListView,
    DetailView,
    UpdateView,
    DeleteView
)

from django.db.models import (
    Count,
    Prefetch,
    Q
)

from .models import (
    Personas,
    RegistroActividades
)

from .forms import ActividadForm

from apps.bnhpersonas.helpers import (
    get_cueanexos_usuario
)


# =========================================================
# LISTADO PERSONAS
# =========================================================
class PersonasListView(
    LoginRequiredMixin,
    ListView
):

    model = Personas

    template_name = "bnh/personas/list.html"

    context_object_name = "personas"

    paginate_by = 25

    # =====================================================
    # CACHE CUEANEXOS
    # =====================================================
    def dispatch(self, request, *args, **kwargs):

        self.cueanexos_usuario = list(
            get_cueanexos_usuario(
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
                    queryset=actividades_qs,
                    to_attr="actividades_filtradas"
                )
            )

            .annotate(
                total_actividades=Count(
                    "actividades",
                    filter=Q(
                        actividades__cueanexo__in=self.cueanexos_usuario
                    )
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

        context["total_personas"] = (
            context["paginator"].count
        )

        context["total_actividades"] = (
            RegistroActividades.objects
            .filter(
                cueanexo__in=self.cueanexos_usuario
            )
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

    # =====================================================
    # CACHE CUEANEXOS
    # =====================================================
    def dispatch(self, request, *args, **kwargs):

        self.cueanexos_usuario = list(
            get_cueanexos_usuario(
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
                    queryset=actividades_qs,
                    to_attr="actividades_filtradas"
                )
            )
        )

        return queryset


# =========================================================
# UPDATE ACTIVIDAD
# =========================================================
class ActividadUpdateView(
    LoginRequiredMixin,
    UpdateView
):

    model = RegistroActividades

    form_class = ActividadForm

    template_name = 'bnh/personas/modal_update.html'

    # =====================================================
    # QUERYSET
    # =====================================================
    def get_queryset(self):

        cueanexos_usuario = list(
            get_cueanexos_usuario(
                self.request.user
            )
        )

        return RegistroActividades.objects.filter(
            cueanexo__in=cueanexos_usuario
        )

    # =====================================================
    # PASAR USER AL FORM
    # =====================================================
    def get_form_kwargs(self):

        kwargs = super().get_form_kwargs()

        kwargs["user"] = self.request.user

        return kwargs

    # =====================================================
    # VALID
    # =====================================================
    def form_valid(self, form):

        self.object = form.save()

        return JsonResponse({
            'success': True
        })

    # =====================================================
    # INVALID
    # =====================================================
    def form_invalid(self, form):

        return self.render_to_response(
            self.get_context_data(form=form)
        )
        

# =========================================================
# DELETE ACTIVIDAD
# =========================================================
class ActividadDeleteView(
    LoginRequiredMixin,
    DeleteView
):

    model = RegistroActividades

    def get_queryset(self):

        cueanexos_usuario = list(
            get_cueanexos_usuario(
                self.request.user
            )
        )

        return RegistroActividades.objects.filter(
            cueanexo__in=cueanexos_usuario
        )

    def post(self, request, *args, **kwargs):

        self.object = self.get_object()

        self.object.delete()

        return JsonResponse({
            'success': True
        })