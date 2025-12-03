from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.template import loader
from apps.evaluaciones_educativas import *
from apps.evaluaciones_educativas.forms.forms import *
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout


@login_required
def carga_alumno(request,grado_public_id):
    grado=get_object_or_404(Grado,public_id= grado_public_id)
    alumno_form = AlumnoForm()
    grado_form = GradoForm(instance=grado)
    seccion_form = SeccionForm()
    if request.method == 'POST':
        alumno_form = AlumnoForm(request.POST)
        grado_form = GradoForm(request.POST)
        seccion_form = SeccionForm(request.POST)
        if alumno_form.is_valid() and grado_form.is_valid() and seccion_form.is_valid():
           #una instancia a la vez
            with transaction.atomic():
                turno_seccion=seccion_form.cleaned_data["turno"]
                nombre_seccion=seccion_form.cleaned_data["seccion"]
                instancia_seccion, creado_seccion = Seccion.objects.get_or_create(
                seccion=nombre_seccion,
                turno=turno_seccion,
                grado=grado
                )
                
                alumno = alumno_form.save(commit=False)
                alumno.seccion = instancia_seccion
                alumno.save()
            return redirect("evaluaciones_educativas:asistencia", alumno_public_id=alumno.public_id)
            
    context = {
        'alumno_form': alumno_form,
        'grado_form': grado_form,
        'seccion_form': seccion_form,
        'grado_public':grado_public_id,
               }
    return render(request, "alumno.html", context)

@login_required
def editar_alumno(request,alumno_public_id):
    instancia_alumno=get_object_or_404(Alumno,public_id=alumno_public_id)
    instancia_seccion=get_object_or_404(Seccion,id=instancia_alumno.seccion_id)
    instancia_grado=get_object_or_404(Grado,id=instancia_seccion.grado_id)
    alumno_form = AlumnoForm(instance=instancia_alumno)
    seccion_form = SeccionForm(instance=instancia_seccion)
    grado_form = GradoForm(instance=instancia_grado)
    if request.method == 'POST':
        alumno_form = AlumnoForm(request.POST, instance=instancia_alumno)
        grado_form = GradoForm(request.POST, instance=instancia_grado)
        seccion_form = SeccionForm(request.POST, instance=instancia_seccion)
        if alumno_form.is_valid() and grado_form.is_valid() and seccion_form.is_valid():
            with transaction.atomic():
                nombre_grado=grado_form.cleaned_data["nombre_grado"]
                cueanexo_grado=grado_form.cleaned_data["cueanexo"]
                instancia_grado, creado_grado=Grado.objects.get_or_create(
                    nombre_grado=nombre_grado,
                    cueanexo=cueanexo_grado
                    )
                turno_seccion=seccion_form.cleaned_data["turno"]
                nombre_seccion=seccion_form.cleaned_data["seccion"]
                instancia_seccion, creado_seccion = Seccion.objects.get_or_create(
                seccion=nombre_seccion,
                turno=turno_seccion,
                grado=instancia_grado
                )
                alumno = alumno_form.save(commit=False)
                alumno.seccion = instancia_seccion
                alumno.save()
            return redirect("evaluaciones_educativas:editar_asistencia", alumno_public_id=alumno.public_id)
    context = {
        'alumno_form': alumno_form,
         'grado_form': grado_form,
        'seccion_form': seccion_form,
        'grado_public':instancia_grado.public_id,
               }
    return render(request, "alumno.html", context)

@login_required
def lista(request,grado_public_id): 
    instancia_grado=get_object_or_404(Grado,public_id=grado_public_id)
    instancia_seccion=Seccion.objects.filter(grado_id=instancia_grado)
    alumnos = Alumno.objects.filter(seccion_id__in=instancia_seccion).order_by('nombre')
    evaluacion = EvaluacionFluidezLectora.objects.filter(alumno__in=alumnos)
    contexto = {
        'lista_alumnos': alumnos,
        'evaluciones': evaluacion,
        'nombre_grado':instancia_grado.nombre_grado,
    }
    return render(request,"lista.html", contexto)
#-----------------lista para grados------------------
@login_required
def lista_grado(request,grado): 
    #---------logica para obtener cueanexo por medio de username--------------
    usuario= request.user
    if usuario.is_authenticated:
        name=usuario.username
    #-----logica para DNI+CUEANEXO---------
    if len(name)>9  and len(name)<=17:
        #DNI+CUEANEXO
        nombre_usuario_cueanexo=name[8:]
    else:
        nombre_usuario_cueanexo=name
    #cueanexo=int(nombre_usuario_cueanexo)   
