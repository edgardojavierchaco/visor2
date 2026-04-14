from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .forms import ExamenMatematicaForm
from .models import ExamenAlumnoCueanexoM, PreguntaM, AlumnosSecundaria, RespuestaM, Opcion

def guardar_examen_matematica(request):
    if request.method == 'POST':
        form = ExamenMatematicaForm(request.POST)

        if form.is_valid():
            dni_alumno = form.cleaned_data['dni_alumno']
            apellidos = form.cleaned_data['apellidos']
            nombres = form.cleaned_data['nombres']
            cueanexo = form.cleaned_data['cueanexo']
            anio=form.cleaned_data['anio']
            division = form.cleaned_data['division']

            # Buscar o crear el alumno
            alumno, created = AlumnosSecundaria.objects.get_or_create(
                dni=dni_alumno,
                cueanexo=request.user.username,  # 👈 cueanexo desde el usuario logueado
                anio=1,  # 👈 anio fijo en 1
                defaults={
                    'apellidos': apellidos,
                    'nombres': nombres,
                    'division': division
                }                
            )
            
            if created:
                # Si es un nuevo alumno, guardamos sus datos
                alumno.apellidos = apellidos
                alumno.nombres = nombres
                alumno.cueanexo = request.user.username # 👈 cueanexo desde el usuario logueado
                alumno.anio = 1 # 👈 anio fijo en 1
                alumno.division = division
                alumno.save()

            # Crear el examen
            examen = ExamenAlumnoCueanexoM(alumno=alumno)
            examen.save()

            # Guardar respuestas como JSON
            for pregunta in form.preguntas:
                opciones_seleccionadas = []

                opciones = pregunta.opciones.all()
                categorias_presentes = set(op.categoria for op in opciones if op.categoria)

                if categorias_presentes:
                    # Procesar opciones con categorías
                    for categoria in categorias_presentes:
                        opcion_seleccionada_id = form.cleaned_data.get(f'preg_{pregunta.id}_cat_{categoria.id}')
                        
                        if opcion_seleccionada_id:
                            opcion_seleccionada = Opcion.objects.get(id=opcion_seleccionada_id)

                            # Convertir puntaje a float para evitar error de serialización
                            opciones_seleccionadas.append({
                                "opcion_id": opcion_seleccionada.id,
                                "descripcion": opcion_seleccionada.descripcion,
                                "puntaje": float(opcion_seleccionada.puntaje)  # 👈 Solución
                            })

                else:
                    # Procesar opciones sin categorías
                    opcion_seleccionada_id = form.cleaned_data.get(f'preg_{pregunta.id}')
                    
                    if opcion_seleccionada_id:
                        opcion_seleccionada = Opcion.objects.get(id=opcion_seleccionada_id)

                        # Convertir puntaje a float para evitar error de serialización
                        opciones_seleccionadas.append({
                            "opcion_id": opcion_seleccionada.id,
                            "descripcion": opcion_seleccionada.descripcion,
                            "puntaje": float(opcion_seleccionada.puntaje)  # 👈 Solución
                        })

                # Crear la respuesta con JSON
                RespuestaM.objects.create(
                    examen=examen,
                    pregunta=pregunta,
                    opciones_seleccionadas=opciones_seleccionadas
                )

            # Redirigir a la página de listado después de guardar el examen
            return redirect('operative:listadomat')  # 👈 Asegúrate de que la URL esté configurada en `urls.py`

        else:
            print("Formulario inválido:", form.errors)
            return render(request, 'operativoschaco/examen_matem_formulario.html', {
                'form': form,
                'preguntas_con_opciones': form.preguntas,
                'errors': form.errors
            }) 
    # Si es un GET, cargar el formulario
    form = ExamenMatematicaForm()

    # Preprocesar opciones para el template
    preguntas_con_opciones = []
    for pregunta in form.preguntas:
        opciones = pregunta.opciones.all()
        categorias_presentes = set(op.categoria for op in opciones if op.categoria)

        categorias_opciones = {}

        if categorias_presentes:
            for categoria in categorias_presentes:
                opciones_categoria = opciones.filter(categoria=categoria)
                categorias_opciones[categoria] = opciones_categoria
        else:
            categorias_opciones['sin_categoria'] = opciones

        preguntas_con_opciones.append({
            'pregunta': pregunta,
            'categorias_opciones': categorias_opciones
        })

    return render(request, 'operativoschaco/examen_matem_formulario.html', {
        'form': form,
        'preguntas_con_opciones': preguntas_con_opciones
    })


def examen_guardado(request):
    return render(request, 'operativoschaco/examen_guardado.html')



@csrf_exempt
def buscar_alumno_por_dni(request):
    dni = request.GET.get('dni', None)
    print("Valor recibido de DNI:", dni)  # ✅ Confirmación de valor
    if dni:
        # Verificar si el DNI tiene exactamente 8 dígitos
        if len(dni) == 8:
            try:
                alumno = AlumnosSecundaria.objects.get(dni=dni)
                data = {
                    "error": False,  # ✅ Clave explícita para indicar éxito
                    "dni": alumno.dni,
                    "apellidos": alumno.apellidos,
                    "nombres": alumno.nombres,
                    "cueanexo": alumno.cueanexo,
                    "anio": alumno.anio,
                    "division": alumno.division,
                }
                print("Alumno encontrado:", data)  # ✅ Confirmación de respuesta
            except AlumnosSecundaria.DoesNotExist:
                data = {
                    "error": True, 
                    "message": "Alumno no encontrado. Puede ser agregado.",
                    "allow_add": True  # ✅ Permitir agregar desde el frontend
                    }
                print("Error:", data)
    else:
        data = {"error": True, "message": "DNI no proporcionado"}
        print("Error:", data)
    
    return JsonResponse(data)