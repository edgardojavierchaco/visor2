from django.contrib import messages

from django.contrib.auth.mixins import LoginRequiredMixin

from django.urls import reverse_lazy

from django.db import transaction

from django.views.generic import (
    ListView,
    CreateView,
    UpdateView,
    DeleteView,
    DetailView,
)


from django_tables2.views import SingleTableMixin


from apps.sirtee.models.hallazgos import Hallazgo

from apps.sirtee.forms.hallazgos import (
    HallazgoForm
)

from apps.sirtee.forms.evidencias import (
    EvidenciaHallazgoFormSet
)

from apps.sirtee.filters.hallazgos import (
    HallazgoFilter
)

from apps.sirtee.tables.hallazgos import (
    HallazgoTable
)



# ==========================================================
# LISTADO
# ==========================================================

class HallazgoListView(
    LoginRequiredMixin,
    SingleTableMixin,
    ListView
):

    model = Hallazgo

    table_class = HallazgoTable

    template_name = (
        "sirtee/hallazgos/list.html"
    )

    context_object_name = (
        "hallazgos"
    )

    paginate_by = 25



    def get_queryset(self):

        queryset = (

            Hallazgo.objects

            .select_related(

                "relevamiento",

                "sistema_constructivo",

                "area_afectada",

                "tipo_hallazgo",

                "criticidad",

                "riesgo",

                "estado",

                "usuario_responsable",

            )

            .prefetch_related(

                "evidencias",

            )

        )


        self.filterset = HallazgoFilter(

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


        context["filter"] = (
            self.filterset
        )


        return context




# ==========================================================
# DETALLE
# ==========================================================

class HallazgoDetailView(
    LoginRequiredMixin,
    DetailView
):

    model = Hallazgo


    template_name = (
        "sirtee/hallazgos/detail.html"
    )


    context_object_name = (
        "hallazgo"
    )



    def get_queryset(self):

        return (

            Hallazgo.objects

            .select_related(

                "relevamiento",

                "sistema_constructivo",

                "area_afectada",

                "tipo_hallazgo",

                "criticidad",

                "riesgo",

                "estado",

                "usuario_responsable",

            )

            .prefetch_related(

                "evidencias",

                "intervenciones",

            )

        )





# ==========================================================
# CREAR
# ==========================================================

class HallazgoCreateView(
    LoginRequiredMixin,
    CreateView
):


    model = Hallazgo


    form_class = HallazgoForm



    template_name = (
        "sirtee/hallazgos/form.html"
    )



    success_url = reverse_lazy(
        "sirtee:hallazgos-list"
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





    def get_context_data(
        self,
        **kwargs
    ):

        context = super().get_context_data(
            **kwargs
        )


        if self.request.POST:


            context["evidencias"] = (

                EvidenciaHallazgoFormSet(

                    self.request.POST,

                    self.request.FILES

                )

            )


        else:


            context["evidencias"] = (

                EvidenciaHallazgoFormSet()

            )



        return context





    @transaction.atomic

    def form_valid(
        self,
        form
    ):


        context = self.get_context_data()



        evidencia_formset = (

            context["evidencias"]

        )



        if not evidencia_formset.is_valid():


            return self.form_invalid(
                form
            )



        self.object = form.save()



        evidencias = (

            evidencia_formset.save(
                commit=False
            )

        )



        for evidencia in evidencias:


            evidencia.hallazgo = (
                self.object
            )


            evidencia.usuario = (
                self.request.user
            )


            evidencia.save()



        messages.success(

            self.request,

            "Hallazgo registrado correctamente."

        )



        return super().form_valid(form)






# ==========================================================
# EDITAR
# ==========================================================

class HallazgoUpdateView(
    LoginRequiredMixin,
    UpdateView
):


    model = Hallazgo


    form_class = HallazgoForm



    template_name = (
        "sirtee/hallazgos/form.html"
    )



    success_url = reverse_lazy(
        "sirtee:hallazgos-list"
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






    def get_context_data(
        self,
        **kwargs
    ):


        context = super().get_context_data(
            **kwargs
        )



        if self.request.POST:


            context["evidencias"] = (

                EvidenciaHallazgoFormSet(

                    self.request.POST,

                    self.request.FILES,

                    instance=self.object

                )

            )


        else:


            context["evidencias"] = (

                EvidenciaHallazgoFormSet(

                    instance=self.object

                )

            )



        return context






    @transaction.atomic

    def form_valid(
        self,
        form
    ):


        context = self.get_context_data()



        evidencia_formset = (

            context["evidencias"]

        )



        if not evidencia_formset.is_valid():


            return self.form_invalid(
                form
            )



        self.object = form.save()



        evidencias = (

            evidencia_formset.save(
                commit=False
            )

        )



        for evidencia in evidencias:


            evidencia.hallazgo = (
                self.object
            )


            evidencia.usuario = (
                self.request.user
            )


            evidencia.save()




        for evidencia in (
            evidencia_formset.deleted_objects
        ):


            evidencia.delete()





        messages.success(

            self.request,

            "Hallazgo actualizado correctamente."

        )



        return super().form_valid(form)






# ==========================================================
# ELIMINAR
# ==========================================================

class HallazgoDeleteView(
    LoginRequiredMixin,
    DeleteView
):


    model = Hallazgo



    template_name = (

        "sirtee/hallazgos/confirm_delete.html"

    )



    success_url = reverse_lazy(

        "sirtee:hallazgos-list"

    )




    def delete(
        self,
        request,
        *args,
        **kwargs
    ):


        messages.success(

            request,

            "Hallazgo eliminado correctamente."

        )


        return super().delete(

            request,

            *args,

            **kwargs

        )