from contextlib import contextmanager
from datetime import date
from decimal import Decimal
import json
from pathlib import Path
import threading
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, close_old_connections, connection
from django.db.utils import OperationalError
from django.http import Http404, HttpResponse
from django.test import Client, RequestFactory, SimpleTestCase, TestCase, TransactionTestCase, override_settings
from django.urls import reverse

from .forms import EspecialDocenteSeccionForm, EspecialMatriculaCompartidaForm
from .models import (
    AlumnoSeccion,
    DocenteSeccion,
    EspecialAlumnoBanco,
    EspecialDocenteBanco,
    SeccionEspecial,
    cueanexo_tiene_oferta_matricula_compartida,
)
from .permisos import (
    _resolver_permisos_especial,
    cueanexo_autorizado_especial,
    especial_required,
    get_permisos_especial_request,
)
from .performance import PERF_SESSION_KEY, perf_begin, perf_capture_queries, perf_finish, perf_phase
from .views_contexto import (
    CACHE_TTL_CONTEXTO_ESPECIAL,
    CACHE_VERSION_CONTEXTO_ESPECIAL,
    ESTABLECIMIENTO_CACHE_FIELDS,
    _CACHE_MISS_CONTEXTO,
    _cache_key_especial_options,
    _get_establecimiento_cached,
    _get_especial_options_cached,
    _resolver_ciclo,
    _resolver_cueanexo,
    contexto_base,
    datos_establecimiento_items,
)
from .views_carga_seccion import _alta_docente_nuevo_gestionar
from .views_ciclo import _exigir_admin
from .views_docentes_seccion import dar_alta_docente_seccion
from .services_alumnos import dar_baja_alumno_banco
from .views_inscripcion_seccion import crear_inscripcion_activa, dar_alta_inscripcion_seccion
from .views_alumnos import (
    _actualizar_matricula_compartida,
    _asegurar_alumno_banco,
    _matricula_compartida_habilitada,
    alumnos,
)
from .views_localizaciones import (
    CACHE_TTL_LOCALIZACIONES_ESPECIAL,
    CACHE_VERSION_LOCALIZACIONES_ESPECIAL,
    _CACHE_MISS,
    _apply_filters_items,
    _apply_order_items,
    _cache_key_localizaciones_especial,
    _get_items_base_cached,
    _get_items_base_authorized,
    visualizacion_localizaciones,
)

from apps.bnhalumnos.models import Alumno, CatalogoSinoTipo
from apps.bnhpersonas.models import DocumentoTipo, EstadosCiviles, Localidades, Pais, Provincias, Sexo, validar_cuil

User = get_user_model()


class _FakeValuesList:
    def __init__(self, values):
        self.values = values

    def distinct(self):
        return self

    def __iter__(self):
        return iter(self.values)


class _FakeSchoolQuerySet:
    def __init__(self, cueanexos, items=None):
        self.cueanexos = tuple(cueanexos)
        self.only_fields = ()
        if items is None:
            self.items = [
                SimpleNamespace(
                    cueanexo=cueanexo,
                    nom_est=f"Escuela {cueanexo}",
                    region_loc="Region 1",
                    departamento="Departamento 1",
                    localidad="Localidad 1",
                )
                for cueanexo in self.cueanexos
            ]
        else:
            self.items = list(items)

    def values_list(self, field, flat=False):
        if flat:
            return _FakeValuesList(self.cueanexos)
        return _FakeValuesList(
            [(getattr(item, "cueanexo", ""), getattr(item, "nom_est", "")) for item in self.items]
        )

    def only(self, *fields):
        self.only_fields = fields
        return self

    def order_by(self, *fields):
        return self

    def select_related(self, *fields):
        return self

    def filter(self, **kwargs):
        items = self.items
        for key, value in kwargs.items():
            items = [item for item in items if getattr(item, key, None) == value]
        return _FakeSchoolQuerySet([getattr(item, "cueanexo", "") for item in items], items)

    def first(self):
        return self.items[0] if self.items else None

    def distinct(self):
        return self

    def none(self):
        return _FakeSchoolQuerySet((), [])

    def __iter__(self):
        return iter(self.items)


class _FakeCycleManager:
    def __init__(self, cycles):
        self.cycles = cycles

    def filter(self, **kwargs):
        return self

    def order_by(self, *fields):
        return self

    def __iter__(self):
        return iter(self.cycles)


def _cuil_valido(base10):
    for digito in range(10):
        candidato = f"{base10}{digito}"
        try:
            validar_cuil(candidato)
        except ValidationError:
            continue
        return candidato
    raise AssertionError("No se pudo generar un CUIL valido")


def _crear_base_especial_db():
    usuario_admin = User.objects.create_user(username="20111111111", password="x")
    usuario_director = User.objects.create_user(username="20222222222", password="x")
    usuario_director_modalidad = User.objects.create_user(username="20333333333", password="x")
    usuario_otro = User.objects.create_user(username="20444444444", password="x")

    ciclo_activo = SeccionEspecial._meta.get_field("ciclo").remote_field.model.objects.create(
        anio=2026,
        descripcion="Ciclo 2026",
        activo=True,
        actual=True,
        creado_por=usuario_admin,
        actualizado_por=usuario_admin,
    )
    ciclo_inactivo = SeccionEspecial._meta.get_field("ciclo").remote_field.model.objects.create(
        anio=2025,
        descripcion="Ciclo 2025",
        activo=False,
        actual=False,
        creado_por=usuario_admin,
        actualizado_por=usuario_admin,
    )

    tipo_seccion = SeccionEspecial._meta.get_field("cd_tipo_seccion").remote_field.model.objects.create(
        cd_tipo_seccion=1,
        descripcion="Tipo A",
    )
    estructura = SeccionEspecial._meta.get_field("tipo_estructura_especial").remote_field.model.objects.create(
        cd_tipoestructuraespecial=1,
        descripcion="Estructura A",
    )
    rango = SeccionEspecial._meta.get_field("rango_etario").remote_field.model.objects.create(
        cd_tiporangoetario=1,
        descripcion="6 a 12",
    )
    turno = SeccionEspecial._meta.get_field("turno").remote_field.model.objects.create(
        cd_turno=1,
        descripcion="Mañana",
    )
    modalidad = SeccionEspecial._meta.get_field("modalidad").remote_field.model.objects.create(
        cd_modalidad_dictado=1,
        descripcion="Presencial",
    )

    pais_argentina = Pais.objects.create(c_pais=14, descrip_pais="ARGENTINA")
    provincia = Provincias.objects.create(c_provincia=1, descrip_provincia="Chaco")
    localidad = Localidades.objects.create(
        c_localidad=1,
        descrip_localidad="Resistencia",
        c_departamento=1,
        descrip_departamento="San Fernando",
        c_provincia=provincia,
    )
    documento = DocumentoTipo.objects.create(c_tipo_doc=2, descrip_doc="Libreta")
    sexo = Sexo.objects.create(c_sexo=1, descrip_sexo="Femenino")
    estado_civil = EstadosCiviles.objects.create(c_estado_civil=1, descrip_estado_civil="Soltero")
    sino_ns = CatalogoSinoTipo.objects.create(codigo=-2, descripcion="Sin informacion")

    escuelas = _FakeSchoolQuerySet(
        ("123456700", "987654300"),
        [
            SimpleNamespace(
                cueanexo="123456700",
                nom_est="Escuela permitida",
                region_loc="Region 1",
                departamento="Departamento 1",
                localidad="Localidad 1",
            ),
            SimpleNamespace(
                cueanexo="987654300",
                nom_est="Escuela ajena",
                region_loc="Region 2",
                departamento="Departamento 2",
                localidad="Localidad 2",
            ),
        ],
    )

    return SimpleNamespace(
        usuario_admin=usuario_admin,
        usuario_director=usuario_director,
        usuario_director_modalidad=usuario_director_modalidad,
        usuario_otro=usuario_otro,
        ciclo_activo=ciclo_activo,
        ciclo_inactivo=ciclo_inactivo,
        tipo_seccion=tipo_seccion,
        estructura=estructura,
        rango=rango,
        turno=turno,
        modalidad=modalidad,
        pais_argentina=pais_argentina,
        provincia=provincia,
        localidad=localidad,
        documento=documento,
        sexo=sexo,
        estado_civil=estado_civil,
        sino_ns=sino_ns,
        cueanexo_permitido="123456700",
        cueanexo_ajeno="987654300",
        escuelas=escuelas,
    )


def _crear_seccion_db(ctx, cueanexo, nombre, capacidad=1, ciclo=None):
    return SeccionEspecial.objects.create(
        cueanexo=cueanexo,
        cd_tipo_seccion=ctx.tipo_seccion,
        tipo_estructura_especial=ctx.estructura,
        nombre_seccion=nombre,
        capacidad_total=capacidad,
        ciclo=ciclo or ctx.ciclo_activo,
        turno=ctx.turno,
        rango_etario=ctx.rango,
        modalidad=ctx.modalidad,
        lugar_dictado="Escuela especial",
        estado=SeccionEspecial.Estado.ACTIVO,
        creado_por=ctx.usuario_admin,
        actualizado_por=ctx.usuario_admin,
    )


def _crear_alumno_db(ctx, idx, cuil=None):
    cuil = cuil or _cuil_valido(f"20{12345670 + idx:08d}")
    return Alumno.objects.create(
        apellidos=f"Apellido {idx}",
        nombres=f"Nombre {idx}",
        tipo_doc=ctx.documento,
        nro_doc=f"{30000000 + idx}",
        cuil=cuil,
        fecha_nacimiento=date(2010, 1, min(idx, 28) or 1),
        lugar_nacimiento="",
        sexo=ctx.sexo,
        pais_nacimiento=ctx.pais_argentina,
        prov_nacimiento=ctx.provincia,
        loc_nacimiento=ctx.localidad,
        pais_residencia=ctx.pais_argentina,
        prov_residencia=ctx.provincia,
        loc_residencia=ctx.localidad,
        est_civil=ctx.estado_civil,
        pertenece_pueblo_indigena=ctx.sino_ns,
        comunidad_originaria=None,
        lengua_originaria=None,
        tiene_discapacidad=ctx.sino_ns,
        tiene_ppi=ctx.sino_ns,
        talla=Decimal("1.50"),
        peso=Decimal("40.00"),
        usuario_modificacion=ctx.usuario_admin,
        cuil_usuario_modificacion=cuil,
    )


def _crear_alumno_banco_db(ctx, alumno, seccion, estado="activo"):
    return EspecialAlumnoBanco.objects.create(
        cueanexo=seccion.cueanexo,
        ciclo=seccion.ciclo,
        alumno=alumno,
        estado=estado,
        creado_por=ctx.usuario_admin,
        actualizado_por=ctx.usuario_admin,
    )


def _crear_inscripcion_db(ctx, alumno, seccion, estado="activo"):
    hoy = date.today()
    kwargs = {
        "alumno": alumno,
        "seccion": seccion,
        "estado": estado,
        "creado_por": ctx.usuario_admin,
        "actualizado_por": ctx.usuario_admin,
    }
    if estado == AlumnoSeccion.Estado.BAJA:
        kwargs.update(
            {
                "fecha_inscripcion": hoy,
                "fecha_baja": hoy,
                "motivo_baja": "Baja de prueba",
            }
        )
    return AlumnoSeccion.objects.create(**kwargs)


def _crear_banco_docente_db(ctx, cuil, seccion, estado="activo"):
    return EspecialDocenteBanco.objects.create(
        cueanexo=seccion.cueanexo,
        ciclo=seccion.ciclo,
        docente_cuil=cuil,
        estado=estado,
        creado_por=ctx.usuario_admin,
        actualizado_por=ctx.usuario_admin,
    )


def _crear_asignacion_docente_db(ctx, cuil, seccion, rol, estado="activo"):
    hoy = date.today()
    kwargs = {
        "seccion": seccion,
        "docente_cuil": cuil,
        "rol": rol,
        "estado": estado,
        "creado_por": ctx.usuario_admin,
        "actualizado_por": ctx.usuario_admin,
    }
    if estado == DocenteSeccion.Estado.BAJA:
        kwargs.update(
            {
                "fecha_desde": hoy,
                "fecha_hasta": hoy,
            }
        )
    return DocenteSeccion.objects.create(**kwargs)


@contextmanager
def _permisos_especial_patched(rol, escuelas):
    with patch(
        "apps.especial.permisos.obtener_rol_usuario_especial",
        return_value=rol,
    ), patch(
        "apps.especial.permisos.get_escuelas_especiales_visualizacion_usuario",
        return_value=escuelas,
    ), patch(
        "apps.especial.permisos.get_escuelas_especiales_cargables_usuario",
        return_value=escuelas,
    ):
        yield


