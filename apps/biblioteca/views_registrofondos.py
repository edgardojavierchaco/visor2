from django.http import JsonResponse
from django.urls import reverse_lazy
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from .models import GenerarInforme, RegistroDestinoFondos, DestinoFondos
from .forms import RegistroDestinoFondosForm
from django.views.generic import CreateView, UpdateView, ListView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.consultasge.models import CapaUnicaOfertas
from django.db.models import Func, F, Value
import re
from .mixins import InformeBloqueoMixin


# Cargar
class RegistroDestinoFondosCreateView(LoginRequiredMixin, InformeBloqueoMixin, CreateView):
    model = RegistroDestinoFondos
    form_class = RegistroDestinoFondosForm
    template_name = 'biblioteca/pem/fondos/create.html'
    success_url = reverse_lazy('bibliotecas:fondos_list')
    
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
        
        context['title'] = 'Registro Destino de Fondos'
        context['entity'] = 'Servicios_Referencia'
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



#editar
class RegistroDestinoFondosUpdateView(LoginRequiredMixin, InformeBloqueoMixin, UpdateView):
    model = RegistroDestinoFondos
    form_class = RegistroDestinoFondosForm
    template_name = 'biblioteca/pem/fondos/create.html'
    success_url = reverse_lazy('bibliotecas:fondos_list')
    #permission_required = 'apps.change_client'
    url_redirect = success_url

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
        
        context['title'] = 'Edición Registro Destino de Fondos'
        context['entity'] = 'Registro Destino de Fondos'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        context['cueanexo'] = cueanexo
        
        ultimo_informe = GenerarInforme.objects.filter(
            cueanexo=cueanexo
        ).order_by('-annos', '-meses').first()

        context['mes'] = ultimo_informe.meses if ultimo_informe else None
        context['anno'] = ultimo_informe.annos if ultimo_informe else None
            
        return context


#Eliminar
class RegistroDestinoFondosDeleteView(LoginRequiredMixin, InformeBloqueoMixin, DeleteView):
    model = RegistroDestinoFondos
    template_name = 'biblioteca/pem/fondos/delete.html'
    success_url = reverse_lazy('bibliotecas:fondos_list')
    #permission_required = 'apps.delete_client'
    url_redirect = success_url

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
        context['title'] = 'Eliminación Registro Destino de Fondos'
        context['entity'] = 'Registro Destino de Fondos'
        context['list_url'] = self.success_url
        return context


#Listado
class RegistroDestinoFondosListView(LoginRequiredMixin, ListView):
    model = RegistroDestinoFondos
    template_name = 'biblioteca/pem/fondos/list_fondos.html'
    #permission_required = 'apps.view_supervisor'    
    
    def get_queryset(self):    
        # 🔹 Obtener usuario logueado correctamente
        usuario_logueado = self.request.user.username  
        usuario_limpio = re.sub(r'\D', '', usuario_logueado)
        print("Usuario logueado:", usuario_logueado)  # Debug: Verificar el usuario logueado
        
        # 🔹 Obtener todos los cueanexos que cumplan la condición
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
        
        fondos = RegistroDestinoFondos.objects.filter(cueanexo=cueanexos[0] if cueanexos else None)  # Filtrar por el primer cueanexo encontrado o None si no hay
        print('material:',fondos)
        return fondos
        

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'searchdata':
                data = []
                for i in self.get_queryset():
                    data.append(i.toJSON())
            else:
                data['error'] = 'Ha ocurrido un error'
        except Exception as e:
            data['error'] = str(e)
        print(data)
        return JsonResponse(data, safe=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Registro Destino de Fondos'
        context['create_url'] = reverse_lazy('bibliotecas:fondos_create')
        context['list_url'] = reverse_lazy('bibliotecas:fondos_list')
        context['update_url'] = reverse_lazy('bibliotecas:fondos_update', args=[0])
        context['hide_lock_button'] = False      
        context['generar_pdf_button'] = True,   
        context['before_url'] = reverse_lazy('bibliotecas:aguapey_list')
        context['next_url'] = reverse_lazy('bibliotecas:bibliotecario_create')
        context['entity'] = 'Registro Destino de Fondos'
        return context
        


