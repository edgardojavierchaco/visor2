from inspect import unwrap
from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace
from unittest import TestCase as UnitTestCase
from unittest.mock import MagicMock, Mock, patch

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.test import RequestFactory, SimpleTestCase
from openpyxl import load_workbook

from . import forms as pof_forms
from . import models, permisos, views
from .models import (
    ROL_POF_DIRECTOR,
    ROL_POF_REGIONAL,
    ROLES_AUTORIZADOS_POF,
    ROLES_POF_ACCESO_COMPLETO,
    ROLES_POF_SOLO_VISUALIZACION_COMPLETA,
    VCapaUnicaOfertasAnt,
    obtener_cueanexos_director_pof,
    obtener_regiones_usuario_pof,
)
from .services import anexo_pof_service
from .services import carga_service
from .services import exportacion_columnas_config as exportacion_columnas_service
from .services import exportacion_reunida as exportacion_service
from .services import exportacion_rows as exportacion_rows_service
from .services import guardado_pof_service
from .services import historial_service
from .services import reunidas_service
from .services import visualizacion_cargos_localizacion_service as visualizacion_service
from .services import zona_educativa_service
from .services.grilla_pof.detalle_politicas import obtener_politicas_detalle_reunida
from .services.grilla_pof.detalle_rows import construir_grupos_operativos_detalle


class RolesPofTests(SimpleTestCase):
    def test_roles_centralizados_coinciden_con_la_matriz(self):
        self.assertEqual(ROLES_POF_ACCESO_COMPLETO, {"Pof", "Administrador"})
        self.assertEqual(
            ROLES_POF_SOLO_VISUALIZACION_COMPLETA,
            {"Director General", "Subsecretario", "Gestor"},
        )
        self.assertEqual(
            ROLES_AUTORIZADOS_POF,
            {"Pof", "Administrador", "Director General", "Subsecretario", "Gestor"},
        )
        self.assertNotIn(ROL_POF_REGIONAL, ROLES_AUTORIZADOS_POF)
        self.assertNotIn(ROL_POF_DIRECTOR, ROLES_AUTORIZADOS_POF)
        self.assertNotIn("Director de Nivel Inicial", ROLES_AUTORIZADOS_POF)
        self.assertNotIn("Ministro", ROLES_AUTORIZADOS_POF)
        self.assertNotIn("Supervisor", ROLES_AUTORIZADOS_POF)