#-----logica para DNI+CUEANEXO---------
    if grado =='SEGUNDO':
        grado='2do Año/Grado'
    elif grado =='TERCERO':
            grado='3er Año/Grado'
    try:
        instancia_grado=Grado.objects.get(cueanexo=nombre_usuario_cueanexo, nombre_grado=grado)
        return redirect("evaluaciones_educativas:lista", grado_public_id=instancia_grado.public_id)
    except Grado.DoesNotExist:
        return render(request,"lista.html")
@login_required
def grado(request):
    usuario= request.user
    if usuario.is_authenticated:
        name=usuario.username
        #-----logica para DNI+CUEANEXO---------
        if len(name)>9  and len(name)<=17:
            #DNI+CUEANEXO
            nombre_usuario_cueanexo=name[8:]
        else:
            nombre_usuario_cueanexo=name
        #cueanexo=int(nombre_usuario_cueanexo)
        #-----logica para DNI+CUEANEXO---------
        
    opciones_grado = [
                     ('2do Año/Grado', '2do Año/Grado'),
                      ('3er Año/Grado','3er Año/Grado')
                        ]
    grado_form_data = GradoViewForm()
    if request.method == 'POST':
        grado_form_data = GradoViewForm(request.POST)
        grado_form_data.fields['grado'].choices = opciones_grado
        if grado_form_data.is_valid():
            with transaction.atomic():
                grado=grado_form_data.cleaned_data["grado"]
                print(grado)
                instancia_grado, creado_grado=Grado.objects.get_or_create(
                    nombre_grado=grado,
                    cueanexo=nombre_usuario_cueanexo
                    )
                grado_public=instancia_grado.public_id
            return redirect("evaluaciones_educativas:carga_alumno", grado_public_id=grado_public)
    else:
        grado_form_data.fields['grado'].choices = opciones_grado
    contexto = {
        'grado_form_data': grado_form_data
    }
    return render(request,"grados.html", contexto)

    
@login_required
def carga_evaluacion(request, alumno_public_id):
    alumno_id=get_object_or_404(Alumno, public_id=alumno_public_id)
    instancia_seccion=get_object_or_404(Seccion,id=alumno_id.seccion_id)
    # seccion_public=instancia_seccion.public_id
    # turno_seccion=instancia_seccion.turno
    instancia_grado=get_object_or_404(Grado,id=instancia_seccion.grado_id)
    grado_public=instancia_grado.public_id
    # print(instancia_grado.nombre_grado)
    if instancia_grado.nombre_grado =='SEGUNDO':
        cantidad_palabra_maxima=170
    else:
        cantidad_palabra_maxima=211
    if request.method == 'POST':
        form = EvaluacionFluidezForm(request.POST, max_cantidad_palabra=cantidad_palabra_maxima)
        if form.is_valid():
            with transaction.atomic():
                evaluacion = form.save(commit=False)
                evaluacion.alumno = alumno_id
                evaluacion.asistencia ='PRESENTE'
                evaluacion.encargado_carga='DIRECTOR'
                evaluacion.save()
            return redirect("evaluaciones_educativas:lista", grado_public_id=grado_public)
    else:
        #Instancia vacia para metodo get
        form = EvaluacionFluidezForm(max_cantidad_palabra=cantidad_palabra_maxima)
        #Creacion de diccionario para el Post
    context = {'form': form,
               'alumno':alumno_id}
    return render(request, "evaluacion.html", context)

@login_required
def editar_evaluacion(request, alumno_public_id):
    alumno_id=get_object_or_404(Alumno,public_id=alumno_public_id)
    instancia_seccion=get_object_or_404(Seccion,id=alumno_id.seccion_id)
    instancia_grado=get_object_or_404(Grado,id=instancia_seccion.grado_id)
    grado_public=instancia_grado.public_id
    instancia_evaluacion=EvaluacionFluidezLectora.objects.get(alumno_id=alumno_id.id)
    if instancia_grado.nombre_grado =='SEGUNDO':
        cantidad_palabra_maxima=170
    else:
        cantidad_palabra_maxima=211
    form=EvaluacionFluidezForm(instance=instancia_evaluacion, max_cantidad_palabra=cantidad_palabra_maxima)
    if request.method == 'POST':
        form=EvaluacionFluidezForm(request.POST,instance=instancia_evaluacion,max_cantidad_palabra=cantidad_palabra_maxima)
        if form.is_valid():
            with transaction.atomic():
                evaluacion=form.save(commit=False)
                evaluacion.alumno_id = alumno_id
                evaluacion.asistencia='PRESENTE'
                evaluacion.encargado_carga='DIRECTOR'
                evaluacion.save()
            return redirect("evaluaciones_educativas:lista", grado_public_id=grado_public)
    context = {
        'form': form,
        'alumno':alumno_id
        }
    return render(request, "evaluacion.html", context)

