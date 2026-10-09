import csv

from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Count
from django.http import (
    Http404,
    HttpResponse,
    StreamingHttpResponse,
)
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.utils import timezone
from django.conf import settings
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_GET, require_POST

from .domain.access import (
    activity_scope,
    get_user_cueanexos,
    is_admin,
    is_regional,
    operator_required,
    person_scope,
    scoped_offers,
)

from .domain.catalogs import titulacion_label

from .models import (
    EventoAuditoria,
    TipoPersonal,
    Personas,
    RegistroActividades,
    ConstanciaServicio,
)


# ============================================================
# FILTRADO DE ACTIVIDADES
# ============================================================

def filtered_activities(request, *, include_deleted=False, archived=False):

    qs = activity_scope(
        request.user,
        include_deleted=include_deleted,
    )

    if archived is not None:
        qs = qs.filter(persona__archivada=archived)

    for param, field in (
        (
            "cueanexo",
            "cueanexo",
        ),
        (
            "tipo_personal",
            "tipo_personal_id",
        ),
        (
            "estado",
            "estado",
        ),
        (
            "validacion",
            "validacion",
        ),
    ):

        if request.GET.get(param):

            qs = qs.filter(
                **{
                    field:
                        request.GET[
                            param
                        ][:100]
                }
            )

    search = (
        request.GET.get(
            "q",
            "",
        )
        .strip()
    )[:150]

    if search:

        for term in search.split()[:8]:

            qs = qs.filter(

                Q(
                    persona__apellido__icontains=
                        term
                )

                |

                Q(
                    persona__nombre__icontains=
                        term
                )

                |

                Q(
                    persona__dni__startswith=
                        term
                )

                |

                Q(
                    persona__cuil__startswith=
                        term
                )
            )

    return qs


# ============================================================
# LISTADO DE PERSONAS
# ============================================================

@method_decorator(
    operator_required,
    name="dispatch",
)
class PersonasListView(View):

    def get(
        self,
        request,
    ):

        show_archived = bool(
            is_admin(request.user)
            and request.GET.get("archivadas") == "1"
        )

        activities = (
            filtered_activities(
                request,
                include_deleted=show_archived,
                archived=True if show_archived else False,
            )
        )

        people = (
            Personas.objects.filter(archivada=True)
            if show_archived
            else person_scope(request.user)
        )

        filters = any(
            request.GET.get(
                key
            )
            for key in (
                "cueanexo",
                "tipo_personal",
                "estado",
                "validacion",
                "q",
            )
        )

        if filters:

            people = (
                people
                .filter(
                    actividades__in=
                        activities
                )
                .distinct()
            )

        people = (
            people
            .annotate(
                total_actividades=
                    Count(
                        "actividades",
                        filter=
                            Q(
                                actividades__in=
                                    activities
                            ),
                        distinct=True,
                    )
            )
            .order_by(
                "apellido",
                "nombre",
                "pk",
            )
        )

        page = (
            Paginator(
                people,
                25,
            )
            .get_page(
                request.GET.get(
                    "page"
                )
            )
        )

        params = (
            request.GET.copy()
        )

        params.pop(
            "page",
            None,
        )

        totals = (
            activities
            .aggregate(

                cargos=
                    Count(
                        "pk"
                    ),

                docentes=
                    Count(
                        "pk",
                        filter=
                            Q(
                                tipo_personal_id=1
                            ),
                    ),

                no_docentes=
                    Count(
                        "pk",
                        filter=
                            Q(
                                tipo_personal_id=2
                            ),
                    ),

                pendientes=
                    Count(
                        "pk",
                        filter=
                            Q(
                                validacion=
                                    "BORRADOR"
                            ),
                    ),
            )
        )

        return render(
            request,
            "bnh/personas/list.html",
            {
                "page_obj":
                    page,

                "personas":
                    page.object_list,

                "total_personas":
                    page.paginator.count,

                "totals":
                    totals,

                "query":
                    params.urlencode(),

                "instituciones":
                    (
                        scoped_offers(
                            request.user
                        )
                        .order_by(
                            "cueanexo_str"
                        )
                        .values(
                            "cueanexo_str",
                            "nom_est",
                        )
                        .distinct()
                    ),

                "tipos_personal":
                    TipoPersonal.objects
                    .order_by(
                        "c_tpersonal"
                    ),

                "filters":
                    request.GET,

                "show_archived":
                    show_archived,

                "can_view_archived":
                    is_admin(request.user),
            },
        )


