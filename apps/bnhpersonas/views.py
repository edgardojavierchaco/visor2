import logging

import re



from django.contrib import messages

from django.core.exceptions import PermissionDenied, ValidationError

from django.db import IntegrityError, OperationalError, transaction

from django.http import JsonResponse

from django.shortcuts import get_object_or_404, redirect, render

from django.urls import reverse

from django.views.decorators.http import require_GET, require_POST, require_http_methods

from .domain.access import operator_required, person_scope, activity_scope, is_admin, is_regional

from .domain.catalogs import activity_catalogs, available_levels, ceic_aplica, condiciones_actividad, curricular_catalogs

from .forms import PersonaForm, ActividadDirectorForm, HorarioActividadForm, ConfirmacionForm, VincularPersonaForm

from .models import Personas, RegistroActividades, HorarioActividad, Localidades, CodAreasTelefonos, TipoPersonal, SituacionServicio, validar_cuil

from .services.rate_limit import user_rate_limit

logger = logging.getLogger(__name__)





from .services.crud import (

    Conflict,

    PossibleDuplicate,

    ConcurrentIdentityConflict,

    add_schedule,

    archive_person,

    restore_person,

    change_activity,

    create_person_with_activity,

    delete_schedule,

    integrity_error_message,

    link_existing_person_with_activity,

    save_activity,

    save_person,

)





def errors_to_form(form, exc, *, activity_form=None):

    """Convierte errores de concurrencia/BD en mensajes útiles sin exponer SQL."""

    target = activity_form or form



    if isinstance(exc, PossibleDuplicate):

        if hasattr(target, "expose_duplicate_warning"):

            target.expose_duplicate_warning(exc.messages[0] if exc.messages else str(exc))

        for message in getattr(exc, "messages", [str(exc)]):

            target.add_error(None, message)

        return



    if isinstance(exc, IntegrityError):

        target.add_error(None, integrity_error_message(exc))

        return



    if isinstance(exc, OperationalError):

        target.add_error(

            None,

            "La operación encontró un bloqueo concurrente y no pudo completarse tras los "

            "reintentos automáticos. Espere unos segundos, recargue y vuelva a intentar.",

        )

        return



    messages_list = getattr(exc, "messages", None) or [str(exc)]

    for message in messages_list:

        target.add_error(None, message)







def _validation_summary(form, *, title):

    """

    Registra y expone un resumen claro cuando un formulario no valida.



    No sustituye los errores de campo de Django: agrega un error general para

    que el usuario vea inmediatamente por qué no se ejecutó el guardado.

    """

    if not form or not form.errors:

        return



    logger.warning(

        "BNH formulario inválido | %s | errors=%s",

        title,

        form.errors.as_json(),

    )



    labels = []

    for field_name in form.errors:

        if field_name == "__all__":

            continue

        field = form.fields.get(field_name)

        label = (

            getattr(field, "label", None)

            or field_name.replace("_", " ").capitalize()

        )

        if label not in labels:

            labels.append(str(label))



    if labels:

        form.add_error(

            None,

            "No se pudo guardar. Revise los siguientes campos: "

            + ", ".join(labels)

            + ".",

        )

    else:

        form.add_error(

            None,

            "No se pudo guardar. Revise los datos informados en el formulario.",

        )





@operator_required

@require_http_methods(["GET", "POST"])

def carga_personal(request, pk=None):

    person = get_object_or_404(person_scope(request.user), pk=pk) if pk else None

    form = PersonaForm(request.POST if request.method == "POST" else None, instance=person, prefix="persona")

    activity = None if person else ActividadDirectorForm(request.POST if request.method == "POST" else None, user=request.user, prefix="actividad")

    if request.method == "POST":

        valid_person = form.is_valid()

        valid_activity = activity.is_valid() if activity else True



        # Si el POST no valida, el guardado no se ejecuta.

        # Dejamos un resumen visible y el detalle completo en el log de Django.

        if not valid_person:

            _validation_summary(

                form,

                title="Persona - Alta/edición",

            )



        if activity is not None and not valid_activity:

            _validation_summary(

                activity,

                title="Actividad - Alta de personal y primer cargo",

            )



        if valid_person and valid_activity:

            try:

                if activity:

                    obj, saved_activity, created_person = create_person_with_activity(

                        request.user, form, activity

                    )

                    if created_person:

                        messages.success(request, "Personal y primer cargo guardados correctamente.")

                    else:

                        messages.info(

                            request,

                            "La persona fue registrada simultáneamente por otra unidad de servicio. "

                            "Se reutilizó la ficha existente sin sobrescribir sus datos y se registró "

                            "la nueva vinculación institucional.",

                        )

                else:

                    obj = save_person(request.user, form)

                    messages.success(request, "Datos personales actualizados correctamente.")

                return redirect("bnhpersonas:personas_detail", pk=obj.pk)

            except (ValidationError, IntegrityError, OperationalError) as exc:

                errors_to_form(form, exc, activity_form=activity)

    return render(request, "bnh/personas/form.html", {"form": form, "actividad_form": activity, "persona": person, "title": "Editar datos personales" if person else "Alta de personal y primer cargo"})