class PermisosEspecialTests(SimpleTestCase):
    def test_roles_autorizados_y_alcance_por_cuil(self):
        expected = {
            "Administrador": (True, ()),
            "Director": (False, ("111111111",)),
            "Director de Modalidad Especial": (False, ("111111111",)),
        }

        for role, (is_admin, cueanexos) in expected.items():
            user = SimpleNamespace(is_authenticated=True, username="20-12345678-9")
            queryset = _FakeSchoolQuerySet(cueanexos)
            with self.subTest(role=role), patch(
                "apps.especial.permisos.obtener_rol_usuario_especial",
                return_value=role,
            ), patch(
                "apps.especial.permisos.get_escuelas_especiales_visualizacion_usuario",
                return_value=queryset,
            ), patch(
                "apps.especial.permisos.get_escuelas_especiales_cargables_usuario",
                return_value=queryset,
            ):
                permisos = _resolver_permisos_especial(user)

            self.assertTrue(permisos["puede_ver"])
            self.assertEqual(permisos["es_admin"], is_admin)
            self.assertEqual(permisos["cueanexos_visualizacion"], frozenset(cueanexos))
            self.assertEqual(permisos["cueanexos_cargables"], frozenset(cueanexos))

    def test_administrador_no_materializa_cueanexos_autorizados(self):
        user = SimpleNamespace(is_authenticated=True, username="20-12345678-9")
        queryset = MagicMock()

        with patch(
            "apps.especial.permisos.obtener_rol_usuario_especial",
            return_value="Administrador",
        ), patch(
            "apps.especial.permisos.get_escuelas_especiales_visualizacion_usuario",
            return_value=queryset,
        ), patch(
            "apps.especial.permisos.get_escuelas_especiales_cargables_usuario",
            return_value=queryset,
        ):
            permisos = _resolver_permisos_especial(user)

        self.assertTrue(permisos["puede_ver"])
        self.assertTrue(permisos["es_admin"])
        self.assertEqual(permisos["cueanexos_visualizacion"], frozenset())
        self.assertEqual(permisos["cueanexos_cargables"], frozenset())
        queryset.values_list.assert_not_called()
        queryset.distinct.assert_not_called()
        queryset.__iter__.assert_not_called()

    def test_director_materializa_su_alcance_explicito(self):
        user = SimpleNamespace(is_authenticated=True, username="20-12345678-9")
        queryset = MagicMock()
        queryset.values_list.return_value.distinct.return_value = [
            "111111111",
            "222222222",
        ]

        with patch(
            "apps.especial.permisos.obtener_rol_usuario_especial",
            return_value="Director",
        ), patch(
            "apps.especial.permisos.get_escuelas_especiales_visualizacion_usuario",
            return_value=queryset,
        ), patch(
            "apps.especial.permisos.get_escuelas_especiales_cargables_usuario",
            return_value=queryset,
        ):
            permisos = _resolver_permisos_especial(user)

        self.assertFalse(permisos["es_admin"])
        self.assertEqual(
            permisos["cueanexos_visualizacion"],
            frozenset({"111111111", "222222222"}),
        )
        self.assertEqual(permisos["cueanexos_cargables"], permisos["cueanexos_visualizacion"])
        queryset.values_list.assert_called_once_with("cueanexo", flat=True)
        queryset.values_list.return_value.distinct.assert_called_once_with()

    def test_permisos_se_resuelven_una_vez_por_request(self):
        request = RequestFactory().get("/")
        request.user = SimpleNamespace(is_authenticated=True)
        permisos = {"puede_ver": True}

        with patch(
            "apps.especial.permisos._resolver_permisos_especial",
            return_value=permisos,
        ) as resolver:
            self.assertIs(get_permisos_especial_request(request), permisos)
            self.assertIs(get_permisos_especial_request(request), permisos)

        resolver.assert_called_once_with(request.user)

    def test_rol_no_autorizado_no_tiene_alcance(self):
        user = SimpleNamespace(is_authenticated=True, username="20-12345678-9")
        queryset = _FakeSchoolQuerySet(())

        with patch(
            "apps.especial.permisos.obtener_rol_usuario_especial",
            return_value="Otro rol",
        ), patch(
            "apps.especial.permisos.get_escuelas_especiales_visualizacion_usuario",
            return_value=queryset,
        ), patch(
            "apps.especial.permisos.get_escuelas_especiales_cargables_usuario",
            return_value=queryset,
        ):
            permisos = _resolver_permisos_especial(user)

        self.assertFalse(permisos["puede_ver"])
        self.assertFalse(permisos["es_admin"])
        self.assertEqual(permisos["cueanexos_visualizacion"], frozenset())
        self.assertEqual(permisos["cueanexos_cargables"], frozenset())

    def test_cueanexo_autorizado_especial_centraliza_alcance_por_rol(self):
        admin = {
            "puede_ver": True,
            "es_admin": True,
            "cueanexos_visualizacion": frozenset(),
            "cueanexos_cargables": frozenset(),
        }
        director = {
            "puede_ver": True,
            "es_admin": False,
            "cueanexos_visualizacion": frozenset({"123456789"}),
            "cueanexos_cargables": frozenset({"123456789"}),
        }

        self.assertTrue(cueanexo_autorizado_especial(admin, "12-3456789", "visualizacion"))
        self.assertTrue(cueanexo_autorizado_especial(director, "12-3456789", "cargables"))
        self.assertFalse(cueanexo_autorizado_especial(director, "987654321", "cargables"))
        self.assertFalse(cueanexo_autorizado_especial(admin, "", "visualizacion"))
        self.assertFalse(cueanexo_autorizado_especial({"puede_ver": False, "es_admin": True}, "123456789", "visualizacion"))
        with self.assertRaises(ValueError):
            cueanexo_autorizado_especial(admin, "123456789", "desconocido")


class AccesoEspecialTests(SimpleTestCase):
    @override_settings(LOGIN_URL="/accounts/login/")
    def test_usuario_no_autenticado_es_redirigido_al_login(self):
        request = RequestFactory().get("/")
        request.user = AnonymousUser()
        view = especial_required(lambda request: "ok")

        response = view(request)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_usuario_autenticado_sin_rol_recibe_403(self):
        request = RequestFactory().get("/")
        request.user = SimpleNamespace(is_authenticated=True)
        view = especial_required(lambda request: "ok")

        with patch(
            "apps.especial.permisos.get_permisos_especial_request",
            return_value={"puede_ver": False},
        ):
            with self.assertRaises(PermissionDenied):
                view(request)


class ContextoEspecialTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.cycles = [
            SimpleNamespace(pk=2, actual=True),
            SimpleNamespace(pk=1, actual=False),
        ]

    def test_ciclo_ausente_usa_el_actual(self):
        request = self.factory.get("/")
        manager = _FakeCycleManager(self.cycles)

        with patch("apps.especial.views_contexto.EspecialCiclo.objects", manager):
            ciclo, _ = _resolver_ciclo(request)

        self.assertEqual(ciclo.pk, 2)

    def test_ciclo_malformado_o_inexistente_no_hace_fallback(self):
        manager = _FakeCycleManager(self.cycles)
        for query in ("?ciclo=abc", "?ciclo=999"):
            request = self.factory.get(query)
            with self.subTest(query=query), patch(
                "apps.especial.views_contexto.EspecialCiclo.objects", manager
            ):
                with self.assertRaises(PermissionDenied):
                    _resolver_ciclo(request)

    def test_resolver_cueanexo_rechaza_un_cue_fuera_de_las_opciones(self):
        request = self.factory.get("/?cueanexo=987654321")

        with self.assertRaises(PermissionDenied):
            _resolver_cueanexo(request, [{"cueanexo": "123456789", "nombre": "Escuela"}])

    def test_cache_key_contexto_administrador_usa_alcance_all(self):
        request = self.factory.get("/")
        request.user = SimpleNamespace(pk=7)
        admin = {
            "rol": "Administrador",
            "es_admin": True,
            "cueanexos_visualizacion": frozenset(),
            "cueanexos_cargables": frozenset(),
            "escuelas_visualizacion": MagicMock(),
            "escuelas_cargables": MagicMock(),
        }
        accidental_scope = dict(
            admin,
            cueanexos_visualizacion={"123456789"},
            cueanexos_cargables={"987654321"},
        )

        base_key = _cache_key_especial_options(request, admin, "cargables")
        self.assertEqual(
            base_key,
            _cache_key_especial_options(request, accidental_scope, "cargables"),
        )
        self.assertNotEqual(
            base_key,
            _cache_key_especial_options(request, dict(admin, rol="Director", es_admin=False), "cargables"),
        )
        self.assertNotEqual(
            base_key,
            _cache_key_especial_options(request, admin, "visualizacion"),
        )
        admin["escuelas_visualizacion"].values_list.assert_not_called()
        admin["escuelas_visualizacion"].__iter__.assert_not_called()


