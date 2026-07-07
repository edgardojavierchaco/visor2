"""Vistas y endpoints AJAX para la carga integral de BNH Alumnos.

La pantalla trabaja como una aplicacion de una sola carga: renderiza catalogos,
arma colecciones temporales en JavaScript y envia un unico JSON para guardar
alumno, obras sociales, discapacidades, planes sociales y tutores.
"""

import json
import re

from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST

# Catálogos externos reutilizados por la pantalla. Se consultan desde
# bnhpersonas para no duplicar datos maestros dentro del módulo alumnos.
from apps.bnhpersonas.models import (
    DocumentoTipo,
    Provincias,
    Localidades,
    Nacionalidad,
    Pais,
    Sexo,
    EstadosCiviles,
    RelacionParentesco,
    TipoPlanesSociales,
    NivelFormacion,
    TipoOS,
    TipoComunidadOriginaria,
    TipoLenguaOriginaria,
    TipoDiscapacidad,
    CodAreasTelefonos,
    validar_cuil,
)

from .models import (
    Alumno,
    Tutor,
    CatalogoObraSocial,
    CatalogoSinoTipo,
)
from .forms import (
    AlumnoForm,
    TutorForm,
    ObraSocialForm,
    DiscapacidadForm,
    PlanesSocialesForm,
    ParentalForm,
    form_errors_to_json,
    payload_tiene_datos,
    validar_y_guardar,
)
from .permisos import bnh_alumnos_required


def _solo_digitos(valor):
    """Devuelve solo los dígitos de un valor recibido desde formulario o querystring."""

    return re.sub(r"\D", "", str(valor or ""))


def _validar_cuil_para_ui(valor, nombre="CUIL"):
    """Normaliza y valida CUIL para respuestas claras hacia la interfaz."""

    cuil = _solo_digitos(valor)
    if not cuil:
        raise ValidationError(f"{nombre} es obligatorio.")
    if len(cuil) != 11:
        raise ValidationError(f"{nombre} debe tener 11 dígitos.")
    validar_cuil(cuil)
    return cuil


def _catalogo(modelo):
    """Obtiene opciones de catálogo sin bloquear la pantalla si falla una consulta."""

    try:
        return list(modelo.objects.all())
    except Exception:
        return []


def _fecha_iso(valor):
    """Convierte fechas de modelo al formato ISO que espera el frontend."""

    if not valor:
        return ""
    return valor.isoformat()


def _decimal_text(valor):
    """Serializa decimales como texto para no perder formato en JSON."""

    if valor is None:
        return ""
    return str(valor)


def _fk_id(objeto, campo):
    """Extrae el id crudo de un ForeignKey para seleccionar opciones en HTML."""

    return getattr(objeto, f"{campo}_id", "") or ""


def _telefono_label(objeto):
    """Arma una etiqueta legible con codigo de area y numero local."""

    if not getattr(objeto, "telefono", None) or not getattr(objeto, "codigo_area_id", None):
        return ""
    return f"({objeto.codigo_area.codigo}) {objeto.telefono}"


def _error_json(exc):
    """Unifica errores Django para devolverlos en JsonResponse."""

    if hasattr(exc, "message_dict"):
        return exc.message_dict
    if hasattr(exc, "messages"):
        return exc.messages
    return str(exc)


