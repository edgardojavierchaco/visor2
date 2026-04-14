from django.http import JsonResponse
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import CreateView, UpdateView, ListView, DeleteView

from django.contrib.auth.mixins import LoginRequiredMixin

from django.db.models import F, Func, Value
import re

from .models import Aguapey, GenerarInforme
from .forms import AguapeyForm
from apps.consultasge.models_padron import CapaUnicaOfertas


# =========================================================
# 🔥 MIXIN: obtiene cueanexo una sola vez (REUTILIZABLE)
# =========================================================
class CueanexoMixin:
    def get_cueanexo(self):
        usuario_limpio = re.sub(r'\D', '', self.request.user.username)

        qs = CapaUnicaOfertas.objects.annotate(
            cuit_limpio=Func(
                F('resploc_cuitcuil'),
                Value('-'),
                Value(''),
                function='REPLACE'
            )
        ).filter(
            cuit_limpio=usuario_limpio,
            oferta='Común - Servicios complementarios ',
            acronimo='BI'
        ).values_list('cueanexo', flat=True)

        return qs.first() if qs.exists() else None


# =========================================================
# CARGA
# =========================================================
class AguapeyCreateView(LoginRequiredMixin, CueanexoMixin, CreateView):
    model = Aguapey
    form_class = AguapeyForm
    template_name = 'biblioteca/pem/aguapey/create.html'
    success_url = reverse_lazy('bibliotecas:aguapey_list')

    def form_valid(self, form):
        form.instance.cueanexo = self.get_cueanexo()
        return super().form_valid(form)

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST.get('action')

            if action == 'add':
                form = self.get_form()
                if form.is_valid():
                    instance = form.save()
                    data = {
                        'message': 'Guardado correctamente',
                        'instance': instance.toJSON()
                    }
                else:
                    total_error = form.errors.get('total')
                    data['error'] = total_error[0] if total_error else 'Errores en el formulario'
            else:
                data['error'] = 'Acción no válida'

        except Exception as e:
            data['error'] = str(e)

        return JsonResponse(data)


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        cueanexo = self.get_cueanexo()

        context['title'] = 'Carga de Aguapey'
        context['entity'] = 'Aguapey'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        context['cueanexo'] = cueanexo

        ultimo_informe = None
        if cueanexo:
            ultimo_informe = GenerarInforme.objects.filter(
                cueanexo=cueanexo
            ).order_by('-annos', '-meses').first()

        context['mes'] = ultimo_informe.meses if ultimo_informe else None
        context['anno'] = ultimo_informe.annos if ultimo_informe else None

        return context


# =========================================================
# EDITAR
# =========================================================
class AguapeyUpdateView(LoginRequiredMixin, CueanexoMixin, UpdateView):
    model = Aguapey
    form_class = AguapeyForm
    template_name = 'biblioteca/pem/aguapey/create.html'
    success_url = reverse_lazy('bibliotecas:aguapey_list')

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST.get('action')

            if action == 'edit':
                form = self.get_form()
                if form.is_valid():
                    instance = form.save()
                    data = {
                        'message': 'Actualizado correctamente',
                        'instance': instance.toJSON()
                    }
                else:
                    total_error = form.errors.get('total')
                    data['error'] = total_error[0] if total_error else 'Errores en el formulario'
            else:
                data['error'] = 'Acción no válida'

        except Exception as e:
            data['error'] = str(e)

        return JsonResponse(data)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        cueanexo = self.get_cueanexo()

        context['title'] = 'Edición de Aguapey'
        context['entity'] = 'Aguapey'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        context['cueanexo'] = cueanexo

        ultimo_informe = None
        if cueanexo:
            ultimo_informe = GenerarInforme.objects.filter(
                cueanexo=cueanexo
            ).order_by('-anio', '-mes').first()

        context['mes'] = ultimo_informe.mes if ultimo_informe else None
        context['anno'] = ultimo_informe.anio if ultimo_informe else None

        return context


# =========================================================
# ELIMINAR
# =========================================================
class AguapeyDeleteView(LoginRequiredMixin, DeleteView):
    model = Aguapey
    template_name = 'biblioteca/pem/aguapey/delete.html'
    success_url = reverse_lazy('bibliotecas:aguapey_list')

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            self.object = self.get_object()
            self.object.delete()
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Eliminación de Aguapey'
        context['entity'] = 'Aguapey'
        context['list_url'] = self.success_url
        return context


# =========================================================
# LISTADO (SOLO DEL USUARIO)
# =========================================================
class AguapeyListView(LoginRequiredMixin, CueanexoMixin, ListView):
    model = Aguapey
    template_name = 'biblioteca/pem/aguapey/list_aguapey.html'

    def get_queryset(self):
        cueanexo = self.get_cueanexo()

        if not cueanexo:
            return Aguapey.objects.none()

        return Aguapey.objects.filter(
            cueanexo=cueanexo
        )

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = []

        try:
            action = request.POST.get('action')

            if action == 'searchdata':
                for obj in self.get_queryset():
                    data.append(obj.toJSON())
            else:
                data = {'error': 'Acción inválida'}

        except Exception as e:
            data = {'error': str(e)}

        return JsonResponse(data, safe=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['title'] = 'Listado de Aguapey'
        context['create_url'] = reverse_lazy('bibliotecas:aguapey_create')
        context['list_url'] = reverse_lazy('bibliotecas:aguapey_list')
        context['update_url'] = reverse_lazy('bibliotecas:aguapey_update', args=[0])
        context['entity'] = 'Aguapey'
        context['hide_lock_button'] = False
        context['generar_pdf_button'] = True
        context['next_url'] = reverse_lazy('bibliotecas:regfondos')

        return context