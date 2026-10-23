from django.http import JsonResponse
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import CreateView, UpdateView, ListView, DeleteView

from django.contrib.auth.mixins import LoginRequiredMixin

from .mixins import InformeBloqueoMixin

from .models import Aguapey, es_planilla_biblioteca_nueva
from .forms import AguapeyForm


class AguapeyVersionadoMixin:
    """Presentación por período sin modificar los registros históricos."""

    def es_planilla_nueva(self):
        periodo = self.get_periodo_activo()
        return es_planilla_biblioteca_nueva(periodo.meses, periodo.annos)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        planilla_nueva = self.es_planilla_nueva()
        nombre = 'Base de datos utilizada' if planilla_nueva else 'Aguapey'
        context['planilla_nueva'] = planilla_nueva
        context['nombre_seccion_periodo'] = nombre
        context['section_return_label'] = f'Volver a {nombre}'
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if not self.es_planilla_nueva():
            # Excluir el campo también del ModelForm: ni siquiera un POST
            # con ese dato debe alterar un registro del formato anterior.
            form.fields.pop('nombre_base_datos', None)
        return form


# =========================
# 🔹 UTIL
# =========================
class AguapeyCreateView(LoginRequiredMixin, InformeBloqueoMixin, AguapeyVersionadoMixin, CreateView):
    model = Aguapey
    form_class = AguapeyForm
    template_name = 'biblioteca/pem/aguapey/create.html'
    success_url = reverse_lazy('bibliotecas:aguapey_list')

    # =========================
    # DISPATCH
    # =========================
    def post(self, request, *args, **kwargs):

        try:
            action = request.POST.get('action')

            if action == 'add':

                form = self.get_form()

                if form.is_valid():
                    instance = form.save(commit=False)
                    self.aplicar_periodo_activo(instance)
                    instance.save()
                    form.save_m2m()
                    return JsonResponse(instance.toJSON())
                else:
                    return JsonResponse({
                        'error': True,
                        'errors': form.errors
                    })

            return JsonResponse({
                'error': True,
                'message': 'Acción no válida'
            })

        except Exception as e:
            return JsonResponse({
                'error': True,
                'message': str(e)
            })

    # =========================
    # CONTEXTO
    # =========================
    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)





        context['title'] = context['nombre_seccion_periodo']
        context['entity'] = context['nombre_seccion_periodo']
        context['list_url'] = self.success_url
        context['action'] = 'add'
        
        return context


#===========================
# UPDATE
#===========================
class AguapeyUpdateView(LoginRequiredMixin, InformeBloqueoMixin, AguapeyVersionadoMixin, UpdateView):
    model = Aguapey
    form_class = AguapeyForm
    template_name = 'biblioteca/pem/aguapey/create.html'
    success_url = reverse_lazy('bibliotecas:aguapey_list')

    # =========================
    # DISPATCH
    # =========================
    def post(self, request, *args, **kwargs):

        # 🔒 BLOQUEO
        try:
            action = request.POST.get('action')

            if action == 'edit':

                form = self.get_form()

                if form.is_valid():
                    instance = form.save(commit=False)
                    self.aplicar_periodo_activo(instance)
                    instance.save()
                    form.save_m2m()
                    return JsonResponse(instance.toJSON())
                else:
                    return JsonResponse({
                        "error": True,
                        "errors": form.errors
                    })

            return JsonResponse({
                "error": True,
                "message": "Acción no válida"
            })

        except Exception as e:
            return JsonResponse({
                "error": True,
                "message": str(e)
            })

    # =========================
    # CONTEXTO
    # =========================
    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)



        context['title'] = context['nombre_seccion_periodo']
        context['entity'] = context['nombre_seccion_periodo']
        context['list_url'] = self.success_url
        context['action'] = 'edit'        



        return context


#=====================
# DELETE
#=====================
class AguapeyDeleteView(LoginRequiredMixin, InformeBloqueoMixin, AguapeyVersionadoMixin, DeleteView):
    model = Aguapey
    template_name = 'biblioteca/pem/aguapey/delete.html'
    success_url = reverse_lazy('bibliotecas:aguapey_list')

    # =========================
    # DISPATCH
    # =========================
    def post(self, request, *args, **kwargs):

        # 🔒 BLOQUEO
        try:
            self.object.delete()

            return JsonResponse({
                "success": True,
                "message": "Registro eliminado correctamente"
            })

        except Exception as e:
            return JsonResponse({
                "error": True,
                "message": str(e)
            })

    # =========================
    # CONTEXTO
    # =========================
    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

    
        context['title'] = context['nombre_seccion_periodo']
        context['entity'] = context['nombre_seccion_periodo']
        context['list_url'] = self.success_url
        return context


#=========================
# LIST
#=========================
class AguapeyListView(LoginRequiredMixin, InformeBloqueoMixin, AguapeyVersionadoMixin, ListView):
    model = Aguapey
    template_name = 'biblioteca/pem/aguapey/list_aguapey.html'

    # =========================
    # SESSION
    # =========================
    def get_queryset(self):
        periodo = self.get_periodo_activo()
        return self.model.objects.filter(
            cueanexo=str(periodo.cueanexo),
            mes=periodo.meses,
            anio=periodo.annos,
        ).order_by('-anio', '-mes')

    def post(self, request, *args, **kwargs):

        try:
            if request.POST.get('action') == 'searchdata':

                data = [obj.toJSON() for obj in self.get_queryset()]

                return JsonResponse(data, safe=False)

            return JsonResponse({
                'error': True,
                'message': 'Acción no válida'
            })

        except Exception as e:
            import traceback
            print(traceback.format_exc())

            return JsonResponse({
                'error': True,
                'message': str(e)
            }, status=500)

    # =========================
    # CONTEXTO
    # =========================
    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)


        

        context['title'] = context['nombre_seccion_periodo']
        context['create_url'] = reverse_lazy('bibliotecas:aguapey_create')
        context['list_url'] = reverse_lazy('bibliotecas:aguapey_list')
        context['update_url'] = reverse_lazy('bibliotecas:aguapey_update', args=[0])
        context['entity'] = context['nombre_seccion_periodo']
        if context['planilla_nueva']:
            nombre = self.get_queryset().values_list(
                'nombre_base_datos', flat=True,
            ).first()
            context['tiene_registro_base_datos'] = nombre is not None
            context['nombre_base_datos'] = nombre or 'No informado'
        context['hide_lock_button'] = False
        context['generar_pdf_button'] = True
        context['before_url'] = reverse_lazy('bibliotecas:proctec_list')
        context['next_url'] = reverse_lazy('bibliotecas:fondos_list')

        return context
