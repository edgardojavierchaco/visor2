from dataclasses import dataclass
from datetime import date, datetime
import logging
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import DatabaseError, transaction
from django.db.models import (
    Case,
    Count,
    IntegerField,
    OuterRef,
    Subquery,
    Value,
    When,
)
from django.db.models.functions import Coalesce
from django.http import Http404, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.generic import TemplateView

from .models import (
    Aguapey,
    AsistenciaUsuarios,
    BibliotecariosCue,
    GenerarInforme,
    InformePedagogico,
    InstitucionesPrestaServicios,
    MaterialBibliografico,
    ProcesosTecnicos,
    RegistroDestinoFondos,
    ServicioPrestamo,
    ServicioReferencia,
    ServicioReferenciaVirtual,
)
from .mixins import PERIODO_ACTIVO_SESSION_KEY, get_cueanexos_usuario


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SeccionCarga:
    clave: str
    nombre: str
    modelo: object
    url_name: str
    icono: str
    material_icon: str
    columnas: tuple
    campos_totalizables: tuple = ()
    modo_total: str = 'sum'


SECCIONES_CARGA = (
    SeccionCarga(
        'material-bibliografico',
        'Material bibliográfico',
        MaterialBibliografico,
        'materialbibliografico_list',
        'fa-book',
        'menu_book',
        (
            ('servicio__nom_servicio', 'Servicio'),
            ('turnos__nom_turno', 'Turno'),
            ('t_material__nom_material', 'Material'),
            ('cantidad', 'Cantidad'),
        ),
        campos_totalizables=('cantidad',),
    ),
    SeccionCarga(
        'referencia',
        'Referencia',
        ServicioReferencia,
        'servref_list',
        'fa-search',
        'contact_support',
        (
            ('servicio__nom_servicio', 'Servicio'),
            ('turnos__nom_turno', 'Turno'),
            ('varones', 'Varones'),
            ('total', 'Total'),
        ),
        campos_totalizables=('varones', 'total'),
    ),
    SeccionCarga(
        'referencia-virtual',
        'Referencia virtual',
        ServicioReferenciaVirtual,
        'servrefvirtual_list',
        'fa-globe',
        'settings_system_daydream',
        (
            ('servicio__nom_servicio', 'Servicio'),
            ('turnos__nom_turno', 'Turno'),
            ('varones', 'Varones'),
            ('total', 'Total'),
        ),
        campos_totalizables=('varones', 'total'),
    ),
    SeccionCarga(
        'prestamos',
        'Préstamos',
        ServicioPrestamo,
        'servprestamo_list',
        'fa-exchange-alt',
        'box',
        (
            ('servicio__nom_servicio', 'Servicio'),
            ('turnos__nom_turno', 'Turno'),
            ('instalacion', 'Instalación'),
            ('total', 'Total'),
        ),
        campos_totalizables=('total',),
    ),
    SeccionCarga(
        'informe-pedagogico',
        'Informe pedagógico',
        InformePedagogico,
        'infopedago_list',
        'fa-chalkboard-teacher',
        'school',
        (
            ('servicio__nom_servicio', 'Servicio'),
            ('varones', 'Varones'),
            ('total', 'Total'),
        ),
        campos_totalizables=('varones', 'total'),
    ),
    SeccionCarga(
        'asistencia',
        'Asistencia',
        AsistenciaUsuarios,
        'asistusua_list',
        'fa-users',
        'groups',
        (
            ('nivel', 'Nivel'),
            ('usuario', 'Usuario'),
            ('varones', 'Varones'),
            ('total', 'Total'),
        ),
        campos_totalizables=('varones', 'total'),
    ),
    SeccionCarga(
        'instituciones',
        'Instituciones',
        InstitucionesPrestaServicios,
        'instituciones_list',
        'fa-school',
        'add_home_work',
        (
            ('escuela', 'Institución'),
            ('matricula', 'Matrícula'),
            ('docentes', 'Docentes'),
            ('matricdisc', 'Matrícula con discapacidad'),
            ('etnia', 'Etnia'),
        ),
        campos_totalizables=('matricula', 'docentes', 'matricdisc', 'etnia'),
    ),
    SeccionCarga(
        'procesos-tecnicos',
        'Procesos técnicos',
        ProcesosTecnicos,
        'proctec_list',
        'fa-cogs',
        'settings_suggest',
        (
            ('material__nom_material', 'Material'),
            ('procesos', 'Proceso'),
            ('total', 'Total'),
        ),
        campos_totalizables=('total',),
    ),
    SeccionCarga(
        'aguapey',
        'Aguapey',
        Aguapey,
        'aguapey_list',
        'fa-database',
        'dns',
        (
            ('total_mes', 'Total del mes'),
            ('total_base', 'Total de la base'),
            ('total_usuarios', 'Total de usuarios'),
            ('observaciones', 'Observaciones'),
        ),
        campos_totalizables=('total_mes', 'total_base', 'total_usuarios'),
    ),
    SeccionCarga(
        'destino-fondos',
        'Destino de fondos',
        RegistroDestinoFondos,
        'fondos_list',
        'fa-coins',
        'payments',
        (
            ('destino__nom_fondo', 'Destino'),
            ('descripcion', 'Descripción'),
            ('cantidad', 'Cantidad'),
        ),
        campos_totalizables=('cantidad',),
    ),
    SeccionCarga(
        'personal-bibliotecario',
        'Personal bibliotecario',
        BibliotecariosCue,
        'bibliotecario_list',
        'fa-id-badge',
        'badge',
        (
            ('cuil', 'CUIL'),
            ('apellidos', 'Apellidos'),
            ('nombres', 'Nombres'),
            ('cargo', 'Cargo'),
            ('situacion_revista', 'Situación de revista'),
            ('f_ingreso', 'Ingreso'),
            ('f_hasta', 'Hasta'),
            ('turno__nom_turno', 'Turno'),
        ),
        modo_total='count',
    ),
)