@operator_required

@require_http_methods(["GET", "POST"])

def nueva_actividad(request, persona_id):

    person = get_object_or_404(person_scope(request.user), pk=persona_id)

    form = ActividadDirectorForm(request.POST if request.method == "POST" else None, user=request.user)

    if request.method == "POST" and form.is_valid():

        try:

            obj = save_activity(request.user, form, person)

            return redirect("bnhpersonas:editar_actividad", pk=obj.pk)

        except (ValidationError, IntegrityError, OperationalError) as exc:

            errors_to_form(form, exc)

    return render(request, "bnh/personas/form.html", {"form": form, "persona": person, "title": "Agregar cargo"})





@operator_required

@require_http_methods(["GET", "POST"])

def vincular_persona(request):

    form = VincularPersonaForm(request.POST if request.method == "POST" else None)

    activity = ActividadDirectorForm(request.POST if request.method == "POST" else None, user=request.user, prefix="actividad")

    if request.method == "POST":

        valid_person, valid_activity = form.is_valid(), activity.is_valid()

        if valid_person and valid_activity:

            try:

                person, saved_activity = link_existing_person_with_activity(

                    request.user, form.cleaned_data, activity

                )

                messages.success(request, "Persona vinculada mediante el nuevo cargo.")

                return redirect("bnhpersonas:personas_detail", pk=person.pk)

            except (ValidationError, IntegrityError, OperationalError) as exc:

                errors_to_form(form, exc, activity_form=activity)

    return render(request, "bnh/personas/form.html", {"form": form, "actividad_form": activity, "title": "Vincular personal ya registrado", "linking": True})





@operator_required

@require_http_methods(["GET", "POST"])

def editar_actividad(request, pk):

    obj = get_object_or_404(activity_scope(request.user), pk=pk)

    form = ActividadDirectorForm(request.POST if request.method == "POST" else None, instance=obj, user=request.user)

    if request.method == "POST" and form.is_valid():

        try:

            saved = save_activity(request.user, form, obj.persona)

            messages.success(request, "Cargo actualizado. Quedó pendiente de validación.")

            return redirect("bnhpersonas:personas_detail", pk=saved.persona_id)

        except (ValidationError, IntegrityError, OperationalError) as exc:

            errors_to_form(form, exc)

    schedules = HorarioActividad.objects.filter(actividad_sede__actividad=obj, actividad_sede__cueanexo=obj.cueanexo).order_by("dia", "hora_desde")

    return render(request, "bnh/personas/form.html", {"form": form, "actividad": obj, "persona": obj.persona, "horarios": schedules, "horario_form": HorarioActividadForm(), "title": "Editar cargo y horarios"})





@operator_required

@require_http_methods(["GET", "POST"])

def accion_actividad(request, pk, accion):

    actions = {"eliminar": "ELIMINAR", "restaurar": "RESTAURAR", "validar": "VALIDAR", "observar": "OBSERVAR"}

    from django.http import Http404

    if accion not in actions:

        raise Http404

    obj = get_object_or_404(activity_scope(request.user, include_deleted=True), pk=pk)

    form = ConfirmacionForm(request.POST if request.method == "POST" else None, initial={"version": obj.version})

    if request.method == "POST" and form.is_valid():

        try:

            changed = change_activity(request.user, pk, actions[accion], form.cleaned_data["version"], form.cleaned_data["motivo"])

            messages.success(request, "Operación registrada correctamente.")

            return redirect("bnhpersonas:personas_detail", pk=changed.persona_id)

        except (ValidationError, IntegrityError, OperationalError) as exc:

            if isinstance(exc, ValidationError):

                logger.warning(

                    "BNH validación rechazada | pk=%s | accion=%s | error=%s",

                    pk, accion, exc,

                )

            else:

                logger.exception(

                    "BNH acción actividad fallida | pk=%s | accion=%s | user=%s",

                    pk, accion, getattr(request.user, "pk", None),

                )

            errors_to_form(form, exc)

    return render(request, "bnh/personas/confirm.html", {"form": form, "title": f"{accion.capitalize()} cargo", "obj": obj, "persona": obj.persona})