# ============================================================
# DETALLE DE PERSONA
# ============================================================

@method_decorator(
    operator_required,
    name="dispatch",
)
class PersonaDetailView(View):

    def get(
        self,
        request,
        pk,
    ):

        # ====================================================
        # DEBUG TEMPORAL
        # ====================================================

        print(
            "\n========== DEBUG PERSONA DETAIL =========="
        )

        print(
            "PK:",
            pk,
        )

        print(
            "USER:",
            request.user,
        )

        print(
            "USERNAME:",
            request.user.username,
        )

        print(
            "AUTH:",
            request.user.is_authenticated,
        )

        print(
            "CUES:",
            list(
                get_user_cueanexos(
                    request.user
                )
            )
        )

        print(
            "PERSONA EXISTE GLOBAL:",
            Personas.objects.filter(
                pk=pk
            ).exists()
        )

        print(
            "PERSONA EN SCOPE:",
            person_scope(
                request.user
            )
            .filter(
                pk=pk
            )
            .exists()
        )

        print(
            "ACTIVIDADES GLOBALES:",
            list(
                RegistroActividades.objects
                .filter(
                    persona_id=pk
                )
                .values(
                    "id",
                    "cueanexo",
                    "estado",
                    "eliminado",
                )
            )
        )

        print(
            "=========================================="
        )

        # ====================================================
        # PERSONA
        # ====================================================

        person_queryset = (
            Personas.objects.all()
            if is_admin(request.user)
            else person_scope(request.user)
        )

        person = get_object_or_404(
            person_queryset
            .select_related(
                "sexo",
                "provincia",
                "localidad",
                "codigo_area",
            ),
            pk=pk,
        )

        print(
            "DEBUG 1 - PERSONA OBTENIDA:",
            person,
        )

        # ====================================================
        # ACTIVIDADES
        # ====================================================

        activities = list(
            activity_scope(
                request.user,
                include_deleted=True,
            )
            .filter(
                persona=person
            )
            .select_related(
                "tipo_personal",
                "cond_actividad",
                "ceic",
                "sit_revista",
                "t_designacion",
                "modalidad",
                "niveles",
                "modalidad_curricular",
                "nivel_curricular",
                "espacio_curricular",
                "espacios",
                "grado_anio",
                "secciones",
            )
            .prefetch_related(
                "ubicaciones_curriculares__grado_anio",
                "ubicaciones_curriculares__seccion",
                "titulaciones_curriculares",
            )
            .order_by(
                "eliminado",
                "cueanexo",
                "-f_desde",
                "pk",
            )
        )

        for actividad in activities:
            actividad.ubicaciones_ui = list(
                actividad.ubicaciones_curriculares.all()
            )
            actividad.titulaciones_ui = [
                {
                    "id": item.titulacion,
                    "label": titulacion_label(item.titulacion_fuente, item.titulacion)
                    or str(item.titulacion),
                }
                for item in actividad.titulaciones_curriculares.all()
            ]

        print(
            "DEBUG 2 - ACTIVITIES:",
            len(activities),
            [
                (
                    actividad.pk,
                    actividad.cueanexo,
                    actividad.eliminado,
                )
                for actividad
                in activities
            ],
        )

        # ====================================================
        # CONSTANCIAS POR INSTITUCIÓN
        #
        # Una constancia:
        # persona + CUEANEXO
        #
        # Incluye todos los servicios NO eliminados.
        # ====================================================

        constancias_map = {}

        for actividad in activities:

            if actividad.eliminado:
                continue

            cue = str(
                actividad.cueanexo
                or ""
            ).strip()

            if not cue:
                continue

            item = (
                constancias_map
                .setdefault(
                    cue,
                    {
                        "cueanexo":
                            cue,

                        "nom_est":
                            "",

                        "total_servicios":
                            0,
                    },
                )
            )

            item[
                "total_servicios"
            ] += 1

        cues = list(
            constancias_map.keys()
        )

        print(
            "DEBUG 3 - CUES CONSTANCIAS:",
            cues,
        )

        # ====================================================
        # NOMBRE DE LOS ESTABLECIMIENTOS
        # ====================================================

        if cues:

            print(
                "DEBUG 4 - ANTES DE SCOPED_OFFERS"
            )

            ofertas = list(
                scoped_offers(
                    request.user
                )
                .filter(
                    cueanexo_str__in=
                        cues
                )
                .exclude(
                    nom_est__isnull=True
                )
                .exclude(
                    nom_est=""
                )
                .order_by(
                    "cueanexo_str",
                    "nom_est",
                )
                .values(
                    "cueanexo_str",
                    "nom_est",
                )
            )

            print(
                "DEBUG 5 - OFERTAS:",
                ofertas,
            )

            for oferta in ofertas:

                cue = str(
                    oferta[
                        "cueanexo_str"
                    ]
                    or ""
                ).strip()

                if (
                    cue
                    in constancias_map

                    and

                    not
                    constancias_map[
                        cue
                    ][
                        "nom_est"
                    ]
                ):

                    constancias_map[
                        cue
                    ][
                        "nom_est"
                    ] = (
                        oferta[
                            "nom_est"
                        ]
                    )

        # ====================================================
        # ARMADO DE CONSTANCIAS
        # ====================================================

        constancias_instituciones = []

        for cue, item in sorted(
            constancias_map.items()
        ):

            if not item[
                "nom_est"
            ]:

                item[
                    "nom_est"
                ] = (
                    "Establecimiento educativo"
                )

            constancias_instituciones.append(
                item
            )

        print(
            "DEBUG 6 - CONSTANCIAS:",
            constancias_instituciones,
        )

        # ====================================================
        # AUDITORÍA
        # ====================================================

        activity_ids = [
            actividad.pk

            for actividad
            in activities
        ]

        audit_filter = Q(
            entidad="personas",
            objeto_id=person.pk,
        )

        if activity_ids:
            audit_filter |= Q(
                entidad="registroactividades",
                objeto_id__in=activity_ids,
            )

        events = list(
            EventoAuditoria.objects
            .filter(audit_filter)
            .select_related(
                "usuario"
            )
            [:40]
        )

        print(
            "DEBUG 7 - EVENTOS:",
            len(events),
        )

        # ====================================================
        # RENDER
        # ====================================================

        print(
            "DEBUG 8 - ANTES DEL RENDER"
        )

        response = render(
            request,
            "bnh/personas/detail.html",
            {
                "persona":
                    person,

                "actividades":
                    activities,

                "eventos":
                    events,

                "constancias_instituciones":
                    constancias_instituciones,

                "can_observe":
                    (
                        is_admin(
                            request.user
                        )

                        or

                        is_regional(
                            request.user
                        )
                    ),

                "can_restore":
                    (
                        is_admin(request.user)
                        and person.archivada
                    ),
            },
        )

        print(
            "DEBUG 9 - RENDER OK"
        )

        return response