SECCIONES_CARGA_POR_CLAVE = {
    seccion.clave: seccion for seccion in SECCIONES_CARGA
}


PERSONAL_COLUMNAS_ACTUALES = (
    ('cuil', 'CUIL'),
    ('apellidos', 'Apellidos'),
    ('nombres', 'Nombres'),
    ('cuof', 'CUOF'),
    ('cuof_anexo', 'CUOF Anexo'),
    ('licencia_permiso__tipo_licencia', 'Licencia'),
    ('f_desde_lic', 'Desde'),
    ('f_hasta_lic', 'Hasta'),
    ('situacion_laboral__tipo_situacion', 'Situación laboral'),
)

PERSONAL_COLUMNAS_HISTORICAS = (
    ('cuil', 'CUIL'),
    ('apellidos', 'Apellidos'),
    ('nombres', 'Nombres'),
    ('cargo', 'Cargo'),
    ('situacion_revista', 'Situación de revista'),
    ('f_ingreso', 'Ingreso'),
    ('f_hasta', 'Hasta'),
    ('turno__nom_turno', 'Turno'),
)

PERSONAL_CAMPOS_LEGACY = (
    'cargo',
    'situacion_revista',
    'f_ingreso',
    'f_hasta',
    'turno__nom_turno',
)

PERSONAL_DETALLES_ACTUALES = (
    ('cuof', 'CUOF'),
    ('cuof_anexo', 'CUOF Anexo'),
    ('licencia_permiso__tipo_licencia', 'Licencia'),
    ('f_desde_lic', 'Desde licencia'),
    ('f_hasta_lic', 'Hasta licencia'),
    ('situacion_laboral__tipo_situacion', 'Situación laboral'),
    ('observaciones', 'Observaciones'),
)

PERSONAL_DETALLES_HISTORICOS = (
    ('cargo', 'Cargo'),
    ('situacion_revista', 'Situación de revista'),
    ('f_ingreso', 'Ingreso'),
    ('f_hasta', 'Hasta'),
    ('turno__nom_turno', 'Turno'),
)

PERSONAL_CAMPOS_CONSULTA = tuple(dict.fromkeys([
    campo
    for grupo in (
        PERSONAL_COLUMNAS_ACTUALES,
        PERSONAL_COLUMNAS_HISTORICAS,
        PERSONAL_DETALLES_ACTUALES,
        PERSONAL_DETALLES_HISTORICOS,
    )
    for campo, _etiqueta in grupo
] + ['turno_bnh']))


