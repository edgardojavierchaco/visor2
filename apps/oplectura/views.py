from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, ListView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from .models import RegDocporSeccion, RegEvaluacionFluidezLectora
from .forms import RegDocporSeccionEdicionForm, RegDocporSeccionForm, RegEvaluacionFluidezLectoraForm, FiltroEvaluacionForm, RegAlumnosFluidezLectoraForm, RegEvaluacionFluidezLectoraDirectoresForm
from .forms import RegAlumnosFluidezLectoraDirectorForm
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import urlencode

def DepEvaluacionPortada(request):
    """
    Renderiza la plantilla de la portada de evaluación.

    Args:
        request: El objeto de solicitud HTTP.

    Returns:
        HttpResponse: La respuesta renderizada con la plantilla de portada.
    """
    
    return render(request, 'oplectura/portadaevaluacion.html')

@method_decorator(login_required, name='dispatch')
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
@method_decorator(login_required, name='dispatch')
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
class EliminarEvaluacionAlumnoDirectoresView(DeleteView):
    def get(self, request):
        user_id = request.GET.get('id')
        user = get_object_or_404(RegEvaluacionFluidezLectora, id=user_id)
        user.delete()
        return redirect('oplectura:listado_alumnos')
        

#listado de evaluacion alumnos para director
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

