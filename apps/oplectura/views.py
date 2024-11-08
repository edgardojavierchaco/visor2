from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, ListView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from .models import RegAplicador, RegDocporSeccion, RegEvaluacionFluidezLectora
from .forms import RegDocporSeccionEdicionForm, RegDocporSeccionForm, RegEvaluacionFluidezLectoraForm, FiltroEvaluacionForm, RegAlumnosFluidezLectoraForm, RegEvaluacionFluidezLectoraDirectoresForm
from .forms import RegAlumnosFluidezLectoraDirectorForm
from .forms import RegAplicadorporSeccionEdicionForm
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import urlencode
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import connection
from django.db.models import Q

@cache_control(no_cache=True, must_revalidate=True)
@login_required
def DepEvaluacionPortada(request):
    """
    Renderiza la plantilla de la portada de evaluación.

    Args:
        request: El objeto de solicitud HTTP.

    Returns:
        HttpResponse: La respuesta renderizada con la plantilla de portada.
    """
    
    return render(request, 'oplectura/portadaevaluacion.html')

@cache_control(no_cache=True, must_revalidate=True)
@login_required
def RegionalPortada(request):
    return render(request, 'oplectura/portadaregional.html')

@method_decorator([login_required, cache_control(no_cache=True, must_revalidate=True)], name='dispatch')
class CreateRegDocporSeccionView(CreateView):
    """
    Vista para crear un nuevo registro de documento por sección.

    Atributos:
        model: El modelo RegDocporSeccion.
        form_class: El formulario RegDocporSeccionForm.
        template_name: La plantilla utilizada para el formulario.
        success_url: La URL a la que se redirige tras el éxito.
    """
    
    model = RegDocporSeccion
    form_class = RegDocporSeccionForm
    template_name = 'oplectura/regdocporseccion.html'
    success_url = reverse_lazy('oplectura:cargar')  
    
    
    def form_valid(self, form):
        """
        Procesa el formulario cuando es válido.

        Args:
            form: El formulario válido.

        Returns:
            HttpResponse: Redirige a la URL de éxito tras guardar el registro.
        """
        
        regdocporseccion = form.save(commit=False)
        regdocporseccion.save(user=self.request.user)
        regdocporseccion.save()
        return super().form_valid(form)
    

# listado de aplicadores para dptoEvaluación
@method_decorator([login_required, cache_control(no_cache=True, must_revalidate=True)], name='dispatch')
class ListadoDocentesView(ListView):
    """
    Vista para listar los docentes registrados.

    Atributos:
        model: El modelo RegDocporSeccion.
        template_name: La plantilla utilizada para mostrar el listado.
        context_object_name: El nombre del contexto para los docentes.
    """
    
    model=RegDocporSeccion
    template_name='oplectura/listadodocentes.html'
    context_object_name='docentesporseccion'
    
    def get_queryset(self):
        """
        Obtiene la consulta de los docentes.

        Returns:
            QuerySet: Todos los registros de RegDocporSeccion.
        """
        
        return RegDocporSeccion.objects.all
    
    def get_context_data(self, **kwargs):
        """
        Agrega contexto adicional a la plantilla.

        Args:
            **kwargs: Contexto adicional.

        Returns:
            dict: Contexto actualizado con el título.
        """
        
        context=super().get_context_data(**kwargs)
        context['title']='Listado de Aplicadores'
        return context

#edición de aplicadores para dptoEvaluación
@method_decorator([login_required, cache_control(no_cache=True, must_revalidate=True)], name='dispatch')
class EditarDocentesView(UpdateView):
    """
    Vista para editar un registro de docente.

    Atributos:
        model: El modelo RegDocporSeccion.
        form_class: El formulario RegDocporSeccionEdicionForm.
        template_name: La plantilla utilizada para editar.
        success_url: La URL a la que se redirige tras el éxito.
    """
    
    model = RegDocporSeccion
    form_class = RegDocporSeccionEdicionForm
    template_name = 'oplectura/editardocentes.html'
    success_url = reverse_lazy('oplectura:listados')

    def get_object(self):
        """
        Obtiene el objeto a editar.

        Returns:
            RegDocporSeccion: El objeto correspondiente al ID proporcionado.
        """
        
        user_id = self.request.GET.get('id')
        return get_object_or_404(RegDocporSeccion, id=user_id)

    def get_context_data(self, **kwargs):
        """
        Agrega contexto adicional a la plantilla.

        Args:
            **kwargs: Contexto adicional.

        Returns:
            dict: Contexto actualizado con el título.
        """
        
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Validación'
        return context

    def form_valid(self, form):
        """
        Procesa el formulario cuando es válido.

        Args:
            form: El formulario válido.

        Returns:
            HttpResponse: Redirige a la URL de éxito tras la actualización.
        """
        
        return super().form_valid(form)