def _cueanexos_autorizados(user):
    return list(dict.fromkeys(
        str(cueanexo) for cueanexo in get_cueanexos_usuario(user)
    ))


def _resolver_periodo_enviado_autorizado(request, periodo_id):
    cueanexos_autorizados = _cueanexos_autorizados(request.user)
    try:
        return (
            GenerarInforme.objects
            .only('pk', 'cueanexo', 'meses', 'annos', 'estado')
            .get(
                pk=periodo_id,
                estado='ENVIADO',
                cueanexo__in=cueanexos_autorizados,
            )
        )
    except GenerarInforme.DoesNotExist:
        raise Http404('El período solicitado no está disponible.')


def _periodos_pendientes(cueanexos):
    return list(
        GenerarInforme.objects.filter(
            cueanexo__in=cueanexos,
            estado='GENERADO',
        )
        .only('pk', 'cueanexo', 'meses', 'annos', 'estado', 'f_generacion')
        .order_by('pk')
    )


def _alinear_periodo_sesion(request, periodo_pendiente):
    cueanexo = str(periodo_pendiente.cueanexo)
    if request.session.get(PERIODO_ACTIVO_SESSION_KEY) != periodo_pendiente.pk:
        request.session[PERIODO_ACTIVO_SESSION_KEY] = periodo_pendiente.pk
    if str(request.session.get('cueanexo_activo') or '') != cueanexo:
        request.session['cueanexo_activo'] = cueanexo
    return cueanexo


def _limpiar_periodo_sesion(request):
    request.session.pop(PERIODO_ACTIVO_SESSION_KEY, None)
    request.session.pop('cueanexo_activo', None)


def _resolver_periodo_pendiente(request, cueanexos_autorizados, pendientes):
    request._biblioteca_cueanexos_autorizados = cueanexos_autorizados
    cueanexos_autorizados_set = set(cueanexos_autorizados)
    pendientes = [
        periodo
        for periodo in pendientes
        if (
            periodo.estado == 'GENERADO'
            and str(periodo.cueanexo) in cueanexos_autorizados_set
        )
    ]
    cantidad_por_cue = {}
    for periodo in pendientes:
        cueanexo = str(periodo.cueanexo)
        cantidad_por_cue[cueanexo] = cantidad_por_cue.get(cueanexo, 0) + 1

    cueanexos_inconsistentes = tuple(
        cueanexo
        for cueanexo, cantidad in cantidad_por_cue.items()
        if cantidad > 1
    )
    cueanexos_inconsistentes_set = set(cueanexos_inconsistentes)
    periodos_seleccionables = [
        periodo
        for periodo in pendientes
        if str(periodo.cueanexo) not in cueanexos_inconsistentes_set
    ]

    periodo_pendiente = None
    periodo_solicitado = request.GET.get('periodo')
    periodo_solicitado_invalido = False

    if periodo_solicitado is not None:
        periodo_pendiente = next(
            (
                periodo
                for periodo in periodos_seleccionables
                if str(periodo.pk) == str(periodo_solicitado)
            ),
            None,
        )
        periodo_solicitado_invalido = periodo_pendiente is None

    if periodo_solicitado is None and periodo_pendiente is None:
        periodo_sesion = request.session.get(PERIODO_ACTIVO_SESSION_KEY)
        periodo_pendiente = next(
            (
                periodo
                for periodo in periodos_seleccionables
                if str(periodo.pk) == str(periodo_sesion)
            ),
            None,
        )

    if (
        periodo_solicitado is None
        and periodo_pendiente is None
        and len(periodos_seleccionables) == 1
    ):
        periodo_pendiente = periodos_seleccionables[0]

    if periodo_pendiente is not None:
        _alinear_periodo_sesion(request, periodo_pendiente)
    elif not periodo_solicitado_invalido:
        _limpiar_periodo_sesion(request)

    return {
        'periodo_pendiente': periodo_pendiente,
        'periodos_pendientes': pendientes,
        'opciones_periodos': [
            {
                'periodo': periodo,
                'seleccionable': (
                    str(periodo.cueanexo) not in cueanexos_inconsistentes_set
                ),
            }
            for periodo in pendientes
        ],
        'requiere_seleccion_periodo': (
            periodo_pendiente is None and len(periodos_seleccionables) > 1
        ),
        'hay_varios_periodos_seleccionables': len(periodos_seleccionables) > 1,
        'cueanexos_inconsistentes': cueanexos_inconsistentes,
        'periodo_solicitado_invalido': periodo_solicitado_invalido,
    }


