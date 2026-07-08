from django.urls import reverse_lazy
from apps.usuarios.models import UsuariosVisualizador
from django.views.generic import (
    ListView,
    CreateView,
    UpdateView,
    DetailView,
    DeleteView,
)


from apps.sirtee.models.relevamientos import Relevamiento

from apps.sirtee.forms.relevamientos import RelevamientoForm

from apps.sirtee.security.mixins import SirteePermissionMixin

from apps.sirtee.forms.relevamientos_update import (
    RelevamientoUpdateForm
)

from django.core.paginator import Paginator

from apps.sirtee.filters.relevamientos import (
    RelevamientoFilter
)

from apps.sirtee.data.padron import (
    PadronEscuelas
)

# --------------------------------------
# LISTADO
# --------------------------------------
class RelevamientoListView(
    SirteePermissionMixin,
    ListView
):

    model = Relevamiento


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
            .activos()
            .order_by("-fecha")

        )


        self.filterset = RelevamientoFilter(
            self.request.GET,
            queryset=queryset
        )


        return self.filterset.qs



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

                    "escuela": escuelas.get(
                        str(r.cueanexo)
                    )
                }

            )



        return context

# --------------------------------------
# DETALLE
# --------------------------------------

class RelevamientoDetailView(
    DetailView
):

    model = Relevamiento


    template_name = (
        "sirtee/relevamientos/detail.html"
    )


    context_object_name = (
        "relevamiento"
    )



# --------------------------------------
# CREAR
# --------------------------------------

class RelevamientoCreateView(
    CreateView
):

    model = Relevamiento

    form_class = RelevamientoForm


    template_name = (
        "sirtee/relevamientos/form.html"
    )


    success_url = reverse_lazy(
        "sirtee:relevamientos-list"
    )


    def form_valid(self, form):

        usuario = UsuariosVisualizador.objects.get(
            username=self.request.user.username
        )

        form.instance.usuario_creador = usuario
        
        return super().form_valid(
            form
        )



# --------------------------------------
# EDITAR
# --------------------------------------

class RelevamientoUpdateView(
    UpdateView
):

    model = Relevamiento

    form_class = RelevamientoUpdateForm


    template_name = (
        "sirtee/relevamientos/update.html"
    )


    success_url = reverse_lazy(
        "sirtee:relevamientos-list"
    )
    
    def form_valid(
        self,
        form
    ):

        response = super().form_valid(
            form
        )

        return response



# --------------------------------------
# ELIMINAR
# --------------------------------------

class RelevamientoDeleteView(
    DeleteView
):

    model = Relevamiento


    template_name = (
        "sirtee/relevamientos/confirm_delete.html"
    )


    success_url = reverse_lazy(
        "sirtee:relevamientos-list"
    )


    def delete(
        self,
        request,
        *args,
        **kwargs
    ):

        obj = self.get_object()

        obj.delete()

        return super().delete(
            request,
            *args,
            **kwargs
        )