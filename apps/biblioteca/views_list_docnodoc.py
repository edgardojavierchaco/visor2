from django.http import JsonResponse
from django.urls import reverse_lazy
from django.shortcuts import render, redirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from .models import DocentePonMensual, NoDocentesMensual
from .forms import DocentePonMensualForm, NoDocentesMensualForm
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin



# Listar Nómina de Docentes
class DocentePonMensualListView(LoginRequiredMixin, ListView):    
    model = DocentePonMensual
    template_name = 'biblioteca/pem/docentes/list_docentes.html'    

    def get_queryset(self):    
        # Obtenemos todos los docentes para el usuario actual
        docentes = DocentePonMensual.objects.filter(cueanexo=self.request.user.username)
        return docentes

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'searchdata':
                docentes_data = [
                    {
                        'id': docente.id,
                        'cueanexo': docente.cueanexo,
                        'cuof': docente.cuof,
                        'cuof_anexo': docente.cuof_anexo,
                        'ptaid': docente.ptaid,
                        'apellidos': docente.apellidos,
                        'nombres': docente.nombres,
                        'n_doc': docente.n_doc,
                        'cuil': docente.cuil,
                        'f_nac': docente.f_nac,
                        'sit_rev': docente.sit_rev,
                        'nivel': docente.nivel,
                        'ceic': docente.ceic,
                        'denom_cargo': docente.denom_cargo,
                        'f_desde': docente.f_desde,
                        'f_hasta': docente.f_hasta,
                        'regional': docente.regional,
                        'localidad': docente.localidad,
                        'carga_horaria': docente.carga_horaria
                    }
                    for docente in self.get_queryset()
                ]
                data['docentes'] = docentes_data
                print(docentes_data)
            else:
                data['error'] = 'Ha ocurrido un error'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data, safe=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nómina de Personal Docente (** Base de Datos PON)'        
        context['list_url'] = reverse_lazy('bibliotecas:nom_doc')      
        context['entity'] = 'Docentes'

        # Obtenemos todos los docentes para pasarlos al contexto
        context['docentes'] = self.get_queryset()

        return context

# Listar Nómina de No Docentes
class NoDocentePonMensualListView(LoginRequiredMixin, ListView):    
    model = NoDocentesMensual
    template_name = 'biblioteca/pem/docentes/list_nodocentes.html'    

    def get_queryset(self):    
        # Filtra los docentes por 'cueanexo' del usuario logueado        
        nodocentes= NoDocentesMensual.objects.filter(cueanexo=self.request.user.username).order_by('apellidos', 'nombres')
        print('no docentes',nodocentes)
        return nodocentes
    
    @method_decorator(csrf_exempt)  # No es recomendable deshabilitar CSRF sin necesidad
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST.get('action')  # Usar .get() por si la clave no está presente
            if action == 'searchdata':
                # Obtiene los datos de los docentes según el filtro
                nodocentes_data = [
                    {
                        'id': docente.id,
                        'cueanexo': docente.cueanexo or '',  
                        'cuof': docente.cuof or '',  
                        'cuof_anexo': docente.cuof_anexo or '',
                        'ptaid': docente.ptaid or '',
                        'apellidos': docente.apellidos or '',
                        'nombres': docente.nombres or '',
                        'ndoc': docente.ndoc or '',
                        'cuil': docente.cuil or '',
                        'f_nac': docente.f_nac or '',
                        'denom_cargo': docente.denom_cargo or '',
                        'categ': docente.categ or '',
                        'gpo': docente.gpo or '',
                        'apart': docente.apart or '',
                        'f_desde': docente.f_desde or '',
                        'f_hasta': docente.f_hasta or '',
                        'regional': docente.regional or '',
                        'localidad': docente.localidad or '',
                    }
                    for docente in self.get_queryset()
                ]

                data['nodocentes'] = nodocentes_data  # Renombrado para consistencia
                print('data de no docentes:', nodocentes_data)  
            else:
                data['error'] = 'Acción no reconocida'  # Mensaje más claro
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data, safe=False) 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nómina de Personal No Docente (** Base de Datos PON)'        
        context['list_url'] = reverse_lazy('bibliotecas:nom_ndoc')      
        context['entity'] = 'No Docentes'
        
        context['nodocentes'] = self.get_queryset()
        
        return context