#eliminación
@method_decorator([login_required, cache_control(no_cache=True, must_revalidate=True)], name='dispatch')
class EliminarDocentesView(DeleteView):
    """
    Vista para eliminar un registro de docente.

    Métodos:
        get: Elimina el registro de docente y redirige al listado.
    """
    
    def get(self, request):
        """
        Elimina el docente especificado.

        Args:
            request: El objeto de solicitud HTTP.

        Returns:
            HttpResponse: Redirige al listado de docentes.
        """
        
        user_id = request.GET.get('id')
        user = get_object_or_404(RegDocporSeccion, id=user_id)
        user.delete()
        return redirect('oplectura:listados')

@cache_control(no_cache=True, must_revalidate=True)
@login_required
def RegistrarEvaluacionLectora(request):
    """
    Vista para registrar una evaluación de fluidez lectora.

    Args:
        request: El objeto de solicitud HTTP.

    Returns:
        HttpResponse: La respuesta renderizada con el formulario o redirige tras el registro.
    """
    
    if request.method == 'POST':
        form = RegEvaluacionFluidezLectoraForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('oplectura:evaluacion')  
    else:
        form = RegEvaluacionFluidezLectoraForm()
    return render(request, 'oplectura/registro_evaluacion_lectura.html', {'form': form})


#listado de alumnos para aplicador
@method_decorator([login_required, cache_control(no_cache=True, must_revalidate=True)], name='dispatch')
class ListadoEvaluacionLectora(ListView):
    """
    Vista para listar las evaluaciones de fluidez lectora.

    Atributos:
        model: El modelo RegEvaluacionFluidezLectora.
        template_name: La plantilla utilizada para mostrar el listado.
        context_object_name: El nombre del contexto para las evaluaciones.
    """
    
    model=RegEvaluacionFluidezLectora     
    template_name='oplectura/listadoevaluacionlectora.html' 
    context_object_name='evaluacionlectora'   
    print(context_object_name)
    
    def get_queryset(self):
        """
        Filtra las evaluaciones según los parámetros de búsqueda.

        Returns:
            QuerySet: Las evaluaciones filtradas.
        """
        
        queryset = super().get_queryset()
        cueanexo = self.request.GET.get('cueanexo')
        grado = self.request.GET.get('grado')
        seccion = self.request.GET.get('seccion')

        if cueanexo:
            queryset = queryset.filter(cueanexo=cueanexo)
        if grado:
            queryset = queryset.filter(grado=grado)
        if seccion:
            queryset = queryset.filter(seccion=seccion)

        return queryset
    
    def get_context_data(self, **kwargs):
        """
        Agrega contexto adicional a la plantilla.

        Args:
            **kwargs: Contexto adicional.

        Returns:
            dict: Contexto actualizado con el título y el formulario de filtro.
        """
        
        context=super().get_context_data(**kwargs)
        context['title']='Listado de Alumnos'
        context['form']=FiltroEvaluacionForm(self.request.GET or None, user=self.request.user)
        return context


#edición evaluación alumnos
@method_decorator([login_required, cache_control(no_cache=True, must_revalidate=True)], name='dispatch')
class EditarEvaluacionAlumnosView(UpdateView):
    """
    Vista para editar una evaluación de alumnos.

    Atributos:
        model: El modelo RegEvaluacionFluidezLectora.
        form_class: El formulario RegEvaluacionFluidezLectoraForm.
        template_name: La plantilla utilizada para editar.
    """
    
    model = RegEvaluacionFluidezLectora
    form_class = RegEvaluacionFluidezLectoraForm
    template_name = 'oplectura/editarevaluacionalumnos.html'
    

    def get_object(self):
        """
        Obtiene el objeto a editar.

        Returns:
            RegEvaluacionFluidezLectora: El objeto correspondiente al ID proporcionado.
        """
        
        user_id = self.request.GET.get('id')
        return get_object_or_404(RegEvaluacionFluidezLectora, id=user_id)

    def get_context_data(self, **kwargs):
        """
        Agrega contexto adicional a la plantilla.

        Args:
            **kwargs: Contexto adicional.

        Returns:
            dict: Contexto actualizado con el título.
        """
        
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Evaluación'
        return context

    def form_valid(self, form):
        """
        Procesa el formulario cuando es válido.

        Args:
            form: El formulario válido.

        Returns:
            HttpResponse: Redirige a la URL de éxito tras la actualización.
        """
        
        return super().form_valid(form)

    def get_success_url(self):
        """
        Construye la URL de éxito tras la actualización.

        Returns:
            str: La URL con los parámetros de búsqueda.
        """
        
        # reverse_lazy para construir la URL de éxito
        base_url = reverse_lazy('oplectura:evaluacion')
        query_string = urlencode({'cueanexo': 0, 'grado': 'TERCERO', 'seccion': 'A'})
        return f"{base_url}?{query_string}"
    