@operator_required

@require_http_methods(["GET", "POST"])

def eliminar_persona(request, pk):

    obj = get_object_or_404(person_scope(request.user), pk=pk)

    form = ConfirmacionForm(request.POST if request.method == "POST" else None, initial={"version": obj.version})

    if request.method == "POST" and form.is_valid():

        try:

            archive_person(request.user, pk, form.cleaned_data["version"], form.cleaned_data["motivo"])

            messages.success(request, "Ficha personal archivada; se conserva su historial.")

            if is_admin(request.user):
                return redirect("bnhpersonas:personas_detail", pk=pk)

            return redirect("bnhpersonas:personas_list")

        except (ValidationError, IntegrityError, OperationalError) as exc:

            errors_to_form(form, exc)

    return render(request, "bnh/personas/confirm.html", {"form": form, "persona": obj, "title": "Archivar ficha personal", "archive": True})


@operator_required
@require_http_methods(["GET", "POST"])
def reactivar_persona(request, pk):
    """Reactiva una ficha archivada. Solo disponible para administradores BNH."""
    if not is_admin(request.user):
        raise PermissionDenied("Solo un administrador puede reactivar una ficha personal archivada.")

    obj = get_object_or_404(Personas.objects, pk=pk, archivada=True)
    form = ConfirmacionForm(
        request.POST if request.method == "POST" else None,
        initial={"version": obj.version},
    )

    if request.method == "POST" and form.is_valid():
        try:
            restore_person(
                request.user,
                pk,
                form.cleaned_data["version"],
                form.cleaned_data["motivo"],
            )
            messages.success(
                request,
                "Ficha personal reactivada. El historial se conserva y los cargos dados de baja permanecen cerrados.",
            )
            return redirect("bnhpersonas:personas_detail", pk=pk)
        except (Conflict, ValidationError, IntegrityError, OperationalError) as exc:
            errors_to_form(form, exc)

    return render(
        request,
        "bnh/personas/confirm.html",
        {
            "form": form,
            "persona": obj,
            "title": "Reactivar ficha personal",
            "restore": True,
        },
    )


@operator_required

@require_POST

def agregar_horario(request, actividad_id):

    form = HorarioActividadForm(request.POST)

    if form.is_valid():

        try:

            add_schedule(request.user, actividad_id, form, form.cleaned_data.get("version"))

            messages.success(request, "Horario agregado.")

            return redirect("bnhpersonas:editar_actividad", pk=actividad_id)

        except (ValidationError, IntegrityError, OperationalError) as exc:

            errors_to_form(form, exc)

    activity = get_object_or_404(activity_scope(request.user), pk=actividad_id)

    return render(request, "bnh/personas/schedule_form.html", {"form": form, "actividad": activity, "title": "Corregir horario"}, status=400)





@operator_required

@require_POST

def eliminar_horario(request, pk):

    form = ConfirmacionForm(request.POST)

    if not form.is_valid():

        return JsonResponse({"ok": False, "errors": form.errors}, status=400)

    try:

        activity = delete_schedule(request.user, pk, form.cleaned_data["version"], form.cleaned_data["motivo"])

        return redirect("bnhpersonas:editar_actividad", pk=activity.pk)

    except (ValidationError, IntegrityError, OperationalError) as exc:

        return JsonResponse({"ok": False, "errors": getattr(exc, "messages", [str(exc)])}, status=409)





@operator_required

@require_GET

def horarios_actividad(request, actividad_id):

    return redirect("bnhpersonas:editar_actividad", pk=get_object_or_404(activity_scope(request.user), pk=actividad_id).pk)





@operator_required

@require_GET

def buscar_persona(request):

    cuil = request.GET.get("cuil", "")

    person = person_scope(request.user).filter(cuil=cuil).first() if len(cuil) == 11 else None

    return JsonResponse({"existe": bool(person), "id": person.pk if person else None})





@operator_required

@require_GET

@user_rate_limit("verificar_persona_alta", limit=60, window_seconds=60)

