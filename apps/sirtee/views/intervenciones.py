# apps/sirtee/views/intervenciones.py

from django.contrib import messages

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


from apps.sirtee.permissions import (
    PuedeVerIntervenciones
)

from apps.sirtee.services.permisos import PermisosSirtee



# =====================================================
# LISTADO
# =====================================================

class IntervencionListView(
    SirteePermissionMixin,
    ListView
):

    model = Intervencion

    permiso_requerido=PermisosSirtee.puede_ver_intervenciones


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

            .permitidos(
                self.request.user
            )

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
    
    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context["puede_gestionar"] = (
            PermisosSirtee.puede_gestionar(
                self.request.user
            )
        )

        return context







# =====================================================
# DETALLE
# =====================================================

class IntervencionDetailView(
    SirteePermissionMixin,
    DetailView
):

    model = Intervencion

    permiso_requerido=PermisosSirtee.puede_ver_intervenciones


    template_name = (
        "sirtee/intervenciones/detail.html"
    )


    context_object_name = (
        "intervencion"
    )



    def get_queryset(self):

        return (

            Intervencion.objects

            .permitidos(
                self.request.user
            )

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
    SirteePermissionMixin,
    CreateView
):

    model = Intervencion

    permiso_requerido=PermisosSirtee.puede_gestionar


    form_class = IntervencionForm


    template_name = (
        "sirtee/intervenciones/form.html"
    )



    def get_form_kwargs(self):

        kwargs = super().get_form_kwargs()

        kwargs.update(
            {
                "usuario":
                self.request.user
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
    SirteePermissionMixin,
    UpdateView
):

    model = Intervencion

    permiso_requerido=PermisosSirtee.puede_gestionar


    form_class = IntervencionForm


    template_name = (
        "sirtee/intervenciones/form.html"
    )



    def get_queryset(self):

        return (

            Intervencion.objects

            .permitidos(
                self.request.user
            )

        )




    def get_form_kwargs(self):

        kwargs = super().get_form_kwargs()


        kwargs.update(
            {
                "usuario":
                self.request.user
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
    SirteePermissionMixin,
    DeleteView
):

    model = Intervencion

    permiso_requerido=PermisosSirtee.puede_gestionar


    template_name = (
        "sirtee/intervenciones/confirm_delete.html"
    )


    success_url = reverse_lazy(
        "sirtee:intervenciones-list"
    )



    def get_queryset(self):

        return (

            Intervencion.objects

            .permitidos(
                self.request.user
            )

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
    SirteePermissionMixin,
    View
):


    permission = PuedeVerIntervenciones


    estado_destino = None


    mensaje = ""


    nivel = "success"




    def post(
        self,
        request,
        pk
    ):


        intervencion = get_object_or_404(

            Intervencion.objects.permitidos(
                request.user
            ),

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



        acciones = {

            "EN_EJECUCION": "iniciar",

            "PAUSADA": "pausar",

            "FINALIZADA": "finalizar",

            "CANCELADA": "cancelar",

        }


        accion = acciones.get(
            self.estado_destino
        )


        if not accion:

            messages.error(
                request,
                "Acción de estado no configurada."
            )

            return redirect(
                "sirtee:intervenciones-detail",
                pk=pk
            )


        metodo = getattr(
            intervencion,
            accion,
            None
        )


        if not metodo:

            messages.error(
                request,
                "La intervención no soporta esta transición."
            )

            return redirect(
                "sirtee:intervenciones-detail",
                pk=pk
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


class IntervencionIniciarView(
    IntervencionEstadoBaseView
):

    estado_destino = "EN_EJECUCION"

    mensaje = (
        "La intervención fue iniciada."
    )


class IntervencionPausarView(
    IntervencionEstadoBaseView
):

    estado_destino = "PAUSADA"

    nivel = "warning"

    mensaje = (
        "La intervención fue pausada."
    )

class IntervencionFinalizarView(
    IntervencionEstadoBaseView
):

    estado_destino = "FINALIZADA"

    mensaje = (
        "La intervención fue finalizada."
    )


class IntervencionCancelarView(
    IntervencionEstadoBaseView
):

    estado_destino = "CANCELADA"

    nivel = "error"

    mensaje = (
        "La intervención fue cancelada."
    )