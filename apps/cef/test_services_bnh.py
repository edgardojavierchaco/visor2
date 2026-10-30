"""Regresiones CEF/BNH con Django real y persistencia simulada, sin conexiones."""

from contextlib import ExitStack, nullcontext
from datetime import date, time
import inspect
import json
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import OperationalError
from django.template.loader import get_template, render_to_string
from django.test import RequestFactory

from apps.bnhpersonas.models import Personas, RegistroActividades
from . import models, permisos, services, services_anual, views_asistencia
from . import views_contexto, views_docentes_grupo, views_profesores, views_carga_grupo


CUIL = "20123456789"
OTRO = "27123456780"
CUE = "220000100"
OTRO_CUE = "220000200"


def atributo(obj, ruta):
    for parte in ruta.split("__"):
        obj = getattr(obj, parte, None)
    return obj


class Filas:
    """Doble del límite ORM; las funciones y modelos bajo prueba son reales."""

    def __init__(self, filas=()):
        self.filas = list(filas)

    def filter(self, **criterios):
        def coincide(fila):
            for campo, esperado in criterios.items():
                if campo.endswith("__in"):
                    if atributo(fila, campo[:-4]) not in esperado:
                        return False
                elif atributo(fila, campo) != esperado:
                    return False
            return True
        return Filas(fila for fila in self.filas if coincide(fila))

    def exclude(self, **criterios):
        descartadas = self.filter(**criterios).filas
        return Filas(fila for fila in self.filas if fila not in descartadas)

    def none(self):
        return Filas()

    def exists(self):
        return bool(self.filas)

    def first(self):
        return next(iter(self.filas), None)

    def get(self, **criterios):
        return self.filter(**criterios).first()

    def values_list(self, *campos, flat=False):
        valores = [tuple(atributo(fila, campo) for campo in campos) for fila in self.filas]
        return Filas(valor[0] if flat else valor for valor in valores)

    def distinct(self):
        unicas = []
        for fila in self.filas:
            if fila not in unicas:
                unicas.append(fila)
        return Filas(unicas)

    def __iter__(self):
        return iter(self.filas)

    def __len__(self):
        return len(self.filas)

    def order_by(self, *args):
        return self

    only = select_related = prefetch_related = select_for_update = order_by


class BnhCefTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.persona = Personas(cuil=CUIL, apellido="Pérez", nombre="Ana", dni="12345678")
        self.otra = Personas(cuil=OTRO, apellido="Otro", nombre="Docente")
        self.personas = [self.persona, self.otra]
        self.registros = [
            NS(persona=self.persona, cueanexo=CUE, eliminado=False),
            NS(persona=self.persona, cueanexo=CUE, eliminado=False),
            NS(persona=self.persona, cueanexo=OTRO_CUE, eliminado=False),
            NS(persona=self.otra, cueanexo=OTRO_CUE, eliminado=False),
        ]
        self.stack.enter_context(patch.object(
            Personas.objects, "filter",
            side_effect=lambda **kw: Filas(self.personas).filter(**kw),
        ))
        self.consultas_bnh = self.stack.enter_context(patch.object(
            RegistroActividades.objects, "filter",
            side_effect=lambda **kw: Filas(self.registros).filter(**kw),
        ))
        from . import services_bnh
        self.bnh = services_bnh

    def test_contrato_modelos_bnh_reales(self):
        for modelo, campos in (
            (Personas, ("cuil", "archivada")),
            (RegistroActividades, ("persona", "cueanexo", "eliminado")),
        ):
            for campo in campos:
                self.assertIsNotNone(modelo._meta.get_field(campo))

    def test_normalizacion_y_pertenencia_multiple_sin_filtros_extra(self):
        self.assertEqual(self.bnh.validar_docente_vinculado_bnh("20-12345678-9", CUE), CUIL)
        self.assertEqual(self.bnh.cueanexos_docente_bnh(CUIL), [CUE, OTRO_CUE])
        self.assertEqual(self.bnh.cuiles_docentes_bnh(CUE), [CUIL])
        self.assertEqual(
            self.bnh.pares_docente_cue_bnh([CUIL, OTRO], [CUE, OTRO_CUE]),
            {(CUIL, CUE), (CUIL, OTRO_CUE), (OTRO, OTRO_CUE)},
        )

    def test_inexistente_archivado_eliminado_y_otro_cef_rechazados(self):
        casos = ("inexistente", "archivada", "eliminados", "otro_cue")
        for caso in casos:
            with self.subTest(caso=caso):
                self.persona.archivada = caso == "archivada"
                for registro in self.registros:
                    if registro.persona is self.persona:
                        registro.eliminado = caso == "eliminados"
                cuil = "20999999999" if caso == "inexistente" else OTRO if caso == "otro_cue" else CUIL
                with self.assertRaises(ValidationError):
                    self.bnh.validar_docente_vinculado_bnh(cuil, CUE)

    def test_identificadores_invalidos_no_autorizan(self):
        for cuil, cue in (("", CUE), ("123", CUE), (CUIL, "123")):
            with self.subTest(cuil=cuil, cue=cue), self.assertRaises(ValidationError):
                self.bnh.validar_docente_vinculado_bnh(cuil, cue)
        self.assertEqual(self.bnh.cueanexos_docente_bnh("123"), [])

    def test_caida_bnh_falla_cerrado(self):
        self.consultas_bnh.side_effect = OperationalError("simulado")
        with self.assertRaisesMessageCompat("No se pudo consultar BNH"):
            self.bnh.validar_docente_vinculado_bnh(CUIL, CUE)

    def assertRaisesMessageCompat(self, texto):
        return self.assertRaisesRegex(ValidationError, texto)

    def test_profesor_sin_grupos_accede_a_sus_cefs(self):
        user = NS(is_authenticated=True, username=CUIL)
        filas = Filas([NS(cueanexo=CUE), NS(cueanexo=OTRO_CUE), NS(cueanexo="220000300")])
        with patch.object(models, "get_todos_los_cef", return_value=filas):
            resultado = models.get_cefs_cargables_usuario(
                user, {"puede_ver": True, "es_admin": False, "es_profesor_cef": True},
            )
        self.assertEqual([fila.cueanexo for fila in resultado], [CUE, OTRO_CUE])

    def test_cache_profesor_se_revalida_por_solicitud(self):
        user = NS(pk=987654)
        clave = permisos._permisos_cef_cache_key(user)
        cache.set(clave, {"es_profesor_cef": True, "cueanexos_cargables": [CUE]})
        self.addCleanup(cache.delete, clave)
        fresco = {"es_profesor_cef": True, "cueanexos_cargables": []}
        with patch.object(permisos, "_resolver_permisos_cef", return_value=fresco) as resolver:
            request = NS(user=user)
            self.assertEqual(permisos.get_permisos_cef_request(request)["cueanexos_cargables"], [])
            permisos.get_permisos_cef_request(request)
            self.assertEqual(resolver.call_count, 1)
            permisos.get_permisos_cef_request(NS(user=user))
            self.assertEqual(resolver.call_count, 2)

    def test_selector_profesor_no_reutiliza_cache_entre_solicitudes(self):
        request = NS(user=NS(pk=987654))
        opciones = [{"cueanexo": CUE, "nombre": "CEF"}]
        with patch.object(views_contexto, "_consultar_opciones_cef", return_value=(opciones, {})) as consultar:
            resultado = views_contexto._cef_options_usuario(
                request, {"es_profesor_cef": True, "puede_ver": True,
                          "es_admin": False, "cueanexos_cargables": [CUE]},
            )
        self.assertEqual(resultado, opciones)
        consultar.assert_called_once()

    def test_modelo_activo_rechaza_otro_cef_y_conserva_roles(self):
        grupo = models.CefGrupo(pk=1, cueanexo=CUE, ciclo_id=1)
        with patch.object(models.CefDocenteGrupo.objects, "filter", return_value=Filas()):
            for rol, _ in models.CefDocenteGrupo.Rol.choices:
                models.validar_docente_grupo_activo(grupo, CUIL, rol)
                with self.assertRaises(ValidationError):
                    models.validar_docente_grupo_activo(grupo, OTRO, rol)

    def test_modelo_conserva_duplicados_y_rol_unico(self):
        grupo = models.CefGrupo(pk=1, cueanexo=CUE, ciclo_id=1)
        existente = NS(docente_cuil=CUIL, rol="titular", docente_nombre_snapshot="Ana")
        with patch.object(models.CefDocenteGrupo.objects, "filter", return_value=Filas([existente])):
            with self.assertRaises(ValidationError):
                models.validar_docente_grupo_activo(grupo, CUIL, "suplente")
        existente.docente_cuil = OTRO
        with patch.object(models.CefDocenteGrupo.objects, "filter", return_value=Filas([existente])):
            with self.assertRaises(ValidationError):
                models.validar_docente_grupo_activo(grupo, CUIL, "titular")

    def test_baja_historica_no_exige_vinculacion(self):
        grupo = models.CefGrupo(pk=1, cueanexo=CUE, ciclo_id=1)
        self.persona.archivada = True
        asignacion = models.CefDocenteGrupo(
            grupo=grupo, docente_cuil=CUIL, rol="titular", estado="baja",
            fecha_desde=date(2026, 3, 1), fecha_hasta=date(2026, 4, 1),
        )
        asignacion.clean()
        asignacion.estado = "activo"
        asignacion.fecha_hasta = None
        with self.assertRaises(ValidationError):
            asignacion.clean()

    def test_creacion_usa_cue_del_grupo_recuperado_antes_de_escribir(self):
        grupo = NS(pk=1, ciclo_id=1, cueanexo=OTRO_CUE)
        recuperado = NS(pk=1, ciclo_id=1, cueanexo=CUE, ciclo=NS(anio=2026), estado="activo")
        with patch.object(services.transaction, "atomic", return_value=nullcontext()), \
             patch.object(services, "validar_ciclo_escribible"), \
             patch.object(services.CefGrupo.objects, "select_for_update", return_value=Filas([recuperado])), \
             patch.object(services, "validar_fecha_interactiva_ciclo", side_effect=lambda ciclo, fecha, **kw: fecha), \
             patch.object(services, "asegurar_docente_banco_activo") as banco, \
             patch.object(services.CefDocenteGrupo.objects, "create") as crear:
            with self.assertRaises(ValidationError):
                services.crear_asignacion_docente_activa(grupo, OTRO, "titular", NS(), date(2026, 3, 1))
            banco.assert_not_called()
            crear.assert_not_called()

    def test_busqueda_no_expone_ficha_de_otro_cef(self):
        with self.assertRaises(ValidationError):
            views_docentes_grupo._buscar_docente(OTRO, CUE)
        self.assertEqual(views_docentes_grupo._buscar_docente(CUIL, CUE).apellido, "Pérez")

    def test_post_banco_manual_deshabilitado(self):
        contexto = {"cef_context": {"cueanexo": CUE}}
        for accion in ("baja_cef", "reincorporar_cef", ""):
            request = NS(method="POST", POST={"accion": accion}, GET={},
                         headers={"x-requested-with": "XMLHttpRequest"})
            with patch.object(views_profesores, "contexto_base", return_value=contexto), \
                 patch.object(views_profesores, "perf_start_view"), \
                 patch.object(views_profesores, "asegurar_docente_banco_activo") as crear:
                respuesta = inspect.unwrap(views_profesores.profesores)(request)
            self.assertEqual(respuesta.status_code, 405)
            self.assertFalse(json.loads(respuesta.content)["ok"])
            crear.assert_not_called()

    def test_listado_bnh_incluye_docentes_sin_banco_ni_grupos(self):
        contexto = {"puede_consultar": True, "cueanexo": CUE}
        docentes = views_profesores._docentes_cef(contexto)
        self.assertEqual(len(docentes), 1)
        self.assertEqual(docentes[0].docente_cuil, CUIL)
        html = render_to_string("cef/profesores_lista_cef.html", {
            "docentes": docentes, "cef_context": {"puede_consultar": True},
        })
        self.assertIn("Sin grupos activos asignados", html)
        self.assertNotIn("Dar de baja del CEF", html)
        self.assertNotIn("Reincorporar", html)

    def test_modal_sin_vinculo_no_muestra_formulario_ni_ficha(self):
        error = "El profesor existe en BNH Personas, pero no está vinculado al CUE-Anexo seleccionado."
        html = render_to_string("cef/modal_busqueda_docente_cef.html", {
            "cuil_buscado": OTRO, "cuil_error": error, "modal_tiene_grupo": True,
        })
        self.assertIn(error, html)
        self.assertNotIn("Otro", html)
        self.assertNotIn("data-docente-modal-post-form>", html)

    def test_asistencia_filtra_grupos_asignados(self):
        base = Filas([NS(pk=1, estado="activo"), NS(pk=2, estado="activo")])
        with patch.object(views_asistencia, "get_permisos_cef_request", return_value={"es_profesor_cef": True}), \
             patch.object(views_asistencia.CefGrupo.objects, "filter", return_value=base), \
             patch.object(views_asistencia, "asignaciones_docentes_vigentes", return_value=Filas([
                 NS(docente_cuil=CUIL, rol="titular", grupo_id=1),
             ])):
            filas = views_asistencia._grupos_asistencia_queryset(
                NS(user=NS(is_authenticated=True, username=CUIL)),
                {"cueanexo": CUE, "ciclo": NS()},
            )
        self.assertEqual([grupo.pk for grupo in filas], [1])

    def anual(self, disponible=True):
        ciclo = NS(pk=1, anio=2026, actual=False, cerrado=True)
        grupo = NS(
            pk=1, cueanexo=CUE, ciclo=ciclo, estado="activo",
            actividad_id=1, numero=1, actividad_nombre_snapshot="Actividad",
            actividad=NS(nombre="Actividad"), turno_id=1,
            turno=NS(activo=True, nombre="Mañana", hora_desde_referencia=time(8),
                     hora_hasta_referencia=time(12)),
            hora_inicio=time(9), hora_fin=time(10), cupo_maximo=25,
            dias_prevalidacion=[NS(pk=1, dia_semana_id=1, dia_semana=NS(numero=1))],
        )
        bancos = [NS(pk=i, cueanexo=CUE, docente_cuil=cuil, ciclo=ciclo,
                     estado="activo", docente_nombre_snapshot="Profesor")
                  for i, cuil in enumerate((CUIL, OTRO), 1)]
        asignaciones = [NS(pk=i, grupo_id=1, grupo=grupo, docente_cuil=cuil,
                          estado="activo", rol="suplente", docente_nombre_snapshot="Profesor")
                        for i, cuil in enumerate((CUIL, OTRO), 1)]
        filas_por_modelo = (
            (models.CefCiclo, []), (models.CefDatosRelevamiento, []),
            (models.CefGrupo, [grupo]), (models.CefAlumnoCef, []),
            (models.CefDocenteCef, bancos), (models.CefInscripcion, []),
            (models.CefDocenteGrupo, asignaciones), (models.CefInventarioMaterial, []),
        )
        for modelo, filas in filas_por_modelo:
            self.stack.enter_context(patch.object(
                modelo.objects, "filter", side_effect=lambda _filas=filas, **kw: Filas(_filas).filter(**kw),
            ))
        for modelo in (models.CefGrupoDiaFuncionamiento, models.CefInventarioMaterialEstado):
            self.stack.enter_context(patch.object(modelo.objects, "select_related", return_value=Filas()))
        self.stack.enter_context(patch.object(services_anual, "origen_anual_previsualizable", return_value=True))
        self.stack.enter_context(patch.object(services_anual, "_anio_maximo_ciclo", return_value=2099))
        if not disponible:
            self.consultas_bnh.side_effect = OperationalError("simulado")
        return services_anual.prevalidar_generacion_anual(ciclo)

    def test_anual_omite_sin_vinculo_y_ajusta_contadores_por_lote(self):
        resultado = self.anual()
        self.assertFalse(resultado["bloqueado"], resultado["errores"])
        self.assertEqual(resultado["proyeccion"]["docentes_origen_ids"], [1])
        self.assertEqual(resultado["proyeccion"]["asignaciones_origen_ids"], [1])
        self.assertEqual(resultado["totales"]["asignaciones"], {"encontrados": 2, "proyectables": 1})
        self.assertEqual(resultado["omisiones_bnh"], {"docentes": 1, "asignaciones": 1})
        self.assertTrue(any("sin vinculación" in aviso["mensaje"] for aviso in resultado["advertencias"]))
        self.consultas_bnh.assert_called_once()

    def test_anual_bloquea_si_bnh_no_esta_disponible(self):
        resultado = self.anual(disponible=False)
        self.assertTrue(resultado["bloqueado"])
        self.assertEqual(resultado["proyeccion"]["asignaciones_origen_ids"], [])
        self.assertTrue(any(error["codigo"] == "bnh_no_disponible" for error in resultado["errores"]))


    def test_ajax_vinculacion_perdida_muestra_error_y_conserva_modal(self):
        self.persona.archivada = True
        ciclo = models.CefCiclo(pk=1, anio=2026, fecha_inicio=date(2026, 3, 1))
        grupo = models.CefGrupo(pk=1, cueanexo=CUE, ciclo=ciclo)
        cef_context = {
            "cueanexo": CUE, "ciclo": ciclo, "puede_operar": True,
            "puede_consultar": True, "ciclo_cerrado": False, "querystring": "",
        }
        request = RequestFactory().post(
            "/cef/profesores/", {"accion": "asignar_grupo", "grupo_id": "1", "cuil": CUIL},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        request.user = NS()
        with patch.object(views_profesores, "contexto_base", return_value={"cef_context": cef_context}), \
             patch.object(views_profesores, "perf_start_view"), \
             patch.object(views_profesores, "_grupo_profesores_seguro", return_value=grupo), \
             patch.object(views_profesores, "_profesores_listado_context", return_value={}), \
             patch.object(views_profesores, "crear_asignacion_docente_activa") as crear:
            respuesta = inspect.unwrap(views_profesores.profesores)(request)
        datos = json.loads(respuesta.content)
        self.assertFalse(datos["ok"])
        self.assertFalse(datos["close_modal"])
        self.assertIn("BNH Personas", datos["message"])
        self.assertIn("disabled", datos["modal_html"])
        self.assertIn("fragment_html", datos)
        crear.assert_not_called()

    def test_creacion_incorpora_banco_automaticamente_y_conserva_rol_manual(self):
        grupo = NS(pk=1, ciclo_id=1, cueanexo=CUE, ciclo=NS(anio=2026), estado="activo")
        periodo = NS(pk=1, fecha_alta=date(2026, 3, 1))
        with patch.object(services.transaction, "atomic", return_value=nullcontext()), \
             patch.object(services, "validar_ciclo_escribible"), \
             patch.object(services.CefGrupo.objects, "select_for_update", return_value=Filas([grupo])), \
             patch.object(services, "validar_fecha_interactiva_ciclo", side_effect=lambda ciclo, fecha, **kw: fecha), \
             patch.object(services, "asegurar_docente_banco_activo", return_value=(periodo, True)) as banco, \
             patch.object(services, "_periodo_docente_activo", return_value=periodo), \
             patch.object(services, "_fecha_minima_asignacion", return_value=periodo.fecha_alta), \
             patch.object(models.CefDocenteGrupo.objects, "filter", return_value=Filas()), \
             patch.object(services.CefDocenteGrupo.objects, "create") as crear:
            services.crear_asignacion_docente_activa(grupo, CUIL, "interino", NS(), date(2026, 3, 1))
        banco.assert_called_once()
        self.assertEqual(crear.call_args.kwargs["rol"], "interino")
        self.assertEqual(crear.call_args.kwargs["docente_cuil"], CUIL)

    def test_edicion_y_reactivacion_revalidan_bnh(self):
        self.persona.archivada = True
        grupo = NS(pk=1, ciclo_id=1, cueanexo=CUE, ciclo=NS(anio=2026), estado="activo")
        asignacion = NS(
            pk=10, grupo=grupo, grupo_id=1, docente_cuil=CUIL,
            estado="activo", rol="titular", save=Mock(),
        )
        with patch.object(services.transaction, "atomic", side_effect=lambda: nullcontext()), \
             patch.object(services, "validar_ciclo_escribible"), \
             patch.object(services.CefGrupo.objects, "select_for_update", return_value=Filas([grupo])), \
             patch.object(services.CefDocenteGrupo.objects, "select_for_update", return_value=Filas([asignacion])):
            with self.assertRaises(ValidationError):
                services.editar_asignacion_docente_activa(asignacion, NS(), "titular", date(2026, 3, 1))
            asignacion.estado = "baja"
            with self.assertRaises(ValidationError):
                services.reasignar_docente_grupo(asignacion, NS())
        asignacion.save.assert_not_called()

    def test_navegacion_nuevo_grupo_y_edicion(self):
        cef_context = {
            "cueanexo": CUE, "ciclo": NS(pk=1, anio=2026),
            "puede_operar": True, "querystring": f"cueanexo={CUE}&ciclo=1",
        }
        grupo = NS(pk=17, estado="activo")
        request = NS(method="POST", POST={}, user=NS())
        for existente in (False, True):
            with self.subTest(existente=existente), \
                 patch.object(views_carga_grupo, "contexto_base", return_value={"cef_context": cef_context}), \
                 patch.object(views_carga_grupo, "_grupo_seguro", return_value=grupo), \
                 patch.object(views_carga_grupo, "CefGrupoForm") as form, \
                 patch.object(views_carga_grupo, "CefGrupoDiasForm") as dias, \
                 patch.object(views_carga_grupo, "_guardar_grupo", return_value=grupo), \
                 patch.object(views_carga_grupo.messages, "success"):
                form.return_value.is_valid.return_value = True
                dias.return_value.is_valid.return_value = True
                respuesta = inspect.unwrap(views_carga_grupo.carga_grupo_form)(
                    request, grupo_id=17 if existente else None,
                )
            self.assertEqual(respuesta.status_code, 302)
            self.assertIn("ciclo=1", respuesta.url)
            self.assertEqual("#profesores-curso" in respuesta.url, not existente)

    def test_templates_modificados_compilan(self):
        for nombre in (
            "profesores_lista_cef.html", "profesores_historial_lista_cef.html",
            "profesores_seccion_cef.html", "modal_busqueda_docente_cef.html",
            "asignar_profesor_grupo_modal_cef.html", "profesores_cef.html",
        ):
            with self.subTest(template=nombre):
                self.assertIsNotNone(get_template("cef/" + nombre))

    def test_profesor_solo_puede_acceder_a_asistencia(self):
        from django.core.exceptions import PermissionDenied
        perfil = {"puede_ver": True, "solo_asistencia": True}
        with patch.object(permisos, "get_permisos_cef_request", return_value=perfil):
            with self.assertRaises(PermissionDenied):
                permisos._validar_acceso_cef(NS())
            permisos._validar_acceso_cef(NS(), permitir_solo_asistencia=True)

    def test_edicion_desde_vista_conserva_la_busqueda_con_cue(self):
        ciclo = models.CefCiclo(pk=1, anio=2026, fecha_inicio=date(2026, 3, 1))
        grupo = models.CefGrupo(pk=1, cueanexo=CUE, ciclo=ciclo)
        asignacion = models.CefDocenteGrupo(
            pk=10, grupo=grupo, docente_cuil=CUIL, rol="titular",
            fecha_desde=date(2026, 3, 1),
        )
        contexto = {"cef_context": {
            "cueanexo": CUE, "ciclo": ciclo, "puede_operar": True,
            "querystring": f"cueanexo={CUE}&ciclo=1",
        }}
        request = RequestFactory().post("/cef/grupos/1/docentes/10/", {})
        request.user = NS()
        form = Mock(instance=asignacion)
        form.is_valid.return_value = True
        form.cleaned_data = {"rol": "titular", "fecha_desde": date(2026, 3, 1)}
        with patch.object(views_docentes_grupo, "contexto_base", return_value=contexto), \
             patch.object(views_docentes_grupo, "_grupo_seguro", return_value=grupo), \
             patch.object(views_docentes_grupo, "get_object_or_404", return_value=asignacion), \
             patch.object(views_docentes_grupo, "CefDocenteGrupoForm", return_value=form), \
             patch.object(views_docentes_grupo, "editar_asignacion_docente_activa", return_value=asignacion) as editar, \
             patch.object(views_docentes_grupo.messages, "success"):
            respuesta = inspect.unwrap(views_docentes_grupo.editar_docente_grupo)(request, 1, 10)
        self.assertEqual(respuesta.status_code, 302)
        editar.assert_called_once()

    def test_listado_ignora_personas_sin_identidad_cuil_valida(self):
        sin_cuil = Personas(cuil=None, apellido="Sin CUIL", nombre="Persona")
        self.personas.append(sin_cuil)
        self.registros.append(NS(persona=sin_cuil, cueanexo=CUE, eliminado=False))
        self.assertEqual(self.bnh.cuiles_docentes_bnh(CUE), [CUIL])
        self.assertEqual(len(views_profesores._docentes_cef(
            {"puede_consultar": True, "cueanexo": CUE},
        )), 1)

    def test_consulta_booleana_no_autoriza_identificadores_ausentes(self):
        for cuil, cue in ((None, CUE), (CUIL, None), (None, None), ("123", CUE)):
            with self.subTest(cuil=cuil, cue=cue):
                self.assertFalse(self.bnh.docente_vinculado_bnh(cuil, cue))
