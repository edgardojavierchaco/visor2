from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.db import transaction
from django.contrib import messages
from django.core.exceptions import PermissionDenied

from .models import (
    Personas,
    RegistroActividades,
    NomencladorCeic,
    Localidades,
    CodAreasTelefonos,
    Grado_anio,
    Secciones,
    HorarioActividad,
    ActividadSede,
    ModalidadNivelCeic
)

from .forms import (
    PersonaForm,
    ActividadDirectorForm,
    HorarioActividadForm
)

from apps.bnhpersonas.domain.access import get_user_cueanexos

# ==============
# HELPERS
# ==============
def get_sede(actividad, cueanexo):
    return ActividadSede.objects.get_or_create(
        actividad=actividad,
        cueanexo=str(cueanexo)
    )[0]

def expandir_rangos(texto):
    """
    Convierte:
        1-21,220,221

    en

        [1,2,3,...,21,220,221]
    """

    ids = []

    if not texto:
        return ids

    for parte in texto.split(","):

        parte = parte.strip()

        if "-" in parte:

            inicio, fin = parte.split("-")

            ids.extend(
                range(int(inicio), int(fin) + 1)
            )

        else:

            ids.append(int(parte))

    return ids

# =====================================================
# FILTROS AJAX
# =====================================================
def filtrar_ceic(request):

    modalidad = request.GET.get("modalidad")
    nivel = request.GET.get("nivel")
    
    print(modalidad)
    print(nivel)

    try:

        configuracion = ModalidadNivelCeic.objects.get(
            modalidad_id=modalidad,
            nivel_id=nivel
        )
        
        print(configuracion.rango_ceic)

    except ModalidadNivelCeic.DoesNotExist:

        return JsonResponse([], safe=False)

    ceic_ids = expandir_rangos(
        configuracion.rango_ceic
    )

    qs = (
        NomencladorCeic.objects
        .filter(c_ceic__in=ceic_ids)
        .order_by("c_ceic")
    )

    data = list(
        qs.values(
            "c_ceic",
            "descripcion"
        )
    )

    return JsonResponse(data, safe=False)


def filtrar_grado_anio(request):
    modalidad = request.GET.get("modalidad")
    nivel = request.GET.get("nivel")

    qs = Grado_anio.objects.all()

    if nivel:
        qs = qs.filter(t_niv_grado="Nivel", c_niv_grado=int(nivel))
    elif modalidad:
        qs = qs.filter(t_niv_grado="Modalidad", c_niv_grado=int(modalidad))

    return JsonResponse(list(qs.values("c_grado_anio", "nombre_grado_anio")), safe=False)


def filtrar_secciones(request):
    modalidad = request.GET.get("modalidad")
    nivel = request.GET.get("nivel")

    qs = Secciones.objects.all()

    if nivel:
        qs = qs.filter(t_niv_seccion="Nivel", c_niv_seccion=int(nivel))
    elif modalidad:
        qs = qs.filter(t_niv_seccion="Modalidad", c_niv_seccion=int(modalidad))

    return JsonResponse(list(qs.values("c_seccion", "nombre_seccion")), safe=False)


def filtrar_localidades(request):
    provincia_id = request.GET.get("provincia")

    if not provincia_id:
        return JsonResponse([], safe=False)

    qs = Localidades.objects.filter(
        c_provincia_id=provincia_id
    ).values("c_localidad", "descrip_localidad")

    return JsonResponse(list(qs), safe=False)


def buscar_persona(request):
    cuil = request.GET.get("cuil")

    if not cuil:
        return JsonResponse({}, status=400)

    persona = Personas.objects.filter(cuil=cuil).first()

    if not persona:
        return JsonResponse({"existe": False})

    return JsonResponse({
        "existe": True,
        "id": persona.id,
        "dni": persona.dni,
        "apellido": persona.apellido,
        "nombre": persona.nombre,
        "sexo": persona.sexo_id,
        "provincia": persona.provincia_id,
        "localidad": persona.localidad_id,
        "telefono": persona.telefono or "",
        "whatsapp": bool(persona.whatsapp),
    })


def buscar_codigos_area(request):
    q = request.GET.get("q", "").strip()

    qs = CodAreasTelefonos.objects.all()

    if q:
        qs = qs.filter(codigo__startswith=q)

    qs = qs.order_by("codigo")[:20]

    data = [
        {
            "id": c.id,
            "label": f"{c.codigo} - {c.localidad} ({c.provincia})"
        }
        for c in qs
    ]

    return JsonResponse(data, safe=False)


# =====================================================
# CARGA PERSONA + ACTIVIDAD
# =====================================================

