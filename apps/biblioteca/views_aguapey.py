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
            acronimo__startswith='BI'
        ).values_list('cueanexo', flat=True)

        return qs.first() if qs.exists() else None


# =========================================================
# CARGA
# =========================================================
class AguapeyCreateView(LoginRequiredMixin, InformeBloqueoMixin, CreateView):
    model = Aguapey
    form_class = AguapeyForm
    template_name = 'biblioteca/pem/aguapey/create.html'
    success_url = reverse_lazy('bibliotecas:aguapey_list')

    def get_cueanexo(self):
        usuario_limpio = re.sub(r'\D', '', self.request.user.username)

        return (
            CapaUnicaOfertas.objects.annotate(
                cuit_limpio=Func(
                    F('resploc_cuitcuil'),
                    Value('-'),
                    Value(''),
                    function='REPLACE'
                )
            )
            .filter(
                cuit_limpio=usuario_limpio,
                oferta='Común - Servicios complementarios ',
                acronimo__startswith='BI'
            )
            .values_list('cueanexo', flat=True)
            .first()
        )
    
    def form_valid(self, form):
        
        # 🔹 Obtener usuario logueado correctamente
        usuario_logueado = self.request.user.username
        usuario_limpio = re.sub(r'\D', '', usuario_logueado)

        print("Usuario logueado:", usuario_logueado)  # Debug

        # 🔹 Obtener cueanexos del usuario
        cueanexos_qs = CapaUnicaOfertas.objects.annotate(
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

        cueanexos = list(cueanexos_qs)

        # 🔥 cueanexo activo
        cueanexo = cueanexos[0] if cueanexos else None

        # 🔥 GUARDAR EN SESIÓN (CLAVE PARA EL Mixin)
        self.request.session["cueanexo"] = cueanexo
        print("SESSION CUEANEXO:", self.request.session.get("cueanexo"))
        
        # 🔥 asignar al objeto
        form.instance.cueanexo = cueanexo

        return super().form_valid(form)

    def dispatch(self, request, *args, **kwargs):
        self.request = request

        # 🔥 obtener cueanexo UNA SOLA VEZ
        cueanexo = self.get_cueanexo()

        # 🔥 guardar en sesión
        request.session["cueanexo"] = cueanexo

        print("🔥 CUEANEXO EN DISPATCH:", cueanexo)
        print("🔥 SESIÓN:", request.session.get("cueanexo"))
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}

        # 🔥 BLOQUEO REAL
        if self.informe_bloqueado():
            return JsonResponse({
                "error": True,
                "message": "El último informe ya fue ENVIADO. No se puede modificar."
            }, status=403)

        try:
            action = request.POST['action']

            if action == 'add':
                form = self.get_form()

                if form.is_valid():
                    instance = form.save()
                    data = instance.toJSON()
                else:
                    data['error'] = form.errors.as_json()

            else:
                data['error'] = 'No ha ingresado a ninguna opción'

        except Exception as e:
            data['error'] = str(e)

        return JsonResponse(data) 


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        usuario_logueado = self.request.user.username

        # Limpiar caracteres no numéricos del CUIT/CUIL
        usuario_limpio = re.sub(r'\D', '', usuario_logueado)

        # Obtener primer cueanexo del usuario
        cueanexo_qs = CapaUnicaOfertas.objects.annotate(
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

        context['title'] = 'Carga de Aguapey'
        context['entity'] = 'Aguapey'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        context['cueanexo'] = cueanexo_qs.first() if cueanexo_qs.exists() else None 

        # Obtener el último mes y año del usuario logueado
        ultimo_informe = GenerarInforme.objects.filter(cueanexo=context['cueanexo']).order_by('-annos', '-meses').first()

        if ultimo_informe:
            context['mes'] = ultimo_informe.meses
            context['anno'] = ultimo_informe.annos
        else:
            context['mes'] = None
            context['anno'] = None
        print(context)
        return context


# =========================================================
# EDITAR
# =========================================================
class AguapeyUpdateView(LoginRequiredMixin, InformeBloqueoMixin, UpdateView):
    model = Aguapey
    form_class = AguapeyForm
    template_name = 'biblioteca/pem/aguapey/create.html'
    success_url = reverse_lazy('bibliotecas:aguapey_list')

    # 🔥 obtener objeto (UpdateView lo necesita)
    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.request = request
        return super().dispatch(request, *args, **kwargs)

    # 🔥 POST con SweetAlert + AJAX (igual que CREATE)
    def post(self, request, *args, **kwargs):
        data = {}

        # 🚨 BLOQUEO POR INFORME ENVIADO
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
                    data = instance.toJSON()
                else:
                    return JsonResponse({
                        "error": True,
                        "message": form.errors.as_json()
                    })

            else:
                return JsonResponse({
                    "error": True,
                    "message": "Acción no válida"
                })

        except Exception as e:
            return JsonResponse({
                "error": True,
                "message": str(e)
            })

        return JsonResponse(data)

    # 🔥 CONTEXTO 
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        usuario_limpio = re.sub(r'\D', '', self.request.user.username)

        cueanexo = (
            CapaUnicaOfertas.objects.annotate(
                cuit_limpio=Func(
                    F('resploc_cuitcuil'),
                    Value('-'),
                    Value(''),
                    function='REPLACE'
                )
            )
            .filter(
                cuit_limpio=usuario_limpio,
                oferta='Común - Servicios complementarios ',
                acronimo__startswith='BI'
            )
            .values_list('cueanexo', flat=True)
            .first()
        )

        context['title'] = 'Edición de Aguapey'
        context['entity'] = 'Aguapey'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        context['cueanexo'] = cueanexo

        ultimo_informe = GenerarInforme.objects.filter(
            cueanexo=cueanexo
        ).order_by('-annos', '-meses').first()

        context['mes'] = ultimo_informe.meses if ultimo_informe else None
        context['anno'] = ultimo_informe.annos if ultimo_informe else None


        return context


# =========================================================
# ELIMINAR
# =========================================================
class AguapeyDeleteView(LoginRequiredMixin, InformeBloqueoMixin,DeleteView):
    model = Aguapey
    template_name = 'biblioteca/pem/aguapey/delete.html'
    success_url = reverse_lazy('bibliotecas:aguapey_list')

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.request = request
        return super().dispatch(request, *args, **kwargs)

    # 🔥 DELETE con AJAX + SweetAlert
    def post(self, request, *args, **kwargs):
        data = {}

        # 🚨 BLOQUEO POR INFORME ENVIADO
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
        print(data)
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
        context['before_url'] = reverse_lazy('bibliotecas:proctec_list')
        context['next_url'] = reverse_lazy('bibliotecas:fondos_create')

        return context