# ============================================================
# CONSTANCIA DE SERVICIO
# ============================================================

@operator_required
@require_GET
def constancia_servicio_pdf(request, persona_id, cueanexo):
    """Emite una constancia nueva y genera un QR de verificación pública."""
    cue = str(cueanexo or '').strip()

    person = get_object_or_404(
        person_scope(request.user).select_related(
            'sexo', 'provincia', 'localidad', 'codigo_area'
        ),
        pk=persona_id,
    )

    actividades = list(
        activity_scope(request.user)
        .filter(persona=person, cueanexo=cue)
        .select_related(
            'tipo_personal', 'cond_actividad', 'ceic', 'sit_revista',
            't_designacion', 'modalidad', 'niveles', 'modalidad_curricular',
            'nivel_curricular', 'espacio_curricular', 'espacios',
            'grado_anio', 'secciones',
        )
        .order_by('f_desde', 'ceic_id', 'pk')
    )

    if not actividades:
        raise Http404(
            'No existen servicios accesibles para esta persona en la institución indicada.'
        )

    nom_est = (
        scoped_offers(request.user)
        .filter(cueanexo_str=cue)
        .exclude(nom_est__isnull=True)
        .exclude(nom_est='')
        .order_by('nom_est')
        .values_list('nom_est', flat=True)
        .first()
        or 'Establecimiento educativo'
    )

    from .services.constancia_servicio import generar_constancia_servicio_pdf
    from .services.constancia_verificacion import (
        crear_constancia_servicio,
        registrar_hash_pdf,
    )

    # La creación y el PDF forman una única emisión lógica. Si el PDF falla,
    # la transacción no deja una constancia huérfana.
    with transaction.atomic():
        constancia = crear_constancia_servicio(
            usuario=request.user,
            persona=person,
            cueanexo=cue,
            nom_est=nom_est,
            actividades=actividades,
        )

        verify_path = reverse(
            'bnhpersonas:verificar_constancia',
            kwargs={'token': constancia.token},
        )
        public_base = str(getattr(settings, 'BNH_PUBLIC_BASE_URL', '') or '').rstrip('/')
        verification_url = (
            f'{public_base}{verify_path}'
            if public_base
            else request.build_absolute_uri(verify_path)
        )

        pdf = generar_constancia_servicio_pdf(
            persona=person,
            cueanexo=cue,
            nom_est=nom_est,
            actividades=actividades,
            fecha_emision=timezone.localtime(constancia.fecha_emision).date(),
            numero_constancia=constancia.numero,
            verification_url=verification_url,
            hash_contenido=constancia.hash_contenido,
        )
        registrar_hash_pdf(constancia.pk, pdf)

    cuil = str(person.cuil or 'sin_cuil').replace('-', '')
    filename = f'constancia_servicio_{cuil}_{cue}.pdf'

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    response['Cache-Control'] = 'private, no-store'
    response['X-Constancia-Numero'] = constancia.numero
    return response