def carga_personal(request, pk=None):

    persona = None


    # =========================
    # PERSONA DESDE URL
    # =========================

    if pk:

        persona = get_object_or_404(
            Personas,
            pk=pk
        )


    persona_form = PersonaForm(
        request.POST or None,
        instance=persona
    )


    actividad_form = ActividadDirectorForm(
        request.POST or None,
        user=request.user
    )


    if request.method == "POST":


        accion = request.POST.get("accion")


        # =========================
        # RECUPERAR PERSONA AJAX
        # =========================

        if not persona:

            persona_id = request.POST.get(
                "persona_id"
            )


            if persona_id:

                persona = Personas.objects.filter(
                    pk=persona_id
                ).first()



        # =========================
        # GUARDAR PERSONA
        # =========================

        if accion == "persona":


            if persona_form.is_valid():


                obj = persona_form.save(
                    commit=False
                )


                if not obj.pk:

                    obj.usuario_creacion = request.user



                obj.usuario_modificacion = request.user


                obj.save()



                return redirect(
                    "bnhpersonas:carga_personal",
                    pk=obj.pk
                )



        # =========================
        # GUARDAR ACTIVIDAD
        # =========================

        if accion == "cargo":



            if not persona:


                if request.headers.get(
                    "X-Requested-With"
                ) == "XMLHttpRequest":


                    return JsonResponse({

                        "ok":False,

                        "mensaje":
                        "Debe cargar primero la persona."

                    },status=400)



                messages.error(
                    request,
                    "Debe cargar primero la persona."
                )



            elif actividad_form.is_valid():



                with transaction.atomic():


                    actividad = actividad_form.save(
                        commit=False
                    )


                    actividad.persona = persona


                    actividad.usuario_creacion = request.user


                    actividad.usuario_modificacion = request.user


                    actividad.save()



                if request.headers.get(
                    "X-Requested-With"
                ) == "XMLHttpRequest":



                    return JsonResponse({

                        "ok":True,

                        "mensaje":
                        "Cargo registrado correctamente.",

                        "id":
                        actividad.pk,
                        
                        "persona_id":
                        actividad.persona.pk

                    })



                messages.success(
                    request,
                    "Cargo registrado correctamente."
                )


                return redirect(
                    "bnhpersonas:editar_actividad",
                    pk=actividad.pk
                )



            else:


                if request.headers.get(
                    "X-Requested-With"
                ) == "XMLHttpRequest":



                    return JsonResponse({

                        "ok":False,

                        "errores":
                        actividad_form.errors

                    },status=400)



    actividades = []


    if persona:


        actividades = RegistroActividades.objects.filter(
            persona=persona
        ).order_by(
            "cueanexo"
        )



    return render(
        request,
        "bnh/personas/carga_personal.html",
        {

            "persona":persona,

            "form":persona_form,

            "actividad_form":actividad_form,

            "actividades":actividades,

        }
    )


# =====================================================
# EDITAR ACTIVIDAD
# =====================================================
def editar_actividad(request, pk):

    actividad = get_object_or_404(RegistroActividades, pk=pk)

    cueanexos_usuario = set(get_user_cueanexos(request.user))

    if str(actividad.cueanexo) not in cueanexos_usuario:
        raise PermissionDenied("No tiene permisos para editar esta actividad.")
    
    # 🔥 OBTENER SEDE REAL
    sede = get_sede(actividad, actividad.cueanexo)

    if request.method == "POST":

        form = ActividadDirectorForm(
            request.POST,
            instance=actividad,
            user=request.user
        )

        if form.is_valid():

            obj = form.save(commit=False)
            obj.usuario_modificacion = request.user
            obj.save()

            messages.success(request, "Actividad actualizada correctamente.")

            return redirect(
                "bnhpersonas:personas_detail",
                pk=actividad.persona.pk
            )

    else:
        form = ActividadDirectorForm(
            instance=actividad,
            user=request.user
        )
    
    horarios = HorarioActividad.objects.filter(
        actividad_sede=sede
    ).order_by("dia", "hora_desde")

    return render(request, "bnh/personas/editar_actividad.html", {
        "actividad": actividad,
        "form": form,
        "horarios": horarios,
        "horario_form": HorarioActividadForm(),
        "sede": sede
    })


# =====================================================
# HORARIOS
# =====================================================
def horarios_actividad(request, actividad_id):

    actividad = get_object_or_404(RegistroActividades, pk=actividad_id)

    cueanexos_usuario = set(get_user_cueanexos(request.user))

    if str(actividad.cueanexo) not in cueanexos_usuario:
        raise PermissionDenied("No tiene permisos sobre esta institución.")
    
    sede = get_sede( actividad, actividad.cueanexo )

    horarios = HorarioActividad.objects.filter(
        actividad_sede=sede
    ).order_by("dia", "hora_desde")

    return render(request, "bnh/personas/horarios_actividad.html", {
        "actividad": actividad,
        "horarios": horarios,
    })


