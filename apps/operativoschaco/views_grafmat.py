from django.views import View
from django.shortcuts import render
from django.http import JsonResponse
from .models import RespuestaM, Opcion, ExamenAlumnoCueanexoM

class GraficoMatematicaView(View):
    template_name = 'operativoschaco/examen_grafico_matematica.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        cueanexo = request.user.username
        examenes = ExamenAlumnoCueanexoM.objects.filter(alumno__cueanexo=cueanexo)

        resumen_por_categoria = {
            "Aritmética": 0,
            "Geometría": 0,
            "Estadística": 0
        }

        for examen in examenes:
            respuestas = RespuestaM.objects.filter(examen=examen)

            for respuesta in respuestas:
                for opcion_data in respuesta.opciones_seleccionadas or []:
                    opcion_id = opcion_data.get('opcion_id')
                    if not opcion_id:
                        continue

                    try:
                        opcion_obj = Opcion.objects.get(id=opcion_id)
                        categoria = opcion_obj.categoria.nombre if opcion_obj.categoria else None
                        puntaje = opcion_obj.puntaje

                        if categoria in ['M1', 'M2', 'M3', 'M4', 'M5', 'M6']:
                            resumen_por_categoria["Aritmética"] += puntaje
                        elif categoria in ['M7', 'M8', 'M9', 'M10']:
                            resumen_por_categoria["Geometría"] += puntaje
                        elif categoria in ['M11', 'M12', 'M13', 'M14']:
                            resumen_por_categoria["Estadística"] += puntaje

                    except Opcion.DoesNotExist:
                        continue

        chart_data = [
            {"categoria": k, "puntaje_total": v}
            for k, v in resumen_por_categoria.items()
        ]

        return JsonResponse(chart_data, safe=False)
