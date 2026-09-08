from dataclasses import dataclass
from datetime import date, datetime
from urllib.parse import urlencode

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Case, IntegerField, Value, When
from django.http import Http404, JsonResponse
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
from .views_generarinforme import get_cueanexos_usuario


@dataclass(frozen=True)
class SeccionCarga:
    clave: str
    nombre: str
    modelo: object
    url_name: str
    icono: str
    material_icon: str
    columnas: tuple


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
    ),
    SeccionCarga(
        'referencia-virtual',
        'Referencia virtual',
        ServicioReferenciaVirtual,
        'servrefvirtual_list',
        'fa-globe',
        'language',
        (
            ('servicio__nom_servicio', 'Servicio'),
            ('turnos__nom_turno', 'Turno'),
            ('varones', 'Varones'),
            ('total', 'Total'),
        ),
    ),
    SeccionCarga(
        'prestamos',
        'Préstamos',
        ServicioPrestamo,
        'servprestamo_list',
        'fa-exchange-alt',
        'swap_horiz',
        (
            ('servicio__nom_servicio', 'Servicio'),
            ('turnos__nom_turno', 'Turno'),
            ('instalacion', 'Instalación'),
            ('total', 'Total'),
        ),
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
    ),
    SeccionCarga(
        'instituciones',
        'Instituciones',
        InstitucionesPrestaServicios,
        'instituciones_list',
        'fa-school',
        'apartment',
        (
            ('escuela', 'Institución'),
            ('matricula', 'Matrícula'),
            ('docentes', 'Docentes'),
            ('matricdisc', 'Matrícula con discapacidad'),
            ('etnia', 'Etnia'),
        ),
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
    ),
)

SECCIONES_CARGA_POR_CLAVE = {
    seccion.clave: seccion for seccion in SECCIONES_CARGA
}


def _cueanexos_autorizados(user):
    return list(dict.fromkeys(
        str(cueanexo) for cueanexo in get_cueanexos_usuario(user)
    ))


def _periodos_pendientes(cueanexos):
    return list(
        GenerarInforme.objects.filter(
            cueanexo__in=cueanexos,
            estado='GENERADO',
        )
        .only('cueanexo', 'meses', 'annos', 'estado', 'f_generacion')
        .order_by('pk')[:2]
    )


def _alinear_cue_sesion(request, periodo_pendiente):
    cueanexo = str(periodo_pendiente.cueanexo)
    if str(request.session.get('cueanexo_activo') or '') != cueanexo:
        request.session['cueanexo_activo'] = cueanexo
    return cueanexo


def _construir_resumen_secciones(periodo_pendiente):
    cueanexo = str(periodo_pendiente.cueanexo)
    filtros_periodo = {
        'cueanexo': cueanexo,
        'mes': periodo_pendiente.meses,
        'anio': periodo_pendiente.annos,
    }
    querystring = urlencode({
        'anio': periodo_pendiente.annos,
        'mes': periodo_pendiente.meses,
    })
    secciones = []

    for numero, seccion in enumerate(SECCIONES_CARGA, 1):
        cantidad = seccion.modelo.objects.filter(**filtros_periodo).count()
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


class DashboardView(TemplateView):
    template_name = 'biblioteca/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['panel'] = 'Panel de administrador'
        context['title'] = 'Biblioteca | Inicio'

        cueanexos_autorizados = _cueanexos_autorizados(self.request.user)
        pendientes = _periodos_pendientes(cueanexos_autorizados)

        periodo_pendiente = pendientes[0] if len(pendientes) == 1 else None

        context.update({
            'periodo_pendiente': periodo_pendiente,
            'periodos_pendientes_ambiguos': len(pendientes) > 1,
        })
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

        context.update({
            'periodo_pendiente': pendientes[0] if len(pendientes) == 1 else None,
            'periodos_pendientes': pendientes,
            'periodos_pendientes_ambiguos': len(pendientes) > 1,
            'historial': [
                informe for informe in informes if informe.estado == 'ENVIADO'
            ],
            'puede_crear_periodo': not pendientes,
        })
        return context


class CargaView(LoginRequiredMixin, TemplateView):
    template_name = 'biblioteca/carga.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Biblioteca | Carga'
        cueanexos_autorizados = _cueanexos_autorizados(self.request.user)
        pendientes = _periodos_pendientes(cueanexos_autorizados)
        periodo_pendiente = pendientes[0] if len(pendientes) == 1 else None

        context.update({
            'periodo_pendiente': periodo_pendiente,
            'periodos_pendientes_ambiguos': len(pendientes) > 1,
            'secciones': [],
        })

        if not periodo_pendiente:
            return context

        _alinear_cue_sesion(self.request, periodo_pendiente)
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
        periodo_pendiente = pendientes[0] if len(pendientes) == 1 else None

        context.update({
            'periodo_pendiente': periodo_pendiente,
            'periodos_pendientes_ambiguos': len(pendientes) > 1,
            'secciones': [],
        })

        if not periodo_pendiente:
            return context

        _alinear_cue_sesion(self.request, periodo_pendiente)
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
        if len(pendientes) != 1:
            mensaje = (
                'No hay un período pendiente disponible para revisar.'
                if not pendientes
                else 'Hay más de un período pendiente y no se puede elegir uno de forma segura.'
            )
            return JsonResponse({'detail': mensaje}, status=409)

        periodo_pendiente = pendientes[0]
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
