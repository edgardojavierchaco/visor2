from django.contrib import messages

from django.urls import reverse_lazy

from django.db import transaction

from django.views.generic import (
    ListView,
    CreateView,
    UpdateView,
    DetailView,
    DeleteView,
)

from django.contrib.auth.mixins import LoginRequiredMixin


from apps.sirtee.models.seguimiento import Seguimiento

from apps.sirtee.forms.seguimiento import SeguimientoForm

from apps.sirtee.security.mixins import (
    SirteePermissionMixin
)





# =====================================================
# LISTADO
# =====================================================


class SeguimientoListView(
    LoginRequiredMixin,
    SirteePermissionMixin,
    ListView
):


    model = Seguimiento


    template_name = (
        "sirtee/seguimientos/list.html"
    )


    context_object_name = (
        "seguimientos"
    )


    paginate_by = 25



    def get_queryset(self):


        return (

            Seguimiento.objects

            .select_related(

                "relevamiento",

                "hallazgo",

                "intervencion",

                "intervencion__estado",

            )

            .order_by(
                "-fecha"
            )

        )







# =====================================================
# DETALLE
# =====================================================


class SeguimientoDetailView(
    LoginRequiredMixin,
    SirteePermissionMixin,
    DetailView
):


    model = Seguimiento


    template_name = (
        "sirtee/seguimientos/detail.html"
    )


    context_object_name = (
        "seguimiento"
    )



    def get_queryset(self):


        return (

            Seguimiento.objects

            .select_related(

                "relevamiento",

                "hallazgo",

                "intervencion",

            )

        )








# =====================================================
# CREAR
# =====================================================


class SeguimientoCreateView(
    LoginRequiredMixin,
    SirteePermissionMixin,
    CreateView
):


    model = Seguimiento


    form_class = SeguimientoForm


    template_name = (
        "sirtee/seguimientos/form.html"
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


        self.object = form.save(
            commit=False
        )


        self.object.usuario = (
            self.request.user
        )



        self.object.save()



        messages.success(

            self.request,

            "Seguimiento registrado correctamente."

        )


        return super().form_valid(form)





    def get_success_url(self):


        if self.object.intervencion:


            return reverse_lazy(

                "sirtee:intervenciones-detail",

                kwargs={

                    "pk":
                    self.object.intervencion.pk

                }

            )



        if self.object.hallazgo:


            return reverse_lazy(

                "sirtee:hallazgos-detail",

                kwargs={

                    "pk":
                    self.object.hallazgo.pk

                }

            )



        return reverse_lazy(

            "sirtee:seguimientos-list"

        )










# =====================================================
# EDITAR
# =====================================================


class SeguimientoUpdateView(
    LoginRequiredMixin,
    SirteePermissionMixin,
    UpdateView
):


    model = Seguimiento


    form_class = SeguimientoForm



    template_name = (
        "sirtee/seguimientos/form.html"
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


        response = super().form_valid(
            form
        )



        messages.success(

            self.request,

            "Seguimiento actualizado correctamente."

        )


        return response





    def get_success_url(self):


        return reverse_lazy(

            "sirtee:seguimientos-list"

        )









# =====================================================
# ELIMINAR
# =====================================================


class SeguimientoDeleteView(
    LoginRequiredMixin,
    SirteePermissionMixin,
    DeleteView
):


    model = Seguimiento



    template_name = (

        "sirtee/seguimientos/confirm_delete.html"

    )



    success_url = reverse_lazy(

        "sirtee:seguimientos-list"

    )




    def delete(
        self,
        request,
        *args,
        **kwargs
    ):


        messages.success(

            request,

            "Seguimiento eliminado correctamente."

        )


        return super().delete(

            request,

            *args,

            **kwargs

        )