def verificar_persona_alta(request):

    """

    Verifica si un CUIL ya existe antes de permitir un alta nueva.



    No expone datos personales de una persona fuera del ámbito del usuario.

    Sólo informa el estado necesario para orientar el flujo:

      - NUEVA: puede continuar con Alta de personal.

      - VISIBLE: ya está en el ámbito; debe usar Ver ficha / Agregar cargo.

      - VINCULAR: existe, pero aún no está vinculada a una institución del usuario.

      - ARCHIVADA: requiere revisión administrativa.

    """

    cuil = re.sub(r"\D", "", request.GET.get("cuil", ""))



    try:

        validar_cuil(cuil)

    except ValidationError as exc:

        return JsonResponse(

            {

                "ok": False,

                "estado": "INVALIDA",

                "mensaje": exc.messages[0] if exc.messages else "CUIL inválido.",

            },

            status=400,

        )



    person = Personas.objects.filter(cuil=cuil).only(

        "id", "cuil", "archivada"

    ).first()



    if not person:

        return JsonResponse(

            {

                "ok": True,

                "existe": False,

                "estado": "NUEVA",

                "mensaje": "CUIL disponible para una nueva alta.",

            }

        )



    if person.archivada:

        return JsonResponse(

            {

                "ok": True,

                "existe": True,

                "estado": "ARCHIVADA",

                "mensaje": (

                    "La persona ya existe pero su ficha está archivada. "

                    "Solicite revisión antes de crear una nueva ficha."

                ),

            }

        )



    visible = person_scope(request.user).filter(pk=person.pk).exists()



    if visible:

        return JsonResponse(

            {

                "ok": True,

                "existe": True,

                "estado": "VISIBLE",

                "id": person.pk,

                "mensaje": (

                    "La persona ya está registrada y se encuentra dentro de su ámbito. "

                    "Ingrese a su ficha para agregar o editar cargos."

                ),

                "accion_url": reverse(

                    "bnhpersonas:personas_detail",

                    kwargs={"pk": person.pk},

                ),

                "accion_label": "Ver ficha",

            }

        )



    return JsonResponse(

        {

            "ok": True,

            "existe": True,

            "estado": "VINCULAR",

            "mensaje": (

                "La persona ya está registrada en BNH Personal Educativo. "

                "Utilice “Vincular existente” para agregar una nueva vinculación institucional."

            ),

            "accion_url": reverse("bnhpersonas:vincular_persona"),

            "accion_label": "Vincular existente",

        }

    )





@operator_required

@require_GET

@user_rate_limit("buscar_persona_vincular", limit=60, window_seconds=60)

def buscar_persona_vincular(request):

    """

    Busca una persona existente por CUIL para el flujo de vinculación.



    No usa person_scope(), porque precisamente este flujo permite vincular

    una persona que ya existe en BNH pero todavía no está en el ámbito del

    directivo. No devuelve cargos ni información de otras instituciones.

    """

    cuil = re.sub(r"\D", "", request.GET.get("cuil", ""))



    try:

        validar_cuil(cuil)

    except ValidationError as exc:

        return JsonResponse(

            {

                "ok": False,

                "existe": False,

                "mensaje": exc.messages[0] if exc.messages else "CUIL inválido.",

            },

            status=400,

        )



    person = Personas.objects.filter(cuil=cuil).only(

        "id", "cuil", "dni", "apellido", "nombre", "archivada"

    ).first()



    if not person:

        return JsonResponse(

            {

                "ok": True,

                "existe": False,

                "mensaje": (

                    "No se encontró personal registrado con ese CUIL. "

                    "Si corresponde, utilice “Alta de personal”."

                ),

                "alta_url": reverse("bnhpersonas:carga_personal"),

            }

        )



    if person.archivada:

        return JsonResponse(

            {

                "ok": True,

                "existe": False,

                "archivada": True,

                "mensaje": (

                    "La persona existe pero su ficha está archivada. "

                    "Solicite revisión antes de vincularla."

                ),

            }

        )



    visible = person_scope(request.user).filter(pk=person.pk).exists()



    return JsonResponse(

        {

            "ok": True,

            "existe": True,

            "id": person.pk,

            "cuil": person.cuil,

            "dni": person.dni or "",

            "apellido": person.apellido,

            "nombre": person.nombre,

            "visible": visible,

            "detalle_url": (

                reverse("bnhpersonas:personas_detail", kwargs={"pk": person.pk})

                if visible

                else ""

            ),

        }

    )





@operator_required

@require_POST

