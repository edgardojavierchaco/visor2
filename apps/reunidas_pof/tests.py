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
                "tipo_operacion": "AFECTADO",
            })

            self.assertTrue(formulario.is_valid(), formulario.errors)

    def test_servicio_guardado_admite_anio_posterior_si_la_pof_existe(self):
        manager = MagicMock()
        manager.filter.return_value.exists.return_value = True
        datos = {
            "cabecera_tipo": "REUNIDA",
            "anio": 2099,
            "nivel": "ADULTOS",
            "tipo_operacion": "AFECTADO",
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


class VisualizacionFiltrosCanonicosTests(SimpleTestCase):
    """
    Verifica la normalizacion compartida entre busqueda rapida y filtros avanzados.

    - Mantiene el CUE como busqueda parcial en la ruta canonica.
    - Traduce URLs legacy sin duplicar criterios del mismo campo.
    - Conserva la acumulacion y el OR de multiples valores avanzados.
    """

    def setUp(self):
        self.request_factory = RequestFactory()

    def test_filtro_cue_parecido_usa_icontains(self):
        consulta = visualizacion_service._filtro_avanzado_q("cue", "0", "313")

        self.assertEqual(
            consulta.children,
            [("localizacion__cueanexo__icontains", "313")],
        )

    def test_busqueda_columna_cue_usa_icontains(self):
        queryset = Mock()
        visualizacion_service._aplicar_busqueda_columna(queryset, "cue", "313")

        filtro_q = queryset.filter.call_args.args[0]
        self.assertEqual(
            filtro_q.children,
            [("localizacion__cueanexo__icontains", "313")],
        )

    def test_busqueda_rapida_numerica_usa_la_anotacion_textual_canonica(self):
        filtro_q = visualizacion_service._filtro_avanzado_q("cantidad", "0", "2")

        self.assertEqual(
            filtro_q.children,
            [("cantidad_busqueda__icontains", "2")],
        )

    def test_columna_legacy_se_convierte_en_un_chip_avanzado(self):
        request = self.request_factory.get("/visualizacion/?col_cue=313")

        filtros = visualizacion_service._obtener_filtros_avanzados(request)
        chips = visualizacion_service._armar_chips(filtros)

        self.assertEqual(
            filtros,
            [{
                "indice": None,
                "campo": "cue",
                "operador": "0",
                "valor": "313",
                "origen": "legacy_columna",
            }],
        )
        self.assertEqual(len(chips), 1)
        self.assertEqual(chips[0]["texto"], "CUE parecido a: 313")
        self.assertEqual(chips[0]["tipo"], "avanzado")
        self.assertEqual(chips[0]["origen"], "legacy_columna")

    def test_filtro_avanzado_gana_sobre_columna_legacy_del_mismo_campo(self):
        request = self.request_factory.get(
            "/visualizacion/?col_cue=313&campo_filtro=cue&operador_filtro=2&valor_filtro=522522"
        )

        filtros = visualizacion_service._obtener_filtros_avanzados(request)

        self.assertEqual(
            [(filtro["campo"], filtro["operador"], filtro["valor"]) for filtro in filtros],
            [("cue", "2", "522522")],
        )

    def test_columna_legacy_se_conserva_si_la_tripleta_avanzada_es_invalida(self):
        request = self.request_factory.get(
            "/visualizacion/?col_cue=313&campo_filtro=cue&operador_filtro=99&valor_filtro=522522"
        )

        filtros = visualizacion_service._obtener_filtros_avanzados(request)

        self.assertEqual(
            [(filtro["campo"], filtro["operador"], filtro["valor"]) for filtro in filtros],
            [("cue", "0", "313")],
        )

    def test_columnas_legacy_de_campos_distintos_se_acumulan(self):
        request = self.request_factory.get(
            "/visualizacion/?col_cue=313&col_cuof=ABC"
        )

        filtros = visualizacion_service._obtener_filtros_avanzados(request)

        self.assertEqual(
            [(filtro["campo"], filtro["valor"]) for filtro in filtros],
            [("cue", "313"), ("cuof", "ABC")],
        )

    def test_multiples_valores_avanzados_del_mismo_campo_se_conservan(self):
        request = self.request_factory.get(
            "/visualizacion/?campo_filtro=oferta&campo_filtro=oferta"
            "&operador_filtro=0&operador_filtro=0"
            "&valor_filtro=Primaria&valor_filtro=Secundaria"
        )

        filtros = visualizacion_service._obtener_filtros_avanzados(request)

        self.assertEqual(
            [(filtro["campo"], filtro["valor"]) for filtro in filtros],
            [("oferta", "Primaria"), ("oferta", "Secundaria")],
        )

    def test_chips_conservan_multiples_valores_del_mismo_campo(self):
        filtros = [
            {"indice": 0, "campo": "cue", "operador": "0", "valor": "313"},
            {"indice": 1, "campo": "cue", "operador": "0", "valor": "522"},
        ]

        chips = visualizacion_service._armar_chips(filtros)

        self.assertEqual(
            [chip["valor"] for chip in chips],
            ["313", "522"],
        )

    def test_barra_no_muestra_un_valor_si_hay_dos_campos_canonicos(self):
        filtros = [
            {"campo": "cue", "operador": "0", "valor": "313"},
            {"campo": "cuof", "operador": "0", "valor": "ABC"},
        ]

        self.assertEqual(
            visualizacion_service._obtener_busqueda_columna_activa(filtros),
            ("cueanexo", ""),
        )

    def test_barra_no_muestra_un_operador_distinto_de_parecido(self):
        filtros = [{"campo": "cue", "operador": "2", "valor": "313"}]

        self.assertEqual(
            visualizacion_service._obtener_busqueda_columna_activa(filtros),
            ("cueanexo", ""),
        )

    def test_querystring_y_exportacion_reemplazan_columna_legacy(self):
        request = self.request_factory.get(
            "/visualizacion/?anio=2025&col_cue=313&page=2&page_size=50"
        )

        query = visualizacion_service._normalizar_query_filtros(request)
        exportacion = visualizacion_service._query_exportar_filtros(request)

        self.assertNotIn("col_cue", query)
        self.assertIn("campo_filtro=cue", query.urlencode())
        self.assertNotIn("page=", exportacion)
        self.assertNotIn("page_size=", exportacion)
        self.assertIn("operador_filtro=0", exportacion)
        self.assertIn("valor_filtro=313", exportacion)

    def test_querystring_no_duplica_legacy_cuando_gana_el_filtro_avanzado(self):
        request = self.request_factory.get(
            "/visualizacion/?col_cue=313&campo_filtro=cue&operador_filtro=2&valor_filtro=522522"
        )

        query = visualizacion_service._normalizar_query_filtros(request)

        self.assertEqual(query.getlist("campo_filtro"), ["cue"])
        self.assertEqual(query.getlist("operador_filtro"), ["2"])
        self.assertEqual(query.getlist("valor_filtro"), ["522522"])


class VisualizacionOrdenamientoTests(SimpleTestCase):
    def setUp(self):
        self.request_factory = RequestFactory()

    def _armar_columnas(self, querystring=""):
        request = self.request_factory.get(f"/visualizacion/?{querystring}")
        return visualizacion_service._armar_columnas(
            request,
            visualizacion_service.COLUMNAS_DEFAULT_IDS,
        )

    def _obtener_columna(self, columnas, columna_id):
        return next(columna for columna in columnas if columna["id"] == columna_id)

    def test_sin_orden_activo_el_siguiente_enlace_genera_asc(self):
        columnas = self._armar_columnas("anio=2025")
        cueanexo = self._obtener_columna(columnas, "cueanexo")
        query = self.request_factory.get(f"/?{cueanexo['order_querystring']}").GET

        self.assertEqual(query["orden"], "cueanexo")
        self.assertEqual(query["dir"], "asc")
        self.assertFalse(any(columna["order_active"] for columna in columnas))

    def test_orden_asc_activo_el_siguiente_enlace_genera_desc(self):
        columnas = self._armar_columnas("orden=cueanexo&dir=asc")
        cueanexo = self._obtener_columna(columnas, "cueanexo")
        query = self.request_factory.get(f"/?{cueanexo['order_querystring']}").GET

        self.assertEqual(query["orden"], "cueanexo")
        self.assertEqual(query["dir"], "desc")
        self.assertTrue(cueanexo["order_active"])
        self.assertEqual(cueanexo["order_dir"], "asc")

    def test_orden_desc_activo_el_siguiente_enlace_vuelve_al_predeterminado(self):
        columnas = self._armar_columnas("orden=cueanexo&dir=desc")
        cueanexo = self._obtener_columna(columnas, "cueanexo")
        query = self.request_factory.get(f"/?{cueanexo['order_querystring']}").GET

        self.assertNotIn("orden", query)
        self.assertNotIn("dir", query)
        columnas_predeterminadas = self._armar_columnas(query.urlencode())
        self.assertFalse(
            any(columna["order_active"] for columna in columnas_predeterminadas)
        )

    def test_vuelta_al_predeterminado_conserva_contexto_y_elimina_paginacion(self):
        columnas = self._armar_columnas(
            "anio=2025&cabecera_tipo=PROYECTO_ESPECIAL&proyecto_especial_id=34"
            "&campo_filtro=cue&operador_filtro=0&valor_filtro=313&q=maestra"
            "&visible_col=cueanexo&visible_col=cargo&page=3&page_size=50"
            "&orden=cueanexo&dir=desc"
        )
        cueanexo = self._obtener_columna(columnas, "cueanexo")
        query = self.request_factory.get(f"/?{cueanexo['order_querystring']}").GET

        self.assertEqual(query["anio"], "2025")
        self.assertEqual(query["cabecera_tipo"], "PROYECTO_ESPECIAL")
        self.assertEqual(query["proyecto_especial_id"], "34")
        self.assertEqual(query.getlist("campo_filtro"), ["cue"])
        self.assertEqual(query.getlist("operador_filtro"), ["0"])
        self.assertEqual(query.getlist("valor_filtro"), ["313"])
        self.assertEqual(query["q"], "maestra")
        self.assertEqual(query.getlist("visible_col"), ["cueanexo", "cargo"])
        self.assertNotIn("orden", query)
        self.assertNotIn("dir", query)
        self.assertNotIn("page", query)
        self.assertNotIn("page_size", query)

    def test_total_general_continua_sin_ser_ordenable(self):
        columnas = self._armar_columnas()
        total_general = self._obtener_columna(columnas, "total_general")

        self.assertFalse(total_general["ordenable"])
        self.assertEqual(total_general["order_querystring"], "")
        self.assertFalse(total_general["order_active"])

    def test_sin_orden_aplica_el_orden_predeterminado_existente(self):
        queryset = Mock()
        request = self.request_factory.get("/visualizacion/")

        resultado = visualizacion_service._aplicar_orden(queryset, request)

        self.assertIs(resultado, queryset.order_by.return_value)
        queryset.order_by.assert_called_once_with(
            "localizacion__cueanexo",
            "localizacion__cuof",
            "ceic",
            "id",
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
