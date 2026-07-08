from django.contrib import messages

from django.contrib.auth.mixins import LoginRequiredMixin

from django.db import transaction

from django.shortcuts import (
    get_object_or_404,
    redirect,
)

from django.urls import reverse_lazy

from django.views import View

from django.views.generic import (
    ListView,
    CreateView,
    UpdateView,
    DetailView,
    DeleteView,
)


from apps.sirtee.models.intervenciones import (
    Intervencion
)


from apps.sirtee.forms.intervenciones import (
    IntervencionForm
)


from apps.sirtee.security.mixins import (
    SirteePermissionMixin
)



# =====================================================
# LISTADO
# =====================================================

class IntervencionListView(
    LoginRequiredMixin,
    SirteePermissionMixin,
    ListView
):

    model = Intervencion

    template_name = (
        "sirtee/intervenciones/list.html"
    )

    context_object_name = (
        "intervenciones"
    )

    paginate_by = 25


    def get_queryset(self):

        return (

            Intervencion.objects

            .activos()

            .select_related(

                "hallazgo",

                "hallazgo__relevamiento",

                "tipo",

                "estado",

                "prioridad",

                "empresa",

                "organismo_responsable",

                "fuente_financiamiento",

            )

            .order_by(
                "-id"
            )

        )



# =====================================================
# DETALLE
# =====================================================

class IntervencionDetailView(
    LoginRequiredMixin,
    SirteePermissionMixin,
    DetailView
):

    model = Intervencion


    template_name = (
        "sirtee/intervenciones/detail.html"
    )


    context_object_name = (
        "intervencion"
    )


    def get_queryset(self):

        return (

            Intervencion.objects

            .activos()

            .select_related(

                "hallazgo",

                "hallazgo__relevamiento",

                "tipo",

                "estado",

                "prioridad",

                "empresa",

                "organismo_responsable",

                "fuente_financiamiento",

            )

        )



# =====================================================
# CREAR
# =====================================================

class IntervencionCreateView(
    LoginRequiredMixin,
    SirteePermissionMixin,
    CreateView
):

    model = Intervencion

    form_class = IntervencionForm


    template_name = (
        "sirtee/intervenciones/form.html"
    )


    def get_form_kwargs(self):

        kwargs = super().get_form_kwargs()

        kwargs.update(
            {
                "usuario": self.request.user
            }
        )

        return kwargs



    def get_initial(self):

        initial = super().get_initial()

        hallazgo_id = self.kwargs.get(
            "pk"
        )

        if hallazgo_id:

            initial["hallazgo"] = hallazgo_id


        return initial



    @transaction.atomic
    def form_valid(
        self,
        form
    ):

        self.object = form.save()


        messages.success(
            self.request,
            "Intervención creada correctamente."
        )


        return super().form_valid(
            form
        )



    def get_success_url(self):

        return reverse_lazy(
            "sirtee:intervenciones-detail",
            kwargs={
                "pk":
                self.object.pk
            }
        )



# =====================================================
# EDITAR
# =====================================================

class IntervencionUpdateView(
    LoginRequiredMixin,
    SirteePermissionMixin,
    UpdateView
):

    model = Intervencion


    form_class = IntervencionForm


    template_name = (
        "sirtee/intervenciones/form.html"
    )


    def get_form_kwargs(self):

        kwargs = super().get_form_kwargs()

        kwargs.update(
            {
                "usuario": self.request.user
            }
        )

        return kwargs



    @transaction.atomic
    def form_valid(
        self,
        form
    ):

        self.object = form.save()


        messages.success(
            self.request,
            "Intervención actualizada correctamente."
        )


        return super().form_valid(
            form
        )



    def get_success_url(self):

        return reverse_lazy(
            "sirtee:intervenciones-detail",
            kwargs={
                "pk":
                self.object.pk
            }
        )



# =====================================================
# ELIMINAR
# =====================================================

class IntervencionDeleteView(
    LoginRequiredMixin,
    SirteePermissionMixin,
    DeleteView
):

    model = Intervencion


    template_name = (
        "sirtee/intervenciones/confirm_delete.html"
    )


    success_url = reverse_lazy(
        "sirtee:intervenciones-list"
    )



    def delete(
        self,
        request,
        *args,
        **kwargs
    ):

        messages.success(
            request,
            "Intervención eliminada correctamente."
        )


        return super().delete(
            request,
            *args,
            **kwargs
        )



# =====================================================
# CAMBIO DE ESTADOS
# =====================================================


class IntervencionEstadoBaseView(
    LoginRequiredMixin,
    SirteePermissionMixin,
    View
):


    estado_destino = None


    mensaje = ""


    nivel = "success"



    def post(
        self,
        request,
        pk
    ):

        intervencion = get_object_or_404(
            Intervencion,
            pk=pk
        )


        if hasattr(
            intervencion,
            "puede_cambiar_a"
        ):

            if not intervencion.puede_cambiar_a(
                self.estado_destino
            ):

                messages.error(
                    request,
                    "Cambio de estado no permitido."
                )

                return redirect(
                    "sirtee:intervenciones-detail",
                    pk=pk
                )


        metodo = getattr(
            intervencion,
            self.estado_destino.lower()
        )


        metodo()


        messages.add_message(
            request,
            getattr(
                messages,
                self.nivel.upper()
            ),
            self.mensaje
        )


        return redirect(
            "sirtee:intervenciones-detail",
            pk=pk
        )



# =====================================================
# INICIAR
# =====================================================

class IntervencionIniciarView(
    IntervencionEstadoBaseView
):

    estado_destino = (
        "EN_EJECUCION"
    )

    mensaje = (
        "La intervención fue iniciada."
    )



# =====================================================
# PAUSAR
# =====================================================

class IntervencionPausarView(
    IntervencionEstadoBaseView
):

    estado_destino = (
        "PAUSADA"
    )

    nivel = "warning"

    mensaje = (
        "La intervención fue pausada."
    )



# =====================================================
# FINALIZAR
# =====================================================

class IntervencionFinalizarView(
    IntervencionEstadoBaseView
):

    estado_destino = (
        "FINALIZADA"
    )

    mensaje = (
        "La intervención fue finalizada."
    )



# =====================================================
# CANCELAR
# =====================================================

class IntervencionCancelarView(
    IntervencionEstadoBaseView
):

    estado_destino = (
        "CANCELADA"
    )

    nivel = "error"

    mensaje = (
        "La intervención fue cancelada."
    )