#eliminación evaluación alumnos
@method_decorator([login_required, cache_control(no_cache=True, must_revalidate=True)], name='dispatch')
class EliminarEvaluacionAlumnoView(DeleteView):
    """
    Vista para eliminar evaluaciones de alumnos.

    Attributes:
        model: Modelo de RegEvaluacionFluidezLectora.
    """
    
    def get(self, request):
        """
        Elimina un registro de evaluación de alumno basado en el ID proporcionado.

        Args:
            request: La solicitud HTTP recibida.

        Returns:
            HttpResponse: Redirige a la lista de evaluaciones tras la eliminación.
        """
        
        user_id = request.GET.get('id')
        user = get_object_or_404(RegEvaluacionFluidezLectora, id=user_id)
        user.delete()
        
        # Construir la URL completa 
        url = reverse('oplectura:evaluacion') + '?cueanexo=0&grado=TERCERO&seccion=A'
        
        return redirect(url)

# agregar alumno para el aplicador
@method_decorator([login_required, cache_control(no_cache=True, must_revalidate=True)], name='dispatch')
class RegAlumnosFluidezLectoraCreateView(CreateView):
    model = RegEvaluacionFluidezLectora
    form_class = RegAlumnosFluidezLectoraForm
    template_name = 'oplectura/regalumnosfluidezlectora_form.html'
    
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Registro de Alumnos'
        return context
    
    def get_success_url(self):
        # reverse_lazy para construir la URL de éxito
        base_url = reverse_lazy('oplectura:evaluacion')
        query_string = urlencode({'cueanexo': 0, 'grado': 'TERCERO', 'seccion': 'A'})
        return f"{base_url}?{query_string}"
    
# agregar alumno por director
@method_decorator([login_required, cache_control(no_cache=True, must_revalidate=True)], name='dispatch')
class RegAlumnosFluidezLectoraDirectorCreateView(CreateView):
    model = RegEvaluacionFluidezLectora
    form_class = RegAlumnosFluidezLectoraDirectorForm
    template_name = 'oplectura/regalumnosfluidezlectoradirector_form.html'
    success_url = reverse_lazy('oplectura:listado_alumnos')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Registro de Alumnos'
        return context
    
    

#listado de alumnos para directores
@method_decorator([login_required, cache_control(no_cache=True, must_revalidate=True)], name='dispatch')
class ListadoAlumnosDirectoresView(ListView):
    model=RegEvaluacionFluidezLectora     
    template_name='oplectura/listadoalumnosevaluacion.html' 
    context_object_name='evaluacionlectora'   
    print(context_object_name)
    
    def get_queryset(self):     
        queryset = super().get_queryset()   
        usuario = self.request.user

        if usuario:
            queryset = queryset.filter(cueanexo=usuario)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context=super().get_context_data(**kwargs)
        context['title']='Listado de Alumnos'        
        return context