@require_GET
def verificar_constancia(request, token):
    """Consulta pública. No requiere sesión y no expone el CUIL completo."""
    from .services.constancia_verificacion import (
        mascara_cuil,
        verificar_integridad_constancia,
    )

    constancia = get_object_or_404(
        ConstanciaServicio.objects.select_related('persona'),
        token=token,
    )
    integridad_ok = verificar_integridad_constancia(constancia)
    snap = constancia.snapshot or {}
    persona = snap.get('persona') or {}
    institucion = snap.get('institucion') or {}
    servicios = snap.get('servicios') or []

    can_anular = False
    if request.user.is_authenticated:
        try:
            can_anular = is_admin(request.user) or scoped_offers(request.user).filter(
                cueanexo_str=constancia.cueanexo
            ).exists()
        except Exception:
            can_anular = False

    response = render(
        request,
        'bnh/personas/verificar_constancia.html',
        {
            'constancia': constancia,
            'integridad_ok': integridad_ok,
            'valida': (
                integridad_ok
                and constancia.estado == ConstanciaServicio.ESTADO_VIGENTE
            ),
            'persona_snapshot': persona,
            'institucion_snapshot': institucion,
            'servicios_snapshot': servicios,
            'cuil_mascarado': mascara_cuil(persona.get('cuil')),
            'can_anular': can_anular,
        },
    )
    response['Cache-Control'] = 'no-store, max-age=0'
    response['Pragma'] = 'no-cache'
    response['X-Robots-Tag'] = 'noindex, nofollow, noarchive'
    return response


