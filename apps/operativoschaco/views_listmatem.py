from django.views.generic import ListView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.db.models import Sum
from .models import ExamenAlumnoCueanexoM, Categoria, RespuestaM, Opcion

class ExamenAlumnoCueanexoMatListView(ListView):
    model = ExamenAlumnoCueanexoM
    template_name = 'operativoschaco/matematica/listm.html'

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        director = self.request.user.username
        if not director:
            return ExamenAlumnoCueanexoM.objects.none()
        return ExamenAlumnoCueanexoM.objects.filter(alumno__cueanexo=director)

    def calcular_totales(self, examenes):
        """Calcula los subtotales por agrupación y el total general por alumno."""
        alumnos_totales = []

        for examen in examenes:
            respuestas = RespuestaM.objects.filter(examen=examen)

            # Inicializar subtotales
            subtotales = {
                "Aritmética": 0,
                "Geometría": 0,
                "Estadística": 0
            }
            total_general = 0

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
                        categoria = opcion_obj.categoria.nombre if opcion_obj.categoria else None
                        puntaje = opcion_obj.puntaje

                        if categoria in ['M1', 'M2', 'M3', 'M4', 'M5', 'M6']:
                            subtotales["Aritmética"] += puntaje
                        elif categoria in ['M7', 'M8', 'M9', 'M10']:
                            subtotales["Geometría"] += puntaje
                        elif categoria in ['M11', 'M12', 'M13', 'M14']:
                            subtotales["Estadística"] += puntaje

                        total_general += puntaje

                    except Opcion.DoesNotExist:
                        continue  # Saltar si la opción no existe

            alumnos_totales.append({
                'alumno': {
                    "id": examen.alumno.id,
                    "dni": examen.alumno.dni,
                    "apellidos": examen.alumno.apellidos,
                    "nombres": examen.alumno.nombres,
                },
                'subtotales': subtotales,
                'total_general': total_general
            })

        return alumnos_totales

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        examenes = self.get_queryset()
        context['alumnos_totales'] = self.calcular_totales(examenes)
        context['title'] = 'Listado de Alumnos Examen Matemática'
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action', '')

        if action == 'searchdata':
            examenes = self.get_queryset()
            data = self.calcular_totales(examenes)

            return JsonResponse({
                "data": data
            }, safe=False)

        return JsonResponse({"error": "Acción no válida"}, status=400)