def _obtener_conteos_secciones(periodo):
    cueanexo = str(periodo.cueanexo)
    anotaciones_conteo = {}
    alias_por_seccion = {}

    for numero, seccion in enumerate(SECCIONES_CARGA, 1):
        alias = f'cantidad_seccion_{numero}'
        conteo_seccion = (
            seccion.modelo.objects.filter(
                cueanexo=OuterRef('cueanexo'),
                mes=OuterRef('meses'),
                anio=OuterRef('annos'),
            )
            .values('cueanexo', 'mes', 'anio')
            .annotate(total=Count('pk'))
            .values('total')[:1]
        )
        anotaciones_conteo[alias] = Coalesce(
            Subquery(conteo_seccion, output_field=IntegerField()),
            Value(0),
            output_field=IntegerField(),
        )
        alias_por_seccion[seccion.clave] = alias

    conteos = (
        GenerarInforme.objects
        .filter(
            pk=periodo.pk,
            cueanexo=cueanexo,
            meses=periodo.meses,
            annos=periodo.annos,
        )
        .annotate(**anotaciones_conteo)
        .values(*alias_por_seccion.values())
        .get()
    )

    return {
        seccion.clave: conteos[alias_por_seccion[seccion.clave]]
        for seccion in SECCIONES_CARGA
    }


def _construir_resumen_secciones(periodo_pendiente):
    cueanexo = str(periodo_pendiente.cueanexo)
    querystring = urlencode({
        'periodo': periodo_pendiente.pk,
        'anio': periodo_pendiente.annos,
        'mes': periodo_pendiente.meses,
    })
    conteos = _obtener_conteos_secciones(periodo_pendiente)
    secciones = []

    for numero, seccion in enumerate(SECCIONES_CARGA, 1):
        cantidad = conteos[seccion.clave]
        secciones.append({
            'numero': numero,
            'clave': seccion.clave,
            'nombre': seccion.nombre,
            'icono': seccion.icono,
            'material_icon': seccion.material_icon,
            'cantidad': cantidad,
            'tiene_registros': cantidad > 0,
            'url': f'{reverse(f"bibliotecas:{seccion.url_name}")}?{querystring}',
        })

    return secciones


def _construir_totales_seccion(seccion_config, campos, registros):
    if seccion_config.modo_total == 'count':
        return {
            'tipo': 'conteo',
            'etiqueta': 'TOTAL DE PERSONAL',
            'valor': len(registros),
        }

    indice_por_campo = {
        campo: indice for indice, (campo, _etiqueta) in enumerate(
            seccion_config.columnas
        )
    }
    valores = [None] * len(campos)
    for campo in seccion_config.campos_totalizables:
        indice = indice_por_campo[campo]
        valores[indice] = sum(
            registro[indice] or 0 for registro in registros
        )
    return {
        'tipo': 'sumas',
        'valores': valores,
    }


def _valor_detalle_visible(valor):
    if valor is None or valor == '':
        return '—'
    if isinstance(valor, datetime):
        if timezone.is_aware(valor):
            valor = timezone.localtime(valor)
        return valor.strftime('%d/%m/%Y %H:%M')
    if isinstance(valor, date):
        return valor.strftime('%d/%m/%Y')
    if isinstance(valor, bool):
        return 'Sí' if valor else 'No'
    return valor


def _personal_tiene_valor(valor):
    if valor is None:
        return False
    if isinstance(valor, str):
        return bool(valor.strip())
    return True