#edición de alumnos para directores
@method_decorator([login_required, cache_control(no_cache=True, must_revalidate=True)], name='dispatch')
class EditarAlumnosDirectoresView(UpdateView):
    model = RegEvaluacionFluidezLectora
    form_class = RegEvaluacionFluidezLectoraDirectoresForm
    template_name = 'oplectura/editaralumnosdirectores.html'
    success_url = reverse_lazy('oplectura:listado_alumnos')  

    def get_object(self):
        user_id = self.request.GET.get('id')
        return get_object_or_404(RegEvaluacionFluidezLectora, id=user_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Alumno'
        return context

    def form_valid(self, form):
        
        return super().form_valid(form)
    
    

#eliminación alumnos directores
@method_decorator([login_required, cache_control(no_cache=True, must_revalidate=True)], name='dispatch')
class EliminarEvaluacionAlumnoDirectoresView(DeleteView):
    def get(self, request):
        user_id = request.GET.get('id')
        user = get_object_or_404(RegEvaluacionFluidezLectora, id=user_id)
        user.delete()
        return redirect('oplectura:listado_alumnos')
        

#listado de evaluacion alumnos para director
@method_decorator([login_required, cache_control(no_cache=True, must_revalidate=True)], name='dispatch')
class ListadoEvaluacionLectoraDirectoresView(ListView):
    model=RegEvaluacionFluidezLectora     
    template_name='oplectura/listadoevaluacionlectoradirector.html' 
    context_object_name='evaluaciondirector'   
    print(context_object_name)
    
    def get_queryset(self):
        queryset = super().get_queryset()
        cueanexo = self.request.user        

        if cueanexo:
            queryset = queryset.filter(cueanexo=cueanexo)        

        return queryset
    
    def get_context_data(self, **kwargs):
        context=super().get_context_data(**kwargs)
        context['title']='Listado Evaluación Alumnos'        
        return context

# listado de aplicadores para regionales
@method_decorator([login_required, cache_control(no_cache=True, must_revalidate=True)], name='dispatch')
class ListadoAplicadoresView(LoginRequiredMixin,ListView):
    """
    Vista para listar los aplicadores registrados.

    Atributos:
        model: El modelo Reg.
        template_name: La plantilla utilizada para mostrar el listado.
        context_object_name: El nombre del contexto para los docentes.
    """
    
    model=RegAplicador
    template_name='oplectura/listadoaplicadores.html'
    context_object_name='aplicadoresporseccion'
    
    def get_regional_usuario(self):
        """
        Obtiene el regional del usuario logueado consultando directamente la tabla cenpe.cueregional.
        
        Returns:
            str: El regional del usuario logueado o None si no se encuentra.
        """
        user = self.request.user
        query = """
            SELECT regional 
            FROM cenpe.cueregional 
            WHERE cueanexo = %s
            LIMIT 1
        """
        with connection.cursor() as cursor:
            cursor.execute(query, [user.username])
            row = cursor.fetchone()
        
        return row[0] if row else None

    def get_queryset(self):
        """
        Obtiene la consulta de los aplicadores filtrada por el regional del usuario logueado.
        
        Returns:
            QuerySet: Lista de RegAplicador filtrados por la región correspondiente.
        """
        regional_usuario = self.get_regional_usuario()
        
        if regional_usuario:
            # Filtramos los aplicadores por el campo 'region' que coincida con el 'regional'
            return RegAplicador.objects.filter(region=regional_usuario)
        
        # Si no se encontró el regional, devolvemos un queryset vacío
        return RegAplicador.objects.none()
    
    def get_context_data(self, **kwargs):
        """
        Agrega contexto adicional a la plantilla.

        Args:
            **kwargs: Contexto adicional.

        Returns:
            dict: Contexto actualizado con el título.
        """
        
        context=super().get_context_data(**kwargs)
        context['title']='Listado de Aplicadores'
        return context

#edición de aplicadores para regionales
@method_decorator([login_required, cache_control(no_cache=True, must_revalidate=True)], name='dispatch')
class EditarAplicadorView(UpdateView):
    """
    Vista para editar un registro de aplicadores

    Atributos:
        model: El modelo RegAplicador.
        form_class: El formulario RegAplicadorporSeccionEdicionForm.
        template_name: La plantilla utilizada para editar.
        success_url: La URL a la que se redirige tras el éxito.
    """
    
    model = RegAplicador
    form_class = RegAplicadorporSeccionEdicionForm
    template_name = 'oplectura/editaraplicador.html'
    success_url = reverse_lazy('oplectura:listaplic')

    def get_object(self):
        """
        Obtiene el objeto a editar.

        Returns:
            RegDocporSeccion: El objeto correspondiente al ID proporcionado.
        """
        
        user_id = self.request.GET.get('id')
        return get_object_or_404(RegAplicador, id=user_id)

    def get_context_data(self, **kwargs):
        """
        Agrega contexto adicional a la plantilla.

        Args:
            **kwargs: Contexto adicional.

        Returns:
            dict: Contexto actualizado con el título.
        """
        
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Validación'
        return context

    def form_valid(self, form):
        """
        Procesa el formulario cuando es válido.

        Args:
            form: El formulario válido.

        Returns:
            HttpResponse: Redirige a la URL de éxito tras la actualización.
        """
        
        return super().form_valid(form)


@cache_control(no_cache=True, must_revalidate=True)
@login_required
def directoresregistrados(username):    
    # consulta para obtener la región
    query = """
        SELECT regional 
        FROM cenpe.cueregional 
        WHERE cueanexo = %s
        LIMIT 1
    """
    
    # consulta para obtener los datos de directores
    query2 = """
        SELECT username, apellido, nombres, nom_est
        FROM public.vista_usuarios_activos_directores
        WHERE region_loc = %s
    """
    
    with connection.cursor() as cursor:
        # Ejecutar la primera consulta para obtener la región
        cursor.execute(query, (username,))
        region = cursor.fetchone()
        
        # Si no se encuentra la región, devolver None
        if not region:
            return None
        
        # Ejecutar la segunda consulta con la región obtenida
        cursor.execute(query2, (region[0],))
        row = cursor.fetchall()
    
    # Devolver todos los registros encontrados
    return row if row else None


# Vista para mostrar los datos en el template
@cache_control(no_cache=True, must_revalidate=True)
@login_required
def mostrar_directores(request):
    # Obtener el username del usuario logueado
    username = request.user.username
    
    # Obtener datos de los directores a partir del username
    directores = directoresregistrados(username)
    
    # Renderizar el template y pasar los datos de los directores
    return render(request, 'oplectura/directoresregistrados.html', {'directores': directores})