def agregar_horario(request, actividad_id):

    actividad = get_object_or_404(RegistroActividades, pk=actividad_id)

    cueanexos_usuario = set(get_user_cueanexos(request.user))

    if str(actividad.cueanexo) not in cueanexos_usuario:
        raise PermissionDenied("No tiene permisos sobre esta institución.")

    if request.method != "POST":
        return JsonResponse({"ok": False}, status=400)
    
    sede = get_sede(actividad, actividad.cueanexo)

    form = HorarioActividadForm(request.POST)

    if form.is_valid():

        horario = form.save(commit=False)
        horario.actividad_sede = sede

        existe = HorarioActividad.objects.filter(
            actividad_sede=sede,
            dia=horario.dia,
            hora_desde=horario.hora_desde,
            hora_hasta=horario.hora_hasta
        ).exists()

        if existe:
            return JsonResponse(
                {"ok": False, "mensaje": "El horario ya existe."},
                status=400
            )

        horario.save()

        return JsonResponse({
            "ok": True,
            "id": horario.pk,
            "dia": horario.dia,
            "desde": horario.hora_desde.strftime("%H:%M"),
            "hasta": horario.hora_hasta.strftime("%H:%M"),
        })

    return JsonResponse({
        "ok": False,
        "errores": form.errors
    }, status=400)


def eliminar_horario(request, pk):

    horario = get_object_or_404(HorarioActividad, pk=pk)

    actividad = horario.actividad_sede.actividad

    cueanexos_usuario = set(get_user_cueanexos(request.user))

    if str(actividad.cueanexo) not in cueanexos_usuario:
        raise PermissionDenied("No tiene permisos.")

    horario.delete()

    return JsonResponse({"ok": True})


def guardar_persona_ajax(request):
    if request.method != "POST":
        return JsonResponse({"ok": False}, status=400)

    persona_id = request.POST.get("persona_id")

    instance = None
    
    if persona_id:
        instance = Personas.objects.filter(pk=persona_id).first()

    form = PersonaForm(request.POST, instance=instance)

    if form.is_valid():
        obj = form.save(commit=False)

        if not obj.pk:
            obj.usuario_creacion = request.user

        obj.usuario_modificacion = request.user
        obj.save()
        
        is_new=persona_id is None

        return JsonResponse({
            "ok": True,
            "id": obj.pk,
            "created": is_new,
            "apellido": obj.apellido,
            "nombre": obj.nombre,
        })

    return JsonResponse({
        "ok": False,
        "errors": form.errors
    }, status=400)
    


def filtrar_datos_actividad(request):

    modalidad = request.GET.get("modalidad")
    nivel = request.GET.get("nivel")
    
    # =========================
    # normalización segura
    # =========================
    try:
        modalidad = int(modalidad) if modalidad else None
    except:
        modalidad = None

    try:
        nivel = int(nivel) if nivel else None
    except:
        nivel = None

    # =========================
    # CEIC
    # =========================

    ceic = []

    try:
        config = ModalidadNivelCeic.objects.get(
            modalidad_id=modalidad,
            nivel_id=nivel
        )

        ids = expandir_rangos(config.rango_ceic)

        ceic = list(
            NomencladorCeic.objects.filter(
                c_ceic__in=ids
            )
            .order_by("descripcion")
            .values(
                "c_ceic",
                "descripcion"
            )
        )

    except ModalidadNivelCeic.DoesNotExist:
        ceic = []

    # =========================
    # GRADO / AÑO
    # =========================
    grado_qs = Grado_anio.objects.all()

    if nivel:
        grado_qs = grado_qs.filter(t_niv_grado="Nivel", c_niv_grado=nivel)
    elif modalidad:
        grado_qs = grado_qs.filter(t_niv_grado="Modalidad", c_niv_grado=modalidad)

    grado = list(
        grado_qs.order_by("nombre_grado_anio").values(
            "c_grado_anio",
            "nombre_grado_anio"
        )
    )

    # =========================
    # SECCIONES
    # =========================
    sec_qs = Secciones.objects.all()

    if nivel:
        sec_qs = sec_qs.filter(t_niv_seccion="Nivel", c_niv_seccion=nivel)
    elif modalidad:
        sec_qs = sec_qs.filter(t_niv_seccion="Modalidad", c_niv_seccion=modalidad)

    secciones = list(
        sec_qs.order_by("nombre_seccion").values(
            "c_seccion",
            "nombre_seccion"
        )
    )

    return JsonResponse({
        "ceic": ceic,
        "grado": grado,
        "secciones": secciones
    })