def _construir_detalle_personal(periodo, preferir_historico=False):
    registros = list(
        BibliotecariosCue.objects.filter(
            cueanexo=str(periodo.cueanexo),
            mes=periodo.meses,
            anio=periodo.annos,
        )
        .order_by('pk')
        .values(*PERSONAL_CAMPOS_CONSULTA)
    )

    for registro in registros:
        turno_bnh = (registro.get('turno_bnh') or '').strip()
        if turno_bnh:
            registro['turno__nom_turno'] = turno_bnh

    usar_formato_historico = preferir_historico and any(
        any(_personal_tiene_valor(registro.get(campo)) for campo in PERSONAL_CAMPOS_LEGACY)
        for registro in registros
    )

    if usar_formato_historico:
        columnas = PERSONAL_COLUMNAS_HISTORICAS
        campos_detalle = PERSONAL_DETALLES_ACTUALES
        formato = 'historico'
    else:
        columnas = PERSONAL_COLUMNAS_ACTUALES
        campos_detalle = (
            ('observaciones', 'Observaciones'),
            *PERSONAL_DETALLES_HISTORICOS,
        )
        formato = 'actual'

    filas = [
        [
            _valor_detalle_visible(registro.get(campo))
            for campo, _etiqueta in columnas
        ]
        for registro in registros
    ]

    detalles = []
    for registro in registros:
        items = []
        for campo, etiqueta in campos_detalle:
            valor = registro.get(campo)
            if not _personal_tiene_valor(valor):
                continue
            items.append({
                'etiqueta': etiqueta,
                'valor': _valor_detalle_visible(valor),
            })
        detalles.append(items)

    return {
        'columnas': [etiqueta for _campo, etiqueta in columnas],
        'filas': filas,
        'detalles': detalles,
        'formato': formato,
        'cantidad': len(registros),
    }


class DashboardView(TemplateView):
    template_name = 'biblioteca/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['panel'] = 'Panel de administrador'
        context['title'] = 'Biblioteca | Inicio'

        cueanexos_autorizados = _cueanexos_autorizados(self.request.user)
        pendientes = _periodos_pendientes(cueanexos_autorizados)
        context.update(_resolver_periodo_pendiente(
            self.request,
            cueanexos_autorizados,
            pendientes,
        ))
        return context


class GuiaUsoView(LoginRequiredMixin, TemplateView):
    template_name = 'biblioteca/guia.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Biblioteca | Guía de uso'
        return context


class PeriodosView(LoginRequiredMixin, TemplateView):
    template_name = 'biblioteca/periodos.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Biblioteca | Períodos'
        cueanexos_autorizados = _cueanexos_autorizados(self.request.user)
        orden_mes = Case(
            When(meses='ABRIL', then=Value(1)),
            When(meses='JULIO', then=Value(2)),
            When(meses='NOVIEMBRE', then=Value(3)),
            When(meses='DICIEMBRE', then=Value(4)),
            default=Value(0),
            output_field=IntegerField(),
        )
        informes = list(
            GenerarInforme.objects.filter(cueanexo__in=cueanexos_autorizados)
            .annotate(orden_mes=orden_mes)
            .only(
                'cueanexo',
                'meses',
                'annos',
                'estado',
                'f_generacion',
                'f_envio',
            )
            .order_by('-annos', '-orden_mes', '-f_generacion', '-pk')
        )
        pendientes = [informe for informe in informes if informe.estado == 'GENERADO']
        cueanexos_ocupados = {
            str(informe.cueanexo) for informe in pendientes
        }

        context.update(_resolver_periodo_pendiente(
            self.request,
            cueanexos_autorizados,
            pendientes,
        ))

        context.update({
            'historial': [
                informe for informe in informes if informe.estado == 'ENVIADO'
            ],
            'puede_crear_periodo': any(
                cueanexo not in cueanexos_ocupados
                for cueanexo in cueanexos_autorizados
            ),
        })
        return context


