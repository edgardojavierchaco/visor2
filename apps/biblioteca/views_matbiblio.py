from django.forms import ValidationError
from django.http import HttpResponse, JsonResponse, HttpRequest
from django.urls import reverse_lazy
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from .models import MaterialBibliografico, GenerarInforme
from .forms import MaterialBibliograficoForm
from django.views.generic import CreateView, UpdateView, ListView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.consultasge.models import CapaUnicaOfertas
from django.db.models import Func, F, Value
import re
from typing import Any, Optional
from .mixins import InformeBloqueoMixin

# =========================
# 🔹 CUEANEXOS DEL USUARIO
# =========================
def get_cueanexos_usuario(user):
    usuario_limpio = re.sub(r'\D', '', user.username)

    return list(
        CapaUnicaOfertas.objects.annotate(
            cuit_limpio=Func(
                F('resploc_cuitcuil'),
                Value('-'),
                Value(''),
                function='REPLACE'
            )
        ).filter(
            cuit_limpio=usuario_limpio,
            oferta='Común - Servicios complementarios ',
            acronimo__startswith='BI'
        ).values_list('cueanexo', flat=True)
    )


# =========================
# 🔹 CUEANEXO ACTIVO
# =========================
def get_cueanexo_activo(request):
    return request.session.get("cueanexo_activo")
    
# ==========================================================
# CREATE
# ==========================================================
class MaterialBibliograficoCreateView(LoginRequiredMixin, InformeBloqueoMixin, CreateView):
    model = MaterialBibliografico
    form_class = MaterialBibliograficoForm
    template_name = 'biblioteca/pem/matbibl/create.html'
    success_url = reverse_lazy('bibliotecas:materialbibliografico_list')    
    
    # =========================
    # DISPATCH
    # =========================
    def dispatch(self, request, *args, **kwargs):
        self.request = request

        cueanexo = request.session.get("cueanexo_activo")

        # 🔥 fallback si no existe
        if not cueanexo:
            cueanexos = get_cueanexos_usuario(request.user)
            cueanexo = cueanexos[0] if cueanexos else None
            request.session["cueanexo_activo"] = cueanexo

        return super().dispatch(request, *args, **kwargs)
    
    # =========================
    # FORM VALID
    # =========================   
    def form_valid(self, form):
        
        if self.informe_bloqueado():
            return JsonResponse({
                "error": True,
                "message": "El último informe ya fue ENVIADO. No se puede modificar."
            }, status=403)

        cueanexo = self.request.session.get("cueanexo_activo")

        if not cueanexo:
            return JsonResponse({
                "error": True,
                "message": "No hay cueanexo activo"
            }, status=400)

        form.instance.cueanexo = cueanexo

        return super().form_valid(form)
    

    # =========================
    # POST AJAX
    # =========================
    def post(self, request, *args, **kwargs):

        if self.informe_bloqueado():
            return JsonResponse({
                "error": True,
                "message": "El último informe ya fue ENVIADO. No se puede modificar."
            }, status=403)

        try:
            action = request.POST.get('action')

            if action == 'add':
                form = self.get_form()

                if form.is_valid():
                    instance = form.save()
                    return JsonResponse(instance.toJSON())
                else:
                    return JsonResponse({
                        'error': True,
                        'errors': form.errors
                    })

            return JsonResponse({'error': 'Acción no válida'})

        except Exception as e:
            return JsonResponse({'error': str(e)})

    # =========================
    # CONTEXTO
    # =========================
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        cueanexo = get_cueanexo_activo(self.request)

        context['cueanexo'] = cueanexo
        context['cueanexos_usuario'] = get_cueanexos_usuario(self.request.user)

        ultimo = GenerarInforme.objects.filter(
            cueanexo=cueanexo
        ).order_by('-annos', '-meses').first()

        context['mes'] = ultimo.meses if ultimo else None
        context['anno'] = ultimo.annos if ultimo else None

        context['title'] = 'Carga Servicio Material Bibliográfico'
        context['entity'] = 'Material'
        context['list_url'] = self.success_url
        context['action'] = 'add'

        return context    