@login_required
def asistencia(request,alumno_public_id):
    alumno_id=get_object_or_404(Alumno, public_id=alumno_public_id)
    #SI instanciamos aca se crea antes de que confirme asistencia (puede ser conveniente)...
    instancia_evaluacion, creando_evaluacion=EvaluacionFluidezLectora.objects.get_or_create(
        alumno_id=alumno_id.id, encargado_carga='DIRECTOR')
    instancia_seccion=get_object_or_404(Seccion,id=alumno_id.seccion_id)
    instancia_grado=get_object_or_404(Grado,id=instancia_seccion.grado_id)
    grado_public=instancia_grado.public_id
    if request.method == 'POST':
            form = AsistenciaForm(request.POST)
            if form.is_valid():
                with transaction.atomic():
                    asistencia= form.cleaned_data["asistencia"]
                    if asistencia: 
                        return redirect("evaluaciones_educativas:carga_evaluacion", alumno_public_id=alumno_id.public_id)
                    else:
                        #llamamos a funcion ausentismo
                        evaluacion=ausentismo_evaluacion(instancia_evaluacion)
                        evaluacion.save()
                        return redirect("lista", grado_public_id=grado_public)
    else:
        form = AsistenciaForm()
    context = {'form': form,
               'alumno':alumno_id
               }
    return render(request,"asistencia.html",context)

@login_required
def editar_asistencia(request,alumno_public_id):
    #INSTANCIAS
    alumno_id=get_object_or_404(Alumno, public_id=alumno_public_id)
    instancia_seccion=get_object_or_404(Seccion,id=alumno_id.seccion_id)
    instancia_grado=get_object_or_404(Grado,id=instancia_seccion.grado_id)
    grado_public=instancia_grado.public_id
    if request.method == 'POST':
        form = AsistenciaForm(request.POST)
        #Campos de tabla evaluacion
        if form.is_valid():
            with transaction.atomic():
                asistencia = form.cleaned_data["asistencia"]
                #verificamos alumno presente
                if asistencia: 
                    return redirect("evaluaciones_educativas:editar_evaluacion", alumno_public_id=alumno_id.public_id)
                else:
                    #Recien instanciamos en el ELSE 
                    instancia_evaluacion, creando_evaluacion=EvaluacionFluidezLectora.objects.get_or_create(alumno_id=alumno_id.id)
                    evaluacion=ausentismo_evaluacion(instancia_evaluacion)
                    evaluacion.save()
                    return redirect("lista", grado_public_id=grado_public)
    else:
        asistencia_form = AsistenciaForm()
    context = {'form': asistencia_form}
    return render(request,"asistencia.html",context)

@login_required
def borrar_registro_alumno(request,alumno_public_id):
    alumno_id=get_object_or_404(Alumno, public_id=alumno_public_id)
    instancia_seccion=get_object_or_404(Seccion,id=alumno_id.seccion_id)
    instancia_grado=get_object_or_404(Grado,id=instancia_seccion.grado_id)
    grado_public=instancia_grado.public_id
    if request.method == 'POST':
        form = BorrarRegistroAlumnoForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                eleccion= form.cleaned_data["borrar"]
                if eleccion:
                    alumno_id.delete()
                    return redirect("evaluaciones_educativas:lista", grado_public_id=grado_public)
                else:
                    return redirect("evaluaciones_educativas:lista", grado_public_id=grado_public)
    else:
        form = BorrarRegistroAlumnoForm()
    context = {'form': form,
               'alumno':alumno_id
               }
    return render(request,"borrar_registro_alumno.html",context)

# @login_required
# def monitoreo(request):
#     instancia_grado_cueanexo=Grado.objects.all()
#     # instancia_grado=Grado.objects.filter(cueanexo__in=instancia_grado_cueanexo).values_list('nombre_grado',flat=True)
#     # # for i in instancia_grado:
#     # #     print(i)
#     contexto={'grados':instancia_grado_cueanexo}
#     return render(request,"monitoreo.html", contexto)

def ausentismo_evaluacion(instancia_evaluacion):
    evaluacion_campos=instancia_evaluacion._meta.fields
    for i in evaluacion_campos:
        if i.name == 'asistencia':
            #FUNCION DE PYTHON para estabalecer valores a campos de un objeto
            setattr(instancia_evaluacion, i.name, 'AUSENTE')
            #verificamos campos PK y NOT NULL
        if not i.primary_key and i.null:
            setattr(instancia_evaluacion, i.name, None)
    return instancia_evaluacion

#logica de logue--BORRAR-------------------
# def salir(request):
#     logout(request)
#     return redirect('accounts/login.html')
#-----------------------------