class AlcanceLocalizacionesTests(SimpleTestCase):
    def test_conserva_el_queryset_autorizado_sin_serializar_el_padron(self):
        permisos = {"escuelas_visualizacion": _FakeSchoolQuerySet(("111111111",))}

        queryset = _get_items_base_authorized(permisos)

        self.assertIs(queryset, permisos["escuelas_visualizacion"])
        self.assertIn("cueanexo", queryset.only_fields)

    def test_fragmento_no_construye_opciones_ni_contexto_completo(self):
        request = RequestFactory().get(
            "/especial/visualizacion/localizaciones/",
            {
                "fragmento": "resultados",
                "establecimientos": ["123456700", "987654300"],
            },
        )
        request.user = SimpleNamespace(is_authenticated=True, pk=7)
        base_items = [
            {"cueanexo": "123456700", "nom_est": "Escuela 123456700"},
            {"cueanexo": "987654300", "nom_est": "Escuela 987654300"},
        ]
        permisos = {
            "puede_ver": True,
            "escuelas_visualizacion": MagicMock(),
            "rol": "Administrador",
            "es_admin": True,
            "cueanexos_visualizacion": frozenset(),
        }
        page_obj = SimpleNamespace(
            number=1,
            object_list=[{"cueanexo": "123456700"}],
        )
        paginator = MagicMock()
        paginator.count = 1
        paginator.page.return_value = page_obj
        filtrado = [{"cueanexo": "123456700"}]
        ordenado = [{"cueanexo": "123456700"}]

        with patch(
            "apps.especial.permisos.get_permisos_especial_request",
            return_value=permisos,
        ), patch(
            "apps.especial.views_localizaciones.get_permisos_especial_request",
            return_value=permisos,
        ), patch(
            "apps.especial.views_localizaciones._get_items_base_cached",
            return_value=base_items,
        ) as get_items_base_cached, patch(
            "apps.especial.views_localizaciones._resolver_establecimientos_autorizados",
            return_value=["123456700"],
        ), patch(
            "apps.especial.views_localizaciones._get_filter_options"
        ) as get_filter_options, patch(
            "apps.especial.views_localizaciones._get_establecimientos_options"
        ) as get_establecimientos_options, patch(
            "apps.especial.views_localizaciones.contexto_base"
        ) as contexto_base, patch(
            "apps.especial.views_localizaciones._apply_filters_items",
            return_value=filtrado,
        ) as apply_filters, patch(
            "apps.especial.views_localizaciones._apply_order_items",
            return_value=(ordenado, ""),
        ), patch(
            "apps.especial.views_localizaciones.Paginator",
            return_value=paginator,
        ), patch(
            "apps.especial.views_localizaciones.render",
            return_value=HttpResponse("fragmento"),
        ) as render:
            response = visualizacion_localizaciones(request)

        self.assertEqual(response.status_code, 200)
        get_items_base_cached.assert_called_once_with(request, permisos)
        get_filter_options.assert_not_called()
        get_establecimientos_options.assert_not_called()
        contexto_base.assert_not_called()
        apply_filters.assert_called_once_with(
            base_items,
            request,
            establecimientos=["123456700"],
        )
        render.assert_called_once()
        self.assertEqual(
            render.call_args.args[1],
            "especial/componentes/localizaciones_resultados_especial.html",
        )
        self.assertEqual(
            render.call_args.args[2]["lista_items"],
            [{"cueanexo": "123456700"}],
        )
        fragment_context = render.call_args.args[2]
        self.assertIs(fragment_context["page_obj"], page_obj)
        self.assertIs(fragment_context["paginator"], paginator)
        self.assertIs(fragment_context["request"], request)
        self.assertNotIn("filter_options", fragment_context)
        self.assertNotIn("establecimientos_options", fragment_context)

    def test_cache_key_depende_de_usuario_rol_alcance_y_version(self):
        request = RequestFactory().get("/")
        request.user = SimpleNamespace(pk=7)
        permisos = {
            "rol": "Director",
            "es_admin": False,
            "cueanexos_visualizacion": frozenset({"987654300", "123456700"}),
        }

        same_scope = {
            "rol": "Director",
            "es_admin": False,
            "cueanexos_visualizacion": ["123456700", "987654300"],
        }
        changed_scope = {
            "rol": "Director",
            "es_admin": False,
            "cueanexos_visualizacion": ["123456700"],
        }
        changed_role = {
            "rol": "Supervisor",
            "es_admin": False,
            "cueanexos_visualizacion": ["123456700", "987654300"],
        }

        self.assertEqual(
            _cache_key_localizaciones_especial(request, permisos),
            _cache_key_localizaciones_especial(request, same_scope),
        )
        self.assertNotEqual(
            _cache_key_localizaciones_especial(request, permisos),
            _cache_key_localizaciones_especial(request, changed_scope),
        )
        base_key = _cache_key_localizaciones_especial(request, permisos)
        self.assertNotEqual(base_key, _cache_key_localizaciones_especial(request, changed_role))
        with patch(
            "apps.especial.views_localizaciones.CACHE_VERSION_LOCALIZACIONES_ESPECIAL",
            "v1_cache_20991231",
        ):
            self.assertNotEqual(
                base_key,
                _cache_key_localizaciones_especial(request, permisos),
            )
        request.user = SimpleNamespace(pk=8)
        self.assertNotEqual(
            _cache_key_localizaciones_especial(request, permisos),
            _cache_key_localizaciones_especial(
                SimpleNamespace(user=SimpleNamespace(pk=7)), permisos
            ),
        )
        request.user = SimpleNamespace(pk=None)
        self.assertIsNone(_cache_key_localizaciones_especial(request, permisos))

    def test_cache_key_localizaciones_administrador_usa_alcance_all(self):
        request = RequestFactory().get("/")
        request.user = SimpleNamespace(pk=7)
        admin = {
            "rol": "Administrador",
            "es_admin": True,
            "cueanexos_visualizacion": frozenset(),
            "escuelas_visualizacion": MagicMock(),
        }
        accidental_scope = dict(admin, cueanexos_visualizacion={"123456789", "987654321"})

        self.assertEqual(
            _cache_key_localizaciones_especial(request, admin),
            _cache_key_localizaciones_especial(request, accidental_scope),
        )
        self.assertNotEqual(
            _cache_key_localizaciones_especial(request, admin),
            _cache_key_localizaciones_especial(
                request,
                dict(admin, rol="Director", es_admin=False, cueanexos_visualizacion={"123456789"}),
            ),
        )

    def test_cache_miss_hit_y_lista_vacia_no_se_confunden(self):
        request = RequestFactory().get("/")
        request.user = SimpleNamespace(pk=7)
        permisos = {
            "rol": "Administrador",
            "es_admin": True,
            "cueanexos_visualizacion": frozenset(),
            "escuelas_visualizacion": MagicMock(),
        }
        source = [SimpleNamespace(cueanexo="123456700", nom_est="Escuela")]

        with patch("apps.especial.views_localizaciones.cache") as cache_mock, patch(
            "apps.especial.views_localizaciones._get_items_base_authorized",
            return_value=source,
        ) as base_authorized:
            cache_mock.get.return_value = _CACHE_MISS
            miss_items = _get_items_base_cached(request, permisos)
            cache_mock.set.assert_called_once_with(
                _cache_key_localizaciones_especial(request, permisos),
                miss_items,
                CACHE_TTL_LOCALIZACIONES_ESPECIAL,
            )
            base_authorized.assert_called_once_with(permisos)

        cached_items = [{"cueanexo": "123456700"}]
        cached_before = [dict(item) for item in cached_items]
        with patch("apps.especial.views_localizaciones.cache") as cache_mock, patch(
            "apps.especial.views_localizaciones._get_items_base_authorized"
        ) as base_authorized:
            cache_mock.get.return_value = cached_items
            returned_items = _get_items_base_cached(request, permisos)
            self.assertIs(returned_items, cached_items)
            _apply_filters_items(returned_items, RequestFactory().get("/"))
            _apply_order_items(returned_items, RequestFactory().get("/"))
            self.assertEqual(cached_items, cached_before)
            base_authorized.assert_not_called()

            cache_mock.get.return_value = []
            self.assertEqual(_get_items_base_cached(request, permisos), [])
            base_authorized.assert_not_called()

    def test_user_sin_pk_materializa_sin_cache(self):
        request = RequestFactory().get("/")
        request.user = SimpleNamespace(pk=None)
        permisos = {
            "rol": "Administrador",
            "es_admin": True,
            "cueanexos_visualizacion": frozenset(),
            "escuelas_visualizacion": MagicMock(),
        }
        source = [SimpleNamespace(cueanexo="123456700")]
        with patch("apps.especial.views_localizaciones.cache") as cache_mock, patch(
            "apps.especial.views_localizaciones._get_items_base_authorized",
            return_value=source,
        ) as base_authorized:
            items = _get_items_base_cached(request, permisos)

        self.assertEqual(items[0]["cueanexo"], "123456700")
        cache_mock.get.assert_not_called()
        cache_mock.set.assert_not_called()
        base_authorized.assert_called_once_with(permisos)

    def test_filtros_lista_conservan_operadores_y_normalizacion(self):
        items = [
            {
                "cueanexo": "12-3456700",
                "nom_est": "Escuela \u00c1lvaro",
                "region_loc": "Norte",
                "oferta": "10",
            },
            {
                "cueanexo": "987654300",
                "nom_est": "Otra escuela",
                "region_loc": "Sur",
                "oferta": "20",
            },
        ]
        factory = RequestFactory()

        self.assertEqual(
            len(_apply_filters_items(items, factory.get("/?q=alvaro"))), 1
        )
        self.assertEqual(
            len(
                _apply_filters_items(
                    items, factory.get("/?smart_ui_col=region_loc&smart_ui_val=sur")
                )
            ),
            1,
        )
        self.assertEqual(
            len(_apply_filters_items(items, factory.get("/?region_loc=norte"))), 1
        )
        self.assertEqual(
            len(_apply_filters_items(items, factory.get("/"), ["12.3456700"])), 1
        )

        expected_by_operator = {
            "0": "12-3456700",
            "1": "987654300",
            "2": "12-3456700",
            "3": "987654300",
            "4": "987654300",
            "5": "12-3456700",
            "6": "12-3456700",
            "7": "987654300",
        }
        for operator, expected_cue in expected_by_operator.items():
            request = factory.get(
                f"/?campo_filtro=oferta&operador_filtro={operator}&valor_filtro=15"
            )
            if operator == "0":
                request = factory.get(
                    "/?campo_filtro=oferta&operador_filtro=0&valor_filtro=1"
                )
            elif operator in {"1", "2", "7"}:
                request = factory.get(
                    f"/?campo_filtro=oferta&operador_filtro={operator}&valor_filtro=10"
                )
            result = _apply_filters_items(items, request)
            self.assertEqual([item["cueanexo"] for item in result], [expected_cue])

    def test_filtros_avanzados_multivalor_hacen_or_por_grupo_y_and_entre_grupos(
        self,
    ):
        items = [
            {
                "cueanexo": "1",
                "region_loc": "I",
                "departamento": "San Martin",
                "nom_est": "Uno",
            },
            {
                "cueanexo": "2",
                "region_loc": "II",
                "departamento": "San Justo",
                "nom_est": "Dos",
            },
            {
                "cueanexo": "3",
                "region_loc": "I",
                "departamento": "Belgrano",
                "nom_est": "Tres",
            },
            {
                "cueanexo": "4",
                "region_loc": "III",
                "departamento": "San Martin",
                "nom_est": "Cuatro",
            },
        ]
        request = RequestFactory().get(
            "/",
            {
                "campo_filtro": ["region_loc", "region_loc", "departamento"],
                "operador_filtro": ["2", "2", "0"],
                "valor_filtro": ["I", "II", "San"],
            },
        )

        result = _apply_filters_items(items, request)

        self.assertEqual([item["cueanexo"] for item in result], ["1", "2"])

    def test_orden_descendente_conserva_desempates_predeterminados(self):
        items = [
            {"cueanexo": "1", "nom_est": "Z", "region_loc": "B"},
            {"cueanexo": "2", "nom_est": "Z", "region_loc": "A"},
            {"cueanexo": "3", "nom_est": "A", "region_loc": "A"},
        ]
        ordered, orden = _apply_order_items(
            items, RequestFactory().get("/?orden=-nom_est")
        )

        self.assertEqual(orden, "-nom_est")
        self.assertEqual([item["cueanexo"] for item in ordered], ["2", "1", "3"])
        self.assertEqual(items[0]["cueanexo"], "1")

    def test_excel_todo_usa_el_snapshot_autorizado_sin_reconsultar(self):
        request = RequestFactory().get(
            "/especial/visualizacion/localizaciones/?formato=excel_todo"
        )
        request.user = SimpleNamespace(is_authenticated=True, pk=7)
        permisos = {
            "puede_ver": True,
            "rol": "Administrador",
            "es_admin": True,
            "cueanexos_visualizacion": frozenset(),
            "escuelas_visualizacion": MagicMock(),
        }
        base_items = [{"cueanexo": "123456700"}]
        response = HttpResponse("xlsx")

        with patch(
            "apps.especial.permisos.get_permisos_especial_request",
            return_value=permisos,
        ), patch(
            "apps.especial.views_localizaciones.get_permisos_especial_request",
            return_value=permisos,
        ), patch(
            "apps.especial.views_localizaciones._get_items_base_cached",
            return_value=base_items,
        ) as get_items_base_cached, patch(
            "apps.especial.views_localizaciones._exportar_excel_especial",
            return_value=response,
        ) as exportar:
            self.assertIs(visualizacion_localizaciones(request), response)

        get_items_base_cached.assert_called_once_with(request, permisos)
        exportar.assert_called_once_with(base_items, request, "excel_todo")

    def test_excel_pagina_filtra_y_ordena_el_snapshot_en_memoria(self):
        request = RequestFactory().get(
            "/especial/visualizacion/localizaciones/?formato=excel_pagina"
        )
        request.user = SimpleNamespace(is_authenticated=True, pk=7)
        permisos = {
            "puede_ver": True,
            "rol": "Administrador",
            "es_admin": True,
            "cueanexos_visualizacion": frozenset(),
            "escuelas_visualizacion": MagicMock(),
        }
        base_items = [{"cueanexo": "123456700"}]
        filtered = [{"cueanexo": "123456700", "nom_est": "Escuela"}]
        ordered = [{"cueanexo": "123456700", "nom_est": "Escuela"}]
        response = HttpResponse("xlsx")

        with patch(
            "apps.especial.permisos.get_permisos_especial_request",
            return_value=permisos,
        ), patch(
            "apps.especial.views_localizaciones.get_permisos_especial_request",
            return_value=permisos,
        ), patch(
            "apps.especial.views_localizaciones._get_items_base_cached",
            return_value=base_items,
        ), patch(
            "apps.especial.views_localizaciones._resolver_establecimientos_autorizados",
            return_value=["123456700"],
        ), patch(
            "apps.especial.views_localizaciones._apply_filters_items",
            return_value=filtered,
        ) as apply_filters, patch(
            "apps.especial.views_localizaciones._apply_order_items",
            return_value=(ordered, ""),
        ) as apply_order, patch(
            "apps.especial.views_localizaciones._exportar_excel_especial",
            return_value=response,
        ) as exportar:
            self.assertIs(visualizacion_localizaciones(request), response)

        apply_filters.assert_called_once_with(
            base_items, request, establecimientos=["123456700"]
        )
        apply_order.assert_called_once_with(filtered, request)
        exportar.assert_called_once_with(ordered, request, "excel_pagina")

    def test_json_options_son_persistentes_y_no_se_repite_en_el_partial(self):
        project_root = Path(__file__).resolve().parents[2]
        full_template = (
            project_root / "templates" / "especial" / "localizaciones_especial.html"
        ).read_text(encoding="utf-8-sig")
        partial_template = (
            project_root
            / "templates"
            / "especial"
            / "componentes"
            / "localizaciones_resultados_especial.html"
        ).read_text(encoding="utf-8-sig")

        options_tag = 'json_script:"cefOptionsData"'
        filter_options_tag = 'json_script:"cefFilterOptionsData"'
        include_tag = '{% include "especial/componentes/localizaciones_resultados_especial.html" %}'

        self.assertEqual(full_template.count(options_tag), 1)
        self.assertEqual(full_template.count(filter_options_tag), 1)
        self.assertLess(full_template.index(options_tag), full_template.index(include_tag))
        self.assertNotIn(options_tag, partial_template)
        self.assertNotIn(filter_options_tag, partial_template)


class ValidacionDocenteEspecialTests(SimpleTestCase):
    def test_formulario_no_reemplaza_full_clean_dinamicamente(self):
        instance = DocenteSeccion(docente_cuil="20123456789")

        EspecialDocenteSeccionForm(instance=instance)

        self.assertEqual(instance.full_clean.__func__, DocenteSeccion.full_clean)


