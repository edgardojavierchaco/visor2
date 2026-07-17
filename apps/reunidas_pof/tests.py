from inspect import unwrap
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.test import RequestFactory, SimpleTestCase

from . import forms as pof_forms
from . import models, permisos, views
from .models import (
    ROL_POF_DIRECTOR,
    ROL_POF_REGIONAL,
    ROLES_POF_ACCESO_COMPLETO,
    ROLES_POF_SOLO_VISUALIZACION_COMPLETA,
    VCapaUnicaOfertasAnt,
    obtener_cueanexos_director_pof,
    obtener_regiones_usuario_pof,
)
from .services import carga_service
from .services import guardado_pof_service
from .services import visualizacion_cargos_localizacion_service as visualizacion_service


class RolesPofTests(SimpleTestCase):
    def test_roles_centralizados_coinciden_con_la_matriz(self):
        self.assertEqual(ROLES_POF_ACCESO_COMPLETO, {"Pof", "Administrador"})
        self.assertIn("Director de Nivel Inicial", ROLES_POF_SOLO_VISUALIZACION_COMPLETA)
        self.assertNotIn(ROL_POF_REGIONAL, ROLES_POF_SOLO_VISUALIZACION_COMPLETA)
        self.assertNotIn(ROL_POF_DIRECTOR, ROLES_POF_SOLO_VISUALIZACION_COMPLETA)


class AniosDisponiblesCargaPofTests(SimpleTestCase):
    def test_validacion_cabecera_admite_anio_posterior_si_la_pof_existe(self):
        reunida = SimpleNamespace(
            id=10,
            anio=2099,
            nivel="ADULTOS",
            get_nivel_display=lambda: "Adultos",
        )
        manager = MagicMock()
        manager.filter.return_value.first.return_value = reunida

        with patch.object(carga_service.ReunidaPof, "objects", manager):
            resultado = carga_service.validar_cabecera_reunida(2099, "ADULTOS")

        self.assertTrue(resultado["ok"])
        manager.filter.assert_called_once_with(anio=2099, nivel="ADULTOS")

    def test_formulario_guardado_admite_anio_posterior_si_la_pof_existe(self):
        manager = MagicMock()
        manager.filter.return_value.exists.return_value = True

        with patch.object(pof_forms.ReunidaPof, "objects", manager):
            formulario = pof_forms.GuardarCargaPofForm({
                "cabecera_tipo": "REUNIDA",
                "anio": 2099,
                "nivel": "ADULTOS",
                "tipo_operacion": "ALTA",
            })

            self.assertTrue(formulario.is_valid(), formulario.errors)

    def test_servicio_guardado_admite_anio_posterior_si_la_pof_existe(self):
        manager = MagicMock()
        manager.filter.return_value.exists.return_value = True
        datos = {
            "cabecera_tipo": "REUNIDA",
            "anio": 2099,
            "nivel": "ADULTOS",
            "tipo_operacion": "ALTA",
            "padron": {
                "padron_cueanexo": "123456700",
                "cuof_loc": "123",
            },
            "cargos": [{
                "ceic": "1",
                "cantidad": 1,
                "unidad_cantidad": "CARGO",
                "observacion": "",
            }],
        }

        with patch.object(guardado_pof_service.ReunidaPof, "objects", manager):
            errores = guardado_pof_service._validar_datos_guardado_minimos(datos)

        self.assertNotIn("anio", errores)