def guardar_persona_ajax(request):

    # Compatibilidad de URL: la creación se realiza con primer cargo atómico.

    pk = request.POST.get("persona_id")

    if not pk or not pk.isdecimal():

        return JsonResponse({"ok": False, "mensaje": "Use Alta de personal y primer cargo."}, status=400)

    person = get_object_or_404(person_scope(request.user), pk=pk)

    form = PersonaForm(request.POST, instance=person)

    if form.is_valid():

        try:

            obj = save_person(request.user, form)

            return JsonResponse({"ok": True, "id": obj.pk, "version": obj.version})

        except (ValidationError, IntegrityError, OperationalError) as exc:

            errors_to_form(form, exc)

    return JsonResponse({"ok": False, "errors": form.errors}, status=400)





def integer_param(request, name, *, allow_negative=False):

    """
    Lee un parámetro entero de la query string.

    Por defecto sólo admite enteros no negativos. Algunos valores técnicos
    de BNH, como -2 = NO CORRESPONDE, necesitan admitir signo negativo de
    manera explícita para no relajar la validación del resto de parámetros.
    """

    value = request.GET.get(name, "")

    if value in (None, ""):
        return None

    value = str(value).strip()

    if not value or not value.isascii() or len(value) > 10:
        raise ValidationError("Parámetro inválido.")

    if allow_negative:
        numeric = value[1:] if value.startswith("-") else value
        if not numeric or not numeric.isdecimal():
            raise ValidationError("Parámetro inválido.")
    elif not value.isdecimal():
        raise ValidationError("Parámetro inválido.")

    return int(value)





@operator_required

@require_GET

def filtrar_datos_actividad(request):

    """

    CIRCUITO CARGO / CEIC.



    El Tipo de personal proviene de tipo_personal.

    La lógica CEIC histórica se mantiene sin cambios.

    """

    try:

        modalidad = integer_param(request, "modalidad")

        nivel = integer_param(request, "nivel")

        tipo_personal = integer_param(request, "tipo_personal")



        if tipo_personal and not TipoPersonal.objects.filter(

            c_tpersonal=tipo_personal

        ).exists():

            raise ValidationError("Tipo de personal inválido.")



        es_no_docente = tipo_personal == 2



        if es_no_docente:

            from .models import NomencladorCeic

            ceic = (

                NomencladorCeic.objects

                .filter(c_niv__gte=1023, c_niv__lte=1025)

                .order_by("c_niv", "descripcion")

            )

            niveles = available_levels(modalidad)

            return JsonResponse({

                "tipo_personal": tipo_personal,

                "modo": "NO_DOCENTE",

                "niveles": list(niveles.values("c_nivel", "descrip_nivel")),

                "ceic": list(ceic.values("c_ceic", "c_niv", "descripcion")),

                "grado": [],

                "secciones": [],

                "dependencia_seccion": "no_aplica",

            })



        niveles = available_levels(modalidad)

        ceic, _, _ = activity_catalogs(

            modalidad,

            nivel,

            tipo_personal=tipo_personal,

        )



        aplica_ceic = ceic_aplica(

            modalidad,

            nivel,

            tipo_personal=tipo_personal,

        ) if modalidad and nivel else True



        return JsonResponse({

            "tipo_personal": tipo_personal,

            "modo": "DOCENTE",

            "niveles": list(niveles.values("c_nivel", "descrip_nivel")),

            "ceic": list(ceic.values("c_ceic", "c_niv", "descripcion")),

            "ceic_aplica": aplica_ceic,

            "ceic_motivo": (

                "NO_CORRESPONDE"

                if not aplica_ceic

                else ""

            ),

            "grado": [],

            "secciones": [],

            "dependencia_seccion": "circuito_curricular_independiente",

        })



    except ValidationError as exc:

        return JsonResponse({"error": exc.messages}, status=400)





@operator_required

@require_GET

