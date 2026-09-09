from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from . import views_analisis_sge_ra, views_dash


class FakeQuerySet:
    def __init__(self):
        self.filters = []
        self.none_called = False

    def filter(self, **kwargs):
        self.filters.append(kwargs)
        return self

    def none(self):
        self.none_called = True
        return self


class SgeRoleScopeTests(TestCase):
    def _request(self):
        return SimpleNamespace(
            user=SimpleNamespace(username="20123456783"),
            GET={},
            POST={},
            session={},
        )

    def _connection(self, rows):
        cursor = Mock()
        cursor.fetchall.return_value = rows
        connection = Mock()
        connection.cursor.return_value = cursor
        return connection, cursor

    def test_director_de_nivel_is_global_and_supervisor_is_not(self):
        self.assertIn("Director de Nivel", views_dash.ROLES_GLOBALES_SGE)
        self.assertNotIn("Supervisor", views_dash.ROLES_GLOBALES_SGE)

        request = self._request()
        with patch.object(
            views_dash, "obtener_cargo_usuario", return_value="Director de Nivel"
        ):
            context = views_dash.resolver_contexto_sge(request)
        self.assertEqual(context["alcance"], "global")

    def test_supervisor_uses_all_assigned_cues_without_selector_or_region_scope(self):
        for rows, expected in (
            ([("220084600", "Sede"), ("220084601", "Anexo")],
             ["220084600", "220084601"]),
            ([], []),
        ):
            with self.subTest(cueanexos=expected):
                request = self._request()
                request.user.is_authenticated = True
                request.GET[views_dash.PARAM_SGE_CUEANEXO] = "999999999"
                request.POST[views_dash.PARAM_SGE_CUEANEXO] = "220084600"
                request.session[views_dash.SESSION_SGE_CUEANEXO_KEY] = "220084600"
                connection, cursor = self._connection(rows)
                with (
                    patch.object(views_dash, "obtener_cargo_usuario", return_value="Supervisor"),
                    patch.object(views_dash.psycopg2, "connect", return_value=connection),
                    patch.object(views_dash, "obtener_regiones_permitidas") as regiones,
                    patch.object(views_dash, "_opciones_cueanexo_sge") as director,
                    patch.object(views_dash, "_resolver_cueanexo_sge") as selector,
                ):
                    context = views_dash.resolver_contexto_sge(request)

                self.assertEqual(context["alcance"], "cue")
                self.assertFalse(context["es_global"])
                self.assertEqual(context["cueanexos_permitidos"], expected)
                self.assertEqual(context["regiones_permitidas"], [])
                self.assertEqual(context["cueanexo_actual"], "")
                self.assertFalse(context["mostrar_selector_cueanexo"])
                regiones.assert_not_called()
                director.assert_not_called()
                selector.assert_not_called()
                connection.close.assert_called_once_with()
                queryset = FakeQuerySet()
                result = views_dash.filtrar_queryset_sge(
                    queryset, context, "region", "cueanexo"
                )
                self.assertIs(result, queryset)
                self.assertEqual(queryset.none_called, not expected)
                self.assertEqual(
                    queryset.filters,
                    [{"cueanexo__in": expected}] if expected else [],
                )

    def test_supervisor_options_deduplicate_and_use_active_parameterized_sql(self):
        connection, cursor = self._connection([
            ("2200846-00", " Sede "),
            ("220084600", "Otra oferta"),
            ("220084601", "   "),
            ("220084602", None),
            (None, "Sin CUE"),
            (" ", "Sin CUE"),
            ("abc", "Sin CUE"),
        ])
        user = SimpleNamespace(username="20-12345678-3", is_authenticated=True)
        with patch.object(views_dash.psycopg2, "connect", return_value=connection):
            opciones = views_dash._opciones_cueanexo_supervisor_sge(user)

        self.assertEqual(opciones, [
            {"cueanexo": "220084600", "nombre": "Sede", "region": ""},
            {"cueanexo": "220084601", "nombre": "Establecimiento sin nombre", "region": ""},
            {"cueanexo": "220084602", "nombre": "Establecimiento sin nombre", "region": ""},
        ])
        cursor.execute.assert_called_once()
        sql, params = cursor.execute.call_args.args
        sql = " ".join(sql.split())
        self.assertEqual(params, ["20123456783"])
        self.assertNotIn("20123456783", sql)
        self.assertEqual(sql.count("%s"), 1)
        self.assertIn("FROM supervisores.supervisor_registro_supervisor AS s", sql)
        self.assertIn("JOIN supervisores.supervisor_registro_supervisor_regional AS sr", sql)
        self.assertIn("JOIN supervisores.supervisor_registro_supervisor_regional_oferta AS o", sql)
        self.assertIn("ON sr.supervisor_id = s.id AND sr.activo = TRUE", sql)
        self.assertIn("ON o.supervisor_regional_id = sr.id AND o.activo = TRUE", sql)
        self.assertIn(
            r"WHERE REGEXP_REPLACE(CAST(s.cuil AS TEXT), '\D', '', 'g') = %s AND s.activo = TRUE",
            sql,
        )
        self.assertEqual(sql.count("activo = TRUE"), 3)
        self.assertIn("o.cueanexo IS NOT NULL", sql)
        self.assertIn("TRIM(CAST(o.cueanexo AS TEXT)) <> ''", sql)
        self.assertNotIn("responsable_alta_id", sql)
        self.assertNotIn("region_id", sql)
        connection.close.assert_called_once_with()

    def test_supervisor_invalid_cuil_never_connects_and_denies_access(self):
        for user in (
            None,
            SimpleNamespace(username="", is_authenticated=True),
            SimpleNamespace(username="123", is_authenticated=True),
            SimpleNamespace(username="20123456783", is_authenticated=False),
        ):
            with self.subTest(user=user):
                request = self._request()
                request.user = user
                with (
                    patch.object(views_dash, "obtener_cargo_usuario", return_value="Supervisor"),
                    patch.object(views_dash.psycopg2, "connect") as connect,
                ):
                    context = views_dash.resolver_contexto_sge(request)
                connect.assert_not_called()
                self.assertEqual(context["alcance"], "cue")
                self.assertEqual(context["cueanexos_permitidos"], [])
                queryset = FakeQuerySet()
                views_dash.filtrar_queryset_sge(queryset, context, "region", "cueanexo")
                self.assertTrue(queryset.none_called)
                self.assertEqual(queryset.filters, [])

    def test_supervisor_errors_return_no_options_and_close_connection(self):
        user = SimpleNamespace(username="20123456783", is_authenticated=True)
        for stage in ("connect", "cursor", "execute", "fetchall"):
            with self.subTest(stage=stage):
                connection, cursor = self._connection([])
                with patch.object(
                    views_dash.psycopg2, "connect", return_value=connection
                ) as connect:
                    target = {
                        "connect": connect,
                        "cursor": connection.cursor,
                        "execute": cursor.execute,
                        "fetchall": cursor.fetchall,
                    }[stage]
                    target.side_effect = RuntimeError("Error simulado")
                    self.assertEqual(
                        views_dash._opciones_cueanexo_supervisor_sge(user), []
                    )
                if stage == "connect":
                    connection.close.assert_not_called()
                else:
                    connection.close.assert_called_once_with()

    def test_gestor_roles_and_active_fallback(self):
        self.assertEqual(views_dash.ROLES_REGIONALES_SGE, {"Regional"})
        self.assertEqual(
            views_dash.ROLES_GESTORES_SGE,
            {"Gestor", "Gestor / Agente"},
        )

        perfil_query = Mock()
        perfil_query.get.side_effect = views_dash.UsuarioPerfil.DoesNotExist
        connection = Mock()
        cursor = Mock()
        cursor.fetchone.side_effect = [None, (1,)]
        connection.cursor.return_value = cursor

        with (
            patch.object(
                views_dash.UsuarioPerfil.objects,
                "select_related",
                return_value=perfil_query,
            ),
            patch.object(views_dash.psycopg2, "connect", return_value=connection),
        ):
            cargo = views_dash.obtener_cargo_usuario("20123456783")

        self.assertEqual(cargo, "Gestor / Agente")
        gestor_sql = cursor.execute.call_args_list[1].args[0]
        self.assertIn("activo = true", gestor_sql)

    def test_regional_uses_only_its_active_table(self):
        connection, cursor = self._connection([(" R.E. 7 ",), ("R.E. 9",)])
        with (
            patch.object(views_dash, "obtener_cargo_usuario", return_value="Regional"),
            patch.object(views_dash.psycopg2, "connect", return_value=connection),
        ):
            regiones = views_dash.obtener_regiones_permitidas(
                SimpleNamespace(username="20123456783")
            )

        self.assertEqual(regiones, {"R.E. 7", "R.E. 9"})
        sql = cursor.execute.call_args.args[0]
        self.assertIn("usuarios_regionalusuarios ", sql)
        self.assertNotIn("usuarios_regionalusuariosagentes", sql)
        self.assertIn("activo = true", sql)

    def test_gestor_active_todas_is_global(self):
        connection, cursor = self._connection([(" todas ",), ("R.E. 7",)])
        with (
            patch.object(views_dash, "obtener_cargo_usuario", return_value="Gestor"),
            patch.object(views_dash.psycopg2, "connect", return_value=connection),
        ):
            regiones = views_dash.obtener_regiones_permitidas(
                SimpleNamespace(username="20123456783")
            )

        self.assertEqual(regiones, "TODAS")
        sql = cursor.execute.call_args.args[0]
        self.assertIn("usuarios_regionalusuariosagentes", sql)
        self.assertIn("activo = true", sql)

    def test_gestor_and_legacy_alias_keep_regional_scope(self):
        for cargo in ("Gestor", "Gestor / Agente"):
            request = self._request()
            with (
                patch.object(views_dash, "obtener_cargo_usuario", return_value=cargo),
                patch.object(
                    views_dash,
                    "obtener_regiones_permitidas",
                    return_value={"R.E. 7", "R.E. 9"},
                ),
            ):
                context = views_dash.resolver_contexto_sge(request)

            self.assertEqual(context["alcance"], "regional")
            self.assertEqual(
                context["regiones_permitidas"],
                ["R.E. 7", "R.E. 9"],
            )

    def test_gestor_inactive_todas_or_no_rows_has_no_access(self):
        connection, cursor = self._connection([])
        with (
            patch.object(views_dash, "obtener_cargo_usuario", return_value="Gestor"),
            patch.object(views_dash.psycopg2, "connect", return_value=connection),
        ):
            regiones = views_dash.obtener_regiones_permitidas(
                SimpleNamespace(username="20123456783")
            )

        self.assertEqual(regiones, set())
        self.assertIn("activo = true", cursor.execute.call_args.args[0])

        request = self._request()
        opciones = Mock()
        with (
            patch.object(views_dash, "obtener_cargo_usuario", return_value="Gestor"),
            patch.object(views_dash, "obtener_regiones_permitidas", return_value=set()),
            patch.object(views_dash, "_opciones_cueanexo_sge", opciones),
        ):
            context = views_dash.resolver_contexto_sge(request)

        self.assertEqual(context["alcance"], "regional")
        self.assertEqual(context["regiones_permitidas"], [])
        opciones.assert_not_called()
        queryset = FakeQuerySet()
        views_dash.filtrar_queryset_sge(queryset, context, "region", "cueanexo")
        self.assertTrue(queryset.none_called)

    def test_director_is_cue_and_unknown_role_has_no_access(self):
        opciones = [
            {"cueanexo": "220084600", "nombre": "Sede", "region": "R.E. 7"},
            {"cueanexo": "220084601", "nombre": "Anexo", "region": "R.E. 7"},
        ]
        request = self._request()
        regiones = Mock()
        resolver_cueanexo = Mock()
        with (
            patch.object(views_dash, "obtener_cargo_usuario", return_value="Director"),
            patch.object(views_dash, "obtener_regiones_permitidas", regiones),
            patch.object(views_dash, "_opciones_cueanexo_sge", return_value=opciones),
            patch.object(views_dash, "_resolver_cueanexo_sge", resolver_cueanexo),
        ):
            context = views_dash.resolver_contexto_sge(request)

        self.assertEqual(context["alcance"], "cue")
        self.assertEqual(
            context["cueanexos_permitidos"],
            ["220084600", "220084601"],
        )
        self.assertEqual(context["cueanexo_actual"], "")
        self.assertFalse(context["mostrar_selector_cueanexo"])
        resolver_cueanexo.assert_not_called()
        regiones.assert_not_called()
        queryset = FakeQuerySet()
        result = views_dash.filtrar_queryset_sge(
            queryset,
            context,
            "region",
            "cueanexo",
        )
        self.assertIs(result, queryset)
        self.assertEqual(
            queryset.filters,
            [{"cueanexo__in": ["220084600", "220084601"]}],
        )

        unknown_request = self._request()
        with patch.object(
            views_dash,
            "obtener_cargo_usuario",
            return_value="Rol desconocido",
        ):
            unknown = views_dash.resolver_contexto_sge(unknown_request)
        self.assertEqual(unknown["alcance"], "sin_acceso")
        queryset = FakeQuerySet()
        views_dash.filtrar_queryset_sge(
            queryset,
            unknown,
            "region",
            "cueanexo",
        )
        self.assertTrue(queryset.none_called)

    def test_cue_scope_with_one_or_no_allowed_cueanexos(self):
        one_queryset = FakeQuerySet()
        result = views_dash.filtrar_queryset_sge(
            one_queryset,
            {
                "alcance": "cue",
                "cueanexos_permitidos": ["220084600"],
            },
            "region",
            "cueanexo",
        )
        self.assertIs(result, one_queryset)
        self.assertEqual(
            one_queryset.filters,
            [{"cueanexo__in": ["220084600"]}],
        )

        empty_queryset = FakeQuerySet()
        result = views_dash.filtrar_queryset_sge(
            empty_queryset,
            {
                "alcance": "cue",
                "cueanexos_permitidos": [],
            },
            "region",
            "cueanexo",
        )
        self.assertIs(result, empty_queryset)
        self.assertTrue(empty_queryset.none_called)
        self.assertEqual(empty_queryset.filters, [])

    def test_shared_filter_preserves_regional_and_global_scope(self):
        regional_queryset = FakeQuerySet()
        result = views_dash.filtrar_queryset_sge(
            regional_queryset,
            {
                "alcance": "regional",
                "regiones_permitidas": ["R.E. 7", "R.E. 9"],
            },
            "region",
            "cueanexo",
        )
        self.assertIs(result, regional_queryset)
        self.assertEqual(
            regional_queryset.filters,
            [{"region__in": ["R.E. 7", "R.E. 9"]}],
        )

        global_queryset = FakeQuerySet()
        result = views_dash.filtrar_queryset_sge(
            global_queryset,
            {"alcance": "global"},
            "region",
            "cueanexo",
        )
        self.assertIs(result, global_queryset)
        self.assertEqual(global_queryset.filters, [])
        self.assertFalse(global_queryset.none_called)

    def test_comparativa_director_filters_all_allowed_cues(self):
        queryset = FakeQuerySet()
        with patch.object(
            views_analisis_sge_ra.ResumenSgeRa.objects,
            "using",
            return_value=queryset,
        ):
            result = views_analisis_sge_ra._queryset_resumen_autorizado({
                "alcance": "cue",
                "cueanexos_permitidos": ["220084600", "220084601"],
            })

        self.assertIs(result, queryset)
        self.assertEqual(
            queryset.filters,
            [{"cueanexo__in": ["220084600", "220084601"]}],
        )
