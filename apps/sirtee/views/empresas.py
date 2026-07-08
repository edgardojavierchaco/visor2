from django.contrib import messages

from django.contrib.auth.mixins import LoginRequiredMixin

from django.db import transaction

from django.urls import reverse_lazy

from django.views.generic import (
    ListView,
    CreateView,
    UpdateView,
    DetailView,
    DeleteView,
)


from apps.sirtee.models.empresas import Empresa

from apps.sirtee.tables.empresas import EmpresaTable

from apps.sirtee.filters.empresas import EmpresaFilter

from apps.sirtee.forms.empresas import EmpresaForm

from apps.sirtee.security.mixins import (
    SirteePermissionMixin
)





# =====================================================
# LISTADO
# =====================================================


class EmpresaListView(
    LoginRequiredMixin,
    SirteePermissionMixin,
    ListView,
):


    model = Empresa


    template_name = (
        "sirtee/empresas/list.html"
    )


    context_object_name = (
        "empresas"
    )


    paginate_by = 25



    def get_queryset(self):


        qs = (

            Empresa.objects

            .activos()

            .order_by(
                "razon_social"
            )

        )



        self.filterset = EmpresaFilter(
            self.request.GET,
            queryset=qs
        )



        return self.filterset.qs






    def get_context_data(
        self,
        **kwargs
    ):


        context = super().get_context_data(
            **kwargs
        )



        context["table"] = EmpresaTable(
            self.object_list
        )



        context["filter"] = (
            self.filterset
        )



        return context







# =====================================================
# CREAR
# =====================================================


class EmpresaCreateView(
    LoginRequiredMixin,
    SirteePermissionMixin,
    CreateView,
):


    model = Empresa


    form_class = EmpresaForm


    template_name = (
        "sirtee/empresas/form.html"
    )


    success_url = reverse_lazy(
        "sirtee:empresas-list"
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
            "Empresa creada correctamente."
        )



        return super().form_valid(form)









# =====================================================
# EDITAR
# =====================================================


class EmpresaUpdateView(
    LoginRequiredMixin,
    SirteePermissionMixin,
    UpdateView,
):


    model = Empresa


    form_class = EmpresaForm


    template_name = (
        "sirtee/empresas/form.html"
    )


    success_url = reverse_lazy(
        "sirtee:empresas-list"
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
            "Empresa actualizada correctamente."
        )



        return super().form_valid(form)









# =====================================================
# DETALLE
# =====================================================


class EmpresaDetailView(
    LoginRequiredMixin,
    SirteePermissionMixin,
    DetailView,
):


    model = Empresa


    template_name = (
        "sirtee/empresas/detail.html"
    )


    context_object_name = (
        "empresa"
    )



    def get_queryset(self):


        return (

            Empresa.objects

            .all()

        )









# =====================================================
# ELIMINAR
# =====================================================


class EmpresaDeleteView(
    LoginRequiredMixin,
    SirteePermissionMixin,
    DeleteView,
):


    model = Empresa


    template_name = (
        "sirtee/empresas/confirm_delete.html"
    )


    success_url = reverse_lazy(
        "sirtee:empresas-list"
    )



    def delete(
        self,
        request,
        *args,
        **kwargs
    ):


        messages.success(
            request,
            "Empresa eliminada correctamente."
        )



        return super().delete(
            request,
            *args,
            **kwargs
        )