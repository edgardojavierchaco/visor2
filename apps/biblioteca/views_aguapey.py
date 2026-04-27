from django.http import JsonResponse
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import CreateView, UpdateView, ListView, DeleteView

from django.contrib.auth.mixins import LoginRequiredMixin

from django.db.models import F, Func, Value
import re
from .mixins import InformeBloqueoMixin

from .models import Aguapey, GenerarInforme
from .forms import AguapeyForm
from apps.consultasge.models_padron import CapaUnicaOfertas


# =========================
# 🔹 UTIL
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


def get_cueanexo_activo(request):
    return request.session.get("cueanexo_activo")


# ==========================================================
# CREATE
# ==========================================================
class AguapeyCreateView(LoginRequiredMixin, InformeBloqueoMixin, CreateView):
    model = Aguapey
    form_class = AguapeyForm
    template_name = 'biblioteca/pem/aguapey/create.html'
    success_url = reverse_lazy('bibliotecas:aguapey_list')

    # =========================
    # DISPATCH
    # =========================
    def dispatch(self, request, *args, **kwargs):

        cueanexo = request.session.get("cueanexo_activo")

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
            })

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

        cueanexo = self.request.session.get("cueanexo_activo")

        context['cueanexo'] = cueanexo
        context['cueanexos_usuario'] = get_cueanexos_usuario(self.request.user)

        ultimo = None
        if cueanexo:
            ultimo = GenerarInforme.objects.filter(
                cueanexo=cueanexo
            ).order_by('-annos', '-meses').first()

        context['mes'] = ultimo.meses if ultimo else None
        context['anno'] = ultimo.annos if ultimo else None

        context['title'] = 'Carga de Aguapey'
        context['entity'] = 'Aguapey'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        
        print(context)
        return context


#===========================
# UPDATE
#===========================
class AguapeyUpdateView(LoginRequiredMixin, InformeBloqueoMixin, UpdateView):
    model = Aguapey
    form_class = AguapeyForm
    template_name = 'biblioteca/pem/aguapey/create.html'
    success_url = reverse_lazy('bibliotecas:aguapey_list')

    # =========================
    # DISPATCH
    # =========================
    def dispatch(self, request, *args, **kwargs):

        self.object = self.get_object()

        cueanexo = request.session.get("cueanexo_activo")

        if not cueanexo:
            cueanexos = get_cueanexos_usuario(request.user)
            cueanexo = cueanexos[0] if cueanexos else None
            request.session["cueanexo_activo"] = cueanexo

        return super().dispatch(request, *args, **kwargs)

    # =========================
    # POST AJAX
    # =========================
    def post(self, request, *args, **kwargs):

        # 🔒 BLOQUEO
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

        cueanexo = self.request.session.get("cueanexo_activo")

        context['cueanexo'] = cueanexo
        context['cueanexos_usuario'] = get_cueanexos_usuario(self.request.user)

        context['title'] = 'Edición de Aguapey'
        context['entity'] = 'Aguapey'
        context['list_url'] = self.success_url
        context['action'] = 'edit'        

        ultimo = None
        if cueanexo:
            ultimo = GenerarInforme.objects.filter(
                cueanexo=cueanexo
            ).order_by('-annos', '-meses').first()

        context['mes'] = ultimo.meses if ultimo else None
        context['anno'] = ultimo.annos if ultimo else None

        return context


#=====================
# DELETE
#=====================
class AguapeyDeleteView(LoginRequiredMixin, InformeBloqueoMixin,DeleteView):
    model = Aguapey
    template_name = 'biblioteca/pem/aguapey/delete.html'
    success_url = reverse_lazy('bibliotecas:aguapey_list')

    # =========================
    # DISPATCH
    # =========================
    def dispatch(self, request, *args, **kwargs):

        self.object = self.get_object()

        cueanexo = request.session.get("cueanexo_activo")

        if not cueanexo:
            cueanexos = get_cueanexos_usuario(request.user)
            cueanexo = cueanexos[0] if cueanexos else None
            request.session["cueanexo_activo"] = cueanexo

        return super().dispatch(request, *args, **kwargs)

    # =========================
    # DELETE (AJAX)
    # =========================
    def post(self, request, *args, **kwargs):

        # 🔒 BLOQUEO
        if self.informe_bloqueado():
            return JsonResponse({
                "error": True,
                "message": "El último informe ya fue ENVIADO. No se puede eliminar."
            }, status=403)

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

        cueanexo = self.request.session.get("cueanexo_activo")

        context['cueanexo'] = cueanexo
        context['cueanexos_usuario'] = get_cueanexos_usuario(self.request.user)
    
        context['title'] = 'Eliminación de Aguapey'
        context['entity'] = 'Aguapey'
        context['list_url'] = self.success_url
        return context


#=========================
# LIST
#=========================
class AguapeyListView(LoginRequiredMixin, ListView):
    model = Aguapey
    template_name = 'biblioteca/pem/aguapey/list_aguapey.html'

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
            return Aguapey.objects.none()
        
        qs = Aguapey.objects.filter(cueanexo=cueanexo)

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

        cueanexo = self.request.session.get("cueanexo_activo")

        context['cueanexo'] = cueanexo
        context['cueanexos_usuario'] = get_cueanexos_usuario(self.request.user)
        
        context['title'] = 'Listado de Aguapey'
        context['create_url'] = reverse_lazy('bibliotecas:aguapey_create')
        context['list_url'] = reverse_lazy('bibliotecas:aguapey_list')
        context['update_url'] = reverse_lazy('bibliotecas:aguapey_update', args=[0])
        context['entity'] = 'Aguapey'
        context['hide_lock_button'] = False
        context['generar_pdf_button'] = True
        context['before_url'] = reverse_lazy('bibliotecas:proctec_list')
        context['next_url'] = reverse_lazy('bibliotecas:fondos_create')

        return context