class PeriodoPendienteDeleteView(LoginRequiredMixin, View):
    http_method_names = ('post',)

    def post(self, request, periodo_id, *args, **kwargs):
        cueanexos_autorizados = _cueanexos_autorizados(request.user)

        try:
            with transaction.atomic():
                try:
                    periodo = (
                        GenerarInforme.objects
                        .select_for_update()
                        .only('pk', 'cueanexo', 'meses', 'annos')
                        .get(
                            pk=periodo_id,
                            cueanexo__in=cueanexos_autorizados,
                            estado='GENERADO',
                            f_envio__isnull=True,
                        )
                    )
                except GenerarInforme.DoesNotExist:
                    messages.error(
                        request,
                        'El período no está disponible para eliminar.',
                    )
                    return redirect(reverse('bibliotecas:periodos'))

                cueanexo = str(periodo.cueanexo)
                mes = periodo.meses
                anio = periodo.annos
                periodo_eliminado_id = periodo.pk

                periodos_con_misma_identidad = list(
                    GenerarInforme.objects
                    .select_for_update()
                    .filter(
                        cueanexo=cueanexo,
                        meses=mes,
                        annos=anio,
                    )
                    .exclude(pk=periodo_eliminado_id)
                    .values_list('pk', flat=True)
                )
                if periodos_con_misma_identidad:
                    messages.error(
                        request,
                        'El período no puede eliminarse porque existe otro '
                        'relevamiento con el mismo CUE-Anexo, mes y año. '
                        'Requiere revisión.',
                    )
                    return redirect(reverse('bibliotecas:periodos'))

                for seccion in SECCIONES_CARGA:
                    seccion.modelo.objects.filter(
                        cueanexo=cueanexo,
                        mes=mes,
                        anio=anio,
                    ).delete()

                periodo.delete()
        except DatabaseError:
            logger.exception(
                'No se pudo eliminar el período pendiente %s.',
                periodo_id,
            )
            messages.error(
                request,
                'No fue posible eliminar el período. Los datos se conservaron.',
            )
            return redirect(reverse('bibliotecas:periodos'))

        if str(request.session.get(PERIODO_ACTIVO_SESSION_KEY)) == str(
            periodo_eliminado_id
        ):
            _limpiar_periodo_sesion(request)

        messages.success(
            request,
            f'El período {mes.capitalize()} {anio} fue eliminado.',
        )
        return redirect(reverse('bibliotecas:periodos'))


@method_decorator(never_cache, name='dispatch')
class PeriodoHistoricoResumenView(LoginRequiredMixin, View):
    def get(self, request, periodo_id, *args, **kwargs):
        periodo = _resolver_periodo_enviado_autorizado(request, periodo_id)
        conteos = _obtener_conteos_secciones(periodo)
        secciones = []

        for seccion in SECCIONES_CARGA:
            cantidad = conteos[seccion.clave]
            secciones.append({
                'clave': seccion.clave,
                'nombre': seccion.nombre,
                'material_icon': seccion.material_icon,
                'cantidad': cantidad,
                'tiene_registros': cantidad > 0,
            })

        return JsonResponse({
            'periodo': {
                'id': periodo.pk,
                'cueanexo': str(periodo.cueanexo),
                'mes': periodo.meses,
                'anio': periodo.annos,
                'estado': periodo.estado,
            },
            'secciones': secciones,
        })


@method_decorator(never_cache, name='dispatch')
class PeriodoHistoricoDetalleView(LoginRequiredMixin, View):
    def get(self, request, periodo_id, seccion, *args, **kwargs):
        seccion_config = SECCIONES_CARGA_POR_CLAVE.get(seccion)
        if not seccion_config:
            raise Http404('La sección solicitada no existe.')

        periodo = _resolver_periodo_enviado_autorizado(request, periodo_id)

        if seccion == 'personal-bibliotecario':
            detalle = _construir_detalle_personal(
                periodo,
                preferir_historico=True,
            )
            return JsonResponse({
                'seccion': seccion_config.nombre,
                'columnas': detalle['columnas'],
                'filas': detalle['filas'],
                'detalles': detalle['detalles'],
                'formato': detalle['formato'],
                'totales': {
                    'tipo': 'conteo',
                    'etiqueta': 'TOTAL DE PERSONAL',
                    'valor': detalle['cantidad'],
                },
            })

        campos = tuple(campo for campo, _etiqueta in seccion_config.columnas)
        registros = list(
            seccion_config.modelo.objects.filter(
                cueanexo=str(periodo.cueanexo),
                mes=periodo.meses,
                anio=periodo.annos,
            ).order_by('pk').values_list(*campos)
        )

        filas = [
            [_valor_detalle_visible(valor) for valor in registro]
            for registro in registros
        ]
        totales = _construir_totales_seccion(
            seccion_config,
            campos,
            registros,
        )
        return JsonResponse({
            'seccion': seccion_config.nombre,
            'columnas': [etiqueta for _campo, etiqueta in seccion_config.columnas],
            'filas': filas,
            'totales': totales,
        })