class AsociacionesPofTests(SimpleTestCase):
    def test_regiones_elimina_nulos_espacios_y_duplicados(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [
            (" Región I ",),
            (None,),
            ("",),
            ("Región I",),
            ("Región II",),
        ]
        cursor_contexto = MagicMock()
        cursor_contexto.__enter__.return_value = cursor

        user = SimpleNamespace(username="20123456789")
        with patch.object(
            models.connection,
            "cursor",
            return_value=cursor_contexto,
        ):
            regiones = obtener_regiones_usuario_pof(user)

        self.assertEqual(regiones, {"Región I", "Región II"})
        self.assertEqual(cursor.execute.call_args.args[1], ["20123456789"])

    def test_director_prioriza_padron_cueanexo_y_conserva_el_valor_completo(self):
        manager = MagicMock()
        manager.using.return_value.filter.return_value.values_list.return_value = [
            (" 123456700 ", "999999999"),
            (None, "123456701"),
            ("123456700", None),
            (None, ""),
        ]
        user = SimpleNamespace(username="20-12345678-9")

        with patch.object(VCapaUnicaOfertasAnt, "objects", manager):
            cueanexos = obtener_cueanexos_director_pof(user)

        self.assertEqual(cueanexos, {"123456700", "123456701"})
        filtro = manager.using.return_value.filter.call_args.kwargs
        self.assertIn("20-12345678-9", filtro["resploc_cuitcuil__in"])
        self.assertIn("20123456789", filtro["resploc_cuitcuil__in"])


class DecoradoresPofTests(SimpleTestCase):
    def setUp(self):
        self.request_factory = RequestFactory()
        self.user = SimpleNamespace(is_authenticated=True)

    def test_vista_administrativa_rechaza_usuario_sin_acceso_completo(self):
        request = self.request_factory.get("/administracion/")
        request.user = self.user
        vista = permisos.pof_required(lambda request: JsonResponse({"ok": True}))

        with patch.object(permisos, "usuario_tiene_acceso_completo_pof", return_value=False):
            with self.assertRaises(PermissionDenied):
                vista(request)

    def test_api_administrativa_devuelve_403(self):
        request = self.request_factory.post("/administracion/")
        request.user = self.user
        vista = permisos.pof_api_required(lambda request: JsonResponse({"ok": True}))

        with patch.object(permisos, "usuario_tiene_acceso_completo_pof", return_value=False):
            response = vista(request)

        self.assertEqual(response.status_code, 403)

    def test_api_visualizacion_admite_capacidad_de_consulta(self):
        request = self.request_factory.get("/visualizacion/")
        request.user = self.user
        vista = permisos.pof_visualizacion_api_required(
            lambda request: JsonResponse({"ok": True})
        )

        with patch.object(permisos, "usuario_puede_ver_visualizacion_pof", return_value=True):
            response = vista(request)

        self.assertEqual(response.status_code, 200)

    def test_inicio_muestra_acceso_rapido_limitado_a_usuario_solo_visualizacion(self):
        request = self.request_factory.get("/")
        request.user = self.user
        response_esperada = Mock()

        with patch.object(views, "usuario_tiene_acceso_completo_pof", return_value=False), patch.object(
            views,
            "render",
            return_value=response_esperada,
        ) as render_mock:
            response = unwrap(views.inicio)(request)

        self.assertIs(response, response_esperada)
        render_mock.assert_called_once_with(
            request,
            "reunidas_pof/inicio.html",
            {"pof_solo_visualizacion": True},
        )


class AlcanceVisualizacionPofTests(SimpleTestCase):
    def test_acceso_completo_y_consulta_general_no_reciben_filtro_de_datos(self):
        for rol in ("Pof", "Administrador", "Director de Nivel Inicial"):
            with self.subTest(rol=rol):
                queryset = Mock()
                with patch.object(
                    visualizacion_service,
                    "obtener_rol_usuario_pof",
                    return_value=rol,
                ):
                    resultado = visualizacion_service._aplicar_alcance_visualizacion(
                        queryset,
                        SimpleNamespace(),
                    )

                self.assertIs(resultado, queryset)
                queryset.filter.assert_not_called()
                queryset.none.assert_not_called()

    def test_regional_filtra_por_snapshot_vigente_y_regiones_asociadas(self):
        queryset = Mock()
        queryset.filter.return_value = Mock()
        user = SimpleNamespace()

        with patch.object(
            visualizacion_service,
            "obtener_rol_usuario_pof",
            return_value=ROL_POF_REGIONAL,
        ), patch.object(
            visualizacion_service,
            "obtener_regiones_usuario_pof",
            return_value={"Región I", "Región II"},
        ):
            resultado = visualizacion_service._aplicar_alcance_visualizacion(
                queryset,
                user,
            )

        self.assertIs(resultado, queryset.filter.return_value)
        queryset.filter.assert_called_once_with(
            localizacion__snapshots_padron__vigente=True,
            localizacion__snapshots_padron__region__in={"Región I", "Región II"},
        )

    def test_regional_sin_asociaciones_no_recibe_acceso_general(self):
        queryset = Mock()
        queryset.none.return_value = Mock()

        with patch.object(
            visualizacion_service,
            "obtener_rol_usuario_pof",
            return_value=ROL_POF_REGIONAL,
        ), patch.object(
            visualizacion_service,
            "obtener_regiones_usuario_pof",
            return_value=set(),
        ):
            resultado = visualizacion_service._aplicar_alcance_visualizacion(
                queryset,
                SimpleNamespace(),
            )

        self.assertIs(resultado, queryset.none.return_value)

    def test_director_filtra_por_cueanexo_completo_exacto(self):
        queryset = Mock()
        queryset.filter.return_value = Mock()
        cueanexos = {"123456700", "123456701"}

        with patch.object(
            visualizacion_service,
            "obtener_rol_usuario_pof",
            return_value=ROL_POF_DIRECTOR,
        ), patch.object(
            visualizacion_service,
            "obtener_cueanexos_director_pof",
            return_value=cueanexos,
        ):
            resultado = visualizacion_service._aplicar_alcance_visualizacion(
                queryset,
                SimpleNamespace(),
            )

        self.assertIs(resultado, queryset.filter.return_value)
        queryset.filter.assert_called_once_with(localizacion__cueanexo__in=cueanexos)

    def test_director_sin_asociaciones_no_recibe_acceso_general(self):
        queryset = Mock()
        queryset.none.return_value = Mock()

        with patch.object(
            visualizacion_service,
            "obtener_rol_usuario_pof",
            return_value=ROL_POF_DIRECTOR,
        ), patch.object(
            visualizacion_service,
            "obtener_cueanexos_director_pof",
            return_value=set(),
        ):
            resultado = visualizacion_service._aplicar_alcance_visualizacion(
                queryset,
                SimpleNamespace(),
            )

        self.assertIs(resultado, queryset.none.return_value)