def _alumno_payload(alumno):
    """Arma el JSON de alumno usado para autocompletar el formulario."""

    return {
        "id": alumno.id,
        "apellidos": alumno.apellidos,
        "nombres": alumno.nombres,
        "tipo_doc": _fk_id(alumno, "tipo_doc"),
        "nro_doc": alumno.nro_doc,
        "cuil": alumno.cuil or "",
        "fecha_nacimiento": _fecha_iso(alumno.fecha_nacimiento),
        "sexo": _fk_id(alumno, "sexo"),
        "prov_nacimiento": _fk_id(alumno, "prov_nacimiento"),
        "lugar_nacimiento": alumno.lugar_nacimiento or "",
        "loc_nacimiento": _fk_id(alumno, "loc_nacimiento"),
        "pais_nacimiento": _fk_id(alumno, "pais_nacimiento"),
        "prov_residencia": _fk_id(alumno, "prov_residencia"),
        "pais_residencia": _fk_id(alumno, "pais_residencia"),
        "loc_residencia": _fk_id(alumno, "loc_residencia"),
        "est_civil": _fk_id(alumno, "est_civil"),
        "pertenece_pueblo_indigena": _fk_id(alumno, "pertenece_pueblo_indigena"),
        "comunidad_originaria": _fk_id(alumno, "comunidad_originaria"),
        "lengua_originaria": _fk_id(alumno, "lengua_originaria"),
        "tiene_discapacidad": _fk_id(alumno, "tiene_discapacidad"),
        "tiene_ppi": _fk_id(alumno, "tiene_ppi"),
        "codigo_area": _fk_id(alumno, "codigo_area"),
        "codigo_area_codigo": alumno.codigo_area.codigo if alumno.codigo_area_id else "",
        "telefono": alumno.telefono or "",
        "telefono_normalizado": alumno.telefono_normalizado or "",
        "telefono_label": _telefono_label(alumno),
        "es_celular": alumno.es_celular,
        "whatsapp": alumno.whatsapp,
        "email": alumno.email,
        "talla": _decimal_text(alumno.talla),
        "peso": _decimal_text(alumno.peso),
        "observaciones": alumno.observaciones,
    }


def _tutor_payload(tutor):
    """Arma el JSON de tutor usado por la búsqueda y por relaciones parentales."""

    return {
        "id": tutor.id,
        "cuil_tutor": tutor.cuil_tutor,
        "apellidos": tutor.apellidos,
        "nombres": tutor.nombres,
        "tipo_doc": _fk_id(tutor, "tipo_doc"),
        "nro_doc": tutor.nro_doc,
        "fecha_nac": _fecha_iso(tutor.fecha_nac),
        "nacionalidad": _fk_id(tutor, "nacionalidad"),
        "pais_nac": _fk_id(tutor, "pais_nac"),
        "nivel_formacion": _fk_id(tutor, "nivel_formacion"),
        "ocupacion": tutor.ocupacion,
        "prov_resid": _fk_id(tutor, "prov_resid"),
        "loc_resid": _fk_id(tutor, "loc_resid"),
        "cod_postal": tutor.cod_postal,
        "calle": tutor.calle,
        "nro": tutor.nro,
        "piso": tutor.piso,
        "dpto": tutor.dpto,
        "mail": tutor.mail,
        "codigo_area": _fk_id(tutor, "codigo_area"),
        "codigo_area_codigo": tutor.codigo_area.codigo if tutor.codigo_area_id else "",
        "telefono": tutor.telefono or "",
        "telefono_normalizado": tutor.telefono_normalizado or "",
        "telefono_label": _telefono_label(tutor),
        "es_celular": tutor.es_celular,
        "whatsapp": tutor.whatsapp,
    }


def _relaciones_payload(alumno):
    """Serializa relaciones hijas sin bloquear el autocompletado principal."""

    obras = []
    try:
        for item in alumno.obras_sociales.select_related("tipo_obra", "nombre_obra").all():
            obras.append({
                "tipo_obra": _fk_id(item, "tipo_obra"),
                "tipo_obra_label": str(item.tipo_obra),
                "nombre_obra": _fk_id(item, "nombre_obra"),
                "nombre_obra_label": str(item.nombre_obra),
                "fecha_inicio": _fecha_iso(item.fecha_inicio),
                "fecha_fin": _fecha_iso(item.fecha_fin),
                "descripcion": item.descripcion,
                "estado": item.estado,
            })
    except Exception:
        obras = []

    discapacidades = []
    try:
        for item in alumno.discapacidades.select_related("id_discapacidad").all():
            discapacidades.append({
                "id_discapacidad": _fk_id(item, "id_discapacidad"),
                "id_discapacidad_label": str(item.id_discapacidad),
                "fecha_inicio": _fecha_iso(item.fecha_inicio),
                "fecha_fin": _fecha_iso(item.fecha_fin),
                "porcentaje": _decimal_text(item.porcentaje),
                "certificado_cud": item.certificado_cud,
                "observaciones": item.observaciones,
            })
    except Exception:
        discapacidades = []

    planes = []
    try:
        for item in alumno.planes_sociales.select_related("id_beneficio").all():
            planes.append({
                "id_beneficio": _fk_id(item, "id_beneficio"),
                "id_beneficio_label": str(item.id_beneficio),
                "descripcion": item.descripcion,
                "fecha_desde": _fecha_iso(item.fecha_desde),
                "fecha_hasta": _fecha_iso(item.fecha_hasta),
                "monto": _decimal_text(item.monto),
                "estado": item.estado,
                "observaciones": item.observaciones,
            })
    except Exception:
        planes = []

    tutores = []
    try:
        for item in alumno.parentales.select_related("id_tutor", "parentesco").all():
            tutor_data = _tutor_payload(item.id_tutor)
            tutor_data.update({
                "parentesco": _fk_id(item, "parentesco"),
                "parentesco_label": str(item.parentesco),
                "parental_observaciones": item.observaciones,
            })
            tutores.append(tutor_data)
    except Exception:
        tutores = []

    return {
        "obras_sociales": obras,
        "discapacidades": discapacidades,
        "planes_sociales": planes,
        "tutores": tutores,
    }

