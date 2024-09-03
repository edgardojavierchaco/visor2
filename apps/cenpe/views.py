from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, View
from django.views.generic.edit import UpdateView
from .models import Datos_Personal_Cenpe, Academica_Cenpe, CargosHoras_Cenpe, CeicPuntos
from .forms import DatosPersonalCenpeForm, DatosAcademicosCenpeForm, CargosHorasCenpeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from .models import localidad_tipo, provincia_tipo

######################################################
# Cargar Datos Personales del Docente para el RENPEE #
######################################################
class DatosPersonalCenpeCreateView(LoginRequiredMixin, CreateView):
    model = Datos_Personal_Cenpe
    form_class = DatosPersonalCenpeForm
    template_name = 'cenpe/crear_datos_personales.html'
    success_url = reverse_lazy('cenpe:academico')
    
    def get_initial(self):
        initial = super().get_initial()
        initial['usuario'] = self.request.user.username  # Establecer el username del usuario logueado
        return initial

    def form_valid(self, form):
        form.instance.usuario = self.request.user.username
        return super().form_valid(form)

##################################
# Carga el Ajax para localidades #
##################################
def cargar_localidades(request):
    # Obtener el id de la provincia seleccionada desde la solicitud AJAX
    provincia_id = request.GET.get('provincia_id')
    # Obtener las localidades que corresponden a la provincia seleccionada
    localidades = localidad_tipo.objects.filter(c_provincia=provincia_id).order_by('descripcion_loc')
    # Preparar la lista de localidades como JSON
    localidades_json = [{"id": loc.c_localidad, "descripcion": loc.descripcion_loc} for loc in localidades]
    # Devolver la lista en formato JSON
    print(localidades_json)  # Depuración
    return JsonResponse(localidades_json, safe=False)

##########################################################
# Cargar los Datos Académicos del Docente para el RENPEE #
##########################################################
class DatosAcademicosCenpeCreateView(LoginRequiredMixin, CreateView):
    model = Academica_Cenpe
    form_class = DatosAcademicosCenpeForm
    template_name = 'cenpe/crear_datos_academicos.html'
    success_url = reverse_lazy('cenpe:listado')
    
    def get_initial(self):
        initial = super().get_initial()
        initial['usuario'] = self.request.user.username  # Establecer el username del usuario logueado
        return initial

    def form_valid(self, form):
        form.instance.usuario = self.request.user.username
        return super().form_valid(form)

#########################################################
# Cargar los Datos Laborales del docente para el RENPEE #
#########################################################
class CargosHorasCenpeCreateView(LoginRequiredMixin, CreateView):
    model = CargosHoras_Cenpe
    form_class = CargosHorasCenpeForm
    template_name = 'cenpe/cargar_cargoshoras.html'
    success_url = reverse_lazy('cenpe:listado')
    
    def get_initial(self):
        initial = super().get_initial()
        initial['usuario'] = self.request.user.username  # Establecer el username del usuario logueado
        return initial

    def form_valid(self, form):
        form.instance.usuario = self.request.user.username
        return super().form_valid(form)

##########################################################
# Filtrar los cargos de CEIC según el nivel seleccionado #
########################################################## 
def obtener_cargos_por_nivel(request):
    n_nivel = request.GET.get('nivel')
    if n_nivel=='1':
        nivel='INICIAL'
    elif n_nivel=='2':
        nivel='PRIMARIO'
    elif n_nivel=='3':
        nivel='SECUNDARIO'
    elif n_nivel=='5':
        nivel='ADULTO'
    elif n_nivel=='6':
        nivel='TÉCNICA'
    elif n_nivel=='7':
        nivel='SUPERIOR'
    elif n_nivel=='8':
        nivel='ARTÍSTICA'    
    elif n_nivel=='9':
        nivel='BIBLIOTECAS'   
    elif n_nivel=='10':
        nivel='SERVICIOS TÉCNICOS'
    elif n_nivel=='11':
        nivel='EDUCACIÓN FÍSICA'
    elif n_nivel=='12':
        nivel='JUNTA Y TRIBUNAL'
    else:
        nivel='DIRECTOR GENERAL'           
        
    cargos = CeicPuntos.objects.filter(nivel=nivel, estado=True)  # Filtramos por nivel y estado activo
    cargos_data = [{'id': cargo.ceic_id, 'descripcion': cargo.descripcion_ceic} for cargo in cargos]
    print(cargos_data)
    return JsonResponse(cargos_data, safe=False)

##################################################
# Listado Cargos - Horas Docentes para el RENPEE #
##################################################
class CargosHorasCenpeListView(LoginRequiredMixin, ListView):
    model=CargosHoras_Cenpe
    template_name='cenpe/listadocargoshorascenpe.html' 
    context_object_name='Cargos_Horas'   
    print(context_object_name)
    
    def get_queryset(self):     
        queryset = super().get_queryset()   
        usuario = self.request.user

        if usuario:
            queryset = queryset.filter(usuario=usuario)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context=super().get_context_data(**kwargs)
        context['title']='Listado de Cargos y/u horas'        
        return context

class EliminarDocentesView(View):
    def get(self, request):
        # Captura el parámetro 'id' de la URL
        user_id = request.GET.get('id')
        
        # Verifica que user_id no sea None o esté vacío
        if not user_id:
            print('Error: No se recibió el ID del usuario')
            return HttpResponseBadRequest("ID de usuario no proporcionado.")

        print('user_id', user_id)  # Esto debería imprimir el ID capturado

        # Elimina el objeto correspondiente si existe
        user = get_object_or_404(CargosHoras_Cenpe, id=user_id)
        user.delete()
        return redirect('cenpe:listado')
