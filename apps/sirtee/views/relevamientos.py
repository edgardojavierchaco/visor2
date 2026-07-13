# apps/sirtee/views/relevamientos.py
from django.shortcuts import get_object_or_404
from django.contrib import messages

from django.shortcuts import redirect
from django.urls import reverse_lazy

from django.views.generic import (
    ListView,
    CreateView,
    UpdateView,
    DetailView,
    DeleteView,
)

from apps.sirtee.models.relevamientos import Relevamiento

from apps.sirtee.forms.relevamientos import (
    RelevamientoForm
)

from apps.sirtee.forms.relevamientos_update import (
    RelevamientoUpdateForm
)

from apps.sirtee.security.mixins import (
    SirteePermissionMixin
)

from apps.sirtee.permissions import (
    PuedeVerRelevamientos
)

from apps.usuarios.models import UsuariosVisualizador

from apps.sirtee.filters.relevamientos import (
    RelevamientoFilter
)

from apps.sirtee.data.padron import (
    PadronEscuelas
)

from apps.sirtee.services.permisos import PermisosSirtee



# ==================================================
# LISTADO
# ==================================================

class RelevamientoListView(
    SirteePermissionMixin,
    ListView
):

    model = Relevamiento

    permiso_requerido = PermisosSirtee.puede_ver_relevamientos

    template_name = (
        "sirtee/relevamientos/list.html"
    )

    context_object_name = (
        "relevamientos"
    )

    paginate_by = 20



    def get_queryset(self):


        queryset = (

            Relevamiento.objects
            .permitidos(
                self.request.user
            )
            .activos()
            .order_by(
                "-fecha"
            )

        )


        self.filterset = (
            RelevamientoFilter(
                self.request.GET,
                queryset=queryset
            )
        )


        return self.filterset.qs
    
    

# ==================================================
# CONTEXTO
# ==================================================

    def get_context_data(
        self,
        **kwargs
    ):

        context = super().get_context_data(
            **kwargs
        )


        relevamientos = (
            context["relevamientos"]
        )


        cueanexos = [
            str(r.cueanexo)
            for r in relevamientos
        ]


        escuelas = (
            PadronEscuelas
            .get_by_cueanexos(
                cueanexos
            )
        )


        context["filas"] = []


        for r in relevamientos:

            context["filas"].append(

                {
                    "relevamiento": r,

                    "escuela":
                    escuelas.get(
                        str(r.cueanexo)
                    )
                }

            )
        
        # ==========================================
        # Permisos para la interfaz
        # ==========================================

        context["puede_gestionar"] = (
            PermisosSirtee.puede_gestionar(
                self.request.user
            )
        )


        return context





# ==================================================
# DETALLE
# ==================================================

class RelevamientoDetailView(
    SirteePermissionMixin,
    DetailView
):

    model = Relevamiento

    permiso_requerido = PermisosSirtee.puede_ver_relevamientos


    template_name = (
        "sirtee/relevamientos/detail.html"
    )


    context_object_name = (
        "relevamiento"
    )


    def get_queryset(self):

        return (
            Relevamiento.objects
            .permitidos(
                self.request.user
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["escuela"] = PadronEscuelas.get(
            self.object.cueanexo
        )

        context["puede_gestionar"] = (
            PermisosSirtee.puede_gestionar(
                self.request.user
            )
        )

        return context



# ==================================================
# CREAR
# ==================================================

class RelevamientoCreateView(
    SirteePermissionMixin,
    CreateView
):

    model = Relevamiento

    permiso_requerido=PermisosSirtee.puede_gestionar


    form_class = RelevamientoForm


    template_name = (
        "sirtee/relevamientos/form.html"
    )


    success_url = reverse_lazy(
        "sirtee:relevamientos-list"
    )



    def form_valid(
        self,
        form
    ):


        form.instance.usuario_creador = (
            self.request.user
        )


        return super().form_valid(
            form
        )





# ==================================================
# EDITAR
# ==================================================

class RelevamientoUpdateView(
    SirteePermissionMixin,
    UpdateView
):

    model = Relevamiento

    permiso_requerido=PermisosSirtee.puede_gestionar


    form_class = (
        RelevamientoUpdateForm
    )


    template_name = (
        "sirtee/relevamientos/update.html"
    )


    success_url = reverse_lazy(
        "sirtee:relevamientos-list"
    )



    def get_queryset(self):

        return (
            Relevamiento.objects
            .permitidos(
                self.request.user
            )
        )





# ==================================================
# ELIMINAR
# ==================================================

class RelevamientoDeleteView(
    SirteePermissionMixin,
    DeleteView
):

    model = Relevamiento

    permiso_requerido=PermisosSirtee.puede_gestionar


    template_name = (
        "sirtee/relevamientos/confirm_delete.html"
    )


    success_url = reverse_lazy(
        "sirtee:relevamientos-list"
    )



    def get_queryset(self):

        return (
            Relevamiento.objects
            .permitidos(
                self.request.user
            )
        )



    def delete(self, request, *args, **kwargs):

        messages.success(
            request,
            "Relevamiento eliminado correctamente."
        )

        return super().delete(
            request,
            *args,
            **kwargs
        )


# ==================================================
# RELEVAMIENTOS DE UNA ESCUELA
# ==================================================

class RelevamientosEscuelaView(
    SirteePermissionMixin,
    ListView
):

    model = Relevamiento

    permiso_requerido = (
        PermisosSirtee.puede_ver_relevamientos
    )

    template_name = (
        "sirtee/relevamientos/list_escuela.html"
    )

    context_object_name = (
        "relevamientos"
    )

    paginate_by = 20


    def get_queryset(self):

        self.cueanexo = self.kwargs["cueanexo"]

        queryset = (

            Relevamiento.objects

            .permitidos(
                self.request.user
            )

            .activos()

            .filter(
                cueanexo=self.cueanexo
            )

            .select_related(
                "usuario_creador"
            )

            .prefetch_related(
                "hallazgos",
            )

            .order_by(
                "-fecha"
            )

        )

        return queryset


    def get_context_data(
        self,
        **kwargs
    ):

        context = super().get_context_data(
            **kwargs
        )

        escuela = PadronEscuelas.get(
            self.cueanexo
        )

        context["escuela"] = escuela

        context["cueanexo"] = self.cueanexo

        context["cantidad"] = (
            context["relevamientos"].paginator.count
            if hasattr(
                context["relevamientos"],
                "paginator"
            )
            else len(
                context["relevamientos"]
            )
        )

        context["puede_gestionar"] = (
            PermisosSirtee.puede_gestionar(
                self.request.user
            )
        )

        return context


# ==================================================
# DETALLE RELEVAMIENTO MAPA
# ==================================================

class RelevamientoDetailMapaView(
    SirteePermissionMixin,
    DetailView
):

    model = Relevamiento

    permiso_requerido = (
        PermisosSirtee.puede_ver_relevamientos
    )

    template_name = (
        "sirtee/relevamientos/detail_mapa.html"
    )

    context_object_name = (
        "relevamiento"
    )


    def get_queryset(self):

        return (

            Relevamiento.objects

            .permitidos(
                self.request.user
            )

            .select_related(
                "usuario_creador"
            )

            .prefetch_related(
                "hallazgos"
            )

        )


    def get_context_data(
        self,
        **kwargs
    ):

        context = super().get_context_data(
            **kwargs
        )

        context["escuela"] = (
            PadronEscuelas.get(
                self.object.cueanexo
            )
        )

        context["puede_gestionar"] = (
            PermisosSirtee.puede_gestionar(
                self.request.user
            )
        )

        return context