@bnh_alumnos_required
def carga_alumno_view(request):
    """Renderiza la pantalla de carga con todos los catálogos necesarios."""

    raw_next_url = (request.GET.get("next") or "").strip()
    next_url = ""
    if raw_next_url and url_has_allowed_host_and_scheme(
        raw_next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = raw_next_url

    # El template recibe catálogos completos porque la pantalla filtra y arma
    # varias relaciones en el navegador antes de enviar el POST final.
    context = {
        "cuil_inicial": _solo_digitos(request.GET.get("cuil")),
        "next_url": next_url,
        "return_label": request.GET.get("return_label") or "Volver",
        "tipos_documento": _catalogo(DocumentoTipo),
        "provincias": _catalogo(Provincias),
        "localidades": _catalogo(Localidades),
        "nacionalidades": _catalogo(Nacionalidad),
        "paises": _catalogo(Pais),
        "sexos": _catalogo(Sexo),
        "parentescos": _catalogo(RelacionParentesco),
        "beneficios": _catalogo(TipoPlanesSociales),
        "niveles_formacion": _catalogo(NivelFormacion),
        "tipos_obra_social": _catalogo(TipoOS),
        "catalogo_obras_sociales": _catalogo(CatalogoObraSocial),
        "catalogo_sino_tipo": _catalogo(CatalogoSinoTipo),
        "estados_civiles": _catalogo(EstadosCiviles),
        "comunidades_originarias": _catalogo(TipoComunidadOriginaria),
        "lenguas_originarias": _catalogo(TipoLenguaOriginaria),
        "tipos_discapacidad": _catalogo(TipoDiscapacidad),
        "codigos_area": _catalogo(CodAreasTelefonos),
    }
    return render(request, "bnhalumnos/carga_alumno.html", context)


@bnh_alumnos_required
@require_GET
def buscar_alumno_por_cuil(request):
    """Busca un alumno por CUIL y devuelve sus datos y relaciones asociadas."""

    try:
        cuil = _validar_cuil_para_ui(request.GET.get("cuil"), "CUIL del alumno")
        alumno = Alumno.objects.filter(cuil=cuil).first()
        if not alumno:
            # exists=False permite que el frontend sepa que el CUIL es válido
            # y que debe iniciar una carga nueva en lugar de autocompletar.
            return JsonResponse({"exists": False, "cuil": cuil})
        data = {"exists": True, "alumno": _alumno_payload(alumno)}
        data.update(_relaciones_payload(alumno))
        return JsonResponse(data)
    except ValidationError as exc:
        return JsonResponse({"exists": False, "valid": False, "error": _error_json(exc)}, status=400)
    except Exception as exc:
        return JsonResponse({"exists": False, "valid": False, "error": str(exc)}, status=500)


@bnh_alumnos_required
@require_GET
def buscar_tutor_por_cuil(request):
    """Busca un tutor por CUIL para autocompletar el modal de tutores."""

    try:
        cuil = _validar_cuil_para_ui(request.GET.get("cuil"), "CUIL del tutor")
        tutor = Tutor.objects.filter(cuil_tutor=cuil).first()
        if not tutor:
            # El tutor puede no existir todavía; en ese caso el modal queda
            # disponible para que el usuario complete los campos manualmente.
            return JsonResponse({"exists": False, "cuil": cuil})
        return JsonResponse({"exists": True, "tutor": _tutor_payload(tutor)})
    except ValidationError as exc:
        return JsonResponse({"exists": False, "valid": False, "error": _error_json(exc)}, status=400)
    except Exception as exc:
        return JsonResponse({"exists": False, "valid": False, "error": str(exc)}, status=500)


def _guardar_form(form, prefijo=None):
    """Valida y guarda un ModelForm, con prefijo para errores de listas."""

    if form.is_valid():
        # form.save() no esta definido en este archivo: lo aporta Django ModelForm.
        # Como cada Form tiene Meta.model, Django sabe que tabla/modelo guardar.
        return form.save()

    errores = form_errors_to_json(form)
    if prefijo:
        errores = {f"{prefijo}.{campo}": mensajes for campo, mensajes in errores.items()}
    raise ValidationError(errores)


def _guardar_alumno_form(alumno, data, usuario=None):
    """Guarda el alumno delegando limpieza y validacion en AlumnoForm."""

    data = dict(data)
    if data.get("pueblo_indigena") and not data.get("comunidad_originaria"):
        data["comunidad_originaria"] = data.get("pueblo_indigena")
    data.pop("pueblo_indigena", None)
    data.pop("discapacidad", None)

    if str(data.get("pertenece_pueblo_indigena") or "") != str(CatalogoSinoTipo.SI):
        data["comunidad_originaria"] = ""
    if not data.get("telefono") or not data.get("codigo_area"):
        data["whatsapp"] = False
        data["es_celular"] = False
    elif not data.get("es_celular"):
        data["whatsapp"] = False

    if usuario and getattr(usuario, "is_authenticated", False):
        alumno.usuario_modificacion = usuario
        alumno.cuil_usuario_modificacion = _solo_digitos(getattr(usuario, "username", ""))

    # instance=alumno decide si el form actualiza un Alumno existente o crea uno nuevo.
    # validar_y_guardar() termina llamando a form.save(), que usa models.Alumno y el ORM de Django.
    return validar_y_guardar(AlumnoForm(data, instance=alumno))


def _guardar_tutor_form(tutor, data, prefijo=None):
    """Guarda el tutor delegando limpieza y validacion en TutorForm."""

    data = dict(data)
    if not data.get("es_celular"):
        data["whatsapp"] = False

    # Igual que AlumnoForm: TutorForm es un ModelForm conectado a models.Tutor.
    return _guardar_form(TutorForm(data, instance=tutor), prefijo)


def _guardar_obras_sociales(alumno, items):
    """Reemplaza obras sociales del alumno por la lista vigente del payload."""

    # Las relaciones se reemplazan completas: el frontend envia la lista vigente.
    # Al asignar id_alumno=alumno.pk, cada registro queda asociado al alumno guardado.
    alumno.obras_sociales.all().delete()
    campos = ["tipo_obra", "nombre_obra", "fecha_inicio", "fecha_fin", "descripcion"]
    for indice, item in enumerate(items):
        if not payload_tiene_datos(item, campos):
            continue
        data = dict(item)
        data["id_alumno"] = alumno.pk
        _guardar_form(ObraSocialForm(data), f"obras_sociales[{indice}]")


def _guardar_discapacidades(alumno, items):
    """Reemplaza detalles de discapacidad respetando el indicador principal."""

    # Misma mecanica: borrar relaciones previas y guardar las actuales con ModelForm.
    alumno.discapacidades.all().delete()
    if alumno.tiene_discapacidad_id != CatalogoSinoTipo.SI:
        return

    campos = ["id_discapacidad", "fecha_inicio", "fecha_fin", "porcentaje", "certificado_cud", "observaciones"]
    for indice, item in enumerate(items):
        if not payload_tiene_datos(item, campos):
            continue
        data = dict(item)
        data["id_alumno"] = alumno.pk
        _guardar_form(DiscapacidadForm(data), f"discapacidades[{indice}]")


def _guardar_planes_sociales(alumno, items):
    """Reemplaza planes sociales del alumno por los enviados desde el frontend."""

    # PlanesSocialesForm tiene Meta.model = PlanesSociales; _guardar_form() valida y hace save().
    alumno.planes_sociales.all().delete()
    campos = ["id_beneficio", "descripcion", "fecha_desde", "fecha_hasta", "monto", "observaciones"]
    for indice, item in enumerate(items):
        if not payload_tiene_datos(item, campos):
            continue
        data = dict(item)
        data["id_alumno"] = alumno.pk
        _guardar_form(PlanesSocialesForm(data), f"planes_sociales[{indice}]")


def _guardar_tutores_parentales(alumno, items):
    """Guarda tutores y recrea las relaciones Parental del alumno."""

    # Guarda dos cosas por cada tutor recibido:
    # 1) Tutor: persona adulta, buscada por CUIL/DNI o creada si no existe.
    # 2) Parental: relacion entre ese tutor y el alumno.
    alumno.parentales.all().delete()
    campos = [
        "cuil_tutor",
        "apellidos",
        "nombres",
        "tipo_doc",
        "nro_doc",
        "parentesco",
    ]
    for indice, item in enumerate(items):
        if not payload_tiene_datos(item, campos):
            continue

        cuil_tutor = _validar_cuil_para_ui(item.get("cuil_tutor"), "CUIL del tutor")
        tutor = Tutor.objects.filter(cuil_tutor=cuil_tutor).first()
        if tutor is None and item.get("nro_doc"):
            tutor = Tutor.objects.filter(nro_doc=item.get("nro_doc")).first()
        if tutor is None:
            tutor = Tutor()

        tutor = _guardar_tutor_form(tutor, item, f"tutores[{indice}]")
        parental_data = dict(item)
        parental_data["id_alumno"] = alumno.pk
        parental_data["id_tutor"] = tutor.pk
        parental_data["observaciones"] = item.get("parental_observaciones", "")
        # ParentalForm guarda la fila intermedia que une alumno + tutor + parentesco.
        _guardar_form(ParentalForm(parental_data), f"tutores[{indice}].parental")


@bnh_alumnos_required
@require_POST
def guardar_carga_alumno(request):
    """Guarda alumno y relaciones en una operación atómica desde el formulario."""

    try:
        # El frontend no manda un form HTML tradicional: manda JSON con fetch().
        # request.body trae ese JSON crudo y json.loads() lo convierte en diccionario Python.
        payload = json.loads(request.body.decode("utf-8"))
        alumno_data = payload.get("alumno") or {}
        cuil_alumno = _validar_cuil_para_ui(alumno_data.get("cuil"), "CUIL del alumno")

        # Toda la carga se confirma o se revierte junta para evitar alumnos
        # guardados sin sus relaciones o relaciones sin alumno. Si cualquier
        # ModelForm o save() lanza ValidationError, transaction.atomic() revierte
        # las escrituras realizadas dentro del bloque.
        with transaction.atomic():
            # Primero se intenta reutilizar un alumno existente por CUIL; si no
            # aparece, se prueba documento como segunda llave de búsqueda.
            alumno = Alumno.objects.filter(cuil=cuil_alumno).first()
            if alumno is None and alumno_data.get("nro_doc"):
                alumno = Alumno.objects.filter(nro_doc=alumno_data.get("nro_doc")).first()
                if alumno and alumno.cuil:
                    cuil_existente = re.sub(r"\D", "", str(alumno.cuil or ""))
                    if cuil_existente and cuil_existente != cuil_alumno:
                        raise ValidationError({
                            "cuil": "El CUIL del alumno existente no puede modificarse desde esta pantalla."
                        })
            if alumno is None:
                # Objeto nuevo en memoria. Todavia no esta en la BD hasta que AlumnoForm haga form.save().
                alumno = Alumno()

            # Punto exacto donde se guarda/actualiza el alumno:
            # _guardar_alumno_form -> AlumnoForm -> validar_y_guardar -> form.save() -> models.Alumno -> BD.
            alumno = _guardar_alumno_form(alumno, alumno_data, request.user)

            # El frontend envia la coleccion completa vigente: se reemplazan
            # relaciones hijas dentro de la misma transaccion atomica. En la BD
            # se persiste el JSON ya desarmado en tablas relacionales.
            _guardar_obras_sociales(alumno, payload.get("obras_sociales") or [])
            _guardar_discapacidades(alumno, payload.get("discapacidades") or [])
            _guardar_planes_sociales(alumno, payload.get("planes_sociales") or [])
            _guardar_tutores_parentales(alumno, payload.get("tutores") or [])

        return JsonResponse({"ok": True, "alumno_id": alumno.id, "message": "Carga guardada correctamente."})
    except ValidationError as exc:
        return JsonResponse({"ok": False, "error": _error_json(exc)}, status=400)
    except Exception as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=500)