#editar
class MaterialBibliograficoUpdateView(LoginRequiredMixin, InformeBloqueoMixin, UpdateView):
    model = MaterialBibliografico
    form_class = MaterialBibliograficoForm
    template_name = 'biblioteca/pem/matbibl/create.html'
    success_url = reverse_lazy('bibliotecas:materialbibliografico_list')
    
     # =========================
    # DISPATCH
    # =========================
    def dispatch(self, request, *args, **kwargs):
        self.request = request
        self.object = self.get_object()
        
        # 🔥 asegurar cueanexo activo
        cueanexo = request.session.get("cueanexo_activo")
        
        if not cueanexo:
            cueanexos = get_cueanexos_usuario(request.user)
            cueanexo = cueanexos[0] if cueanexos else None
            request.session["cueanexo_activo"] = cueanexo
        
        return super().dispatch(request, *args, **kwargs)

    # 🔥 POST con SweetAlert + AJAX (igual que CREATE)
    # =========================
    # POST AJAX
    # =========================
    def post(self, request, *args, **kwargs):

        if self.informe_bloqueado():
            return JsonResponse({
                "error": True,
                "message": "El último informe ya fue ENVIADO. No se puede modificar."
            }, status=403)

        try:
            action = request.POST.get('action')

            if action == 'edit':
                form = self.get_form()

                if form.is_valid():
                    instance = form.save()
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

        cueanexo = get_cueanexo_activo(self.request)

        context['cueanexo'] = cueanexo
        context['cueanexos_usuario'] = get_cueanexos_usuario(self.request.user)

        ultimo_informe = GenerarInforme.objects.filter(
            cueanexo=cueanexo
        ).order_by('-annos', '-meses').first()

        context['mes'] = ultimo_informe.meses if ultimo_informe else None
        context['anno'] = ultimo_informe.annos if ultimo_informe else None

        context['title'] = 'Edición Servicio Material Bibliográfico'
        context['entity'] = 'Material'
        context['list_url'] = self.success_url
        context['action'] = 'edit'

        return context


#Eliminar
class MaterialBibliograficoDeleteView(LoginRequiredMixin, InformeBloqueoMixin, DeleteView):
    model = MaterialBibliografico
    template_name = 'biblioteca/pem/matbibl/delete.html'
    success_url = reverse_lazy('bibliotecas:materialbibliografico_list')

    # =========================
    # DISPATCH
    # =========================
    def dispatch(self, request, *args, **kwargs):
        self.request = request
        self.object = self.get_object()

        # 🔥 asegurar cueanexo activo
        cueanexo = request.session.get("cueanexo_activo")

        if not cueanexo:
            cueanexos = get_cueanexos_usuario(request.user)
            cueanexo = cueanexos[0] if cueanexos else None
            request.session["cueanexo_activo"] = cueanexo

        return super().dispatch(request, *args, **kwargs)

    # =========================
    # DELETE AJAX
    # =========================
    def post(self, request, *args, **kwargs):

        # 🚨 BLOQUEO POR INFORME ENVIADO
        if self.informe_bloqueado():
            return JsonResponse({
                "error": True,
                "message": "El último informe ya fue ENVIADO. No se puede eliminar."
            }, status=403)

        try:
            cueanexo = request.session.get("cueanexo_activo")

            # 🔒 SEGURIDAD: evitar borrar otro cueanexo
            if str(self.object.cueanexo) != str(cueanexo):
                return JsonResponse({
                    "error": True,
                    "message": "No autorizado"
                }, status=403)

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

        context['title'] = 'Eliminación Servicio Material Bibliográfico'
        context['entity'] = 'Material'
        context['list_url'] = self.success_url
        context['action'] = 'delete'

        return context


# =========================
# LIST VIEW
# =========================
class MaterialBibliograficoListView(LoginRequiredMixin, ListView):
    model = MaterialBibliografico
    template_name = 'biblioteca/pem/matbibl/list_matbiblio.html'

    # =========================
    # SESSION
    # =========================
    def dispatch(self, request, *args, **kwargs):

        cueanexo = request.session.get("cueanexo_activo")

        if not cueanexo:
            cueanexos = get_cueanexos_usuario(request.user)
            cueanexo = cueanexos[0] if cueanexos else None
            request.session["cueanexo_activo"] = cueanexo

        return super().dispatch(request, *args, **kwargs)

    # =========================
    # QUERYSET
    # =========================
    def get_queryset(self):

        cueanexo = self.request.session.get("cueanexo_activo")

        if not cueanexo:
            return MaterialBibliografico.objects.none()

        qs = MaterialBibliografico.objects.filter(cueanexo=cueanexo)

        anio = self.request.GET.get('anio')
        mes = self.request.GET.get('mes')

        if anio:
            qs = qs.filter(anio=anio)

        if mes:
            qs = qs.filter(mes=mes)

        return qs.order_by('-anio', '-mes')

    # =========================
    # AJAX
    # =========================
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

        context['title'] = 'Listado de Material Bibliográfico'
        context['create_url'] = reverse_lazy('bibliotecas:materialbibliografico_create')
        context['list_url'] = reverse_lazy('bibliotecas:materialbibliografico_list')
        context['update_url'] = reverse_lazy('bibliotecas:materialbibliografico_update', args=[0])
        context['hide_lock_button'] = False    
        context['generar_pdf_button'] = True,    
        context['before_url'] = reverse_lazy('bibliotecas:materialbibliografico_list')
        context['next_url'] = reverse_lazy('bibliotecas:servref_create')
        context['entity'] = 'Material Bibliografico'
        return context