class CargaView(LoginRequiredMixin, TemplateView):
    template_name = 'biblioteca/carga.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Biblioteca | Carga'
        cueanexos_autorizados = _cueanexos_autorizados(self.request.user)
        pendientes = _periodos_pendientes(cueanexos_autorizados)
        resolucion = _resolver_periodo_pendiente(
            self.request,
            cueanexos_autorizados,
            pendientes,
        )
        periodo_pendiente = resolucion['periodo_pendiente']

        context.update(resolucion)
        context['secciones'] = []

        if not periodo_pendiente:
            return context

        secciones = _construir_resumen_secciones(periodo_pendiente)

        primera_sin_registros = next(
            (seccion for seccion in secciones if not seccion['tiene_registros']),
            None,
        )
        secciones_con_registros = sum(
            1 for seccion in secciones if seccion['tiene_registros']
        )

        context.update({
            'secciones': secciones,
            'primera_sin_registros': primera_sin_registros,
            'secciones_con_registros': secciones_con_registros,
            'todas_con_registros': secciones_con_registros == len(SECCIONES_CARGA),
        })
        return context


class InformeView(LoginRequiredMixin, TemplateView):
    template_name = 'biblioteca/informe.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Biblioteca | Informe'
        cueanexos_autorizados = _cueanexos_autorizados(self.request.user)
        pendientes = _periodos_pendientes(cueanexos_autorizados)
        resolucion = _resolver_periodo_pendiente(
            self.request,
            cueanexos_autorizados,
            pendientes,
        )
        periodo_pendiente = resolucion['periodo_pendiente']

        context.update(resolucion)
        context['secciones'] = []

        if not periodo_pendiente:
            return context

        secciones = _construir_resumen_secciones(periodo_pendiente)
        context.update({
            'secciones': secciones,
            'secciones_con_registros': sum(
                1 for seccion in secciones if seccion['tiene_registros']
            ),
        })
        return context


@method_decorator(never_cache, name='dispatch')
class InformeDetalleView(LoginRequiredMixin, View):
    def get(self, request, seccion, *args, **kwargs):
        seccion_config = SECCIONES_CARGA_POR_CLAVE.get(seccion)
        if not seccion_config:
            raise Http404('La sección solicitada no existe.')

        cueanexos_autorizados = _cueanexos_autorizados(request.user)
        pendientes = _periodos_pendientes(cueanexos_autorizados)
        resolucion = _resolver_periodo_pendiente(
            request,
            cueanexos_autorizados,
            pendientes,
        )
        if resolucion['periodo_solicitado_invalido']:
            return JsonResponse({
                'detail': 'El período solicitado no está disponible para revisar.',
            }, status=409)

        periodo_pendiente = resolucion['periodo_pendiente']
        if not periodo_pendiente:
            mensaje = (
                'No hay un período pendiente disponible para revisar.'
                if not pendientes
                else 'Seleccioná el período que querés revisar antes de abrir una sección.'
            )
            return JsonResponse({'detail': mensaje}, status=409)

        if seccion == 'personal-bibliotecario':
            detalle = _construir_detalle_personal(periodo_pendiente)
            return JsonResponse({
                'seccion': seccion_config.nombre,
                'columnas': detalle['columnas'],
                'filas': detalle['filas'],
                'detalles': detalle['detalles'],
                'formato': detalle['formato'],
            })

        campos = tuple(campo for campo, _etiqueta in seccion_config.columnas)
        registros = seccion_config.modelo.objects.filter(
            cueanexo=str(periodo_pendiente.cueanexo),
            mes=periodo_pendiente.meses,
            anio=periodo_pendiente.annos,
        ).order_by('pk').values_list(*campos)

        filas = [
            [_valor_detalle_visible(valor) for valor in registro]
            for registro in registros
        ]
        return JsonResponse({
            'seccion': seccion_config.nombre,
            'columnas': [etiqueta for _campo, etiqueta in seccion_config.columnas],
            'filas': filas,
        })


class DashboardDirView(TemplateView):
    template_name = 'biblioteca/layout_dir.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['panel'] = 'Panel de administrador'
        return context
