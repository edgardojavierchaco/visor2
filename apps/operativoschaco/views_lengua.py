from django.views.generic import ListView
from django.db.models import Q
from .models import ExamenAlumnoCueanexoL, Categoria, Respuesta, Opcion

class ListadoAlumnosLenguaView(ListView):
    model = ExamenAlumnoCueanexoL
    template_name = 'operativoschaco/lengua/listlen.html'
    context_object_name = 'examenes'

    def get_queryset(self):
        director = self.request.user.username
        if not director:
            return ExamenAlumnoCueanexoL.objects.none()
        return ExamenAlumnoCueanexoL.objects.filter(alumno__cueanexo=director)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        categorias = Categoria.objects.exclude(nombre__in=[
            'M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7', 'M8',
            'M9', 'M10', 'M11', 'M12', 'M13', 'M14'
        ])

        if not categorias.exists():
            context['error'] = "No hay categorías disponibles"
            return context

        context['categorias'] = categorias
        alumnos_totales = []

        for examen in self.get_queryset():
            respuestas = Respuesta.objects.filter(examen=examen)

            # Diccionario con los puntajes por pregunta
            totales_por_pregunta = {f'P{i}': 0 for i in range(1, 17)}
            total_general = 0

            for respuesta in respuestas:
                pregunta_id = respuesta.pregunta.id
                if 5 <= pregunta_id <= 22:
                    numero_pregunta = pregunta_id - 4  # ID 5 es P1 → 5 - 4 = 1
                    clave = f'P{numero_pregunta}'

                    # Obtener IDs de opciones seleccionadas
                    opcion_ids = [opcion.get('opcion_id') for opcion in respuesta.opciones_seleccionadas if opcion.get('opcion_id')]

                    # Obtener puntajes de opciones seleccionadas
                    opciones = Opcion.objects.filter(id__in=opcion_ids)
                    puntaje_pregunta = sum(opcion.puntaje for opcion in opciones)

                    # Guardar puntajes en el diccionario
                    totales_por_pregunta[clave] += puntaje_pregunta
                    total_general += puntaje_pregunta

            alumno_data = {
                'alumno': examen.alumno,                
                'cueanexo': examen.alumno.cueanexo,
                'region': examen.alumno.region,
                'por_pregunta': totales_por_pregunta,
                'total_general': total_general,
            }

            alumnos_totales.append(alumno_data)

        context['alumnos_totales'] = alumnos_totales
        context['title'] = 'Listado de Alumnos Examen Lengua'
        context['rango_preguntas'] = range(1, 17)
        return context
