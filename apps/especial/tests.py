from contextlib import contextmanager
from datetime import date
from decimal import Decimal
import threading
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, close_old_connections
from django.http import Http404
from django.test import Client, RequestFactory, SimpleTestCase, TestCase, TransactionTestCase, override_settings
from django.urls import reverse

from .forms import EspecialDocenteSeccionForm
from .models import AlumnoSeccion, DocenteSeccion, EspecialAlumnoBanco, EspecialDocenteBanco, SeccionEspecial
from .permisos import (
    _resolver_permisos_especial,
    especial_required,
    get_permisos_especial_request,
)
from .views_contexto import _resolver_ciclo
from .views_carga_seccion import _alta_docente_nuevo_gestionar
from .views_ciclo import _exigir_admin
from .views_docentes_seccion import dar_alta_docente_seccion
from .views_inscripcion_seccion import dar_alta_inscripcion_seccion
from .views_localizaciones import _get_items_base_authorized

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
            "Administrador": (True, ("111111111", "222222222")),
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


class AlcanceLocalizacionesTests(SimpleTestCase):
    def test_conserva_el_queryset_autorizado_sin_serializar_el_padron(self):
        permisos = {"escuelas_visualizacion": _FakeSchoolQuerySet(("111111111",))}

        queryset = _get_items_base_authorized(permisos)

        self.assertIs(queryset, permisos["escuelas_visualizacion"])
        self.assertIn("cueanexo", queryset.only_fields)


class ValidacionDocenteEspecialTests(SimpleTestCase):
    def test_formulario_no_reemplaza_full_clean_dinamicamente(self):
        instance = DocenteSeccion(docente_cuil="20123456789")

        EspecialDocenteSeccionForm(instance=instance)

        self.assertEqual(instance.full_clean.__func__, DocenteSeccion.full_clean)


class CierreIntegridadEspecialTests(SimpleTestCase):
    def test_queryset_autorizado_vacio_no_hace_fallback(self):
        queryset = MagicMock()
        queryset.model = SeccionEspecial
        queryset.select_for_update.return_value = queryset
        queryset.get.side_effect = SeccionEspecial.DoesNotExist
        inscripcion = SimpleNamespace(pk=8, seccion_id=7)

        with patch("apps.especial.views_inscripcion_seccion.SeccionEspecial.objects.filter") as fallback:
            with self.assertRaises(Http404):
                dar_alta_inscripcion_seccion(
                    inscripcion,
                    SimpleNamespace(),
                    seccion_queryset=queryset,
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
                dar_alta_inscripcion_seccion(inscripcion, self.admin)
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
        )

        with self.assertRaises(ValidationError):
            dar_alta_inscripcion_seccion(
                inscripcion_segunda,
                self.admin,
                seccion_queryset=SeccionEspecial.objects.filter(
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
