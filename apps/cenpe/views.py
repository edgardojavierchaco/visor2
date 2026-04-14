from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, View
from django.views.generic.edit import UpdateView
from .models import Datos_Personal_Cenpe, Academica_Cenpe, CargosHoras_Cenpe, CeicPuntos
from .forms import DatosPersonalCenpeForm, DatosAcademicosCenpeForm, CargosHorasCenpeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from .models import localidad_tipo, provincia_tipo

def IndexCenpe(request):
    """
    Renderiza la página principal del módulo RENPEE para el usuario.

    Args:
        request (HttpRequest): La solicitud HTTP que contiene la información del usuario.

    Returns:
        HttpResponse: Renderiza el template 'cenpe/indexcenpe.html'.
    """
    
    return render(request, 'cenpe/indexcenpe.html')

######################################################
# Cargar Datos Personales del Docente para el RENPEE #
######################################################
class DatosPersonalCenpeCreateView(LoginRequiredMixin, CreateView):
    """
    Vista basada en clases para gestionar la creación de datos personales de los docentes para el RENPEE.

    Atributos:
        model (Model): El modelo relacionado con los datos personales (Datos_Personal_Cenpe).
        form_class (Form): El formulario que se utiliza para gestionar la creación de los datos personales.
        template_name (str): El template que se renderiza para la creación de datos personales.
        success_url (str): La URL de redirección después de la creación exitosa de los datos.

    Métodos:
        get_initial: Inicializa el campo 'usuario' con el nombre de usuario del usuario autenticado.
        form_valid: Asigna el nombre de usuario al campo 'usuario' antes de guardar los datos.
    """
    
    model = Datos_Personal_Cenpe
    form_class = DatosPersonalCenpeForm
    template_name = 'cenpe/crear_datos_personales.html'
    success_url = reverse_lazy('cenpe:academico')
    
    def get_initial(self):
        initial = super().get_initial()
        initial['usuario'] = self.request.user.username 
        return initial

    def form_valid(self, form):
        form.instance.usuario = self.request.user.username
        return super().form_valid(form)

##################################
# Carga el Ajax para localidades #
##################################
def cargar_localidades(request):
    """
    Carga las localidades en función de la provincia seleccionada a través de una solicitud AJAX.

    Args:
        request (HttpRequest): La solicitud HTTP que contiene el parámetro 'provincia_id'.

    Returns:
        JsonResponse: Retorna un JSON con las localidades filtradas por la provincia seleccionada.
    """
    
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
    """
    Vista basada en clases para gestionar la creación de datos académicos del docente para el RENPEE.

    Atributos:
        model (Model): El modelo relacionado con los datos académicos (Academica_Cenpe).
        form_class (Form): El formulario que se utiliza para gestionar la creación de los datos académicos.
        template_name (str): El template que se renderiza para la creación de datos académicos.
        success_url (str): La URL de redirección después de la creación exitosa de los datos académicos.

    Métodos:
        get_initial: Inicializa el campo 'usuario' con el nombre de usuario del usuario autenticado.
        form_valid: Asigna el nombre de usuario al campo 'usuario' antes de guardar los datos.
    """
    
    model = Academica_Cenpe
    form_class = DatosAcademicosCenpeForm
    template_name = 'cenpe/crear_datos_academicos.html'
    success_url = reverse_lazy('cenpe:listado')
    
    def get_initial(self):
        initial = super().get_initial()
        initial['usuario'] = self.request.user.username  
        return initial

    def form_valid(self, form):
        form.instance.usuario = self.request.user.username
        return super().form_valid(form)
    

#########################################################
# Cargar los Datos Laborales del docente para el RENPEE #
#########################################################
class CargosHorasCenpeCreateView(LoginRequiredMixin, CreateView):
    """
    Vista basada en clases para gestionar la creación de los datos laborales del docente para el RENPEE.

    Atributos:
        model (Model): El modelo relacionado con los datos laborales (CargosHoras_Cenpe).
        form_class (Form): El formulario que se utiliza para gestionar la creación de los datos laborales.
        template_name (str): El template que se renderiza para la creación de datos laborales.
        success_url (str): La URL de redirección después de la creación exitosa de los datos laborales.

    Métodos:
        get_initial: Inicializa el campo 'usuario' con el nombre de usuario del usuario autenticado.
        form_valid: Asigna el nombre de usuario al campo 'usuario' antes de guardar los datos.
    """
    
    model = CargosHoras_Cenpe
    form_class = CargosHorasCenpeForm
    template_name = 'cenpe/cargar_cargoshoras.html'
    success_url = reverse_lazy('cenpe:listado')
    
    def get_initial(self):
        initial = super().get_initial()
        initial['usuario'] = self.request.user.username  
        return initial

    def form_valid(self, form):
        form.instance.usuario = self.request.user.username
        return super().form_valid(form)
    
    

##########################################################
# Filtrar los cargos de CEIC según el nivel seleccionado #
########################################################## 
def obtener_cargos_por_nivel(request):
    """
    Filtra los cargos disponibles según el nivel educativo seleccionado.

    Args:
        request (HttpRequest): La solicitud HTTP que contiene el parámetro 'nivel'.

    Returns:
        JsonResponse: Un JSON con los cargos disponibles filtrados por el nivel seleccionado.
    """
    
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
        
    cargos = CeicPuntos.objects.filter(nivel=nivel, estado=True)  
    cargos_data = [{'id': cargo.ceic_id, 'descripcion': cargo.descripcion_ceic} for cargo in cargos]
    print(cargos_data)
    return JsonResponse(cargos_data, safe=False)

##################################################
# Listado Cargos - Horas Docentes para el RENPEE #
##################################################
class CargosHorasCenpeListView(LoginRequiredMixin, ListView):
    """
    Vista basada en clases para mostrar una lista de los cargos y horas del docente en el RENPEE.

    Atributos:
        model (Model): El modelo relacionado con los cargos y horas (CargosHoras_Cenpe).
        template_name (str): El template que se renderiza para mostrar la lista de cargos y horas.
        context_object_name (str): El nombre de la variable de contexto para acceder a los datos en la plantilla.

    Métodos:
        get_queryset: Filtra la lista de cargos y horas para mostrar solo los relacionados con el usuario autenticado.
        get_context_data: Añade el título al contexto de la plantilla.
    """
    
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
    """
    Vista basada en funciones para eliminar los cargos y horas del docente en el RENPEE.

    Métodos:
        get: Captura el ID del docente y lo elimina de la base de datos si existe.
    """
    
    def get(self, request):
        
        # Captura el parámetro 'id' de la URL
        user_id = request.GET.get('id')
        
        # Verifica que user_id no sea None o esté vacío
        if not user_id:
            print('Error: No se recibió el ID del usuario')
            return HttpResponseBadRequest("ID de usuario no proporcionado.")

        print('user_id', user_id) 

        # Elimina el objeto correspondiente si existe
        user = get_object_or_404(CargosHoras_Cenpe, id=user_id)
        user.delete()
        return redirect('cenpe:listado')
