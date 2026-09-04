from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from .domain.access import operator_required, person_scope, activity_scope, is_admin, is_regional
from .domain.catalogs import activity_catalogs, available_levels, expandir_rangos
from .forms import PersonaForm, ActividadDirectorForm, HorarioActividadForm, ConfirmacionForm, VincularPersonaForm
from .models import Personas, RegistroActividades, HorarioActividad, Localidades, CodAreasTelefonos
from .services.crud import save_person, save_activity, change_activity, archive_person, add_schedule, delete_schedule, Conflict


def errors_to_form(form, exc):
    if isinstance(exc, IntegrityError):
        form.add_error(None, "El registro ya existe o cambió mientras guardaba. Recargue y revise los datos.")
    else:
        for message in exc.messages:
            form.add_error(None, message)


@operator_required
@require_http_methods(["GET", "POST"])
def carga_personal(request, pk=None):
    person = get_object_or_404(person_scope(request.user), pk=pk) if pk else None
    form = PersonaForm(request.POST if request.method == "POST" else None, instance=person, prefix="persona")
    activity = None if person else ActividadDirectorForm(request.POST if request.method == "POST" else None, user=request.user, prefix="actividad")
    if request.method == "POST":
        valid_person = form.is_valid()
        valid_activity = activity.is_valid() if activity else True
        if valid_person and valid_activity:
            try:
                with transaction.atomic():
                    if activity:
                        form.authorized_cue = activity.cleaned_data["cueanexo"]
                    obj = save_person(request.user, form)
                    if activity:
                        activity.allow_link = True
                        save_activity(request.user, activity, obj)
                messages.success(request, "Personal guardado correctamente.")
                return redirect("bnhpersonas:personas_detail", pk=obj.pk)
            except (ValidationError, IntegrityError) as exc:
                errors_to_form(form, exc)
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
        except (ValidationError, IntegrityError) as exc:
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
            data = form.cleaned_data
            person = Personas.objects.filter(cuil=data["cuil"], dni=data["dni"], apellido__iexact=" ".join(data["apellido"].split()), archivada=False).first()
            if not person:
                form.add_error(None, "No se pudo vincular con esos datos. Verifique la identidad o solicite revisión al administrador.")
            else:
                try:
                    activity.allow_link = True
                    save_activity(request.user, activity, person)
                    messages.success(request, "Persona vinculada mediante el nuevo cargo.")
                    return redirect("bnhpersonas:personas_detail", pk=person.pk)
                except (ValidationError, IntegrityError) as exc:
                    errors_to_form(form, exc)
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
        except (ValidationError, IntegrityError) as exc:
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
        except ValidationError as exc:
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
            return redirect("bnhpersonas:personas_list")
        except ValidationError as exc:
            errors_to_form(form, exc)
    return render(request, "bnh/personas/confirm.html", {"form": form, "persona": obj, "title": "Archivar ficha personal", "archive": True})


@operator_required
@require_POST
def agregar_horario(request, actividad_id):
    form = HorarioActividadForm(request.POST)
    if form.is_valid():
        try:
            add_schedule(request.user, actividad_id, form, form.cleaned_data.get("version"))
            messages.success(request, "Horario agregado.")
            return redirect("bnhpersonas:editar_actividad", pk=actividad_id)
        except (ValidationError, IntegrityError) as exc:
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
    except ValidationError as exc:
        return JsonResponse({"ok": False, "errors": exc.messages}, status=409)


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
        except (ValidationError, IntegrityError) as exc:
            errors_to_form(form, exc)
    return JsonResponse({"ok": False, "errors": form.errors}, status=400)


def integer_param(request, name):
    value = request.GET.get(name, "")
    if not value:
        return None
    if not value.isascii() or not value.isdecimal() or len(value) > 9:
        raise ValidationError("Parámetro inválido.")
    return int(value)


@operator_required
@require_GET
def filtrar_datos_actividad(request):
    try:
        modalidad, nivel, grado = (integer_param(request, key) for key in ("modalidad", "nivel", "grado"))
        niveles = available_levels(modalidad)
        ceic, grados, secciones = activity_catalogs(modalidad, nivel, grado)
        return JsonResponse({"niveles": list(niveles.values("c_nivel", "descrip_nivel")), "ceic": list(ceic.values("c_ceic", "descripcion")), "grado": list(grados.values("c_grado_anio", "nombre_grado_anio")), "secciones": list(secciones.values("c_seccion", "nombre_seccion")), "dependencia_seccion": "modalidad_nivel_con_grado_valido"})
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