def filtrar_datos_curriculares(request):

    """

    CIRCUITO CURRICULAR NUEVO.



    No modifica ni consulta la configuración del Cargo / CEIC.

    """

    try:

        modalidad = integer_param(request, "modalidad_curricular")

        nivel = integer_param(request, "nivel_curricular")

        # La titulación admite el valor técnico -2 = NO CORRESPONDE.

        titulacion = integer_param(

            request,

            "titulacion",

            allow_negative=True,

        )
        raw_multi = request.GET.getlist("titulaciones")

        if len(raw_multi) == 1 and "," in raw_multi[0]:

            raw_multi = raw_multi[0].split(",")

        titulaciones = []

        for raw in raw_multi:

            try:

                value = int(raw)

            except (TypeError, ValueError):

                continue

            if value not in titulaciones:

                titulaciones.append(value)

        tipo_personal = integer_param(request, "tipo_personal")



        if tipo_personal and not TipoPersonal.objects.filter(

            c_tpersonal=tipo_personal

        ).exists():

            raise ValidationError("Tipo de personal inválido.")



        data = curricular_catalogs(

            modalidad,

            nivel,

            titulacion,

            titulaciones_seleccionadas=titulaciones,

            tipo_personal=tipo_personal,

        )



        return JsonResponse({

            "tipo_personal": tipo_personal,

            "modo": "NO_DOCENTE" if tipo_personal == 2 else "DOCENTE",

            "niveles": list(

                data["niveles"].values("c_nivel", "descripcion")

            ),

            "titulaciones": data["titulaciones"],

            "fuente_titulacion": data["fuente_titulacion"],

            "espacios": list(

                data["espacios"].values(

                    "id",

                    "id_espacio_curricular",

                    "id_titulacion",

                    "nombre",

                )

            ),

            "grados": list(

                data["grados"].values(

                    "c_grado_anio",

                    "nombre_grado_anio",

                )

            ),

            "secciones": list(

                data["secciones"].values(

                    "c_seccion",

                    "nombre_seccion",

                )

            ),

        })



    except ValidationError as exc:

        return JsonResponse({"error": exc.messages}, status=400)





@operator_required

@require_GET

def filtrar_condiciones_actividad(request):

    """

    Filtra condicion_actividad_nombre por:

      - tipo_personal.c_tpersonal

      - situacion_revista.cod_sitrev

    """

    try:

        tipo_personal = integer_param(request, "tipo_personal")

        situacion_revista = integer_param(request, "sit_revista")



        if tipo_personal and not TipoPersonal.objects.filter(

            c_tpersonal=tipo_personal

        ).exists():

            raise ValidationError("Tipo de personal inválido.")



        if situacion_revista and not SituacionServicio.objects.filter(

            cod_sitrev=situacion_revista

        ).exists():

            raise ValidationError("Situación de revista inválida.")



        qs = condiciones_actividad(

            tipo_personal,

            situacion_revista,

        )



        condiciones = [

            {

                "id": obj.pk,

                "c_nomen": obj.c_nomen,

                "denominacion": obj.denominacion,

                "encuadre": obj.encuadre,

                "label": str(obj),

            }

            for obj in qs

        ]



        # No se amplía el catálogo cuando la combinación exacta no existe:

        # una condición válida depende de Tipo de personal + Situación de revista.

        # En cambio se devuelve un diagnóstico explícito para evitar un desplegable

        # vacío sin explicación.

        warning = ""

        if tipo_personal and situacion_revista and not condiciones:

            warning = (

                "No hay condiciones de actividad configuradas para el Tipo de personal "

                "y la Situación de revista seleccionados. Revise el catálogo "

                "condicion_actividad_nombre."

            )



        return JsonResponse({

            "condiciones": condiciones,

            "warning": warning,

            "tipo_personal": tipo_personal,

            "sit_revista": situacion_revista,

        })



    except ValidationError as exc:

        return JsonResponse({"error": exc.messages}, status=400)





@operator_required

@require_GET

def filtrar_localidades(request):

    try:

        province = integer_param(request, "provincia")

    except ValidationError:

        return JsonResponse({"error": "Provincia inválida"}, status=400)

    return JsonResponse(list(Localidades.objects.filter(c_provincia_id=province).values("c_localidad", "descrip_localidad")) if province else [], safe=False)





@operator_required

@require_GET

def buscar_codigos_area(request):

    from django.db.models import CharField

    from django.db.models.functions import Cast

    qs = CodAreasTelefonos.objects.annotate(code_text=Cast("codigo", CharField())).filter(code_text__startswith=request.GET.get("q", "")[:10]).order_by("codigo", "pk")[:20]

    return JsonResponse([{"id": x.pk, "label": str(x)} for x in qs], safe=False)





def legacy_catalog(key):

    @operator_required

    @require_GET

    def view(request):

        response = filtrar_datos_actividad(request)

        if response.status_code != 200:

            return response

        import json

        return JsonResponse(json.loads(response.content)[key], safe=False)

    return view



filtrar_ceic = legacy_catalog("ceic")

filtrar_grado_anio = legacy_catalog("grado")

filtrar_secciones = legacy_catalog("secciones")
