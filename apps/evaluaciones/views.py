from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum
from .models import Alumno, Evaluacion, EvaluacionAlumno, Pregunta, OpcionRespuesta
import spacy

# Cargar el modelo de spaCy en español
nlp = spacy.load("es_core_news_sm")

def cargar_respuestas(request, alumno_id, evaluacion_id):
    alumno = get_object_or_404(Alumno, id=alumno_id)
    evaluacion = get_object_or_404(Evaluacion, id=evaluacion_id)
    preguntas = evaluacion.preguntas.prefetch_related('opciones')

    if request.method == 'POST':
        puntaje_lengua = 0
        puntaje_matematica = 0

        for pregunta in preguntas:
            if pregunta.tipo == 'unica':
                # Respuesta de opción única
                respuesta_id = request.POST.get(f"respuesta_{pregunta.id}")
                if respuesta_id:
                    opcion = pregunta.opciones.get(id=respuesta_id)
                    if opcion.correcta:
                        if evaluacion.materia == 'Lengua':
                            puntaje_lengua += pregunta.puntaje
                        elif evaluacion.materia == 'Matematicas':
                            puntaje_matematica += pregunta.puntaje

            elif pregunta.tipo == 'multiple':
                # Respuesta de opción múltiple
                respuesta_ids = request.POST.getlist(f"respuesta_{pregunta.id}")
                if respuesta_ids:
                    opciones = pregunta.opciones.filter(id__in=respuesta_ids)
                    correctas_seleccionadas = opciones.filter(correcta=True).count()
                    total_correctas = pregunta.opciones.filter(correcta=True).count()

                    # Si se seleccionaron respuestas correctas
                    if correctas_seleccionadas > 0:
                        # Promediar el puntaje según las respuestas correctas
                        puntaje_promedio = (correctas_seleccionadas / total_correctas) * pregunta.puntaje

                        # Asegurarnos de que el puntaje no sea mayor al puntaje total de la pregunta
                        puntaje_promedio = min(puntaje_promedio, pregunta.puntaje)

                        if evaluacion.materia == 'Lengua':
                            puntaje_lengua += puntaje_promedio
                        elif evaluacion.materia == 'Matematicas':
                            puntaje_matematica += puntaje_promedio

            elif pregunta.tipo == 'texto_clasificar':
                # Clasificar sustantivos y adjetivos en texto libre
                texto_alumno = request.POST.get(f"texto_{pregunta.id}", "")
                sustantivos = request.POST.get(f"sustantivos_{pregunta.id}", "").split(',')
                adjetivos = request.POST.get(f"adjetivos_{pregunta.id}", "").split(',')

                # Procesar el texto base
                doc_base = nlp(pregunta.texto_base)
                sustantivos_base = {token.text.lower() for token in doc_base if token.pos_ == "NOUN"}
                adjetivos_base = {token.text.lower() for token in doc_base if token.pos_ == "ADJ"}

                # Calcular el puntaje
                sustantivos_correctos = len(set(map(str.strip, sustantivos)) & sustantivos_base)
                adjetivos_correctos = len(set(map(str.strip, adjetivos)) & adjetivos_base)

                puntaje_sustantivos = sustantivos_correctos / max(len(sustantivos_base), 1)
                puntaje_adjetivos = adjetivos_correctos / max(len(adjetivos_base), 1)

                puntaje_total_clasificar = (puntaje_sustantivos + puntaje_adjetivos) / 2 * pregunta.puntaje

                if evaluacion.materia == 'Lengua':
                    puntaje_lengua += puntaje_total_clasificar

        # Crear o actualizar el puntaje en EvaluacionAlumno
        evaluacion_alumno, created = EvaluacionAlumno.objects.get_or_create(
            alumno=alumno,
            evaluacion=evaluacion,
        )
        evaluacion_alumno.puntaje_lengua = puntaje_lengua
        evaluacion_alumno.puntaje_matematica = puntaje_matematica
        evaluacion_alumno.puntaje_total = puntaje_lengua + puntaje_matematica
        evaluacion_alumno.save()

        return redirect('evaluaciones:ver_puntajes', alumno_id=alumno.id)

    return render(request, 'evaluaciones/evaluacion_formulario.html', {
        'alumno': alumno,
        'evaluacion': evaluacion,
        'preguntas': preguntas,
    })

def ver_puntajes(request, alumno_id):
    alumno = Alumno.objects.get(id=alumno_id)
    evaluaciones = EvaluacionAlumno.objects.filter(alumno=alumno)

    # Obtener el puntaje total combinado
    puntaje_total_combinado = evaluaciones.aggregate(Sum('puntaje_total'))['puntaje_total__sum']
    if puntaje_total_combinado is None:
        puntaje_total_combinado = 0

    return render(request, "evaluaciones/ver_puntajes.html", {
        'alumno': alumno,
        'evaluaciones': evaluaciones,
        'puntaje_total_combinado': puntaje_total_combinado,
    })