class ValidacionMatriculaCompartidaEspecialTests(SimpleTestCase):
    class PadronQuerySet:
        def __init__(self, existe):
            self.existe = existe

        def filter(self, **kwargs):
            return self

        def exists(self):
            return self.existe

    class PadronOfertaManager:
        def __init__(self, rows):
            self.rows = list(rows)
            self.alias = None
            self.oferta_normalizada_anotada = False

        def using(self, alias):
            self.alias = alias
            return self

        def filter(self, **kwargs):
            if "cueanexo" in kwargs:
                self.rows = [
                    row for row in self.rows if row["cueanexo"] == kwargs["cueanexo"]
                ]
            if "oferta_normalizada" in kwargs:
                if not self.oferta_normalizada_anotada:
                    raise AssertionError("La oferta debe normalizarse antes de filtrarla.")
                self.rows = [
                    row
                    for row in self.rows
                    if (row.get("oferta") or "").strip()
                    == kwargs["oferta_normalizada"]
                ]
            return self

        def annotate(self, **kwargs):
            self.oferta_normalizada_anotada = "oferta_normalizada" in kwargs
            return self

        def exists(self):
            return bool(self.rows)

    def _form(self, data, habilitada=True, existe=True, actual="123456700"):
        return EspecialMatriculaCompartidaForm(
            data,
            cueanexo_actual=actual,
            matricula_compartida_habilitada=habilitada,
            padron_queryset=self.PadronQuerySet(existe),
        )

    def _habilitada_para(self, rows, cueanexo="220015500"):
        manager = self.PadronOfertaManager(rows)
        with patch("apps.especial.models.EspecialPadronOferta.objects", manager):
            habilitada = cueanexo_tiene_oferta_matricula_compartida(cueanexo)
        self.assertEqual(manager.alias, "default")
        return habilitada

    def test_cue_con_una_oferta_integracion_normalizada_es_true(self):
        self.assertTrue(
            self._habilitada_para(
                [
                    {
                        "cueanexo": "220015500",
                        "oferta": "Especial - Integración ",
                    }
                ]
            )
        )

    def test_cue_con_varias_ofertas_y_una_integracion_es_true(self):
        self.assertTrue(
            self._habilitada_para(
                [
                    {
                        "cueanexo": "220015500",
                        "oferta": "Especial - Primaria de 7 años ",
                    },
                    {
                        "cueanexo": "220015500",
                        "oferta": "Especial - Integración ",
                    },
                    {
                        "cueanexo": "987654300",
                        "oferta": "Especial - Integración ",
                    },
                ]
            )
        )

    def test_cue_sin_oferta_integracion_es_false(self):
        self.assertFalse(
            self._habilitada_para(
                [
                    {
                        "cueanexo": "220015500",
                        "oferta": "Especial - Primaria de 7 años ",
                    }
                ]
            )
        )

    def test_oferta_normalizada_mantiene_comparacion_exacta(self):
        self.assertFalse(
            self._habilitada_para(
                [
                    {
                        "cueanexo": "220015500",
                        "oferta": "Especial - integración ",
                    },
                    {
                        "cueanexo": "220015500",
                        "oferta": "Especial - Integración ampliada",
                    },
                ]
            )
        )

    def test_error_de_padron_se_registra_y_no_es_false_funcional(self):
        context = {"puede_operar": True, "cueanexo": "220015500"}
        with patch(
            "apps.especial.views_alumnos.cueanexo_tiene_oferta_matricula_compartida",
            side_effect=OperationalError("vista no disponible"),
        ), patch("apps.especial.views_alumnos.logger.exception") as log_exception:
            habilitada = _matricula_compartida_habilitada(context)

        self.assertIsNone(habilitada)
        log_exception.assert_called_once()

    def test_contexto_del_template_recibe_habilitada_true(self):
        request = RequestFactory().get("/especial/alumnos/")
        especial_context = {
            "puede_operar": True,
            "cueanexo": "220015500",
            "ciclo": None,
        }
        render_mock = MagicMock(return_value=HttpResponse("ok"))
        vista_sin_decoradores = alumnos
        while hasattr(vista_sin_decoradores, "__wrapped__"):
            vista_sin_decoradores = vista_sin_decoradores.__wrapped__

        with patch(
            "apps.especial.views_alumnos.contexto_base",
            return_value={"especial_context": especial_context},
        ), patch(
            "apps.especial.views_alumnos._matricula_compartida_habilitada",
            return_value=True,
        ), patch(
            "apps.especial.views_alumnos._alumnos_banco",
            return_value=[],
        ), patch(
            "apps.especial.views_alumnos._secciones_disponibles",
            return_value=[],
        ), patch(
            "apps.especial.views_alumnos.render_especial",
            render_mock,
        ):
            vista_sin_decoradores(request)

        template_context = render_mock.call_args.args[2]
        self.assertIs(template_context["matricula_compartida_habilitada"], True)

    def test_cue_sin_oferta_integracion_rechaza_si_manipulado(self):
        form = self._form(
            {
                "matricula_compartida_opcion": "si",
                "cueanexo_matricula_compartida": "987654300",
            },
            habilitada=False,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("no está habilitada", str(form.errors))

    def test_no_ignora_cue_asociado_manipulado(self):
        form = self._form(
            {
                "matricula_compartida_opcion": "no",
                "cueanexo_matricula_compartida": "texto-invalido",
            }
        )

        self.assertTrue(form.is_valid())
        self.assertIsNone(form.cleaned_data["matricula_compartida"])

    def test_si_sin_cue_asociado_rechaza(self):
        form = self._form({"matricula_compartida_opcion": "si"})

        self.assertFalse(form.is_valid())
        self.assertIn("Debe seleccionar un CUE-Anexo asociado", str(form.errors))

    def test_si_con_cue_inexistente_rechaza(self):
        form = self._form(
            {
                "matricula_compartida_opcion": "si",
                "cueanexo_matricula_compartida": "000000000",
            },
            existe=False,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("no existe en el padrón general", str(form.errors))

    def test_si_con_mismo_cue_actual_rechaza(self):
        form = self._form(
            {
                "matricula_compartida_opcion": "si",
                "cueanexo_matricula_compartida": "12-345-670-0",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("no puede ser igual", str(form.errors))

    def test_si_con_cue_valido_normaliza_a_nueve_digitos(self):
        form = self._form(
            {
                "matricula_compartida_opcion": "si",
                "cueanexo_matricula_compartida": "98-765-430-0",
            }
        )

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["matricula_compartida"], "987654300")

    def test_alta_pasa_matricula_normalizada_al_banco(self):
        manager = MagicMock()
        manager.filter.return_value.first.return_value = None
        banco = SimpleNamespace()
        manager.create.return_value = banco
        context = {
            "puede_operar": True,
            "cueanexo": "123456700",
            "ciclo": SimpleNamespace(pk=1),
        }

        with patch("apps.especial.views_alumnos.EspecialAlumnoBanco.objects", manager), patch(
            "apps.especial.views_alumnos.transaction.atomic"
        ):
            resultado = _asegurar_alumno_banco(
                SimpleNamespace(pk=5),
                context,
                SimpleNamespace(pk=7),
                matricula_compartida="987654300",
            )

        self.assertEqual(resultado, (banco, True, False))
        self.assertEqual(manager.create.call_args.kwargs["matricula_compartida"], "987654300")

    def test_actualizacion_no_limpia_el_valor_y_no_muta_otro_banco(self):
        banco = SimpleNamespace(
            pk=9,
            matricula_compartida="987654300",
            actualizado_por=None,
            save=MagicMock(),
        )
        request = SimpleNamespace(
            POST={
                "alumno_banco_id": "9",
                "matricula_compartida_opcion": "no",
                "cueanexo_matricula_compartida": "987654300",
            },
            user=SimpleNamespace(pk=7),
        )
        context = {
            "puede_operar": True,
            "cueanexo": "123456700",
            "ciclo": SimpleNamespace(pk=1),
        }

        with patch(
            "apps.especial.views_alumnos._matricula_compartida_form",
            return_value=SimpleNamespace(
                is_valid=lambda: True,
                cleaned_data={"matricula_compartida": None},
            ),
        ), patch(
            "apps.especial.views_alumnos._alumno_banco_seguro",
            side_effect=[banco, banco],
        ), patch("apps.especial.views_alumnos.transaction.atomic"):
            ok, _message, updated = _actualizar_matricula_compartida(
                request,
                context,
                True,
            )

        self.assertTrue(ok)
        self.assertIs(updated, banco)
        self.assertIsNone(banco.matricula_compartida)
        banco.save.assert_called_once_with()

    def test_actualizacion_no_a_si_guarda_el_cue_validado(self):
        banco = SimpleNamespace(
            pk=9,
            matricula_compartida=None,
            actualizado_por=None,
            save=MagicMock(),
        )
        request = SimpleNamespace(
            POST={
                "alumno_banco_id": "9",
                "matricula_compartida_opcion": "si",
                "cueanexo_matricula_compartida": "98-765-430-0",
            },
            user=SimpleNamespace(pk=7),
        )
        context = {
            "puede_operar": True,
            "cueanexo": "123456700",
            "ciclo": SimpleNamespace(pk=1),
        }

        with patch(
            "apps.especial.views_alumnos._matricula_compartida_form",
            return_value=SimpleNamespace(
                is_valid=lambda: True,
                cleaned_data={"matricula_compartida": "987654300"},
            ),
        ), patch(
            "apps.especial.views_alumnos._alumno_banco_seguro",
            side_effect=[banco, banco],
        ), patch("apps.especial.views_alumnos.transaction.atomic"):
            ok, _message, updated = _actualizar_matricula_compartida(
                request,
                context,
                True,
            )

        self.assertTrue(ok)
        self.assertIs(updated, banco)
        self.assertEqual(banco.matricula_compartida, "987654300")
        banco.save.assert_called_once_with()

    def test_actualizacion_rechaza_banco_fuera_del_contexto(self):
        request = SimpleNamespace(POST={"alumno_banco_id": "9"}, user=SimpleNamespace())
        context = {"puede_operar": True, "cueanexo": "123456700", "ciclo": SimpleNamespace(pk=1)}

        with patch(
            "apps.especial.views_alumnos._alumno_banco_seguro",
            side_effect=Http404,
        ):
            with self.assertRaises(Http404):
                _actualizar_matricula_compartida(request, context, True)


class CierreIntegridadEspecialTests(SimpleTestCase):
    def test_queryset_autorizado_vacio_no_hace_fallback(self):
        queryset = MagicMock()
        queryset.model = SeccionEspecial
        queryset.select_for_update.return_value = queryset
        queryset.get.side_effect = SeccionEspecial.DoesNotExist
        banco_queryset = MagicMock()
        banco_queryset.select_for_update.return_value.filter.return_value.order_by.return_value = [
            SimpleNamespace(estado=EspecialAlumnoBanco.Estado.ACTIVO)
        ]
        inscripcion = SimpleNamespace(pk=8, seccion_id=7, alumno_id=9)

        with patch("apps.especial.views_inscripcion_seccion.SeccionEspecial.objects.filter") as fallback:
            with self.assertRaises(Http404):
                dar_alta_inscripcion_seccion(
                    inscripcion,
                    SimpleNamespace(),
                    seccion_queryset=queryset,
                    alumno_banco_queryset=banco_queryset,
                )

        fallback.assert_not_called()

    def test_formulario_docente_invalido_no_rompe_ni_guarda(self):
        class FormularioInvalido:
            errors = {"docente_cuil": ["CUIL inválido"]}

            def is_valid(self):
                return False

        request = SimpleNamespace(
            POST={"cuil": "invalido"},
            user=SimpleNamespace(),
        )
        with patch(
            "apps.especial.views_carga_seccion.EspecialDocenteSeccionForm",
            return_value=FormularioInvalido(),
        ):
            resultado = _alta_docente_nuevo_gestionar(request, SimpleNamespace())

        self.assertFalse(resultado[0])
        self.assertIn("CUIL inválido", resultado[1])

    def _docente_service_mocks(self, save_side_effect=None, duplicate=False):
        section = SimpleNamespace(pk=10)
        assignment = SimpleNamespace(pk=2, seccion_id=10)
        locked_assignment = MagicMock()
        locked_assignment.estado = DocenteSeccion.Estado.BAJA
        locked_assignment.rol = DocenteSeccion.Rol.TITULAR
        locked_assignment.get_rol_display.return_value = "Titular"
        locked_assignment.save.side_effect = save_side_effect

        section_manager = MagicMock()
        section_manager.select_for_update.return_value.get.return_value = section
        docente_manager = MagicMock()
        docente_manager.select_for_update.return_value.get.return_value = locked_assignment
        docente_manager.filter.return_value.exclude.return_value.exists.return_value = duplicate
        return assignment, locked_assignment, section_manager, docente_manager

    def test_alta_docente_bloquea_recurso_y_asignacion_reales(self):
        assignment, locked_assignment, section_manager, docente_manager = self._docente_service_mocks()

        with patch("apps.especial.views_docentes_seccion.SeccionEspecial.objects", section_manager), patch(
            "apps.especial.views_docentes_seccion.DocenteSeccion.objects", docente_manager
        ):
            dar_alta_docente_seccion(assignment, SimpleNamespace())

        section_manager.select_for_update.return_value.get.assert_called_once_with(pk=10)
        docente_manager.select_for_update.return_value.get.assert_called_once_with(
            pk=2,
            seccion=section_manager.select_for_update.return_value.get.return_value,
        )
        locked_assignment.save.assert_called_once()
        self.assertEqual(locked_assignment.estado, DocenteSeccion.Estado.ACTIVO)

    def test_alta_docente_convierte_integrity_error_en_validacion_estable(self):
        assignment, _, section_manager, docente_manager = self._docente_service_mocks(
            save_side_effect=IntegrityError("constraint")
        )

        with patch("apps.especial.views_docentes_seccion.SeccionEspecial.objects", section_manager), patch(
            "apps.especial.views_docentes_seccion.DocenteSeccion.objects", docente_manager
        ):
            with self.assertRaisesRegex(ValidationError, "conflicto con otra asignación activa"):
                dar_alta_docente_seccion(assignment, SimpleNamespace())

    def test_solo_el_admin_puede_administrar_ciclos(self):
        request = RequestFactory().get("/")
        for es_admin in (True, False):
            with self.subTest(es_admin=es_admin), patch(
                "apps.especial.views_ciclo.get_permisos_especial_request",
                return_value={"es_admin": es_admin},
            ):
                if es_admin:
                    _exigir_admin(request)
                else:
                    with self.assertRaises(PermissionDenied):
                        _exigir_admin(request)


class EspecialAccesoClienteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ctx = _crear_base_especial_db()

    @override_settings(LOGIN_URL="/accounts/login/")
    def test_usuario_no_autenticado_es_redirigido_al_login_en_inicio(self):
        response = self.client.get(reverse("especial:inicio"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_roles_autorizados_acceden_a_inicio_y_ciclos_y_roles_no_autorizados_reciben_403(self):
        casos = [
            ("Administrador", self.ctx.usuario_admin, 200, 200),
            ("Director", self.ctx.usuario_director, 200, 403),
            (
                "Director de Modalidad Especial",
                self.ctx.usuario_director_modalidad,
                200,
                403,
            ),
            ("Otro rol", self.ctx.usuario_otro, 403, 403),
        ]

        for rol, usuario, esperado_inicio, esperado_ciclos in casos:
            with self.subTest(rol=rol), _permisos_especial_patched(rol, self.ctx.escuelas):
                self.client.force_login(usuario)

                response_inicio = self.client.get(reverse("especial:inicio"))
                self.assertEqual(response_inicio.status_code, esperado_inicio)

                response_ciclos = self.client.get(reverse("especial:administrar_ciclos"))
                self.assertEqual(response_ciclos.status_code, esperado_ciclos)


class EspecialAlcanceClienteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ctx = _crear_base_especial_db()
        cls.seccion_permitida = _crear_seccion_db(
            cls.ctx,
            cls.ctx.cueanexo_permitido,
            "Seccion permitida",
            capacidad=2,
        )
        cls.seccion_ajena = _crear_seccion_db(
            cls.ctx,
            cls.ctx.cueanexo_ajeno,
            "Seccion ajena",
            capacidad=2,
        )

    def test_localizaciones_no_muestra_establecimientos_fuera_del_queryset_autorizado(self):
        escuelas_permitidas = self.ctx.escuelas.filter(cueanexo=self.ctx.cueanexo_permitido)
        self.client.force_login(self.ctx.usuario_director)

        with _permisos_especial_patched("Director", escuelas_permitidas):
            response = self.client.get(
                reverse("especial:visualizacion_localizaciones"),
                {"establecimientos": [self.ctx.cueanexo_permitido, self.ctx.cueanexo_ajeno]},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["cueanexo"] for item in response.context["lista_items"]],
            [self.ctx.cueanexo_permitido],
        )

    def test_cueanexo_y_seccion_ajenos_rechazados_por_backend(self):
        escuelas_permitidas = self.ctx.escuelas.filter(cueanexo=self.ctx.cueanexo_permitido)
        self.client.force_login(self.ctx.usuario_director)

        with _permisos_especial_patched("Director", escuelas_permitidas):
            url_permitida = reverse(
                "especial:inscripcion_seccion",
                kwargs={"seccion_id": self.seccion_permitida.pk},
            )
            url_ajena = reverse(
                "especial:inscripcion_seccion",
                kwargs={"seccion_id": self.seccion_ajena.pk},
            )

            response_get = self.client.get(
                url_permitida,
                {"cueanexo": self.ctx.cueanexo_ajeno, "ciclo": self.ctx.ciclo_activo.pk},
            )
            response_post = self.client.post(
                f"{url_permitida}?cueanexo={self.ctx.cueanexo_ajeno}&ciclo={self.ctx.ciclo_activo.pk}",
                {"cuil": "20111111111"},
            )
            response_get_seccion_ajena = self.client.get(
                url_ajena,
                {"cueanexo": self.ctx.cueanexo_permitido, "ciclo": self.ctx.ciclo_activo.pk},
            )
            response_post_seccion_ajena = self.client.post(
                f"{url_ajena}?cueanexo={self.ctx.cueanexo_permitido}&ciclo={self.ctx.ciclo_activo.pk}",
                {"cuil": "20111111111"},
            )

        self.assertEqual(response_get.status_code, 403)
        self.assertEqual(response_post.status_code, 403)
        self.assertEqual(response_get_seccion_ajena.status_code, 404)
        self.assertEqual(response_post_seccion_ajena.status_code, 404)


class EspecialCiclosDbTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ctx = _crear_base_especial_db()

    def test_resolver_ciclo_valido_inactivo_y_no_numerico_no_hace_fallback(self):
        factory = RequestFactory()

        request_valido = factory.get("/", {"ciclo": self.ctx.ciclo_activo.pk})
        ciclo, ciclos = _resolver_ciclo(request_valido)
        self.assertEqual(ciclo.pk, self.ctx.ciclo_activo.pk)
        self.assertIn(self.ctx.ciclo_activo, ciclos)

        for valor in (self.ctx.ciclo_inactivo.pk, "abc", "999999"):
            with self.subTest(valor=valor):
                request = factory.get("/", {"ciclo": valor})
                with self.assertRaises(PermissionDenied):
                    _resolver_ciclo(request)


class EspecialFlujosTransaccionalesTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.ctx = _crear_base_especial_db()
        self.seccion = _crear_seccion_db(
            self.ctx,
            self.ctx.cueanexo_permitido,
            "Seccion 1",
            capacidad=1,
        )
        self.seccion_ajena = _crear_seccion_db(
            self.ctx,
            self.ctx.cueanexo_ajeno,
            "Seccion 2",
            capacidad=1,
        )
        self.escuelas_permitidas = self.ctx.escuelas.filter(cueanexo=self.ctx.cueanexo_permitido)
        self.director = self.ctx.usuario_director
        self.admin = self.ctx.usuario_admin

    def _forzar_director(self):
        self.client.force_login(self.director)
        return _permisos_especial_patched("Director", self.escuelas_permitidas)

    def _crear_alumno_y_banco(self, idx, seccion=None, cuil=None):
        alumno = _crear_alumno_db(self.ctx, idx, cuil=cuil)
        if seccion is not None:
            _crear_alumno_banco_db(self.ctx, alumno, seccion)
        return alumno

    def _banco_de_alumno(self, alumno, seccion):
        return EspecialAlumnoBanco.objects.get(
            alumno=alumno,
            cueanexo=seccion.cueanexo,
            ciclo=seccion.ciclo,
        )

    def _post_inscribir_desde_alumnos(self, alumno_banco_id, seccion_id):
        url = reverse("especial:alumnos")
        with self._forzar_director():
            return self.client.post(
                f"{url}?cueanexo={self.ctx.cueanexo_permitido}&ciclo={self.ctx.ciclo_activo.pk}",
                {
                    "accion": "inscribir_seccion",
                    "alumno_banco_id": alumno_banco_id,
                    "seccion_id": seccion_id,
                },
            )

    def _post_baja_desde_alumnos(self, alumno_banco_id, motivo="Baja solicitada"):
        url = reverse("especial:alumnos")
        with self._forzar_director():
            return self.client.post(
                f"{url}?cueanexo={self.ctx.cueanexo_permitido}&ciclo={self.ctx.ciclo_activo.pk}",
                {
                    "accion": "baja_especial",
                    "alumno_banco_id": alumno_banco_id,
                    "motivo_baja": motivo,
                },
            )

    def _crear_inscripcion_baja(self, alumno, seccion):
        return _crear_inscripcion_db(self.ctx, alumno, seccion, estado=AlumnoSeccion.Estado.BAJA)

    def _crear_docente_y_banco(self, idx, seccion, rol=DocenteSeccion.Rol.TITULAR):
        cuil = _cuil_valido(f"20{98765000 + idx:08d}")
        _crear_banco_docente_db(self.ctx, cuil, seccion)
        return cuil, _crear_asignacion_docente_db(
            self.ctx,
            cuil,
            seccion,
            rol=rol,
            estado=DocenteSeccion.Estado.BAJA,
        )

    def test_inscripcion_nueva_valida_crea_registro(self):
        alumno = self._crear_alumno_y_banco(1, self.seccion)
        url = reverse("especial:inscripcion_seccion", kwargs={"seccion_id": self.seccion.pk})

        with self._forzar_director():
            response = self.client.post(
                f"{url}?cueanexo={self.ctx.cueanexo_permitido}&ciclo={self.ctx.ciclo_activo.pk}",
                {"cuil": alumno.cuil},
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            AlumnoSeccion.objects.filter(
                seccion=self.seccion,
                alumno=alumno,
                estado=AlumnoSeccion.Estado.ACTIVO,
            ).count(),
            1,
        )

    def test_inscripcion_ya_activa_no_duplica(self):
        alumno = self._crear_alumno_y_banco(2, self.seccion)
        _crear_inscripcion_db(self.ctx, alumno, self.seccion, estado=AlumnoSeccion.Estado.ACTIVO)
        url = reverse("especial:inscripcion_seccion", kwargs={"seccion_id": self.seccion.pk})

        with self._forzar_director():
            response = self.client.post(
                f"{url}?cueanexo={self.ctx.cueanexo_permitido}&ciclo={self.ctx.ciclo_activo.pk}",
                {"cuil": alumno.cuil},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            AlumnoSeccion.objects.filter(
                seccion=self.seccion,
                alumno=alumno,
                estado=AlumnoSeccion.Estado.ACTIVO,
            ).count(),
            1,
        )

    def test_inscripcion_sin_cupo_rechaza_y_no_persiste(self):
        alumno_ocupa = self._crear_alumno_y_banco(3, self.seccion)
        alumno_bloqueado = self._crear_alumno_y_banco(4, self.seccion)
        _crear_inscripcion_db(self.ctx, alumno_ocupa, self.seccion, estado=AlumnoSeccion.Estado.ACTIVO)
        url = reverse("especial:inscripcion_seccion", kwargs={"seccion_id": self.seccion.pk})

        with self._forzar_director():
            response = self.client.post(
                f"{url}?cueanexo={self.ctx.cueanexo_permitido}&ciclo={self.ctx.ciclo_activo.pk}",
                {"cuil": alumno_bloqueado.cuil},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            AlumnoSeccion.objects.filter(
                seccion=self.seccion,
                estado=AlumnoSeccion.Estado.ACTIVO,
            ).count(),
            1,
        )
        self.assertFalse(
            AlumnoSeccion.objects.filter(
                seccion=self.seccion,
                alumno=alumno_bloqueado,
            ).exists()
        )

    def test_ultimo_cupo_en_concurrencia_no_supera_capacidad(self):
        alumno_a = self._crear_alumno_y_banco(5, self.seccion)
        alumno_b = self._crear_alumno_y_banco(6, self.seccion)
        inscripcion_a = self._crear_inscripcion_baja(alumno_a, self.seccion)
        inscripcion_b = self._crear_inscripcion_baja(alumno_b, self.seccion)
        barrier = threading.Barrier(2)
        resultados = []

        def _trabajo(inscripcion_pk):
            close_old_connections()
            try:
                barrier.wait()
                inscripcion = AlumnoSeccion.objects.get(pk=inscripcion_pk)
                dar_alta_inscripcion_seccion(
                    inscripcion,
                    self.admin,
                    seccion_queryset=SeccionEspecial.objects.filter(
                        cueanexo=self.ctx.cueanexo_permitido,
                        ciclo=self.ctx.ciclo_activo,
                    ),
                    alumno_banco_queryset=EspecialAlumnoBanco.objects.filter(
                        cueanexo=self.ctx.cueanexo_permitido,
                        ciclo=self.ctx.ciclo_activo,
                    ),
                )
                resultados.append(("ok", inscripcion_pk))
            except Exception as exc:  # noqa: BLE001
                resultados.append(("error", inscripcion_pk, exc))
            finally:
                close_old_connections()

        hilos = [
            threading.Thread(target=_trabajo, args=(inscripcion_a.pk,)),
            threading.Thread(target=_trabajo, args=(inscripcion_b.pk,)),
        ]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join()

        exito = [item for item in resultados if item[0] == "ok"]
        errores = [item for item in resultados if item[0] == "error"]
        self.assertEqual(len(exito), 1)
        self.assertEqual(len(errores), 1)
        self.assertEqual(
            AlumnoSeccion.objects.filter(
                seccion=self.seccion,
                estado=AlumnoSeccion.Estado.ACTIVO,
            ).count(),
            1,
        )
        self.assertTrue(
            AlumnoSeccion.objects.filter(
                pk=inscripcion_a.pk,
                estado=AlumnoSeccion.Estado.ACTIVO,
            ).exists()
            or AlumnoSeccion.objects.filter(
                pk=inscripcion_b.pk,
                estado=AlumnoSeccion.Estado.ACTIVO,
            ).exists()
        )

    def test_reactivacion_de_inscripcion_respeta_cupo(self):
        alumno_primero = self._crear_alumno_y_banco(7, self.seccion)
        alumno_segundo = self._crear_alumno_y_banco(8, self.seccion)
        inscripcion_primera = self._crear_inscripcion_baja(alumno_primero, self.seccion)
        inscripcion_segunda = self._crear_inscripcion_baja(alumno_segundo, self.seccion)

        dar_alta_inscripcion_seccion(
            inscripcion_primera,
            self.admin,
            seccion_queryset=SeccionEspecial.objects.filter(
                cueanexo=self.ctx.cueanexo_permitido,
                ciclo=self.ctx.ciclo_activo,
            ),
            alumno_banco_queryset=EspecialAlumnoBanco.objects.filter(
                cueanexo=self.ctx.cueanexo_permitido,
                ciclo=self.ctx.ciclo_activo,
            ),
        )

        with self.assertRaises(ValidationError):
            dar_alta_inscripcion_seccion(
                inscripcion_segunda,
                self.admin,
                seccion_queryset=SeccionEspecial.objects.filter(
                    cueanexo=self.ctx.cueanexo_permitido,
                    ciclo=self.ctx.ciclo_activo,
                ),
                alumno_banco_queryset=EspecialAlumnoBanco.objects.filter(
                    cueanexo=self.ctx.cueanexo_permitido,
                    ciclo=self.ctx.ciclo_activo,
                ),
            )

        self.assertEqual(
            AlumnoSeccion.objects.filter(
                seccion=self.seccion,
                estado=AlumnoSeccion.Estado.ACTIVO,
            ).count(),
            1,
        )

    def test_rollback_ante_integrity_error_en_alta_nueva(self):
        alumno = self._crear_alumno_y_banco(9, self.seccion)
        url = reverse("especial:inscripcion_seccion", kwargs={"seccion_id": self.seccion.pk})

        with self._forzar_director(), patch(
            "apps.especial.views_inscripcion_seccion.AlumnoSeccion.objects.create",
            side_effect=IntegrityError("constraint"),
        ):
            response = self.client.post(
                f"{url}?cueanexo={self.ctx.cueanexo_permitido}&ciclo={self.ctx.ciclo_activo.pk}",
                {"cuil": alumno.cuil},
            )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            AlumnoSeccion.objects.filter(
                seccion=self.seccion,
                alumno=alumno,
            ).exists()
        )

    def test_alumnos_post_inscribir_seccion_valida_crea_registro(self):
        alumno = self._crear_alumno_y_banco(10, self.seccion)
        banco = self._banco_de_alumno(alumno, self.seccion)

        response = self._post_inscribir_desde_alumnos(banco.pk, self.seccion.pk)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            AlumnoSeccion.objects.filter(
                alumno=alumno,
                seccion=self.seccion,
                estado=AlumnoSeccion.Estado.ACTIVO,
            ).count(),
            1,
        )

    def test_alumnos_post_rechaza_seccion_de_otro_cue(self):
        alumno = self._crear_alumno_y_banco(11, self.seccion)
        banco = self._banco_de_alumno(alumno, self.seccion)

        response = self._post_inscribir_desde_alumnos(banco.pk, self.seccion_ajena.pk)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(AlumnoSeccion.objects.filter(alumno=alumno).exists())

    def test_alumnos_post_rechaza_seccion_de_otro_ciclo(self):
        seccion_otro_ciclo = _crear_seccion_db(
            self.ctx,
            self.ctx.cueanexo_permitido,
            "Seccion otro ciclo",
            ciclo=self.ctx.ciclo_inactivo,
        )
        alumno = self._crear_alumno_y_banco(12, self.seccion)
        banco = self._banco_de_alumno(alumno, self.seccion)

        response = self._post_inscribir_desde_alumnos(banco.pk, seccion_otro_ciclo.pk)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(AlumnoSeccion.objects.filter(alumno=alumno).exists())

    def test_alumnos_post_rechaza_banco_de_otro_contexto(self):
        alumno = _crear_alumno_db(self.ctx, 13)
        banco_ajeno = _crear_alumno_banco_db(self.ctx, alumno, self.seccion_ajena)

        response = self._post_inscribir_desde_alumnos(banco_ajeno.pk, self.seccion.pk)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(AlumnoSeccion.objects.filter(alumno=alumno).exists())

    def test_alumnos_post_rechaza_banco_inactivo(self):
        alumno = self._crear_alumno_y_banco(14, self.seccion)
        banco = self._banco_de_alumno(alumno, self.seccion)
        EspecialAlumnoBanco.objects.filter(pk=banco.pk).update(
            estado=EspecialAlumnoBanco.Estado.INACTIVO,
        )

        response = self._post_inscribir_desde_alumnos(banco.pk, self.seccion.pk)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(AlumnoSeccion.objects.filter(alumno=alumno).exists())

    def test_alumnos_post_no_duplica_inscripcion_activa(self):
        alumno = self._crear_alumno_y_banco(15, self.seccion)
        banco = self._banco_de_alumno(alumno, self.seccion)
        _crear_inscripcion_db(self.ctx, alumno, self.seccion, estado=AlumnoSeccion.Estado.ACTIVO)

        response = self._post_inscribir_desde_alumnos(banco.pk, self.seccion.pk)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            AlumnoSeccion.objects.filter(
                alumno=alumno,
                seccion=self.seccion,
                estado=AlumnoSeccion.Estado.ACTIVO,
            ).count(),
            1,
        )

    def test_alumnos_post_rechaza_seccion_sin_cupo(self):
        alumno_ocupa = self._crear_alumno_y_banco(16, self.seccion)
        alumno_objetivo = self._crear_alumno_y_banco(17, self.seccion)
        banco_objetivo = self._banco_de_alumno(alumno_objetivo, self.seccion)
        _crear_inscripcion_db(
            self.ctx,
            alumno_ocupa,
            self.seccion,
            estado=AlumnoSeccion.Estado.ACTIVO,
        )

        response = self._post_inscribir_desde_alumnos(
            banco_objetivo.pk,
            self.seccion.pk,
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            AlumnoSeccion.objects.filter(
                alumno=alumno_objetivo,
                seccion=self.seccion,
            ).exists()
        )
        self.assertEqual(
            AlumnoSeccion.objects.filter(
                seccion=self.seccion,
                estado=AlumnoSeccion.Estado.ACTIVO,
            ).count(),
            1,
        )

    def test_alumnos_post_reactiva_inscripcion_en_baja_sin_duplicar(self):
        alumno = self._crear_alumno_y_banco(18, self.seccion)
        banco = self._banco_de_alumno(alumno, self.seccion)
        inscripcion = self._crear_inscripcion_baja(alumno, self.seccion)

        response = self._post_inscribir_desde_alumnos(banco.pk, self.seccion.pk)

        inscripcion.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(inscripcion.estado, AlumnoSeccion.Estado.ACTIVO)
        self.assertEqual(
            AlumnoSeccion.objects.filter(
                alumno=alumno,
                seccion=self.seccion,
            ).count(),
            1,
        )

    def test_baja_alumno_valida_conserva_registro_y_persiste_auditoria(self):
        alumno = self._crear_alumno_y_banco(19, self.seccion)
        banco = self._banco_de_alumno(alumno, self.seccion)
        total_antes = EspecialAlumnoBanco.objects.count()

        response = self._post_baja_desde_alumnos(banco.pk, "  Cambio de trayectoria  ")

        banco.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(banco.estado, EspecialAlumnoBanco.Estado.BAJA)
        self.assertEqual(banco.fecha_baja, date.today())
        self.assertEqual(banco.motivo_baja, "Cambio de trayectoria")
        self.assertEqual(EspecialAlumnoBanco.objects.count(), total_antes)
        self.assertFalse(AlumnoSeccion.objects.filter(alumno=alumno).exists())

        with self._forzar_director():
            lista_response = self.client.get(
                reverse("especial:alumnos"),
                {
                    "cueanexo": self.ctx.cueanexo_permitido,
                    "ciclo": self.ctx.ciclo_activo.pk,
                },
            )

        self.assertContains(lista_response, banco.fecha_baja.strftime("%d/%m/%Y"))
        self.assertContains(lista_response, "Cambio de trayectoria")

    def test_baja_alumno_rechaza_motivo_vacio_sin_mutar(self):
        alumno = self._crear_alumno_y_banco(20, self.seccion)
        banco = self._banco_de_alumno(alumno, self.seccion)

        response = self._post_baja_desde_alumnos(banco.pk, "   ")

        banco.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(banco.estado, EspecialAlumnoBanco.Estado.ACTIVO)
        self.assertFalse(banco.fecha_baja)
        self.assertFalse(banco.motivo_baja)
        self.assertFalse(response.context["modal_alumno_abierto"])
        self.assertEqual(response.context["baja_modal_alumno"].pk, banco.pk)

    def test_baja_alumno_rechaza_inscripciones_activas_y_no_las_elimina(self):
        seccion_dos = _crear_seccion_db(self.ctx, self.ctx.cueanexo_permitido, "Seccion 2", capacidad=2)
        alumno = self._crear_alumno_y_banco(21, self.seccion)
        banco = self._banco_de_alumno(alumno, self.seccion)
        _crear_inscripcion_db(self.ctx, alumno, self.seccion, estado=AlumnoSeccion.Estado.ACTIVO)
        _crear_inscripcion_db(self.ctx, alumno, seccion_dos, estado=AlumnoSeccion.Estado.ACTIVO)

        response = self._post_baja_desde_alumnos(banco.pk)

        banco.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(banco.estado, EspecialAlumnoBanco.Estado.ACTIVO)
        self.assertEqual(
            AlumnoSeccion.objects.filter(
                alumno=alumno,
                estado=AlumnoSeccion.Estado.ACTIVO,
            ).count(),
            2,
        )
        self.assertFalse(response.context["modal_alumno_abierto"])
        self.assertEqual(response.context["baja_modal_alumno"].pk, banco.pk)

    def test_get_baja_abre_solo_el_modal_de_baja(self):
        alumno = self._crear_alumno_y_banco(29, self.seccion)
        banco = self._banco_de_alumno(alumno, self.seccion)

        with self._forzar_director():
            response = self.client.get(
                reverse("especial:alumnos"),
                {
                    "cueanexo": self.ctx.cueanexo_permitido,
                    "ciclo": self.ctx.ciclo_activo.pk,
                    "abrir_modal_baja": "1",
                    "alumno_banco_id": banco.pk,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["baja_modal_alumno"].pk, banco.pk)
        self.assertFalse(response.context["modal_alumno_abierto"])

    def test_baja_no_muestra_acciones_de_alta_ni_inscripcion(self):
        alumno = self._crear_alumno_y_banco(30, self.seccion)
        banco = self._banco_de_alumno(alumno, self.seccion)
        self._post_baja_desde_alumnos(banco.pk)

        with self._forzar_director():
            response = self.client.get(
                reverse("especial:alumnos"),
                {
                    "cueanexo": self.ctx.cueanexo_permitido,
                    "ciclo": self.ctx.ciclo_activo.pk,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "cef-row-inactive")
        self.assertNotContains(response, "Dar de baja de Especial")
        self.assertNotContains(response, "Inscribir a secci&oacute;n")

    def test_baja_alumno_rechaza_banco_de_otro_contexto_sin_mutar(self):
        alumno = _crear_alumno_db(self.ctx, 22)
        banco_ajeno = _crear_alumno_banco_db(self.ctx, alumno, self.seccion_ajena)

        response = self._post_baja_desde_alumnos(banco_ajeno.pk)

        banco_ajeno.refresh_from_db()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(banco_ajeno.estado, EspecialAlumnoBanco.Estado.ACTIVO)

    def test_baja_alumno_rechaza_banco_de_otro_ciclo_sin_mutar(self):
        seccion_otro_ciclo = _crear_seccion_db(
            self.ctx,
            self.ctx.cueanexo_permitido,
            "Seccion otro ciclo",
            ciclo=self.ctx.ciclo_inactivo,
        )
        alumno = _crear_alumno_db(self.ctx, 23)
        banco_ajeno = _crear_alumno_banco_db(self.ctx, alumno, seccion_otro_ciclo)

        response = self._post_baja_desde_alumnos(banco_ajeno.pk)

        banco_ajeno.refresh_from_db()
        self.assertEqual(response.status_code, 404)
        self.assertEqual(banco_ajeno.estado, EspecialAlumnoBanco.Estado.ACTIVO)

    def test_baja_alumno_ya_baja_no_repite_ni_altera(self):
        alumno = self._crear_alumno_y_banco(24, self.seccion)
        banco = self._banco_de_alumno(alumno, self.seccion)
        fecha_previa = date(2026, 8, 1)
        EspecialAlumnoBanco.objects.filter(pk=banco.pk).update(
            estado=EspecialAlumnoBanco.Estado.BAJA,
            fecha_baja=fecha_previa,
            motivo_baja="Baja previa",
        )

        response = self._post_baja_desde_alumnos(banco.pk, "Otro motivo")

        banco.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(banco.estado, EspecialAlumnoBanco.Estado.BAJA)
        self.assertEqual(banco.fecha_baja, fecha_previa)
        self.assertEqual(banco.motivo_baja, "Baja previa")

    def test_despues_de_baja_no_crea_inscripcion_activa(self):
        alumno = self._crear_alumno_y_banco(25, self.seccion)
        banco = self._banco_de_alumno(alumno, self.seccion)
        self._post_baja_desde_alumnos(banco.pk)

        response = self._post_inscribir_desde_alumnos(banco.pk, self.seccion.pk)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            AlumnoSeccion.objects.filter(
                alumno=alumno,
                seccion=self.seccion,
                estado=AlumnoSeccion.Estado.ACTIVO,
            ).exists()
        )

    def test_despues_de_baja_no_reactiva_inscripcion_en_baja(self):
        alumno = self._crear_alumno_y_banco(26, self.seccion)
        banco = self._banco_de_alumno(alumno, self.seccion)
        inscripcion = self._crear_inscripcion_baja(alumno, self.seccion)
        self._post_baja_desde_alumnos(banco.pk)

        with self.assertRaises(ValidationError):
            dar_alta_inscripcion_seccion(
                inscripcion,
                self.admin,
                seccion_queryset=SeccionEspecial.objects.filter(
                    cueanexo=self.ctx.cueanexo_permitido,
                    ciclo=self.ctx.ciclo_activo,
                ),
                alumno_banco_queryset=EspecialAlumnoBanco.objects.filter(
                    cueanexo=self.ctx.cueanexo_permitido,
                    ciclo=self.ctx.ciclo_activo,
                ),
            )

        inscripcion.refresh_from_db()
        self.assertEqual(inscripcion.estado, AlumnoSeccion.Estado.BAJA)

    def test_baja_con_inscripcion_activa_rechaza_ids_manipulados_sin_mutar(self):
        alumno = self._crear_alumno_y_banco(27, self.seccion)
        banco = self._banco_de_alumno(alumno, self.seccion)
        _crear_inscripcion_db(self.ctx, alumno, self.seccion, estado=AlumnoSeccion.Estado.ACTIVO)

        response = self._post_baja_desde_alumnos(
            banco.pk,
            "Motivo válido",
        )

        banco.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(banco.estado, EspecialAlumnoBanco.Estado.ACTIVO)
        self.assertTrue(
            AlumnoSeccion.objects.filter(
                alumno=alumno,
                seccion=self.seccion,
                estado=AlumnoSeccion.Estado.ACTIVO,
            ).exists()
        )

    def test_concurrencia_baja_vs_inscripcion_no_deja_estado_inconsistente(self):
        if connection.vendor != "postgresql":
            self.skipTest("La prueba de locks requiere PostgreSQL.")

        alumno = self._crear_alumno_y_banco(28, self.seccion)
        banco = self._banco_de_alumno(alumno, self.seccion)
        barrier = threading.Barrier(2)
        resultados = []

        def trabajo_baja():
            close_old_connections()
            try:
                barrier.wait()
                banco_local = EspecialAlumnoBanco.objects.get(pk=banco.pk)
                dar_baja_alumno_banco(
                    alumno_banco=banco_local,
                    user=self.admin,
                    motivo_baja="Baja concurrente",
                    alumno_banco_queryset=EspecialAlumnoBanco.objects.filter(
                        cueanexo=self.ctx.cueanexo_permitido,
                        ciclo=self.ctx.ciclo_activo,
                    ),
                )
                resultados.append(("baja", "ok"))
            except Exception as exc:  # noqa: BLE001
                resultados.append(("baja", exc))
            finally:
                close_old_connections()

        def trabajo_inscripcion():
            close_old_connections()
            try:
                barrier.wait()
                seccion_local = SeccionEspecial.objects.get(pk=self.seccion.pk)
                alumno_local = Alumno.objects.get(pk=alumno.pk)
                crear_inscripcion_activa(
                    seccion=seccion_local,
                    alumno=alumno_local,
                    user=self.admin,
                    seccion_queryset=SeccionEspecial.objects.filter(
                        cueanexo=self.ctx.cueanexo_permitido,
                        ciclo=self.ctx.ciclo_activo,
                    ),
                    alumno_banco_queryset=EspecialAlumnoBanco.objects.filter(
                        cueanexo=self.ctx.cueanexo_permitido,
                        ciclo=self.ctx.ciclo_activo,
                    ),
                )
                resultados.append(("inscripcion", "ok"))
            except Exception as exc:  # noqa: BLE001
                resultados.append(("inscripcion", exc))
            finally:
                close_old_connections()

        hilos = [
            threading.Thread(target=trabajo_baja),
            threading.Thread(target=trabajo_inscripcion),
        ]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join()

        banco.refresh_from_db()
        inscripcion_activa = AlumnoSeccion.objects.filter(
            alumno=alumno,
            seccion=self.seccion,
            estado=AlumnoSeccion.Estado.ACTIVO,
        ).exists()
        self.assertFalse(
            banco.estado == EspecialAlumnoBanco.Estado.BAJA and inscripcion_activa
        )

    def test_alta_docente_nuevo_valida_y_persiste(self):
        cuil = _cuil_valido("2098765000")
        _crear_banco_docente_db(self.ctx, cuil, self.seccion)
        url = reverse("especial:gestionar_seccion", kwargs={"seccion_id": self.seccion.pk})

        with self._forzar_director():
            response = self.client.post(
                f"{url}?cueanexo={self.ctx.cueanexo_permitido}&ciclo={self.ctx.ciclo_activo.pk}",
                {
                    "accion": "alta_docente",
                    "cuil": cuil,
                    "rol": DocenteSeccion.Rol.TITULAR,
                    "estado": DocenteSeccion.Estado.ACTIVO,
                    "fecha_desde": "",
                    "fecha_hasta": "",
                    "observaciones": "",
                },
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            DocenteSeccion.objects.filter(
                seccion=self.seccion,
                docente_cuil=cuil,
                estado=DocenteSeccion.Estado.ACTIVO,
            ).count(),
            1,
        )

    def test_alta_docente_nuevo_rechaza_cuil_invalido_sin_escritura(self):
        cuil = "123"
        url = reverse("especial:gestionar_seccion", kwargs={"seccion_id": self.seccion.pk})

        with self._forzar_director():
            response = self.client.post(
                f"{url}?cueanexo={self.ctx.cueanexo_permitido}&ciclo={self.ctx.ciclo_activo.pk}",
                {
                    "accion": "alta_docente",
                    "cuil": cuil,
                    "rol": DocenteSeccion.Rol.TITULAR,
                    "estado": DocenteSeccion.Estado.ACTIVO,
                    "fecha_desde": "",
                    "fecha_hasta": "",
                    "observaciones": "",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            DocenteSeccion.objects.filter(
                seccion=self.seccion,
                docente_cuil=cuil,
            ).exists()
        )

    def test_alta_docente_nuevo_rechaza_duplicado_activo_y_no_modifica_datos(self):
        cuil_activo = _cuil_valido("2098765001")
        cuil_nuevo = _cuil_valido("2098765002")
        _crear_banco_docente_db(self.ctx, cuil_activo, self.seccion)
        _crear_banco_docente_db(self.ctx, cuil_nuevo, self.seccion)
        _crear_asignacion_docente_db(
            self.ctx,
            cuil_activo,
            self.seccion,
            rol=DocenteSeccion.Rol.TITULAR,
            estado=DocenteSeccion.Estado.ACTIVO,
        )
        url = reverse("especial:gestionar_seccion", kwargs={"seccion_id": self.seccion.pk})

        with self._forzar_director():
            response = self.client.post(
                f"{url}?cueanexo={self.ctx.cueanexo_permitido}&ciclo={self.ctx.ciclo_activo.pk}",
                {
                    "accion": "alta_docente",
                    "cuil": cuil_nuevo,
                    "rol": DocenteSeccion.Rol.TITULAR,
                    "estado": DocenteSeccion.Estado.ACTIVO,
                    "fecha_desde": "",
                    "fecha_hasta": "",
                    "observaciones": "",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            DocenteSeccion.objects.filter(
                seccion=self.seccion,
                docente_cuil=cuil_nuevo,
            ).exists()
        )
        self.assertEqual(
            DocenteSeccion.objects.filter(
                seccion=self.seccion,
                rol=DocenteSeccion.Rol.TITULAR,
                estado=DocenteSeccion.Estado.ACTIVO,
            ).count(),
            1,
        )

    def test_reactivacion_docente_valida_y_duplicate_role_rechazado(self):
        cuil_a = _cuil_valido("2098765003")
        cuil_b = _cuil_valido("2098765004")
        _crear_banco_docente_db(self.ctx, cuil_a, self.seccion)
        _crear_banco_docente_db(self.ctx, cuil_b, self.seccion)
        asignacion_a = _crear_asignacion_docente_db(
            self.ctx,
            cuil_a,
            self.seccion,
            rol=DocenteSeccion.Rol.SUPLENTE,
            estado=DocenteSeccion.Estado.BAJA,
        )
        asignacion_b = _crear_asignacion_docente_db(
            self.ctx,
            cuil_b,
            self.seccion,
            rol=DocenteSeccion.Rol.SUPLENTE,
            estado=DocenteSeccion.Estado.BAJA,
        )

        dar_alta_docente_seccion(asignacion_a, self.admin)
        self.assertEqual(
            DocenteSeccion.objects.filter(
                seccion=self.seccion,
                docente_cuil=cuil_a,
                estado=DocenteSeccion.Estado.ACTIVO,
            ).count(),
            1,
        )

        with self.assertRaises(ValidationError):
            dar_alta_docente_seccion(asignacion_b, self.admin)

        self.assertEqual(
            DocenteSeccion.objects.filter(
                seccion=self.seccion,
                rol=DocenteSeccion.Rol.SUPLENTE,
                estado=DocenteSeccion.Estado.ACTIVO,
            ).count(),
            1,
        )


class EspecialPerformanceTests(SimpleTestCase):
    def _request(self, query=None, **headers):
        request = RequestFactory().get("/especial/alumnos/", query or {}, **headers)
        request.session = {}
        return request

    def _logged_payload(self, logger_mock):
        self.assertEqual(logger_mock.warning.call_count, 1)
        self.assertEqual(logger_mock.info.call_count, 0)
        return json.loads(logger_mock.warning.call_args.args[1])

    def test_perf_begin_disabled_with_debug_false_does_not_touch_session(self):
        request = self._request({"especial_perf": "1"})
        request.session = MagicMock()

        with override_settings(DEBUG=False):
            self.assertFalse(perf_begin(request))

        request.session.get.assert_not_called()
        self.assertFalse(hasattr(request, "_especial_perf_after"))

    def test_perf_begin_activation_and_deactivation_use_especial_session_key(self):
        session = {}
        request = RequestFactory().get("/especial/alumnos/", {"especial_perf": "1"})
        request.session = session

        with override_settings(DEBUG=True), patch("apps.especial.performance.logger"):
            self.assertTrue(perf_begin(request))
            self.assertTrue(session[PERF_SESSION_KEY])
            self.assertEqual(len(request._especial_perf_after["id"]), 12)
            perf_finish(request)

        disabled_request = RequestFactory().get("/especial/alumnos/", {"especial_perf": "0"})
        disabled_request.session = session
        with override_settings(DEBUG=True):
            self.assertFalse(perf_begin(disabled_request))
        self.assertFalse(session[PERF_SESSION_KEY])

    def test_perf_phase_is_noop_when_disabled_and_measures_when_enabled(self):
        disabled = self._request()
        with override_settings(DEBUG=True):
            self.assertFalse(perf_begin(disabled))
            with perf_phase(disabled, "view"):
                result = "ok"
        self.assertEqual(result, "ok")

        enabled = self._request({"especial_perf": "1"})
        with override_settings(DEBUG=True), patch("apps.especial.performance.logger") as logger_mock:
            self.assertTrue(perf_begin(enabled))
            with perf_phase(enabled, "view"):
                with perf_phase(enabled, "context"):
                    nested_result = "ok"
            perf_finish(enabled, response=HttpResponse("html"))

        self.assertEqual(nested_result, "ok")
        payload = self._logged_payload(logger_mock)
        self.assertIn("view", payload["durations_ms"])
        self.assertIn("context", payload["durations_ms"])

    def test_perf_capture_groups_queries_by_alias_and_phase_without_logging_sql(self):
        request = self._request(
            {"especial_perf": "1", "dni": "20123456789", "q": "privado"},
            HTTP_X_ESPECIAL_PARTIAL="1",
        )
        connections_mock = MagicMock()
        installed = {}

        def fake_connection(alias):
            connection = SimpleNamespace(alias=alias)

            @contextmanager
            def install(wrapper):
                installed[alias] = wrapper
                yield

            connection.execute_wrapper = install
            return connection

        connections_mock.all.return_value = [fake_connection("default"), fake_connection("padron")]

        with override_settings(DEBUG=True), patch(
            "apps.especial.performance.connections", connections_mock
        ), patch("apps.especial.performance.logger") as logger_mock:
            self.assertTrue(perf_begin(request))
            perf_capture_queries(request)

            def execute(_sql, _params, _many, _context):
                return "ok"

            with perf_phase(request, "view"):
                self.assertEqual(
                    installed["default"](execute, "SELECT CUIL", ("DNI",), False, {}),
                    "ok",
                )
                with perf_phase(request, "context"):
                    installed["padron"](execute, "SELECT email", ("privado",), False, {})
                installed["default"](execute, "SELECT telefono", ("secreto",), False, {})

            perf_finish(request, response=HttpResponse("html"))

        payload = self._logged_payload(logger_mock)
        self.assertEqual(payload["partial"], True)
        self.assertEqual(payload["status_code"], 200)
        self.assertEqual(payload["response_bytes"], 4)
        self.assertEqual(payload["sql"]["count"], 3)
        self.assertEqual(payload["sql"]["by_alias"]["default"]["count"], 2)
        self.assertEqual(payload["sql"]["by_alias"]["padron"]["count"], 1)
        self.assertEqual(payload["sql"]["by_phase"]["view"]["count"], 2)
        self.assertEqual(payload["sql"]["by_phase"]["context"]["count"], 1)
        self.assertNotIn("SELECT", json.dumps(payload))
        self.assertNotIn("20123456789", json.dumps(payload))
        self.assertNotIn("privado", json.dumps(payload))

    def test_disabled_capture_does_not_install_sql_wrappers(self):
        request = self._request()
        with override_settings(DEBUG=True), patch("apps.especial.performance.connections") as connections_mock:
            self.assertFalse(perf_begin(request))
            perf_capture_queries(request)
        connections_mock.all.assert_not_called()

    def test_partial_and_full_classification_uses_only_partial_header(self):
        for header_value, expected in (("1", True), ("0", False), (None, False)):
            with self.subTest(header_value=header_value):
                headers = {}
                if header_value is not None:
                    headers["HTTP_X_ESPECIAL_PARTIAL"] = header_value
                request = self._request({"especial_perf": "1"}, **headers)
                with override_settings(DEBUG=True), patch("apps.especial.performance.logger"):
                    self.assertTrue(perf_begin(request))
                    self.assertEqual(request._especial_perf_after["partial"], expected)
                    perf_finish(request)

    def test_especial_required_preserves_permission_denied(self):
        request = self._request({"especial_perf": "1"})
        request.user = SimpleNamespace(is_authenticated=True)

        @especial_required
        def protected(_request):
            self.fail("la vista no debe ejecutarse sin permisos")

        with override_settings(DEBUG=True), patch(
            "apps.especial.permisos.get_permisos_especial_request",
            return_value={"puede_ver": False},
        ), patch("apps.especial.permisos.perf_capture_queries"), patch(
            "apps.especial.performance.logger"
        ) as logger_mock:
            with self.assertRaises(PermissionDenied):
                protected(request)

        payload = self._logged_payload(logger_mock)
        self.assertEqual(payload["error_type"], "PermissionDenied")

    def test_especial_required_reraises_original_view_exception(self):
        request = self._request({"especial_perf": "1"})
        request.user = SimpleNamespace(is_authenticated=True)
        expected = ValueError("interno")

        @especial_required
        def protected(_request):
            raise expected

        with override_settings(DEBUG=True), patch(
            "apps.especial.permisos.get_permisos_especial_request",
            return_value={"puede_ver": True},
        ), patch("apps.especial.permisos.perf_capture_queries"), patch(
            "apps.especial.performance.logger"
        ) as logger_mock:
            with self.assertRaises(ValueError) as caught:
                protected(request)

        self.assertIs(caught.exception, expected)
        payload = self._logged_payload(logger_mock)
        self.assertEqual(payload["error_type"], "ValueError")
        self.assertNotIn("interno", json.dumps(payload))

    def test_final_log_uses_warning_once_and_not_info(self):
        request = self._request({"especial_perf": "1"})

        with override_settings(DEBUG=True), patch("apps.especial.performance.logger") as logger_mock:
            self.assertTrue(perf_begin(request))
            perf_finish(request, response=HttpResponse("ok"))
            perf_finish(request, response=HttpResponse("duplicado"))

        self.assertEqual(logger_mock.warning.call_count, 1)
        self.assertEqual(logger_mock.info.call_count, 0)

    def test_wrapper_installation_failure_closes_partial_stack_and_reraises(self):
        request = self._request({"especial_perf": "1"})
        request.user = SimpleNamespace(is_authenticated=True)
        expected = RuntimeError("fallo de wrapper")
        state = {"closed": False}

        @contextmanager
        def install_first(_wrapper):
            try:
                yield
            finally:
                state["closed"] = True

        first = SimpleNamespace(alias="default", execute_wrapper=install_first)

        def install_failing(_wrapper):
            raise expected

        failing = SimpleNamespace(alias="padron", execute_wrapper=install_failing)
        connections_mock = MagicMock()
        connections_mock.all.return_value = [first, failing]
        view_called = []

        @especial_required
        def protected(_request):
            view_called.append(True)
            return HttpResponse("no debe ejecutarse")

        with override_settings(DEBUG=True), patch(
            "apps.especial.performance.connections", connections_mock
        ), patch(
            "apps.especial.permisos.get_permisos_especial_request",
            return_value={"puede_ver": True},
        ), patch("apps.especial.performance.logger") as logger_mock:
            with self.assertRaises(RuntimeError) as caught:
                protected(request)

        self.assertIs(caught.exception, expected)
        self.assertTrue(state["closed"])
        self.assertEqual(view_called, [])
        payload = self._logged_payload(logger_mock)
        self.assertEqual(payload["error_type"], "RuntimeError")

    def test_especial_required_success_returns_same_response(self):
        request = self._request({"especial_perf": "1"})
        request.user = SimpleNamespace(is_authenticated=True)
        expected = HttpResponse("respuesta")

        @especial_required
        def protected(_request):
            return expected

        connections_mock = MagicMock()
        connections_mock.all.return_value = []
        with override_settings(DEBUG=True), patch(
            "apps.especial.performance.connections", connections_mock
        ), patch(
            "apps.especial.permisos.get_permisos_especial_request",
            return_value={"puede_ver": True},
        ), patch("apps.especial.performance.logger") as logger_mock:
            response = protected(request)

        self.assertIs(response, expected)
        self._logged_payload(logger_mock)

    def test_especial_required_disabled_does_not_capture(self):
        request = self._request()
        request.user = SimpleNamespace(is_authenticated=True)
        expected = HttpResponse("respuesta")

        @especial_required
        def protected(_request):
            return expected

        with override_settings(DEBUG=True), patch(
            "apps.especial.permisos.get_permisos_especial_request",
            return_value={"puede_ver": True},
        ), patch("apps.especial.permisos.perf_capture_queries") as capture_mock:
            response = protected(request)

        self.assertIs(response, expected)
        capture_mock.assert_not_called()

    def test_context_subphases_are_present_with_non_negative_durations(self):
        request = self._request({"especial_perf": "1"})
        ciclo = SimpleNamespace(pk=2026)
        establecimiento = SimpleNamespace(cueanexo="123456789")
        escuelas = MagicMock()
        escuelas.filter.return_value.order_by.return_value.first.return_value = establecimiento
        permisos = {
            "es_admin": False,
            "escuelas_visualizacion": escuelas,
            "cueanexos_cargables": ["123456789"],
            "cueanexos_visualizacion": ["123456789"],
        }

        with override_settings(DEBUG=True), patch(
            "apps.especial.performance.logger"
        ) as logger_mock, patch(
            "apps.especial.views_contexto.get_permisos_especial_request",
            return_value=permisos,
        ), patch(
            "apps.especial.views_contexto._especial_options_usuario",
            return_value=[{"cueanexo": "123456789"}],
        ), patch(
            "apps.especial.views_contexto._resolver_cueanexo",
            return_value="123456789",
        ), patch(
            "apps.especial.views_contexto._resolver_ciclo",
            return_value=(ciclo, [ciclo]),
        ), patch("apps.especial.views_contexto._alumnos_url", return_value=""), patch(
            "apps.especial.views_contexto.cache"
        ) as cache_mock:
            cache_mock.get.return_value = _CACHE_MISS_CONTEXTO
            self.assertTrue(perf_begin(request))
            contexto = contexto_base(request, "alumnos")["especial_context"]
            perf_finish(request)

        self.assertEqual(
            contexto["establecimiento"].cueanexo,
            establecimiento.cueanexo,
        )
        payload = self._logged_payload(logger_mock)
        for phase in ("context.options", "context.cycle", "context.establishment"):
            self.assertIn(phase, payload["durations_ms"])
            self.assertGreaterEqual(payload["durations_ms"][phase], 0)

    def test_context_operations_keep_order_and_execute_once(self):
        request = self._request({"especial_perf": "1"})
        ciclo = SimpleNamespace(pk=2026)
        events = []
        establecimiento = SimpleNamespace(cueanexo="123456789")
        escuelas = MagicMock()
        filtered = MagicMock()
        ordered = MagicMock()
        escuelas.filter.side_effect = lambda **kwargs: (events.append("establishment.filter") or filtered)
        filtered.order_by.side_effect = lambda *args: (events.append("establishment.order_by") or ordered)
        ordered.first.side_effect = lambda: (events.append("establishment.first") or establecimiento)
        permisos = {
            "es_admin": False,
            "escuelas_visualizacion": escuelas,
            "cueanexos_cargables": ["123456789"],
            "cueanexos_visualizacion": ["123456789"],
        }

        def options(_permisos, scope):
            events.append(("options", scope))
            return [{"cueanexo": "123456789"}]

        def cueanexo(_request, options_result):
            events.append(("cueanexo", options_result))
            return "123456789"

        def cycle(_request):
            events.append("cycle")
            return ciclo, [ciclo]

        with override_settings(DEBUG=True), patch(
            "apps.especial.performance.logger"
        ), patch(
            "apps.especial.views_contexto.get_permisos_especial_request",
            return_value=permisos,
        ), patch(
            "apps.especial.views_contexto._especial_options_usuario",
            side_effect=options,
        ), patch(
            "apps.especial.views_contexto._resolver_cueanexo",
            side_effect=cueanexo,
        ), patch(
            "apps.especial.views_contexto._resolver_ciclo",
            side_effect=cycle,
        ), patch("apps.especial.views_contexto._alumnos_url", return_value=""), patch(
            "apps.especial.views_contexto.cache"
        ) as cache_mock:
            cache_mock.get.return_value = _CACHE_MISS_CONTEXTO
            self.assertTrue(perf_begin(request))
            contexto = contexto_base(request, "cueanexo")["especial_context"]
            perf_finish(request)

        self.assertEqual(
            contexto["establecimiento"].cueanexo,
            establecimiento.cueanexo,
        )
        self.assertEqual(
            events,
            [
                ("options", "visualizacion"),
                ("cueanexo", [{"cueanexo": "123456789"}]),
                "cycle",
                "establishment.filter",
                "establishment.order_by",
                "establishment.first",
            ],
        )

    def test_context_establishment_is_not_queried_without_cueanexo(self):
        request = self._request({"especial_perf": "1"})
        ciclo = SimpleNamespace(pk=2026)
        escuelas = MagicMock()
        permisos = {
            "es_admin": False,
            "escuelas_visualizacion": escuelas,
            "cueanexos_cargables": [],
            "cueanexos_visualizacion": [],
        }

        with override_settings(DEBUG=True), patch(
            "apps.especial.performance.logger"
        ) as logger_mock, patch(
            "apps.especial.views_contexto.get_permisos_especial_request",
            return_value=permisos,
        ), patch(
            "apps.especial.views_contexto._especial_options_usuario",
            return_value=[],
        ), patch(
            "apps.especial.views_contexto._resolver_cueanexo",
            return_value="",
        ), patch(
            "apps.especial.views_contexto._resolver_ciclo",
            return_value=(ciclo, [ciclo]),
        ), patch("apps.especial.views_contexto._alumnos_url", return_value=""):
            self.assertTrue(perf_begin(request))
            contexto = contexto_base(request, "alumnos")["especial_context"]
            perf_finish(request)

        self.assertIsNone(contexto["establecimiento"])
        escuelas.filter.assert_not_called()
        payload = self._logged_payload(logger_mock)
        self.assertIn("context.establishment", payload["durations_ms"])

    def test_context_subphase_sql_is_attributed_by_phase(self):
        request = self._request({"especial_perf": "1"})
        ciclo = SimpleNamespace(pk=2026)
        establecimiento = SimpleNamespace(cueanexo="123456789")
        escuelas = MagicMock()
        filtered = MagicMock()
        ordered = MagicMock()
        escuelas.filter.return_value = filtered
        filtered.order_by.return_value = ordered
        ordered.first.side_effect = lambda: (sql_call() or establecimiento)
        permisos = {
            "es_admin": False,
            "escuelas_visualizacion": escuelas,
            "cueanexos_cargables": ["123456789"],
            "cueanexos_visualizacion": ["123456789"],
        }
        installed = {}

        @contextmanager
        def install(wrapper):
            installed["wrapper"] = wrapper
            yield

        connection = SimpleNamespace(alias="default", execute_wrapper=install)
        connections_mock = MagicMock()
        connections_mock.all.return_value = [connection]

        def sql_call():
            installed["wrapper"](
                lambda _sql, _params, _many, _context: None,
                "SELECT 1",
                (),
                False,
                {},
            )

        def options(_permisos, scope):
            sql_call()
            return [{"cueanexo": "123456789"}]

        def cycle(_request):
            sql_call()
            return ciclo, [ciclo]

        with override_settings(DEBUG=True), patch(
            "apps.especial.performance.connections", connections_mock
        ), patch("apps.especial.performance.logger") as logger_mock, patch(
            "apps.especial.views_contexto.get_permisos_especial_request",
            return_value=permisos,
        ), patch(
            "apps.especial.views_contexto._especial_options_usuario",
            side_effect=options,
        ), patch(
            "apps.especial.views_contexto._resolver_cueanexo",
            return_value="123456789",
        ), patch(
            "apps.especial.views_contexto._resolver_ciclo",
            side_effect=cycle,
        ), patch("apps.especial.views_contexto._alumnos_url", return_value=""), patch(
            "apps.especial.views_contexto.cache"
        ) as cache_mock:
            self.assertTrue(perf_begin(request))
            perf_capture_queries(request)
            cache_mock.get.return_value = _CACHE_MISS_CONTEXTO
            contexto_base(request, "alumnos")
            perf_finish(request)

        payload = self._logged_payload(logger_mock)
        for phase in ("context.options", "context.cycle", "context.establishment"):
            self.assertEqual(payload["sql"]["by_phase"][phase]["count"], 1)

    def _cache_request(self, pk=7):
        request = self._request()
        request.user = SimpleNamespace(pk=pk)
        return request

    def _cache_permissions(self, cueanexos=("123456789",), role="Director"):
        escuelas = MagicMock()
        return {
            "rol": role,
            "puede_ver": role in {"Administrador", "Director", "Director de Modalidad Especial"},
            "es_admin": role == "Administrador",
            "cueanexos_cargables": list(cueanexos),
            "cueanexos_visualizacion": list(cueanexos),
            "escuelas_cargables": escuelas,
            "escuelas_visualizacion": escuelas,
        }

    def _establishment_payload(self, cueanexo="123456789"):
        payload = {field: f"valor-{field}" for field in ESTABLECIMIENTO_CACHE_FIELDS}
        payload["cueanexo"] = cueanexo
        return payload

    def test_context_cache_ttl_is_exactly_five_minutes(self):
        self.assertEqual(CACHE_TTL_CONTEXTO_ESPECIAL, 300)
        self.assertEqual(CACHE_TTL_LOCALIZACIONES_ESPECIAL, 300)
        self.assertTrue(CACHE_VERSION_CONTEXTO_ESPECIAL.startswith("v2_"))
        self.assertTrue(CACHE_VERSION_LOCALIZACIONES_ESPECIAL.startswith("v2_"))

    def test_options_cache_key_depends_on_identity_scope_role_and_authorized_set(self):
        request = self._cache_request(pk=7)
        permisos = self._cache_permissions(("123456789", "987654321"))
        base_key = _cache_key_especial_options(request, permisos, "cargables")
        self.assertIn(CACHE_VERSION_CONTEXTO_ESPECIAL, base_key)

        same_set_different_order = self._cache_permissions(("987654321", "123456789"))
        self.assertEqual(
            base_key,
            _cache_key_especial_options(request, same_set_different_order, "cargables"),
        )

        changed_user = self._cache_request(pk=8)
        changed_role = self._cache_permissions(("123456789", "987654321"), role="Administrador")
        changed_authorized_set = self._cache_permissions(("123456789", "987654321"))
        changed_authorized_set["cueanexos_cargables"] = ["123456789"]

        self.assertNotEqual(base_key, _cache_key_especial_options(changed_user, permisos, "cargables"))
        self.assertNotEqual(base_key, _cache_key_especial_options(request, changed_role, "cargables"))
        self.assertNotEqual(base_key, _cache_key_especial_options(request, permisos, "visualizacion"))
        self.assertNotEqual(
            base_key,
            _cache_key_especial_options(request, changed_authorized_set, "cargables"),
        )
        with patch(
            "apps.especial.views_contexto.CACHE_VERSION_CONTEXTO_ESPECIAL",
            "v2_contexto_test",
        ):
            self.assertNotEqual(base_key, _cache_key_especial_options(request, permisos, "cargables"))

    def test_options_cache_bypasses_cache_for_user_without_pk(self):
        request = self._cache_request(pk=None)
        permisos = self._cache_permissions()
        expected = [{"cueanexo": "123456789", "nombre": "Escuela"}]

        with patch("apps.especial.views_contexto.cache") as cache_mock, patch(
            "apps.especial.views_contexto._especial_options_usuario",
            return_value=expected,
        ) as build_options:
            result = _get_especial_options_cached(request, permisos, "cargables")

        self.assertEqual(result, expected)
        build_options.assert_called_once_with(permisos, scope="cargables")
        cache_mock.get.assert_not_called()
        cache_mock.set.assert_not_called()

    def test_options_cache_miss_builds_once_and_uses_ttl(self):
        request = self._cache_request()
        permisos = self._cache_permissions()
        expected = [{"cueanexo": "123456789", "nombre": "Escuela"}]

        with patch("apps.especial.views_contexto.cache") as cache_mock, patch(
            "apps.especial.views_contexto._especial_options_usuario",
            return_value=expected,
        ) as build_options:
            cache_mock.get.return_value = _CACHE_MISS_CONTEXTO
            result = _get_especial_options_cached(request, permisos, "cargables")

        self.assertEqual(result, expected)
        build_options.assert_called_once_with(permisos, scope="cargables")
        cache_mock.set.assert_called_once()
        self.assertEqual(cache_mock.set.call_args.args[1], expected)
        self.assertEqual(cache_mock.set.call_args.args[2], 300)

    def test_options_cache_hit_and_empty_list_do_not_rebuild(self):
        request = self._cache_request()
        permisos = self._cache_permissions()
        for cached in (
            [{"cueanexo": "123456789", "nombre": "Escuela"}],
            [],
        ):
            with self.subTest(cached=cached), patch(
                "apps.especial.views_contexto.cache"
            ) as cache_mock, patch(
                "apps.especial.views_contexto._especial_options_usuario"
            ) as build_options:
                cache_mock.get.return_value = cached
                result = _get_especial_options_cached(request, permisos, "cargables")

            self.assertEqual(result, cached)
            build_options.assert_not_called()
            cache_mock.set.assert_not_called()

    def test_invalid_options_cache_rebuilds_and_replaces_payload(self):
        request = self._cache_request()
        permisos = self._cache_permissions()
        expected = [{"cueanexo": "123456789", "nombre": "Escuela"}]

        with patch("apps.especial.views_contexto.cache") as cache_mock, patch(
            "apps.especial.views_contexto._especial_options_usuario",
            return_value=expected,
        ) as build_options:
            cache_mock.get.return_value = {"cueanexo": "123456789"}
            result = _get_especial_options_cached(request, permisos, "cargables")

        self.assertEqual(result, expected)
        build_options.assert_called_once()
        self.assertEqual(cache_mock.set.call_args.args[1], expected)
        self.assertEqual(cache_mock.set.call_args.args[2], 300)

    def test_establishment_rejects_unauthorized_cue_before_cache_get(self):
        permisos = self._cache_permissions(("123456789",))

        with patch("apps.especial.views_contexto.cache") as cache_mock:
            with self.assertRaises(PermissionDenied):
                _get_establecimiento_cached(permisos, "987654321", "cargables")

        cache_mock.get.assert_not_called()
        permisos["escuelas_visualizacion"].filter.assert_not_called()

    def test_establishment_hit_returns_attribute_compatible_object(self):
        permisos = self._cache_permissions()
        payload = self._establishment_payload()

        with patch("apps.especial.views_contexto.cache") as cache_mock:
            cache_mock.get.return_value = payload
            result = _get_establecimiento_cached(permisos, "123456789", "cargables")

        self.assertEqual(result.nom_est, payload["nom_est"])
        self.assertTrue(datos_establecimiento_items(result))
        permisos["escuelas_visualizacion"].filter.assert_not_called()

    def test_establishment_admin_hit_uses_total_scope_without_cue_set(self):
        permisos = self._cache_permissions((), role="Administrador")
        payload = self._establishment_payload()

        with patch("apps.especial.views_contexto.cache") as cache_mock:
            cache_mock.get.return_value = payload
            result = _get_establecimiento_cached(permisos, "123456789", "visualizacion")

        self.assertEqual(result.cueanexo, "123456789")
        cache_mock.get.assert_called_once()
        permisos["escuelas_visualizacion"].filter.assert_not_called()

    def test_establishment_miss_queries_authorized_queryset_and_serializes_fields(self):
        permisos = self._cache_permissions()
        model = SimpleNamespace(**self._establishment_payload())
        queryset = permisos["escuelas_visualizacion"]
        queryset.filter.return_value.order_by.return_value.first.return_value = model

        with patch("apps.especial.views_contexto.cache") as cache_mock:
            cache_mock.get.return_value = _CACHE_MISS_CONTEXTO
            result = _get_establecimiento_cached(permisos, "123456789", "cargables")

        queryset.filter.assert_called_once_with(cueanexo="123456789")
        queryset.filter.return_value.order_by.assert_called_once_with("cueanexo", "nom_est")
        queryset.filter.return_value.order_by.return_value.first.assert_called_once_with()
        self.assertEqual(result.nom_est, model.nom_est)
        cached_payload = cache_mock.set.call_args.args[1]
        self.assertEqual(set(cached_payload), set(ESTABLECIMIENTO_CACHE_FIELDS))
        self.assertNotIn(model, cached_payload.values())
        self.assertEqual(cache_mock.set.call_args.args[2], 300)

    def test_establishment_none_is_cached_as_valid_result(self):
        permisos = self._cache_permissions()
        queryset = permisos["escuelas_visualizacion"]
        queryset.filter.return_value.order_by.return_value.first.return_value = None

        with patch("apps.especial.views_contexto.cache") as cache_mock:
            cache_mock.get.side_effect = [_CACHE_MISS_CONTEXTO, None]
            first = _get_establecimiento_cached(permisos, "123456789", "cargables")
            second = _get_establecimiento_cached(permisos, "123456789", "cargables")

        self.assertIsNone(first)
        self.assertIsNone(second)
        queryset.filter.return_value.order_by.return_value.first.assert_called_once_with()
        self.assertIsNone(cache_mock.set.call_args.args[1])

    def test_warm_options_and_establishment_hits_generate_no_sql(self):
        request = self._cache_request()
        permisos = self._cache_permissions()
        options = [{"cueanexo": "123456789", "nombre": "Escuela"}]
        establishment = self._establishment_payload()
        installed = {}

        @contextmanager
        def install(wrapper):
            installed["wrapper"] = wrapper
            yield

        connection = SimpleNamespace(alias="default", execute_wrapper=install)
        connections_mock = MagicMock()
        connections_mock.all.return_value = [connection]

        with override_settings(DEBUG=True), patch(
            "apps.especial.performance.connections", connections_mock
        ), patch("apps.especial.performance.logger") as logger_mock, patch(
            "apps.especial.views_contexto.cache"
        ) as cache_mock:
            cache_mock.get.side_effect = [options, establishment]
            self.assertTrue(perf_begin(request))
            perf_capture_queries(request)
            with perf_phase(request, "context"):
                with perf_phase(request, "context.options"):
                    self.assertEqual(_get_especial_options_cached(request, permisos, "cargables"), options)
                with perf_phase(request, "context.establishment"):
                    self.assertEqual(
                        _get_establecimiento_cached(permisos, "123456789", "cargables").nom_est,
                        establishment["nom_est"],
                    )
            perf_finish(request)

        self.assertTrue(installed)
        self.assertEqual(permisos["escuelas_visualizacion"].filter.call_count, 0)
        self.assertEqual(self._logged_payload(logger_mock)["sql"]["count"], 0)
