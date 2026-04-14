from django.views.generic import ListView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.db.models import Sum
from .models import ExamenAlumnoCueanexoL, Categoria, Respuesta, Opcion

class ExamenAlumnoCueanexoLenGralListView(ListView):
    model = ExamenAlumnoCueanexoL
    template_name = 'operativoschaco/lengua/list_gral.html'

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        director = self.request.user.username
        if not director:
            return ExamenAlumnoCueanexoL.objects.none()
        return ExamenAlumnoCueanexoL.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Validación de categorías
        categorias = Categoria.objects.exclude(nombre__in=[
            'M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7', 'M8', 
            'M9', 'M10', 'M11', 'M12', 'M13', 'M14'
        ])
        print("Categorías excluidas:", categorias)

        if not categorias.exists():
            context['error'] = "No hay categorías disponibles"
            return context

        context['categorias'] = categorias

        # Calcular totales por categoría y sin categoría
        alumnos_totales = []
        for examen in self.get_queryset():
            respuestas = Respuesta.objects.filter(examen=examen)
            totales_por_categoria = {cat.nombre: 0 for cat in categorias}
            total_sin_categoria = 0

            for respuesta in respuestas:
                opciones_seleccionadas = respuesta.opciones_seleccionadas
                if not opciones_seleccionadas:
                    continue  # Saltar si no hay opciones seleccionadas

                for opcion in opciones_seleccionadas:
                    opcion_id = opcion.get('opcion_id')
                    if not opcion_id:
                        continue  # Saltar si no tiene ID

                    try:
                        opcion_obj = Opcion.objects.get(id=opcion_id)
                        if opcion_obj.categoria:
                            totales_por_categoria[opcion_obj.categoria.nombre] += opcion_obj.puntaje
                        else:
                            total_sin_categoria += opcion_obj.puntaje
                    except Opcion.DoesNotExist:
                        continue  # Saltar si la opción no existe

            alumnos_totales.append({
                'alumno': examen.alumno,
                'cueanexo': examen.alumno.cueanexo,
                'region': examen.alumno.region,
                'totales_por_categoria': totales_por_categoria,
                'total_sin_categoria': total_sin_categoria
            })

        context['alumnos_totales'] = alumnos_totales
        context['title'] = 'Listado de Alumnos Examen Lengua'
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action', '')
        if action == 'searchdata':
            categorias = Categoria.objects.exclude(nombre__in=[
                'M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7', 'M8', 
                'M9', 'M10', 'M11', 'M12', 'M13', 'M14'
            ])
            print("Categorías excluidas:", categorias)
            if not categorias.exists():
                return JsonResponse({
                    "error": "No hay categorías disponibles"
                }, status=400)

            examenes = self.get_queryset()
            data = []
            nombres_categorias = [cat.nombre for cat in categorias]

            for examen in examenes:
                respuestas = Respuesta.objects.filter(examen=examen)
                totales_por_categoria = {cat.nombre: 0 for cat in categorias}
                total_sin_categoria = 0

                for respuesta in respuestas:
                    opciones_seleccionadas = respuesta.opciones_seleccionadas
                    if not opciones_seleccionadas:
                        continue  # Saltar si no hay opciones seleccionadas

                    for opcion in opciones_seleccionadas:
                        opcion_id = opcion.get('opcion_id')
                        if not opcion_id:
                            continue  # Saltar si no tiene ID

                        try:
                            opcion_obj = Opcion.objects.get(id=opcion_id)
                            if opcion_obj.categoria:
                                totales_por_categoria[opcion_obj.categoria.nombre] += opcion_obj.puntaje
                            else:
                                total_sin_categoria += opcion_obj.puntaje
                        except Opcion.DoesNotExist:
                            continue  # Saltar si la opción no existe

                data.append({
                    "alumno": {
                        "id": examen.alumno.id,
                        "dni": examen.alumno.dni,
                        "apellidos": examen.alumno.apellidos,
                        "nombres": examen.alumno.nombres,
                        "cueanexo": examen.alumno.cueanexo,
                        "region": examen.alumno.region,
                    },
                    "totales_por_categoria": totales_por_categoria,
                    "total_sin_categoria": total_sin_categoria
                })
            print('Data:', data)
            return JsonResponse({
                "data": data,
                "categorias": nombres_categorias
            }, safe=False)