@operator_required
@require_POST
def anular_constancia(request, token):
    from .services.constancia_verificacion import anular_constancia as service_anular

    constancia = get_object_or_404(ConstanciaServicio, token=token)
    autorizado = is_admin(request.user) or scoped_offers(request.user).filter(
        cueanexo_str=constancia.cueanexo
    ).exists()
    if not autorizado:
        raise Http404

    motivo = str(request.POST.get('motivo') or '').strip()
    try:
        service_anular(
            usuario=request.user,
            constancia_id=constancia.pk,
            motivo=motivo,
        )
    except ValueError as exc:
        response = render(
            request,
            'bnh/personas/verificar_constancia.html',
            {
                'constancia': constancia,
                'integridad_ok': True,
                'valida': constancia.estado == ConstanciaServicio.ESTADO_VIGENTE,
                'persona_snapshot': (constancia.snapshot or {}).get('persona') or {},
                'institucion_snapshot': (constancia.snapshot or {}).get('institucion') or {},
                'servicios_snapshot': (constancia.snapshot or {}).get('servicios') or [],
                'cuil_mascarado': 'Dato protegido',
                'can_anular': True,
                'error_anulacion': str(exc),
            },
            status=400,
        )
        response['Cache-Control'] = 'no-store'
        return response

    return redirect('bnhpersonas:verificar_constancia', token=token)


# ============================================================
# UTILIDAD PARA CSV STREAMING
# ============================================================

class Echo:

    def write(
        self,
        value,
    ):

        return value


# ============================================================
# SEGURIDAD DE CELDAS CSV
# ============================================================

def csv_cell(
    value,
):

    value = str(
        value
        or ""
    )

    if (
        value
        .lstrip()
        .startswith(
            (
                "=",
                "+",
                "-",
                "@",
            )
        )

        or

        value.startswith(
            (
                "\t",
                "\r",
                "\n",
            )
        )
    ):

        return (
            "'"
            +
            value
        )

    return value


# ============================================================
# EXPORTAR PERSONAL
# ============================================================

@operator_required
@require_GET
def exportar_personal(
    request,
):

    qs = (
        filtered_activities(
            request
        )
        .select_related(
            "persona",
            "tipo_personal",
            "ceic",
            "modalidad_curricular",
            "nivel_curricular",
            "espacio_curricular",
            "grado_anio",
            "secciones",
        )
        .order_by(
            "cueanexo",
            "persona__apellido",
            "pk",
        )
    )

    writer = csv.writer(
        Echo(),
        delimiter=";",
    )

    def rows():

        yield (
            "\ufeff"
            +
            writer.writerow(
                [
                    "CUEANEXO",
                    "Apellido",
                    "Nombre",
                    "CUIL",
                    "DNI",
                    "Tipo de personal",
                    "Cargo",
                    "Modalidad curricular",
                    "Nivel curricular",
                    "Titulación",
                    "Espacio curricular",
                    "Grado/Año",
                    "Sección",
                    "Estado",
                    "Validación",
                ]
            )
        )

        for obj in qs.iterator(
            chunk_size=1000
        ):

            yield writer.writerow(
                [
                    csv_cell(x)

                    for x in (
                        obj.cueanexo,
                        obj.persona.apellido,
                        obj.persona.nombre,
                        obj.persona.cuil,
                        obj.persona.dni,
                        obj.tipo_personal,
                        obj.ceic,
                        obj.modalidad_curricular,
                        obj.nivel_curricular,
                        obj.titulacion_descripcion,
                        obj.espacio_curricular,
                        obj.grado_anio,
                        obj.secciones,
                        obj.estado,
                        obj.validacion,
                    )
                ]
            )

    response = StreamingHttpResponse(
        rows(),
        content_type=
            "text/csv; charset=utf-8",
    )

    response[
        "Content-Disposition"
    ] = (
        'attachment; filename="personal_educativo.csv"'
    )

    response[
        "Cache-Control"
    ] = (
        "private, no-store"
    )

    return response