class ExportacionReunidaExcelTests(SimpleTestCase):
    def _abrir_excel_comun(self, columnas_config, filas, schema):
        contexto = {
            "es_proyecto_especial": False,
            "columnas": [columna["titulo"] for columna in columnas_config],
            "filas_exportacion": [],
            "filas_normalizadas_exportacion": filas,
            "columnas_exportacion_config": columnas_config,
            "schema_exportacion": schema,
            "separadores_filas_exportacion": [],
            "secciones_exportacion": [],
            "mensaje_exportacion": "",
            "nombre_archivo": "reunida.xlsx",
            "titulo_hoja": "Reunida",
            "titulo_excel": "Reunida POF",
            "reunida": {},
        }
        respuesta = views._crear_respuesta_excel_exportacion(contexto)
        return load_workbook(BytesIO(respuesta.content), data_only=False).active

    def _columnas_auxiliares(self, ws, cantidad_columnas_visibles):
        return {
            ws.cell(row=4, column=indice).value: indice
            for indice in range(cantidad_columnas_visibles + 1, ws.max_column + 1)
        }

    def test_clave_total_general_estandar_prioriza_cueanexo_y_aplica_fallbacks(self):
        helper = exportacion_service.obtener_clave_total_general_cueanexo_reunida

        self.assertEqual(
            helper({"cueanexo": " 111111100 ", "cuof": "10", "cue": "1111111"}),
            "CUEANEXO:111111100",
        )
        self.assertNotEqual(
            helper({"cueanexo": "111111100", "cue": "1111111"}),
            helper({"cueanexo": "111111101", "cue": "1111111"}),
        )
        self.assertEqual(helper({"cueanexo": "", "cuof": " 20 "}), "CUOF:20")
        self.assertEqual(
            helper({"cueanexo": "", "cuof": "", "localizacion_id": 30}),
            "LOCALIZACION:30",
        )
        self.assertEqual(helper({}, indice=4), "FILA:4")

    def test_preview_total_general_separa_cueanexos_del_mismo_cue(self):
        filas = [
            {"cueanexo": "111111100", "cue": "1111111", "cargo_id": 1},
            {"cueanexo": "111111100", "cue": "1111111", "cargo_id": 2},
            {"cueanexo": "111111101", "cue": "1111111", "cargo_id": 3},
        ]
        totales = {
            "CUEANEXO:111111100": Decimal("300"),
            "CUEANEXO:111111101": Decimal("50"),
        }
        columnas = [
            {"source": "cueanexo", "repetir": "por_cueanexo"},
            {"source": "total_general", "repetir": "por_cue"},
        ]

        exportacion_service._aplicar_totales_generales_preview_reunida(
            filas,
            "PRIMARIA",
            totales,
        )
        proyectadas = exportacion_service._proyectar_filas_exportacion(
            "PRIMARIA",
            filas,
            columnas,
        )

        self.assertEqual(
            proyectadas,
            [
                ["111111100", Decimal("300")],
                ["", ""],
                ["111111101", Decimal("50")],
            ],
        )
        self.assertEqual(filas[0]["total_general_exportacion"], Decimal("300"))
        self.assertEqual(filas[2]["total_general_exportacion"], Decimal("50"))

    def test_excel_total_general_no_encadena_cueanexos_del_mismo_cue(self):
        columnas_config = [
            {"source": "cueanexo", "titulo": "CUEANEXO", "repetir": "por_cueanexo"},
            {
                "source": "total_general",
                "titulo": "Total General",
                "repetir": "por_cue",
            },
        ]
        filas = [
            {
                "cueanexo": "111111100",
                "cue": "1111111",
                "estado_pof_codigo": views.CargoPof.EstadoPof.AFECTADO,
                "total": Decimal("100"),
            },
            {
                "cueanexo": "111111100",
                "cue": "1111111",
                "estado_pof_codigo": views.CargoPof.EstadoPof.AFECTADO,
                "total": Decimal("200"),
            },
            {
                "cueanexo": "111111100",
                "cue": "1111111",
                "estado_pof_codigo": views.CargoPof.EstadoPof.DESAFECTADO,
                "total": Decimal("0"),
            },
            {
                "cueanexo": "111111101",
                "cue": "1111111",
                "estado_pof_codigo": views.CargoPof.EstadoPof.AFECTADO,
                "total": Decimal("50"),
            },
        ]

        ws = self._abrir_excel_comun(
            columnas_config,
            filas,
            {"columnas": [], "grupo_total_general": ("cue",)},
        )
        auxiliares = self._columnas_auxiliares(ws, len(columnas_config))
        letra_total = ws.cell(
            4,
            auxiliares["_total_visible_grupo"],
        ).column_letter
        letra_grupo_visto = ws.cell(
            4,
            auxiliares["_grupo_visto_visible"],
        ).column_letter
        letra_es_afectado = ws.cell(
            4,
            auxiliares["_es_afectado"],
        ).column_letter

        self.assertIn(f"${letra_total}6", ws[f"{letra_total}5"].value)
        self.assertIn(f"${letra_total}7", ws[f"{letra_total}6"].value)
        self.assertNotIn(f"${letra_total}8", ws[f"{letra_total}7"].value)
        self.assertEqual(ws[f"{letra_es_afectado}7"].value, 0)
        self.assertNotIn(f"${letra_grupo_visto}7", ws[f"{letra_grupo_visto}8"].value)
        self.assertIn("0=0", ws["B8"].value)
        self.assertEqual(
            [columna.colId for columna in ws.auto_filter.filterColumn],
            [1],
        )

    def test_totales_tecnicos_visibles_usan_acumuladores_dinamicos_por_grupo(self):
        columnas_config = [
            {"source": "cueanexo", "titulo": "CUEANEXO", "repetir": "por_cueanexo"},
            {
                "source": "total_horas_catedra",
                "titulo": "Total Horas Cátedra",
                "repetir": "siempre",
            },
            {
                "source": "puntos_horas_catedra",
                "titulo": "Puntos Horas Cátedra",
                "repetir": "siempre",
            },
            {"source": "total_puntos", "titulo": "Total Puntos", "repetir": "siempre"},
        ]
        schema = {
            "columnas": [
                {"key": "total_horas_catedra"},
                {"key": "puntos_horas_catedra"},
                {"key": "total_puntos"},
            ],
            "grupo_total_general": ("cue",),
        }
        filas = [
            {
                "cueanexo": "111111100",
                "cue": "1111111",
                "estado_pof_codigo": views.CargoPof.EstadoPof.AFECTADO,
                "cantidad_horas": Decimal("10"),
                "total": Decimal("100"),
                "total_horas_catedra": Decimal("10"),
                "puntos_horas_catedra": Decimal("100"),
                "total_puntos": Decimal("100"),
            },
            {
                "cueanexo": "111111100",
                "cue": "1111111",
                "estado_pof_codigo": views.CargoPof.EstadoPof.AFECTADO,
                "cantidad_horas": "",
                "total": Decimal("200"),
                "total_horas_catedra": "",
                "puntos_horas_catedra": "",
                "total_puntos": Decimal("200"),
            },
            {
                "cueanexo": "111111100",
                "cue": "1111111",
                "estado_pof_codigo": views.CargoPof.EstadoPof.DESAFECTADO,
                "cantidad_horas": Decimal("5"),
                "total": Decimal("50"),
                "total_horas_catedra": Decimal("5"),
                "puntos_horas_catedra": Decimal("50"),
                "total_puntos": Decimal("50"),
            },
            {
                "cueanexo": "222222200",
                "cue": "2222222",
                "estado_pof_codigo": views.CargoPof.EstadoPof.AFECTADO,
                "cantidad_horas": "",
                "total": Decimal("25"),
            },
            {
                "cueanexo": "111111101",
                "cue": "1111111",
                "estado_pof_codigo": views.CargoPof.EstadoPof.AFECTADO,
                "cantidad_horas": "",
                "total": Decimal("300"),
            },
        ]

        ws = self._abrir_excel_comun(columnas_config, filas, schema)
        auxiliares = self._columnas_auxiliares(ws, len(columnas_config))

        self.assertEqual(len(auxiliares), 14)
        self.assertIn("_cantidad_horas", auxiliares)
        self.assertIn("_horas_visible_grupo", auxiliares)
        self.assertIn("_puntos_horas_visible_grupo", auxiliares)
        self.assertTrue(
            all(
                ws.column_dimensions[ws.cell(4, indice).column_letter].hidden
                for indice in auxiliares.values()
            )
        )
        self.assertNotIn(ws.cell(4, auxiliares["_fila_visible"]).column_letter, ws.auto_filter.ref)

        letras = {
            nombre: ws.cell(4, indice).column_letter
            for nombre, indice in auxiliares.items()
        }
        self.assertIn(f"${letras['_horas_visible_grupo']}5", ws["B5"].value)
        self.assertIn(f"${letras['_puntos_horas_visible_grupo']}5", ws["C5"].value)
        self.assertIn(f"${letras['_total_visible_grupo']}5", ws["D5"].value)
        self.assertEqual(ws["B5"].number_format, "#,##0")
        self.assertEqual(ws["C5"].number_format, "#,##0.00")
        self.assertEqual(ws["D5"].number_format, "#,##0.00")

        formula_horas = ws.cell(5, auxiliares["_horas_visible_grupo"]).value
        formula_puntos_horas = ws.cell(
            5, auxiliares["_puntos_horas_visible_grupo"]
        ).value
        self.assertIn(
            f"SUBTOTAL(109,${letras['_cantidad_horas']}5)",
            formula_horas,
        )
        self.assertIn(
            f"SUBTOTAL(109,${letras['_total_cargo']}5)",
            formula_puntos_horas,
        )
        self.assertNotIn("puntos", formula_puntos_horas.lower())
        for acumulador in (
            "_total_visible_grupo",
            "_horas_visible_grupo",
            "_puntos_horas_visible_grupo",
        ):
            formula_intercalada = ws.cell(7, auxiliares[acumulador]).value
            self.assertIn(f"${letras[acumulador]}9", formula_intercalada)

        self.assertEqual(
            {columna.colId for columna in ws.auto_filter.filterColumn},
            {1, 2, 3},
        )
        self.assertTrue(
            all(
                columna.hiddenButton and columna.showButton is False
                for columna in ws.auto_filter.filterColumn
            )
        )
        reglas_condicionales = [
            regla
            for reglas in ws.conditional_formatting._cf_rules.values()
            for regla in reglas
        ]
        self.assertTrue(
            any(
                regla.dxf
                and regla.dxf.font
                and regla.dxf.font.color.rgb == "FFFFFFFF"
                and regla.dxf.numFmt is None
                for regla in reglas_condicionales
            )
        )
        self.assertTrue(
            any(
                regla.dxf
                and regla.dxf.border
                and regla.dxf.border.top.style == "medium"
                and regla.dxf.border.top.color.rgb == "003B5CFF"
                for regla in reglas_condicionales
            )
        )
        self.assertTrue(
            any(
                regla.dxf
                and regla.dxf.border
                and regla.dxf.border.top.style == "medium"
                and regla.dxf.border.top.color.rgb == "009CA3AF"
                for regla in reglas_condicionales
            )
        )

    def test_total_puntos_no_es_dinamico_fuera_del_schema_tecnico(self):
        columnas_config = [
            {"source": "cueanexo", "titulo": "CUEANEXO", "repetir": "por_cueanexo"},
            {"source": "total_puntos", "titulo": "Total Puntos", "repetir": "siempre"},
        ]
        fila = {
            "cueanexo": "111111100",
            "cue": "1111111",
            "total_puntos": Decimal("125"),
        }

        ws = self._abrir_excel_comun(
            columnas_config,
            [fila],
            {"columnas": [{"key": "total_puntos"}]},
        )

        self.assertEqual(ws["B5"].value, 125)
        self.assertEqual(ws.max_column, len(columnas_config) + 7)
        self.assertFalse(ws.auto_filter.filterColumn)
        self.assertIsNone(ws.parent.calculation.forceFullCalc)

    def test_total_general_normal_conserva_once_helpers(self):
        columnas_config = [
            {"source": "cueanexo", "titulo": "CUEANEXO", "repetir": "por_cueanexo"},
            {
                "source": "total_general",
                "titulo": "Total General",
                "repetir": "por_cue",
            },
        ]
        fila = {
            "cueanexo": "111111100",
            "cue": "1111111",
            "estado_pof_codigo": views.CargoPof.EstadoPof.AFECTADO,
            "total": Decimal("125"),
        }

        ws = self._abrir_excel_comun(
            columnas_config,
            [fila],
            {"columnas": [], "grupo_total_general": ("cue",)},
        )

        self.assertEqual(ws.max_column, len(columnas_config) + 11)
        self.assertTrue(ws["B5"].value.startswith("=IF(AND(SUBTOTAL(103,"))
        self.assertEqual(
            [columna.colId for columna in ws.auto_filter.filterColumn],
            [1],
        )

    def test_proyecto_especial_conserva_writer_historico_sin_auxiliares_comunes(self):
        """Proyecto Especial no debe entrar al writer filtrable de Reunidas."""
        contexto = {
            "es_proyecto_especial": True,
            "columnas": ["CUEANEXO", "Cargo"],
            "filas_exportacion": [["123456700", "Cargo A"]],
            "filas_normalizadas_exportacion": [
                {"cueanexo": "123456700", "cargo": "Cargo A"}
            ],
            "columnas_exportacion_config": [
                {"source": "cueanexo", "titulo": "CUEANEXO"},
                {"source": "cargo", "titulo": "Cargo"},
            ],
            "separadores_filas_exportacion": [],
            "secciones_exportacion": [],
            "mensaje_exportacion": "",
            "nombre_archivo": "proyecto.xlsx",
            "titulo_hoja": "Proyecto Especial",
            "titulo_excel": "Proyecto Especial POF",
            "reunida": {},
        }

        respuesta = views._crear_respuesta_excel_exportacion(contexto)
        ws = load_workbook(BytesIO(respuesta.content), data_only=False).active

        self.assertEqual(ws.max_column, 2)
        self.assertEqual(ws.auto_filter.ref, "A4:B5")
        self.assertEqual(ws.freeze_panes, "A5")
        self.assertFalse(ws.column_dimensions["C"].hidden)
        self.assertFalse(
            any(
                isinstance(celda.value, str) and celda.value.startswith("=")
                for fila in ws.iter_rows()
                for celda in fila
            )
        )

    def test_excel_separa_zona_ambito_puntos_cargo_y_zona_educativa(self):
        columnas_config = [
            {"source": "zona", "titulo": "Zona", "repetir": "por_cueanexo"},
            {
                "source": "zona_educativa",
                "titulo": "Zona Educativa",
                "repetir": "por_cueanexo",
            },
            {"source": "puntos", "titulo": "Puntos", "repetir": "siempre"},
            {
                "source": "puntos_zona_educativa",
                "titulo": "Puntos Zona Educativa",
                "repetir": "por_cueanexo",
            },
        ]
        fila = {
            "cueanexo": "123456700",
            "cue": "1234567",
            "zona": "RURAL",
            "zona_educativa": "ZR2",
            "puntos": Decimal("100"),
            "puntos_zona_educativa": 1067,
            "estado_pof_codigo": views.CargoPof.EstadoPof.AFECTADO,
            "total": Decimal("100"),
        }

        ws = self._abrir_excel_comun(
            columnas_config,
            [fila],
            {"columnas": [], "grupo_total_general": ("cue",)},
        )

        self.assertEqual(ws["A5"].value, "RURAL")
        self.assertEqual(ws["B5"].value, "ZR2")
        self.assertEqual(ws["C5"].value, 100)
        self.assertEqual(ws["D5"].value, 1067)


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
                "zona_educativa_tipo": "RURAL",
                "zona_educativa": "ZR1",
            })

            self.assertTrue(formulario.is_valid(), formulario.errors)

    def test_formulario_guardado_reunida_exige_zona_educativa(self):
        formulario = pof_forms.GuardarCargaPofForm({
            "cabecera_tipo": "REUNIDA",
            "anio": 2099,
            "nivel": "ADULTOS",
            "tipo_operacion": "AFECTADO",
        })

        self.assertFalse(formulario.is_valid())
        self.assertIn("zona_educativa_tipo", formulario.errors)
        self.assertIn("zona_educativa", formulario.errors)

    def test_formulario_guardado_proyecto_especial_exige_zona_educativa(self):
        formulario = pof_forms.GuardarCargaPofForm({
            "cabecera_tipo": "PROYECTO_ESPECIAL",
            "proyecto_especial_id": 1,
            "tipo_operacion": "AFECTADO",
        })

        self.assertFalse(formulario.is_valid())
        self.assertIn("zona_educativa_tipo", formulario.errors)
        self.assertIn("zona_educativa", formulario.errors)

    def test_formulario_guardado_proyecto_especial_admite_zona_educativa(self):
        formulario = pof_forms.GuardarCargaPofForm({
            "cabecera_tipo": "PROYECTO_ESPECIAL",
            "proyecto_especial_id": 1,
            "tipo_operacion": "AFECTADO",
            "zona_educativa_tipo": "URBANA",
            "zona_educativa": "ZU 1",
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
            "zona_educativa_tipo": "RURAL",
            "zona_educativa": "ZR1",
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


class AsociacionesPofTests(UnitTestCase):
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
        for rol in ("Pof", "Administrador", "Director General", "Subsecretario", "Gestor"):
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

class ZonaEducativaDetalleTests(SimpleTestCase):
    def test_grupo_operativo_expone_zona_y_localizacion(self):
        filas = [{
            "cueanexo": "123456700",
            "cuof": "CUOF-1",
            "cui": "CUI-1",
            "localizacion_id": 77,
            "zona_educativa_tipo": "RURAL",
            "zona_educativa": "ZR2",
            "puntos_zona_educativa": 1067,
            "nombre": "Escuela de prueba",
            "oferta": "Común",
            "ceic": "1",
            "cargo": "Cargo de prueba",
            "cantidad": 1,
            "unidad_cantidad": "CARGO",
            "puntos": Decimal("100"),
            "total": Decimal("100"),
            "estado_pof_codigo": "AFECTADO",
            "estado_pof": "Afectado",
            "observacion_cargo": "",
            "cargo_ids": [1],
        }]

        grupos = construir_grupos_operativos_detalle(
            filas_normalizadas=filas,
            detalle_politicas=obtener_politicas_detalle_reunida(),
        )

        anexo = grupos[0]["anexos"][0]
        self.assertEqual(anexo["localizacion_id"], 77)
        self.assertEqual(anexo["zona_educativa_tipo"], "RURAL")
        self.assertEqual(anexo["zona_educativa"], "ZR2")
        self.assertEqual(anexo["puntos_zona_educativa"], 1067)


class ZonaEducativaVisualizacionTests(SimpleTestCase):
    def test_columnas_zona_estan_disponibles_y_no_se_repitien_por_identidad(self):
        columnas = {
            columna["id"]
            for columna in visualizacion_service.VISUALIZACION_CARGOS_COLUMNAS
        }

        self.assertIn("zona_educativa", columnas)
        self.assertIn("puntos_zona_educativa", columnas)
        self.assertEqual(
            visualizacion_service.SNAPSHOT_COLUMNAS["zona_educativa"],
            "zona_educativa",
        )
        self.assertEqual(
            visualizacion_service.SNAPSHOT_COLUMNAS["puntos_zona_educativa"],
            "puntos_zona_educativa",
        )
        self.assertIn(
            "zona_educativa",
            visualizacion_service.COLUMNAS_NO_REPETIR_POR_LOCALIZACION,
        )
        self.assertIn(
            "puntos_zona_educativa",
            visualizacion_service.COLUMNAS_NO_REPETIR_POR_LOCALIZACION,
        )

    def test_conflicto_zona_no_muestra_un_valor_arbitrario(self):
        clave_identidad = (2026, "CUEANEXO", "123456700")
        fila_raw = {
            "id": 1,
            "estado_pof_codigo": "AFECTADO",
            "_clave_localizacion_grupo": "CUEANEXO:123456700",
            "_clave_identidad_zona": clave_identidad,
            "_clave_total_general": "CUEANEXO:123456700",
            "_cueanexo_visual": "123456700",
            "zona_educativa": "ZR1",
            "puntos_zona_educativa": 713,
        }
        columnas = [
            {"id": "zona_educativa", "visible": True},
            {"id": "puntos_zona_educativa", "visible": True},
        ]

        with patch.object(
            visualizacion_service,
            "_serializar_cargo",
            return_value=fila_raw,
        ):
            filas = visualizacion_service._armar_filas_tabla(
                [SimpleNamespace()],
                columnas,
                {},
                estados_zona_identidades={
                    clave_identidad: {
                        "conflicto": True,
                        "asignacion": None,
                    }
                },
            )

        valores = {
            celda["id"]: celda["valor"]
            for celda in filas[0]["celdas"]
        }
        self.assertEqual(valores["zona_educativa"], "CONFLICTO")
        self.assertEqual(valores["puntos_zona_educativa"], "CONFLICTO")


class ZonaEducativaExportacionTests(SimpleTestCase):
    def test_todos_los_niveles_exponen_zona_educativa_y_puntos(self):
        for nivel in exportacion_columnas_service.COLUMNAS_REUNIDA_POR_NIVEL:
            columnas = exportacion_columnas_service.obtener_columnas_config_nivel(nivel)
            sources = [columna["source"] for columna in columnas]

            self.assertIn("zona_educativa", sources, nivel)
            self.assertIn("puntos_zona_educativa", sources, nivel)

            zona = next(
                columna
                for columna in columnas
                if columna["source"] == "zona_educativa"
            )
            puntos = next(
                columna
                for columna in columnas
                if columna["source"] == "puntos_zona_educativa"
            )
            self.assertEqual(
                zona["repetir"],
                exportacion_columnas_service.REPETIR_POR_CUEANEXO,
            )
            self.assertEqual(
                puntos["repetir"],
                exportacion_columnas_service.REPETIR_POR_CUEANEXO,
            )

    def test_proyecto_especial_explicita_zona_educativa_y_puntos(self):
        sources = [
            columna["source"]
            for columna in exportacion_service.COLUMNAS_EXPORTACION_PROYECTO_ESPECIAL
        ]

        self.assertIn("zona_educativa", sources)
        self.assertIn("puntos_zona_educativa", sources)
        self.assertIn(
            "zona_educativa",
            exportacion_service.FUENTES_NO_REPETIR_PROYECTO_ESPECIAL,
        )
        self.assertIn(
            "puntos_zona_educativa",
            exportacion_service.FUENTES_NO_REPETIR_PROYECTO_ESPECIAL,
        )

        columnas_zona = [
            columna
            for columna in exportacion_service.COLUMNAS_EXPORTACION_PROYECTO_ESPECIAL
            if columna["source"] in {
                "zona_educativa",
                "puntos_zona_educativa",
            }
        ]
        proyectadas = exportacion_service._proyectar_filas_exportacion_proyecto(
            [
                {
                    "cueanexo": "123456700",
                    "cuof": "CUOF-1",
                    "zona_educativa": "ZR2",
                    "puntos_zona_educativa": 1067,
                },
                {
                    "cueanexo": "123456700",
                    "cuof": "CUOF-1",
                    "zona_educativa": "ZR2",
                    "puntos_zona_educativa": 1067,
                },
            ],
            columnas_zona,
        )
        self.assertEqual(proyectadas, [["ZR2", 1067], ["", ""]])

    def test_mapeo_exportacion_no_confunde_ambito_puntos_cargo_y_zona(self):
        snapshot = SimpleNamespace(
            region="",
            numero_establecimiento="1",
            nombre_establecimiento="Escuela",
            oferta="Común",
            categoria="",
            jornada="",
            acronimo="",
            ambito="RURAL",
            ubicacion="",
            localidad="",
            departamento="",
            ubicacion_localidad_departamento="",
            zona_educativa_tipo="RURAL",
            zona_educativa="ZR2",
            puntos_zona_educativa=1067,
        )
        localizacion = SimpleNamespace(
            reunida=SimpleNamespace(anio=2026),
            proyecto_especial=None,
            cueanexo="123456700",
            cue_base="1234567",
            anexo_localizacion="00",
            cui="CUI-1",
            cuof="CUOF-1",
            snapshots_vigentes=[snapshot],
            id=77,
        )
        cargo = SimpleNamespace(
            localizacion=localizacion,
            localizacion_id=77,
            ofertas_seleccionadas=[],
            oferta="",
            cantidad=1,
            unidad_cantidad=models.CargoPof.UnidadCantidad.CARGO,
            puntos_asignados=Decimal("100"),
            total=Decimal("100"),
            ceic=1,
            cargo="Cargo",
            id=9,
            estado_pof=models.CargoPof.EstadoPof.AFECTADO,
            observacion="",
            get_unidad_cantidad_display=lambda: "Cargo",
            get_estado_pof_display=lambda: "Afectado",
        )

        fila = exportacion_rows_service.construir_datos_normalizados_cargo(cargo)

        self.assertEqual(fila["zona"], "RURAL")
        self.assertEqual(fila["puntos"], Decimal("100"))
        self.assertEqual(fila["zona_educativa"], "ZR2")
        self.assertEqual(fila["puntos_zona_educativa"], 1067)

class ZonaEducativaGestionCargoTests(SimpleTestCase):
    def test_detalle_cargo_expone_localizacion_y_zona_para_edicion_directa(self):
        snapshot = SimpleNamespace(
            nombre_establecimiento="Escuela",
            numero_establecimiento="1",
            zona_educativa_tipo="RURAL",
            zona_educativa="ZR2",
            puntos_zona_educativa=1067,
        )
        reunida = SimpleNamespace(
            anio=2026,
            get_nivel_display=lambda: "Primario",
        )
        localizacion = SimpleNamespace(
            id=77,
            cueanexo="123456700",
            cuof="CUOF-1",
            reunida=reunida,
            proyecto_especial=None,
        )
        cargo = SimpleNamespace(
            id=9,
            localizacion=localizacion,
            ceic=1,
            cargo="Cargo",
            cantidad=1,
            unidad_cantidad=models.CargoPof.UnidadCantidad.CARGO,
            puntos_asignados=Decimal("100"),
            total=Decimal("100"),
            estado_pof=models.CargoPof.EstadoPof.AFECTADO,
            observacion="",
            actualizado_en=None,
            get_unidad_cantidad_display=lambda: "Cargo",
            get_estado_pof_display=lambda: "Afectado",
        )

        with patch.object(
            guardado_pof_service,
            "_obtener_snapshot_vigente",
            return_value=snapshot,
        ), patch.object(
            guardado_pof_service,
            "_catalogo_ofertas_cargo",
            return_value=([], [], ""),
        ), patch.object(
            guardado_pof_service,
            "_cargo_requiere_ofertas",
            return_value=False,
        ):
            detalle = guardado_pof_service._serializar_cargo_detalle(cargo)

        self.assertEqual(detalle["localizacion"]["id"], 77)
        self.assertEqual(detalle["localizacion"]["tipo_identidad"], "CUEANEXO")
        self.assertTrue(detalle["zona_educativa"]["asignada"])
        self.assertEqual(detalle["zona_educativa"]["tipo"], "RURAL")
        self.assertEqual(detalle["zona_educativa"]["zona"], "ZR2")
        self.assertEqual(detalle["zona_educativa"]["puntos"], 1067)

    def test_detalle_cargo_proyecto_con_cueanexo_expone_identidad_cuof(self):
        proyecto = SimpleNamespace(
            anio=2026,
            nombre="Proyecto Especial",
        )
        localizacion = SimpleNamespace(
            id=88,
            cueanexo="220000500",
            cuof="PE-100",
            reunida=None,
            proyecto_especial=proyecto,
        )
        cargo = SimpleNamespace(
            id=10,
            localizacion=localizacion,
            ceic=2,
            cargo="Cargo Proyecto",
            cantidad=1,
            unidad_cantidad=models.CargoPof.UnidadCantidad.CARGO,
            puntos_asignados=Decimal("100"),
            total=Decimal("100"),
            estado_pof=models.CargoPof.EstadoPof.AFECTADO,
            observacion="",
            actualizado_en=None,
            get_unidad_cantidad_display=lambda: "Cargo",
            get_estado_pof_display=lambda: "Afectado",
        )

        with patch.object(
            guardado_pof_service,
            "_obtener_snapshot_vigente",
            return_value=None,
        ), patch.object(
            guardado_pof_service,
            "_catalogo_ofertas_cargo",
            return_value=([], [], ""),
        ), patch.object(
            guardado_pof_service,
            "_cargo_requiere_ofertas",
            return_value=False,
        ):
            detalle = guardado_pof_service._serializar_cargo_detalle(cargo)

        self.assertEqual(detalle["localizacion"]["tipo_identidad"], "CUOF")
        self.assertEqual(detalle["localizacion"]["cueanexo"], "220000500")
        self.assertEqual(detalle["localizacion"]["cuof"], "PE-100")

    def test_cambio_zona_permite_quitar_asignacion_con_tipo_y_zona_vacios(self):
        self.assertIsNone(
            zona_educativa_service._resolver_asignacion_cambio_zona("", "")
        )

    def test_cambio_zona_rechaza_estado_parcial(self):
        with self.assertRaises(ValidationError):
            zona_educativa_service._resolver_asignacion_cambio_zona(
                "RURAL",
                "",
            )

    def test_cambio_zona_con_seleccion_resuelve_catalogo(self):
        asignacion = {
            "tipo": "RURAL",
            "zona": "ZR2",
            "puntos": 1067,
        }
        with patch.object(
            zona_educativa_service,
            "resolver_zona_educativa_catalogo",
            return_value=asignacion,
        ) as resolver:
            resultado = zona_educativa_service._resolver_asignacion_cambio_zona(
                "RURAL",
                "ZR2",
            )

        self.assertEqual(resultado, asignacion)
        resolver.assert_called_once_with("RURAL", "ZR2")


class GestionCargoHistorialContextualTests(SimpleTestCase):
    def test_historial_localizacion_reunida_agrupa_por_cueanexo_en_misma_cabecera(self):
        reunida = SimpleNamespace(
            id=14,
            anio=2025,
            get_nivel_display=lambda: "Adultos",
        )
        localizacion = SimpleNamespace(
            id=77,
            reunida_id=14,
            proyecto_especial_id=None,
            reunida=reunida,
            proyecto_especial=None,
            cueanexo="220000500",
            cuof="121200",
        )
        movimientos_base = MagicMock()
        movimientos_cabecera = MagicMock()
        movimientos_base.filter.return_value = movimientos_cabecera
        movimientos_cabecera.filter.return_value = []

        with patch.object(
            historial_service.LocalizacionPof.objects,
            "select_related",
        ) as select_related, patch.object(
            historial_service,
            "_obtener_movimientos_queryset",
            return_value=movimientos_base,
        ):
            select_related.return_value.get.return_value = localizacion
            resultado = historial_service.obtener_historial_localizacion_cargos_pof(77)

        movimientos_base.filter.assert_called_once_with(
            cargo__localizacion__reunida_id=14
        )
        movimientos_cabecera.filter.assert_called_once_with(
            cargo__localizacion__cueanexo="220000500"
        )
        self.assertEqual(resultado["localizacion"]["tipo_identidad"], "CUEANEXO")
        self.assertEqual(resultado["localizacion"]["identidad"], "220000500")
        self.assertEqual(resultado["movimientos"], [])

    def test_historial_localizacion_proyecto_con_cueanexo_usa_cuof(self):
        proyecto = SimpleNamespace(id=31, anio=2026, nombre="Proyecto Especial")
        localizacion = SimpleNamespace(
            id=88,
            reunida_id=None,
            proyecto_especial_id=31,
            reunida=None,
            proyecto_especial=proyecto,
            cueanexo="220000500",
            cuof="PE-100",
        )
        movimientos_base = MagicMock()
        movimientos_cabecera = MagicMock()
        movimientos_base.filter.return_value = movimientos_cabecera
        movimientos_cabecera.filter.return_value = []

        with patch.object(
            historial_service.LocalizacionPof.objects,
            "select_related",
        ) as select_related, patch.object(
            historial_service,
            "_obtener_movimientos_queryset",
            return_value=movimientos_base,
        ):
            select_related.return_value.get.return_value = localizacion
            resultado = historial_service.obtener_historial_localizacion_cargos_pof(88)

        movimientos_base.filter.assert_called_once_with(
            cargo__localizacion__proyecto_especial_id=31
        )
        movimientos_cabecera.filter.assert_called_once_with(
            cargo__localizacion__cuof__iexact="PE-100"
        )
        self.assertEqual(resultado["localizacion"]["tipo_identidad"], "CUOF")
        self.assertEqual(resultado["localizacion"]["identidad"], "PE-100")
        self.assertEqual(resultado["movimientos"], [])


class ExportacionReunidaPreviewGestionCargoTests(SimpleTestCase):
    def test_preview_conserva_cargo_id_para_accion_directa(self):
        fila = exportacion_service._construir_fila_preview(
            ["Cargo de prueba"],
            [{"key": "cargo", "source": "cargo"}],
            ["cargo"],
            fila_normalizada={
                "cargo_ids": [321],
                "estado_pof_codigo": models.CargoPof.EstadoPof.AFECTADO,
            },
        )

        self.assertEqual(fila["cargo_ids"], [321])


class ExportacionAfectarAtajoTests(SimpleTestCase):
    def test_reunida_muestra_afectar_una_vez_por_cueanexo(self):
        secciones = [{
            "filas": [["A"], ["B"], ["C"], ["D"]],
            "indices_filas": [0, 1, 2, 3],
        }]
        filas_normalizadas = [
            {"cueanexo": "220000500", "cuof": "CUOF-A"},
            {"cueanexo": "220000500", "cuof": "CUOF-B"},
            {"cueanexo": "220000501", "cuof": "CUOF-C"},
            {"cueanexo": "220000500", "cuof": "CUOF-D"},
        ]

        resultado = exportacion_service._construir_secciones_preview(
            secciones,
            [{"key": "cargo", "source": "cargo"}],
            ["cargo"],
            filas_normalizadas=filas_normalizadas,
        )

        filas = resultado[0]["filas"]
        self.assertEqual(
            [fila["mostrar_afectar"] for fila in filas],
            [True, False, True, False],
        )
        self.assertEqual(filas[0]["cueanexo"], "220000500")

    def test_proyecto_especial_muestra_afectar_una_vez_por_cuof(self):
        secciones = [{
            "filas": [["A"], ["B"], ["C"]],
            "indices_filas": [0, 1, 2],
        }]
        filas_normalizadas = [
            {"cueanexo": "", "cuof": "PE-100"},
            {"cueanexo": "", "cuof": "PE-100"},
            {"cueanexo": "", "cuof": "PE-200"},
        ]

        resultado = exportacion_service._construir_secciones_preview(
            secciones,
            [{"key": "cargo", "source": "cargo"}],
            ["cargo"],
            filas_normalizadas=filas_normalizadas,
            identidad_afectar="CUOF",
        )

        filas = resultado[0]["filas"]
        self.assertEqual(
            [fila["mostrar_afectar"] for fila in filas],
            [True, False, True],
        )
        self.assertEqual(filas[0]["cuof"], "PE-100")


class CargaDesdeExportarTests(SimpleTestCase):
    def setUp(self):
        self.request_factory = RequestFactory()

    def test_reunida_precarga_cueanexo_solo_desde_exportar(self):
        request = self.request_factory.get(
            "/reunida/cargar/",
            {
                "anio": "2025",
                "nivel": "ADULTOS",
                "cueanexo": "220000500",
                "origen": "exportar",
            },
        )

        with (
            patch.object(
                carga_service,
                "obtener_anios_reunidas_disponibles",
                return_value=["2025"],
            ),
            patch.object(
                carga_service,
                "obtener_anio_activo",
                return_value="2025",
            ),
            patch.object(
                carga_service,
                "obtener_nivel_activo",
                return_value="ADULTOS",
            ),
            patch.object(
                carga_service,
                "obtener_lista_niveles",
                return_value=[],
            ),
        ):
            contexto = carga_service.construir_contexto_carga(request)

        self.assertEqual(contexto["cueanexo_inicial"], "220000500")

        request_sin_origen = self.request_factory.get(
            "/reunida/cargar/",
            {
                "anio": "2025",
                "nivel": "ADULTOS",
                "cueanexo": "220000500",
            },
        )

        with (
            patch.object(
                carga_service,
                "obtener_anios_reunidas_disponibles",
                return_value=["2025"],
            ),
            patch.object(
                carga_service,
                "obtener_anio_activo",
                return_value="2025",
            ),
            patch.object(
                carga_service,
                "obtener_nivel_activo",
                return_value="ADULTOS",
            ),
            patch.object(
                carga_service,
                "obtener_lista_niveles",
                return_value=[],
            ),
        ):
            contexto_sin_origen = carga_service.construir_contexto_carga(
                request_sin_origen
            )

        self.assertEqual(contexto_sin_origen["cueanexo_inicial"], "")

    def test_reunida_no_reubica_atajo_a_otro_anio_si_la_cabecera_ya_no_existe(self):
        request = self.request_factory.get(
            "/reunida/cargar/",
            {
                "anio": "2025",
                "nivel": "ADULTOS",
                "cueanexo": "220000500",
                "origen": "exportar",
            },
        )

        with (
            patch.object(
                carga_service,
                "obtener_anios_reunidas_disponibles",
                return_value=["2026"],
            ),
            patch.object(
                carga_service,
                "obtener_anio_activo",
                return_value="2025",
            ),
            patch.object(
                carga_service,
                "obtener_nivel_activo",
                return_value="ADULTOS",
            ),
            patch.object(
                carga_service,
                "obtener_lista_niveles",
                return_value=[],
            ),
        ):
            contexto = carga_service.construir_contexto_carga(request)

        self.assertEqual(contexto["anio_activo"], "")
        self.assertEqual(contexto["nivel_activo"], "")
        self.assertEqual(contexto["cueanexo_inicial"], "")

    def test_proyecto_especial_precarga_cuof_solo_desde_exportar(self):
        request = self.request_factory.get(
            "/proyectos-especiales/cargar/",
            {
                "proyecto_especial_id": "12",
                "cuof": "110400",
                "origen": "exportar",
            },
        )
        proyecto = SimpleNamespace(id=12, resolucion="123/26")
        queryset = MagicMock()
        queryset.order_by.return_value = []

        with (
            patch.object(
                views.ProyectosEspecialesPof.objects,
                "all",
                return_value=queryset,
            ),
            patch.object(
                views.ProyectosEspecialesPof.objects,
                "get",
                return_value=proyecto,
            ),
            patch.object(views, "render", return_value=Mock()) as render_mock,
        ):
            unwrap(views.cargar_cargos_proyecto_especial)(request)

        contexto = render_mock.call_args.args[2]
        self.assertEqual(contexto["cuof_inicial"], "110400")
        self.assertIs(contexto["proyecto_especial"], proyecto)


class GestionCargoUnificadaTests(UnitTestCase):
    @staticmethod
    def _atomic_context():
        contexto = MagicMock()
        contexto.__enter__.return_value = None
        contexto.__exit__.return_value = False
        return contexto

    def test_guardado_solo_zona_no_revalida_datos_del_cargo(self):
        detalle = {
            "id": 25,
            "zona_educativa": {
                "asignada": True,
                "tipo": "URBANA",
                "zona": "ZU 2",
                "puntos": 432,
            },
        }
        resultado_zona = {
            "ok": True,
            "mensaje": "Zona Educativa actualizada correctamente.",
            "zona_educativa": detalle["zona_educativa"],
        }
        only_result = MagicMock()
        only_result.get.return_value = SimpleNamespace(localizacion_id=77)
        locked_qs = MagicMock()
        locked_qs.only.return_value = only_result

        with (
            patch.object(
                guardado_pof_service.transaction,
                "atomic",
                return_value=self._atomic_context(),
            ),
            patch.object(
                guardado_pof_service.CargoPof.objects,
                "select_for_update",
                return_value=locked_qs,
            ),
            patch.object(
                guardado_pof_service,
                "modificar_cargo_pof",
            ) as modificar,
            patch.object(
                guardado_pof_service,
                "cambiar_zona_educativa_localizacion",
                return_value=resultado_zona,
            ) as cambiar_zona,
            patch.object(
                guardado_pof_service,
                "obtener_detalle_cargo_pof",
                return_value=detalle,
            ),
        ):
            resultado = guardado_pof_service.guardar_gestion_cargo_pof(
                25,
                {
                    "zona_educativa": {
                        "tipo": "URBANA",
                        "zona": "ZU 2",
                    }
                },
            )

        self.assertTrue(resultado["ok"])
        modificar.assert_not_called()
        cambiar_zona.assert_called_once_with(
            77,
            "URBANA",
            "ZU 2",
            usuario=None,
        )
        self.assertEqual(resultado["cargo"], detalle)

    def test_guardado_con_cargo_y_zona_reutiliza_ambas_operaciones(self):
        detalle = {
            "id": 31,
            "zona_educativa": {
                "asignada": True,
                "tipo": "RURAL",
                "zona": "ZR2",
                "puntos": 1067,
            },
        }
        resultado_cargo = {
            "ok": True,
            "mensaje": "Cargo modificado correctamente.",
            "lote_carga_id": 900,
        }
        resultado_zona = {
            "ok": True,
            "mensaje": "Zona Educativa actualizada correctamente.",
            "zona_educativa": detalle["zona_educativa"],
        }
        only_result = MagicMock()
        only_result.get.return_value = SimpleNamespace(localizacion_id=88)
        locked_qs = MagicMock()
        locked_qs.only.return_value = only_result

        with (
            patch.object(
                guardado_pof_service.transaction,
                "atomic",
                return_value=self._atomic_context(),
            ),
            patch.object(
                guardado_pof_service.CargoPof.objects,
                "select_for_update",
                return_value=locked_qs,
            ),
            patch.object(
                guardado_pof_service,
                "modificar_cargo_pof",
                return_value=resultado_cargo,
            ) as modificar,
            patch.object(
                guardado_pof_service,
                "cambiar_zona_educativa_localizacion",
                return_value=resultado_zona,
            ) as cambiar_zona,
            patch.object(
                guardado_pof_service,
                "obtener_detalle_cargo_pof",
                return_value=detalle,
            ),
        ):
            payload = {
                "cantidad": "2",
                "unidad_cantidad": "CARGO",
                "estado_pof": "AFECTADO",
                "observacion": "",
                "zona_educativa": {
                    "tipo": "RURAL",
                    "zona": "ZR2",
                },
            }
            resultado = guardado_pof_service.guardar_gestion_cargo_pof(
                31,
                payload,
            )

        self.assertTrue(resultado["ok"])
        self.assertEqual(
            resultado["mensaje"],
            "Cargo y Zona Educativa actualizados correctamente.",
        )
        modificar.assert_called_once()
        cambiar_zona.assert_called_once_with(
            88,
            "RURAL",
            "ZR2",
            usuario=None,
        )
        self.assertEqual(resultado["lote_carga_id"], 900)


class PaginacionIdentidadReunidaTests(SimpleTestCase):
    def test_detalle_pagina_por_cueanexo_completo(self):
        cargos_queryset = MagicMock()
        orden_inicial = MagicMock()
        valores = MagicMock()
        distintos = MagicMock()
        cueanexos = [
            "111111100",
            "111111101",
            "111111102",
            "111111103",
            "111111104",
            "111111105",
        ]

        cargos_queryset.order_by.return_value = orden_inicial
        orden_inicial.values_list.return_value = valores
        valores.distinct.return_value = distintos
        distintos.order_by.return_value = cueanexos

        unidades, metadata = reunidas_service._paginar_cueanexos_coincidentes_detalle(
            cargos_queryset,
            1,
        )

        orden_inicial.values_list.assert_called_once_with(
            "localizacion__cueanexo",
            flat=True,
        )
        self.assertEqual(unidades, cueanexos[:5])
        self.assertEqual(metadata["total"], 6)
        self.assertEqual(metadata["showing_start"], 1)
        self.assertEqual(metadata["showing_end"], 5)

    def test_exportar_preview_informa_total_cueanexo(self):
        request = RequestFactory().get("/exportar/", {"anio": "2026"})
        page_obj = Paginator(
            [
                "CUEANEXO:111111100",
                "CUEANEXO:111111101",
                "CUEANEXO:111111102",
                "CUEANEXO:111111103",
                "CUEANEXO:111111104",
                "CUEANEXO:111111105",
            ],
            exportacion_service.CUEANEXOS_POR_PAGINA_EXPORTACION,
        ).get_page(1)

        metadata = exportacion_service._construir_paginacion_preview_reunida(
            page_obj,
            request,
        )

        self.assertEqual(metadata["total_cueanexo"], 6)
        self.assertEqual(metadata["primer_cueanexo"], 1)
        self.assertEqual(metadata["ultimo_cueanexo"], 5)
        self.assertEqual(metadata["cueanexos_por_pagina"], 5)

    def test_visualizador_expone_identidad_funcional_y_proyecto_cuof(self):
        page_obj = Paginator(
            ["CUEANEXO:1", "CUEANEXO:2", "CUEANEXO:3"],
            visualizacion_service.UNIDADES_POR_PAGINA_VISUALIZACION,
        ).get_page(1)

        general = visualizacion_service._construir_metadatos_paginacion(
            page_obj,
            12,
            es_proyecto_especial=False,
        )
        proyecto = visualizacion_service._construir_metadatos_paginacion(
            page_obj,
            12,
            es_proyecto_especial=True,
        )

        self.assertEqual(general["total_unidades"], 3)
        self.assertEqual(general["unidad_label"], "CUEANEXO / CUOF")
        self.assertEqual(proyecto["unidad_label"], "CUOF")


class HistorialResumenCompactoTests(SimpleTestCase):
    def test_alta_muestra_valores_iniciales_sin_flechas(self):
        diff = [
            {"clave": "cantidad", "anterior": "—", "nuevo": "1", "tipo": "agregado"},
            {"clave": "unidad_cantidad", "anterior": "—", "nuevo": "CARGO", "tipo": "agregado"},
            {"clave": "puntos_asignados", "anterior": "—", "nuevo": "2097.00", "tipo": "agregado"},
            {"clave": "total", "anterior": "—", "nuevo": "2097.00", "tipo": "agregado"},
        ]

        partes = historial_service._partes_diff_resumen_compacto(diff, "alta")

        self.assertEqual(
            partes,
            [
                "Cantidad: 1",
                "Unidad: CARGO",
                "Puntos: 2097.00",
                "Total: 2097.00",
            ],
        )
        self.assertTrue(all(historial_service.FLECHA_CAMBIO not in parte for parte in partes))

    def test_modificacion_conserva_flechas_entre_valores(self):
        diff = [
            {"clave": "cantidad", "anterior": "1", "nuevo": "2", "tipo": "modificado"},
            {"clave": "total", "anterior": "2097.00", "nuevo": "4194.00", "tipo": "modificado"},
        ]

        partes = historial_service._partes_diff_resumen_compacto(diff, "modificacion")

        self.assertEqual(
            partes,
            [
                f"Cantidad 1 {historial_service.FLECHA_CAMBIO} 2",
                f"Total 2097.00 {historial_service.FLECHA_CAMBIO} 4194.00",
            ],
        )

    def test_historial_contextual_expone_resumen_visual_estructurado(self):
        movimiento = SimpleNamespace(
            id=10,
            fecha="2026-09-22",
            tipo_movimiento="AFECTADO",
            tipo_movimiento_display="Afectado",
            tipo_movimiento_clase="afectado",
            detalle_resumen="Se añadió el cargo CEIC 80.",
            detalle_resumen_visual={
                "accion": "Se añadió el cargo CEIC 80.",
                "partes": ["Cantidad: 1", "Unidad: CARGO"],
            },
            usuario_movimiento={"nombre": "Usuario"},
            observacion="",
            cargo=SimpleNamespace(id=5, ceic=80, cargo="MAESTRO"),
        )

        with (
            patch.object(
                historial_service,
                "_preparar_movimiento_para_listado",
            ),
            patch.object(
                historial_service,
                "_normalizar_observacion_real",
                return_value="",
            ),
            patch.object(
                historial_service,
                "_construir_diff_movimiento",
                return_value=[],
            ),
        ):
            resultado = historial_service._serializar_movimiento_historial_contextual(
                movimiento
            )

        self.assertEqual(resultado["detalle_visual"], movimiento.detalle_resumen_visual)
        self.assertEqual(resultado["detalle"], movimiento.detalle_resumen)


class HistorialObservacionTimelineTests(SimpleTestCase):
    def test_evento_inicial_usa_observacion_del_snapshot(self):
        movimiento = SimpleNamespace(
            id=1,
            fecha="2026-03-10 09:42",
            tipo_movimiento=models.MovimientoCargoPof.TipoMovimiento.AFECTADO,
            valores_nuevos={"observacion": "  Cargo pendiente de revisión  "},
            usuario=SimpleNamespace(),
        )

        with patch.object(
            historial_service,
            "_serializar_usuario_movimiento",
            return_value={"nombre": "Juan Pérez"},
        ):
            evento = historial_service._serializar_evento_observacion_inicial(
                movimiento
            )

        self.assertEqual(
            historial_service._observacion_inicial_movimiento(movimiento),
            "Cargo pendiente de revisión",
        )
        self.assertEqual(evento["tipo_evento"], "inicial")
        self.assertEqual(evento["label"], "Observación inicial")
        self.assertEqual(evento["valor_inicial"], "Cargo pendiente de revisión")
        self.assertEqual(evento["resumen"], "Cargo pendiente de revisión")

    def test_evento_inicial_vacio_no_genera_valor_real(self):
        movimiento = SimpleNamespace(
            tipo_movimiento=models.MovimientoCargoPof.TipoMovimiento.AFECTADO,
            valores_nuevos={"observacion": "   "},
        )

        self.assertEqual(
            historial_service._observacion_inicial_movimiento(movimiento),
            "",
        )

    def test_modificacion_expone_antes_despues_y_resumen(self):
        movimiento = SimpleNamespace(
            id=2,
            fecha="2026-04-18 11:15",
            tipo_movimiento=models.MovimientoCargoPof.TipoMovimiento.MODIFICACION,
            valores_anteriores={"observacion": "Cargo pendiente de revisión"},
            valores_nuevos={"observacion": "Documentación presentada"},
            usuario=SimpleNamespace(),
        )

        with patch.object(
            historial_service,
            "_serializar_usuario_movimiento",
            return_value={"nombre": "María Gómez"},
        ):
            evento = historial_service._serializar_movimiento_observacion(
                movimiento
            )

        self.assertEqual(evento["tipo_evento"], "modificacion")
        self.assertEqual(evento["label"], "Observación modificada")
        self.assertEqual(evento["observacion_anterior"], "Cargo pendiente de revisión")
        self.assertEqual(evento["observacion_nueva"], "Documentación presentada")
        self.assertEqual(evento["resumen"], "Documentación presentada")

    def test_servicio_devuelve_timeline_descendente_con_inicial(self):
        localizacion = SimpleNamespace(
            reunida_id=14,
            proyecto_especial_id=None,
            cueanexo="220000500",
            cuof="121200",
        )
        cargo = SimpleNamespace(
            id=7,
            ceic=80,
            cargo="MAESTRO",
            observacion="Documentación aprobada",
            localizacion=localizacion,
        )
        inicial = SimpleNamespace(
            id=10,
            cargo_id=7,
            fecha="2026-03-10 09:42",
            tipo_movimiento=models.MovimientoCargoPof.TipoMovimiento.AFECTADO,
            valores_anteriores={},
            valores_nuevos={"observacion": "Cargo pendiente de revisión"},
            usuario=SimpleNamespace(),
        )
        cambio_uno = SimpleNamespace(
            id=11,
            cargo_id=7,
            fecha="2026-04-18 11:15",
            tipo_movimiento=models.MovimientoCargoPof.TipoMovimiento.MODIFICACION,
            valores_anteriores={"observacion": "Cargo pendiente de revisión"},
            valores_nuevos={"observacion": "Documentación presentada"},
            usuario=SimpleNamespace(),
        )
        cambio_dos = SimpleNamespace(
            id=12,
            cargo_id=7,
            fecha="2026-06-02 08:31",
            tipo_movimiento=models.MovimientoCargoPof.TipoMovimiento.MODIFICACION,
            valores_anteriores={"observacion": "Documentación presentada"},
            valores_nuevos={"observacion": "Documentación aprobada"},
            usuario=SimpleNamespace(),
        )

        cargos_queryset = MagicMock()
        cargos_queryset.filter.return_value.order_by.return_value = [cargo]
        movimientos_queryset = MagicMock()
        movimientos_queryset.filter.return_value.order_by.return_value = [
            inicial,
            cambio_uno,
            cambio_dos,
        ]

        with (
            patch.object(
                historial_service.CargoPof.objects,
                "select_related",
                return_value=cargos_queryset,
            ),
            patch.object(
                historial_service.MovimientoCargoPof.objects,
                "select_related",
                return_value=movimientos_queryset,
            ),
            patch.object(historial_service, "_validar_cargos_historial"),
            patch.object(
                historial_service,
                "_serializar_usuario_movimiento",
                return_value={"nombre": "Usuario"},
            ),
        ):
            resultado = historial_service.obtener_historial_observacion_cargos_pof(
                [7]
            )

        eventos = resultado["cargos"][0]["movimientos"]
        self.assertEqual(
            [evento["tipo_evento"] for evento in eventos],
            ["modificacion", "modificacion", "inicial"],
        )
        self.assertEqual(eventos[0]["resumen"], "Documentación aprobada")
        self.assertEqual(eventos[1]["resumen"], "Documentación presentada")
        self.assertEqual(eventos[2]["valor_inicial"], "Cargo pendiente de revisión")
        self.assertTrue(resultado["modificado"])


class ExportacionFiltrosAvanzadosTests(SimpleTestCase):
    def setUp(self):
        self.request_factory = RequestFactory()

    def test_filtro_avanzado_tiene_precedencia_sobre_busqueda_del_mismo_campo(self):
        busquedas = {
            "cargo": "Maestro",
            "observacion": "Titular",
        }
        filtros = [
            {
                "campo": "cargo",
                "operador": "2",
                "valor": "Profesor",
            }
        ]

        resultado = exportacion_service._obtener_busquedas_columnas_exportacion_efectivas(
            busquedas,
            filtros,
        )

        self.assertEqual(resultado, {"observacion": "Titular"})

    def test_filtro_avanzado_tiene_precedencia_sobre_filtro_simple_proyecto(self):
        filtros_simples = {
            "cuof": "ABC",
            "localidad": "Resistencia",
            "cargo": "Maestro",
        }
        filtros_avanzados = [
            {
                "campo": "cargo",
                "operador": "0",
                "valor": "Profesor",
            }
        ]

        resultado = exportacion_service._obtener_filtros_simples_proyecto_efectivos(
            filtros_simples,
            filtros_avanzados,
        )

        self.assertEqual(resultado["cargo"], "")
        self.assertEqual(resultado["cuof"], "ABC")
        self.assertEqual(resultado["localidad"], "Resistencia")

    def test_excel_vista_reunida_conserva_busqueda_y_filtros_avanzados(self):
        from urllib.parse import parse_qs

        request = self.request_factory.get(
            "/exportar/",
            [
                ("col_cargo", "Maestro"),
                ("campo_filtro", "region"),
                ("operador_filtro", "2"),
                ("valor_filtro", "R.E. 1"),
            ],
        )

        querystring = exportacion_service._armar_excel_querystring_reunida(
            "2026",
            "SECUNDARIA",
            ["cueanexo", "cargo"],
            request=request,
            alcance="vista",
        )
        params = parse_qs(querystring)

        self.assertEqual(params["col_cargo"], ["Maestro"])
        self.assertEqual(params["campo_filtro"], ["region"])
        self.assertEqual(params["operador_filtro"], ["2"])
        self.assertEqual(params["valor_filtro"], ["R.E. 1"])
        self.assertEqual(params["alcance"], ["vista"])

    def test_excel_todos_elimina_filtros_en_reunida_y_proyecto(self):
        from urllib.parse import parse_qs

        request = self.request_factory.get(
            "/exportar/",
            [
                ("col_cargo", "Maestro"),
                ("cuof", "ABC"),
                ("campo_filtro", "region"),
                ("operador_filtro", "2"),
                ("valor_filtro", "R.E. 1"),
            ],
        )

        reunida = parse_qs(
            exportacion_service._armar_excel_querystring_reunida(
                "2026",
                "SECUNDARIA",
                ["cueanexo"],
                request=request,
                alcance="todos",
            )
        )
        proyecto = parse_qs(
            exportacion_service._armar_excel_querystring_proyecto(
                15,
                ["proyecto_especial_cuof"],
                request=request,
                alcance="todos",
            )
        )

        for params in (reunida, proyecto):
            self.assertNotIn("col_cargo", params)
            self.assertNotIn("campo_filtro", params)
            self.assertNotIn("operador_filtro", params)
            self.assertNotIn("valor_filtro", params)
            self.assertNotIn("cuof", params)
            self.assertEqual(params["alcance"], ["todos"])

    def test_exportar_incorpora_zona_educativa_sin_modificar_campos_de_detalle(self):
        campos_exportar = [
            campo["id"]
            for campo in exportacion_service.FILTROS_AVANZADOS_EXPORTACION_CAMPOS
        ]
        campos_detalle = [
            campo["id"]
            for campo in reunidas_service.FILTROS_AVANZADOS_DETALLE_CAMPOS
        ]

        self.assertIn("zona_educativa", campos_exportar)
        self.assertNotIn("zona_educativa", campos_detalle)
        self.assertEqual(
            campos_exportar.index("zona_educativa"),
            campos_exportar.index("departamento") + 1,
        )

    def test_exportar_acepta_filtro_exact_zona_educativa(self):
        request = self.request_factory.get(
            "/exportar/",
            [
                ("campo_filtro", "zona_educativa"),
                ("operador_filtro", "2"),
                ("valor_filtro", "ZU 5 c/ ZUE 4"),
            ],
        )

        filtros = exportacion_service._obtener_filtros_avanzados_exportacion(
            request
        )

        self.assertEqual(
            filtros,
            [{
                "indice": 0,
                "campo": "zona_educativa",
                "operador": "2",
                "valor": "ZU 5 c/ ZUE 4",
            }],
        )

    def test_exportar_filtra_zona_sobre_snapshot_vigente(self):
        queryset = MagicMock()
        queryset.filter.return_value = queryset
        queryset.exclude.return_value = queryset
        queryset.distinct.return_value = queryset

        with patch.object(
            exportacion_service,
            "_aplicar_filtros_avanzados_detalle_reunida",
            return_value=queryset,
        ) as aplicar_compartidos:
            resultado = exportacion_service._aplicar_filtros_avanzados_exportacion(
                queryset,
                [{
                    "campo": "zona_educativa",
                    "operador": "2",
                    "valor": "ZR9",
                }],
            )

        aplicar_compartidos.assert_called_once_with(queryset, [])
        filtro_q = queryset.filter.call_args.args[0]
        self.assertIn("snapshots_padron__vigente", str(filtro_q))
        self.assertIn("snapshots_padron__zona_educativa__iexact", str(filtro_q))
        self.assertIn("ZR9", str(filtro_q))
        self.assertIs(resultado, queryset)

    def test_opciones_exportar_precargan_zonas_educativas_reales(self):
        queryset = MagicMock()
        queryset.exclude.return_value = queryset
        queryset.order_by.return_value = queryset
        queryset.values_list.return_value = queryset
        queryset.distinct.return_value = queryset
        queryset.__getitem__.return_value = [
            "ZR9",
            "ZU 5 c/ ZUE 4",
            "ZR9",
        ]
        with (
            patch.object(
                exportacion_service,
                "_construir_opciones_filtros_detalle_reunida",
                return_value={"estado_pof": []},
            ),
            patch.object(
                exportacion_service.SnapshotPadronLocalizacionPof.objects,
                "filter",
                return_value=queryset,
            ),
        ):
            opciones = exportacion_service._construir_opciones_filtros_exportacion()

        self.assertEqual(
            opciones["zona_educativa"],
            ["ZR9", "ZU 5 c/ ZUE 4"],
        )


class AnexoPofPosicionTests(SimpleTestCase):
    """Mantiene Código(s) Anexo POF inmediatamente junto a CUEANEXO."""

    def test_visualizacion_ubica_anexo_pof_despues_de_cueanexo(self):
        ids = [
            columna["id"]
            for columna in visualizacion_service.VISUALIZACION_CARGOS_COLUMNAS
        ]

        self.assertEqual(ids.index("anexo_pof"), ids.index("cueanexo") + 1)

    def test_exportacion_reunida_ubica_anexo_pof_despues_de_cueanexo(self):
        for nivel in exportacion_columnas_service.COLUMNAS_REUNIDA_POR_NIVEL:
            columnas = exportacion_columnas_service.obtener_columnas_config_nivel(nivel)
            sources = [columna["source"] for columna in columnas]

            self.assertEqual(
                sources.index("anexo_pof"),
                sources.index("cueanexo") + 1,
                nivel,
            )

    def test_exportacion_reunida_mantiene_oferta_despues_de_anexo_pof(self):
        columnas = exportacion_columnas_service.obtener_columnas_disponibles_nivel(
            "PRIMARIA"
        )
        columnas_default = exportacion_columnas_service.obtener_columnas_default_ids(
            "PRIMARIA"
        )
        columnas_visibles = list(columnas_default)

        (
            columnas_resultado,
            _,
            columnas_visibles_resultado,
            columna_oferta,
        ) = exportacion_service._agregar_columna_oferta_exportacion(
            columnas,
            columnas_default,
            columnas_visibles,
        )

        sources = [columna["source"] for columna in columnas_resultado]
        self.assertEqual(
            sources[:3],
            ["cueanexo", "anexo_pof", "oferta"],
        )

        keys_por_source = {
            columna["source"]: columna["key"]
            for columna in columnas_resultado
        }
        self.assertEqual(
            columnas_visibles_resultado[:3],
            [
                keys_por_source["cueanexo"],
                keys_por_source["anexo_pof"],
                columna_oferta["key"],
            ],
        )

    def test_exportacion_proyecto_especial_ubica_anexo_pof_despues_de_cueanexo(self):
        sources = [
            columna["source"]
            for columna in exportacion_service.COLUMNAS_EXPORTACION_PROYECTO_ESPECIAL
        ]

        self.assertEqual(
            sources.index("anexo_pof"),
            sources.index("cueanexo") + 1,
        )


class AnexoPofPureTests(UnitTestCase):
    """Cobertura pura de Anexo POF: no usar ORM ni acceso a base de datos."""

    def test_normalizacion_conserva_ceros_y_rechaza_formatos_no_permitidos(self):
        self.assertEqual(
            anexo_pof_service.normalizar_codigo_anexo_pof(" 001 "),
            "001",
        )

        with self.assertRaises(ValidationError):
            anexo_pof_service.normalizar_codigo_anexo_pof("01,02")

        with self.assertRaises(ValidationError):
            anexo_pof_service.normalizar_codigo_anexo_pof("01\n02")

        with self.assertRaises(ValidationError):
            anexo_pof_service.normalizar_codigo_anexo_pof("A" * 51)

    def test_normalizacion_cue_exige_siete_digitos(self):
        self.assertEqual(
            anexo_pof_service.normalizar_cue_anexo_pof(" 2200006 "),
            "2200006",
        )

        for valor in ("", "220006", "22000060", "22000A6"):
            with self.assertRaises(ValidationError):
                anexo_pof_service.normalizar_cue_anexo_pof(valor)

    def test_normalizacion_cuof_conserva_texto_y_rechaza_controles(self):
        self.assertEqual(
            anexo_pof_service.normalizar_cuof_anexo_pof(" CUOF-PE-1 "),
            "CUOF-PE-1",
        )

        with self.assertRaises(ValidationError):
            anexo_pof_service.normalizar_cuof_anexo_pof("")

        with self.assertRaises(ValidationError):
            anexo_pof_service.normalizar_cuof_anexo_pof("CUOF\n1")

    def test_propietario_reunida_usa_cue_y_no_cae_a_cuof(self):
        propietario = anexo_pof_service.resolver_propietario_anexo_pof(
            cue="2200006",
            cuof="CUOF-IGNORADO",
            es_proyecto_especial=False,
        )

        self.assertEqual(
            propietario,
            {
                "tipo": anexo_pof_service.TIPO_PROPIETARIO_CUE,
                "valor": "2200006",
            },
        )

        with self.assertRaises(ValidationError):
            anexo_pof_service.resolver_propietario_anexo_pof(
                cue="",
                cuof="CUOF-PE-1",
                es_proyecto_especial=False,
            )

    def test_propietario_proyecto_prioriza_cue_sobre_cuof(self):
        propietario = anexo_pof_service.resolver_propietario_anexo_pof(
            cue="2200006",
            cuof="CUOF-PE-1",
            es_proyecto_especial=True,
        )

        self.assertEqual(
            propietario,
            {
                "tipo": anexo_pof_service.TIPO_PROPIETARIO_CUE,
                "valor": "2200006",
            },
        )

    def test_propietario_proyecto_sin_cue_usa_cuof(self):
        propietario = anexo_pof_service.resolver_propietario_anexo_pof(
            cue="",
            cuof="CUOF-PE-1",
            es_proyecto_especial=True,
        )

        self.assertEqual(
            propietario,
            {
                "tipo": anexo_pof_service.TIPO_PROPIETARIO_CUOF,
                "valor": "CUOF-PE-1",
            },
        )

    def test_localizacion_reunida_resuelve_cue_base(self):
        localizacion = SimpleNamespace(
            cue_base="2200006",
            cuof="CUOF-1",
            proyecto_especial_id=None,
        )

        self.assertEqual(
            anexo_pof_service.resolver_propietario_anexo_pof_localizacion(
                localizacion
            ),
            {
                "tipo": anexo_pof_service.TIPO_PROPIETARIO_CUE,
                "valor": "2200006",
            },
        )

    def test_localizacion_proyecto_con_cue_prioriza_cue(self):
        localizacion = SimpleNamespace(
            cue_base="2200006",
            cuof="CUOF-PE-1",
            proyecto_especial_id=27,
        )

        self.assertEqual(
            anexo_pof_service.resolver_propietario_anexo_pof_localizacion(
                localizacion
            ),
            {
                "tipo": anexo_pof_service.TIPO_PROPIETARIO_CUE,
                "valor": "2200006",
            },
        )

    def test_localizacion_proyecto_sin_cue_usa_cuof(self):
        localizacion = SimpleNamespace(
            cue_base="",
            cuof="CUOF-PE-1",
            proyecto_especial_id=27,
        )

        self.assertEqual(
            anexo_pof_service.resolver_propietario_anexo_pof_localizacion(
                localizacion
            ),
            {
                "tipo": anexo_pof_service.TIPO_PROPIETARIO_CUOF,
                "valor": "CUOF-PE-1",
            },
        )


