"""Adaptador sintético en memoria. No importa Django, drivers ni configuración.

Extrae por AST funciones de producción: no importa sus módulos ni ejecuta
imports, AppConfig, modelos Django o declaraciones de campos.
No reproduce locks, SQL, constraints de BD, caché, autenticación o transacciones reales.
"""
import ast
import copy
from datetime import date, datetime, time, timedelta
from pathlib import Path
import re
from types import ModuleType, SimpleNamespace

from safety import Blocked, Skipped, safe_code


class ValidationError(Exception):
    def __init__(self, message, *args, **kwargs):
        if isinstance(message, dict):
            self.message_dict = {key: value if isinstance(value, list) else [value]
                                 for key, value in message.items()}
            self.messages = [str(item) for values in self.message_dict.values() for item in values]
        else:
            self.messages = [str(item) for item in message] if isinstance(message, list) else [str(message)]
        super().__init__("VALIDACION_SINTETICA")


class PermissionDenied(Exception):
    pass


class IntegrityError(Exception):
    pass


class MaxValueValidator:
    def __init__(self, value):
        self.limit_value = value


def vals(obj, path):
    if isinstance(obj, dict) and path in obj:
        return [obj[path]]
    parts = path.split("__")
    current = [obj]
    for part in parts:
        out = []
        for item in current:
            if item is None:
                out.append(None)
                continue
            value = item.get(part) if isinstance(item, dict) else getattr(item, part)
            if isinstance(value, Query):
                out.extend(list(value) or [None])
            else:
                out.append(value)
        current = out
    return current


def joined_rows(obj, paths):
    """Correlaciona columnas de una misma relación; no implementa un planificador SQL."""
    aliases = [{}]
    output = []
    while aliases:
        selected = aliases.pop()
        row, expansion = {}, None
        for path in paths:
            if isinstance(obj, dict) and path in obj:
                row[path] = obj[path]
                continue
            value, prefix = obj, []
            for part in path.split("__"):
                prefix.append(part)
                key = "__".join(prefix)
                if key in selected:
                    value = selected[key]
                    continue
                if value is None:
                    break
                value = value.get(part) if isinstance(value, dict) else getattr(value, part)
                if isinstance(value, Query):
                    expansion = (key, list(value) or [None])
                    break
            if expansion:
                break
            row[path] = value
        if expansion:
            key, values = expansion
            aliases.extend(dict(selected, **{key: item}) for item in reversed(values))
        else:
            output.append(row)
    return output


def matches(obj, criteria):
    ops = {"in", "isnull", "lt", "lte", "gt", "gte", "exact"}
    parsed = []
    for key, expected in criteria.items():
        parts = key.split("__")
        op = parts.pop() if parts[-1] in ops else "exact"
        parsed.append(("__".join(parts), op, expected))
    def compare(value, op, expected):
        if op == "isnull":
            return (value is None) == expected
        if op == "in":
            return value is not None and value in expected
        if op == "exact":
            return value == expected
        if value is None or expected is None:
            return False
        return {"lt": lambda: value < expected, "lte": lambda: value <= expected,
                "gt": lambda: value > expected, "gte": lambda: value >= expected}[op]()
    return any(all(compare(row[path], op, expected) for path, op, expected in parsed)
               for row in joined_rows(obj, [item[0] for item in parsed]))


class Q:
    def __init__(self, **kwargs):
        self.predicate = lambda row: matches(row, kwargs)
    def __or__(self, other):
        result = Q()
        result.predicate = lambda row: self.predicate(row) or other.predicate(row)
        return result
    def __and__(self, other):
        result = Q()
        result.predicate = lambda row: self.predicate(row) and other.predicate(row)
        return result
    def __invert__(self):
        result = Q()
        result.predicate = lambda row: not self.predicate(row)
        return result


class Query:
    def __init__(self, model, data):
        self.model, self.data = model, list(data)
    def __iter__(self):
        return iter(self.data)
    def __len__(self):
        return len(self.data)
    def __getitem__(self, index):
        return self.data[index]
    def all(self):
        return Query(self.model, self.data)
    def none(self):
        return Query(self.model, [])
    def filter(self, *predicates, **kwargs):
        return Query(self.model, [x for x in self.data
            if all(p.predicate(x) for p in predicates) and matches(x, kwargs)])
    def exclude(self, *predicates, **kwargs):
        return Query(self.model, [x for x in self.data
            if not (all(p.predicate(x) for p in predicates) and matches(x, kwargs))])
    def order_by(self, *fields):
        data = list(self.data)
        for field in reversed(fields):
            key = field.lstrip("-")
            data.sort(key=lambda obj: (vals(obj, key)[0] is None, vals(obj, key)[0]),
                      reverse=field.startswith("-"))
        return Query(self.model, data)
    def first(self):
        return self.data[0] if self.data else None
    def exists(self):
        return bool(self.data)
    def count(self):
        return len(self.data)
    def get(self, **kwargs):
        rows = self.filter(**kwargs).data
        if not rows:
            raise self.model.DoesNotExist()
        if len(rows) > 1:
            raise self.model.MultipleObjectsReturned()
        return rows[0]
    def delete(self):
        # Sólo las relaciones de días usadas por _guardar_dias; sin cascadas implícitas.
        if self.model.__name__ != "CefGrupoDiaFuncionamiento":
            raise Blocked("BORRADO_NO_REPRESENTADO_EN_ADAPTADOR")
        for row in self.data:
            self.model.objects.rows.pop(row.pk)
        return len(self.data), {self.model.__name__: len(self.data)}
    def get_or_create(self, defaults=None, **kwargs):
        try:
            return self.get(**kwargs), False
        except self.model.DoesNotExist:
            return self.create(**dict(defaults or {}, **kwargs)), True
    def select_for_update(self, *args, **kwargs):
        return self  # Sólo simulación; no prueba exclusión, bloqueos ni concurrencia.
    def select_related(self, *args):
        return self
    def only(self, *args):
        return self
    def using(self, *args):
        return self
    def prefetch_related(self, *items):
        for item in items:
            if not isinstance(item, str) and item.to_attr:
                for row in self.data:
                    related = list(getattr(row, item.lookup))
                    if item.queryset is not None:
                        related = list(item.queryset.filter(pk__in=[record.pk for record in related]))
                    setattr(row, item.to_attr, related)
        return self
    def values(self, *fields):
        rows = []
        for obj in self.data:
            rows.extend(joined_rows(obj, fields))
        return Query(self.model, rows)
    def values_list(self, *fields, flat=False):
        rows = self.values(*fields).data
        return Query(self.model, [row[fields[0]] if flat else tuple(row[f] for f in fields)
                                 for row in rows])
    def distinct(self):
        out = []
        for item in self.data:
            if item not in out:
                out.append(item)
        return Query(self.model, out)
    def aggregate(self, **expressions):
        return {key: max((x for obj in self.data for x in vals(obj, expression.field)
                         if x is not None), default=None)
                for key, expression in expressions.items()}
    def create(self, **kwargs):
        record = self.model(**kwargs)
        record.save()
        return record
    def bulk_create(self, objects, **kwargs):
        for record in objects:
            record.store(validate=False)
        return objects


class Manager:
    def __init__(self, model):
        self.model, self.rows, self.sequence = model, {}, 0
    def all(self):
        return Query(self.model, copy.deepcopy(list(self.rows.values())))
    def __getattr__(self, name):
        return getattr(self.all(), name)


class Record:
    registry = {}
    relations = {"ciclo": "CefCiclo", "grupo": "CefGrupo", "alumno": "Alumno",
                 "jornada": "CefJornadaAsistencia", "inscripcion": "CefInscripcion",
                 "asistencia": "CefAsistencia", "grupo_origen": "CefGrupo"}
    def __init__(self, **kwargs):
        self.__dict__.update(pk=None, estado="activo", fecha_baja=None, fecha_hasta=None,
            motivo_baja="", observaciones="", creado_en=0, actualizado_en=0,
            fecha_inscripcion=None, fecha_desde=None, fecha_alta=None,
            fecha_inicio=None, fecha_fin=None, cerrado=False, actual=False, activo=True,
            codigo_ra_override=None, motivo_codigo_ra_override="", cupo_maximo=None,
            nombre="", apellidos="", nombres="", numero=1, orden=0, descripcion="",
            actividad_nombre_snapshot="", alumno_nombre_snapshot="",
            docente_nombre_snapshot="", docente_cuil="", motivo="",
            estado_anterior=None, cantidad=0)
        self.__dict__.update(kwargs)
    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        if name == "id":
            return self.pk
        if name.endswith("_id"):
            ref = self.__dict__.get(name[:-3])
            return getattr(ref, "pk", None)
        if name in self.relations and name + "_id" in self.__dict__:
            return self.registry[self.relations[name]].objects.get(pk=self.__dict__[name + "_id"])
        related = {
            "dias_funcionamiento": ("CefGrupoDiaFuncionamiento", "grupo"),
            "movimientos_estado": ("CefGrupoEstadoMovimiento", "grupo"),
            "asistencias": ("CefAsistencia", "jornada"),
            "movimientos": ("CefAsistenciaMovimiento", "asistencia"),
            "distribuciones_estado": ("CefInventarioMaterialEstado", "inventario_material"),
        }
        if name in related:
            model, field = related[name]
            return self.registry[model].objects.filter(**{field: self})
        if name.endswith("_snapshot"):
            return ""
        raise Blocked("ATRIBUTO_NO_REPRESENTADO_EN_ADAPTADOR")
    def __eq__(self, other):
        return type(other) is type(self) and self.pk is not None and self.pk == other.pk
    def __hash__(self):
        return hash((type(self), self.pk))
    def __str__(self):
        return "SINTETICO"
    def clean(self):
        pass
    def full_clean(self):
        self.clean()  # Método clean real; campos y constraints Django NO simulados.
    def store(self, validate=True):
        if validate:
            self.full_clean()
        manager = type(self).objects
        if self.pk is None:
            manager.sequence += 1
            self.pk = manager.sequence
            self.creado_en = manager.sequence
        self.actualizado_en += 1
        manager.rows[self.pk] = copy.deepcopy(self)
        return self
    def save(self, *args, user=None, **kwargs):
        self._usuario_operacion_cef = user
        return self.store()
    def refresh_from_db(self):
        self.__dict__ = copy.deepcopy(type(self).objects.get(pk=self.pk).__dict__)


class Atomic:
    """Savepoint de diccionarios, nunca transacción PostgreSQL."""
    depth = 0
    def __enter__(self):
        self.before = {name: (copy.deepcopy(c.objects.rows), c.objects.sequence)
                       for name, c in Record.registry.items()}
        Atomic.depth += 1
        return self
    def __exit__(self, kind, value, traceback):
        Atomic.depth -= 1
        if kind:
            for name, (rows, sequence) in self.before.items():
                Record.registry[name].objects.rows = rows
                Record.registry[name].objects.sequence = sequence


def parse_date(value):
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def functions(path, namespace, names=None):
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    selected = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                and (names is None or n.name in names)]
    # Nunca se ejecutan imports ni asignaciones de los módulos productivos.
    for node in selected:
        if node.decorator_list or any(isinstance(x, (ast.Import, ast.ImportFrom)) for x in ast.walk(node)):
            raise Blocked("FUNCION_AST_NO_COMPATIBLE")
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), "exec"), namespace)


def environment():
    folder = Path(__file__).resolve().parent.parent
    m = ModuleType("cef_model_logic_offline")
    clock = SimpleNamespace(localdate=lambda: date(2024, 4, 5))
    tx = SimpleNamespace(atomic=Atomic, get_connection=lambda: SimpleNamespace(in_atomic_block=Atomic.depth > 0))
    base = dict(ValidationError=ValidationError, PermissionDenied=PermissionDenied,
                IntegrityError=IntegrityError, date=date, timezone=clock, parse_date=parse_date,
                re=re, Q=Q, MaxValueValidator=MaxValueValidator)
    m.__dict__.update(base)
    model_tree = ast.parse((folder / "models.py").read_text("utf-8-sig"))
    Record.registry = {}
    classes = [n for n in model_tree.body if isinstance(n, ast.ClassDef)
               and n.name not in ("CefAuditoriaMixin", "CefCatalogoBase", "CefCatalogoCodigoBase")]
    classes.append(SimpleNamespace(name="Alumno", body=[]))
    for node in classes:
        cls = type(node.name, (Record,), {"DoesNotExist": type("MissingSynthetic", (Exception,), {}),
                                               "MultipleObjectsReturned": type("MultipleSynthetic", (Exception,), {})})
        cls.objects = Manager(cls)
        cls._meta = SimpleNamespace(get_field=lambda name: SimpleNamespace(
            remote_field=SimpleNamespace(model=Record.registry["Alumno"]),
            validators=[MaxValueValidator(2100)]))
        for nested in node.body:
            if isinstance(nested, ast.ClassDef) and nested.name in ("Estado", "Rol"):
                entries = {}
                for item in nested.body:
                    if isinstance(item, ast.Assign):
                        entries[item.targets[0].id] = ast.literal_eval(item.value)[0]
                enum = SimpleNamespace(**entries, choices=[(v, v) for v in entries.values()])
                setattr(cls, nested.name, enum)
        if not hasattr(cls, "Estado"):
            cls.Estado = SimpleNamespace(ACTIVO="activo", BAJA="baja")
        setattr(m, node.name, cls)
        Record.registry[node.name] = cls
    functions(folder / "models.py", m.__dict__)
    for name in ("ROLES_AUTORIZADOS_CEF", "ROL_PROFESOR_CEF", "ROL_DIRECTOR_CEF",
                 "ROL_DIRECTOR_SERVICIOS_COMPLEMENTARIOS", "LONGITUD_CUEANEXO", "PADRON_DB_ALIAS"):
        assignment = next(n for n in model_tree.body if isinstance(n, ast.Assign)
                          and any(isinstance(t, ast.Name) and t.id == name for t in n.targets))
        m.__dict__[name] = ast.literal_eval(assignment.value)
    for node in classes:
        for method in node.body:
            if isinstance(method, ast.FunctionDef) and method.name == "clean":
                exec(compile(ast.Module(body=[method], type_ignores=[]), str(folder / "models.py"), "exec"), m.__dict__)
                getattr(m, node.name).clean = m.clean
    # Clase aislada con save/snapshots originales; super termina exclusivamente en Record.save.
    group_node = next(n for n in classes if n.name == 'CefGrupo')
    group_body = [n for n in group_node.body if isinstance(n, ast.FunctionDef)
                  and n.name in {'clean', 'actualizar_snapshots_catalogo', 'save'}]
    require_names = {n.name for n in group_body}
    if require_names != {'clean', 'actualizar_snapshots_catalogo', 'save'}:
        raise Blocked('METODOS_GRUPO_CAMBIARON')
    m._MemoryGroupBase = m.CefGrupo
    isolated = ast.ClassDef(name='CefGrupo', bases=[ast.Name(id='_MemoryGroupBase', ctx=ast.Load())],
                            keywords=[], body=group_body, decorator_list=[])
    exec(compile(ast.fix_missing_locations(ast.Module(body=[isolated], type_ignores=[])),
                 str(folder / 'models.py'), 'exec'), m.__dict__)
    m.CefGrupo.objects = Manager(m.CefGrupo)
    Record.registry['CefGrupo'] = m.CefGrupo
    s = ModuleType("cef_service_logic_offline")
    s.__dict__.update(m.__dict__)
    s.transaction = tx
    # El subtipo de excepción se conserva con su constructor de producción.
    conflict = next(n for n in ast.parse((folder / "services.py").read_text("utf-8-sig")).body
                    if isinstance(n, ast.ClassDef))
    exec(compile(ast.Module(body=[conflict], type_ignores=[]), "services.exception", "exec"), s.__dict__)
    functions(folder / "services.py", s.__dict__)
    a = ModuleType("cef_attendance_logic_offline")
    a.__dict__.update(s.__dict__)
    functions(folder / "services_asistencia.py", a.__dict__)
    annual = ModuleType("cef_annual_logic_offline")
    annual.__dict__.update(s.__dict__)
    from collections import defaultdict
    annual.defaultdict = defaultdict
    annual.Prefetch = lambda lookup, queryset=None, to_attr=None: SimpleNamespace(
        lookup=lookup, queryset=queryset, to_attr=to_attr)
    tree = ast.parse((folder / "services_anual.py").read_text("utf-8-sig"))
    annual.CATEGORIAS_ANUALES = ast.literal_eval(next(n.value for n in tree.body
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
        and n.targets[0].id == "CATEGORIAS_ANUALES"))
    functions(folder / "services_anual.py", annual.__dict__)
    p = ModuleType("cef_permissions_logic_offline")
    p.__dict__.update(m.__dict__)
    p.get_permisos_cef_request = lambda request: request._cef_permisos_usuario
    functions(folder / "permisos.py", p.__dict__, {"_validar_acceso_cef"})
    return m, s, a, annual, p


def context(m):
    CUES = ("990000001", "990000002")  # CEF ficticios; audit conserva sus CUE originales.
    cycle = m.CefCiclo.objects.create(anio=2024, fecha_inicio=date(2024, 3, 31), actual=True)
    catalog = {}
    for key, name in (("actividad", "CefActividad"), ("nivel", "CefNivelActividad"),
                       ("rango", "CefRangoEtario"), ("turno", "CefTurno"), ("dia", "CefDiaSemana")):
        catalog[key] = getattr(m, name).objects.create(nombre="SINTETICO", numero=1,
            hora_desde_referencia=time(8), hora_hasta_referencia=time(12),
            edad_desde_dias=0, edad_hasta_dias=None)
    catalog["actividad"].eje = m.CefEje.objects.create(nombre="SINTETICO")
    catalog["actividad"].codigo_ra = m.CefCodigoRa.objects.create(codigo="SINTETICO", descripcion="RA_SINTETICA")
    catalog["actividad"].save()
    m.CefActividad.objects.create(nombre="SINTETICO2", eje=catalog["actividad"].eje,
                                codigo_ra=catalog["actividad"].codigo_ra)
    catalog.update(start=time(8), end=time(10), second_end=time(12))
    students, teachers = {}, {}
    for cue in CUES:
        students[cue], teachers[cue] = [], []
        for i in range(4):
            pupil = m.Alumno.objects.create(nombres="SINTETICO", apellidos="SINTETICO")
            students[cue].append(m.CefAlumnoCef.objects.create(
                ciclo=cycle, cueanexo=cue, alumno=pupil, fecha_alta=date(2024, 4, 1)))
            teachers[cue].append(m.CefDocenteCef.objects.create(
                ciclo=cycle, cueanexo=cue, docente_cuil=f"{m.Alumno.objects.sequence:011}",
                fecha_alta=date(2024, 4, 1)))
    return dict(cycle=cycle, catalog=catalog, students=students, teachers=teachers,
        student_ids={k: {x.alumno_id for x in v} for k,v in students.items()},
        teacher_ids={k: {x.docente_cuil for x in v} for k,v in teachers.items()},
        base=date(2024, 4, 5), cues=CUES)


NO_COVERAGE = {
    "B05": "FORMULARIO_DIAS_DJANGO_NO_CUBIERTO",
    "B06": "MODEL_MULTIPLE_CHOICE_FIELD_NO_CUBIERTO",
    "D11": "VALIDACION_DE_CHOICES_DJANGO_NO_CUBIERTA",
}


def build_scenario(case):
    from cases import Scenarios
    from annual_disposable import AnnualScenarios, ACTIONS
    from extended_cases import ExtendedScenarios, CODES
    if Atomic.depth != 0:
        raise Blocked("TRANSACCION_SIMULADA_NO_CERRADA")
    m, s, a, annual, p = environment()
    ctx = context(m)
    if case.code in ACTIONS:
        return AnnualScenarios(m, annual, ctx)
    scenario = Scenarios(m, s, a, annual, None, None, p, ctx)
    if case.category == "H":
        from capacity_cases import CapacityScenarios
        return CapacityScenarios(scenario)
    return ExtendedScenarios(scenario) if case.code in CODES else scenario


def run_offline(only=None):
    from cases import CASES
    from extended_cases import CODES
    from robustness import Capture, install_mutation
    from capacity_cases import PARTIAL
    if only and not set(only) <= {c.code for c in CASES}:
        raise Blocked("CODIGO_DESCONOCIDO")
    output = []
    for case in CASES:
        if only and case.code not in only:
            continue
        partial = case.code in CODES | {"G11", "E13"} | PARTIAL or case.category == "F"
        row = {"codigo": case.code, "resultado": "NO_CUBIERTA",
               "descripcion": case.description, "alcance": case.scope,
               "integracion_postgresql": False, "django_real": False,
               "dependencias_simuladas": ["almacenamiento", "consultas", "reloj", "usuario"],
               "funciones_productivas_ejecutadas": []}
        if case.code in {"B03", "B04", "B15"}:
            row["alcance"] = "metodo_clean_real_aislado_sin_campos_ni_constraints_Django"
        if case.code in CODES:
            row["alcance"] = "AST_original_sin_formularios_ni_autenticacion_Django"
        if case.code == "G11":
            row["alcance"] = "ocho_fallos_en_copia_original_y_rollback_de_diccionarios_sin_atomicidad_SQL"
        if case.code in PARTIAL:
            row["alcance"] = {
                "H01": "validacion_CEF_y_required_AST_sin_ModelForm_Django",
                "H11": "atomic_y_orden_de_bloqueos_observados_sin_carrera_SQL_real",
                "H12": "mensajes_y_ocupacion_AST_sin_render_ni_HTTP_Django",
            }[case.code]
        if case.code in NO_COVERAGE:
            row["detalle"] = NO_COVERAGE[case.code] + "_DJANGO_NO_INSTALADO"
            row["sensibilidad"] = {"resultado": "NO_APLICA_SIN_COBERTURA"}
            output.append(row)
            continue
        capture = Capture()
        try:
            scenario = build_scenario(case)
            with capture:
                scenario.execute(case)
            if Atomic.depth != 0:
                raise Blocked("TRANSACCION_SIMULADA_NO_CERRADA")
            row["resultado"] = "PARCIAL" if partial else "PASS"
            row["detalle"] = "LOGICA_ORIGINAL_AST_CON_DEPENDENCIAS_EN_RAM"
        except Skipped as exc:
            row["detalle"] = safe_code(exc)
        except Blocked as exc:
            row["resultado"], row["detalle"] = "BLOCKED", safe_code(exc)
        except Exception as exc:
            row["resultado"], row["detalle"] = "FAIL", safe_code(exc)
        row["funciones_productivas_ejecutadas"] = capture.report()
        if case.code == "C13":
            source = Path(__file__).resolve().parent.parent / 'services.py'
            tree = ast.parse(source.read_text('utf-8-sig'))
            creator = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                           and n.name == 'crear_inscripcion_activa')
            group = Record.registry['CefGrupo'].objects.get()
            row["evidencia"] = {"cupo_maximo": group.cupo_maximo,
                                "inscripciones_aceptadas_en_memoria": Record.registry["CefInscripcion"].objects.count(),
                                "servicio_consulta_cupo_directamente": any(isinstance(n, ast.Attribute)
                                    and n.attr == 'cupo_maximo' for n in ast.walk(creator)),
                                "validador_cupo_invocado": any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                                    and n.func.id == "validar_cupo_grupo" for n in ast.walk(creator))}
        if row["resultado"] not in {"PASS", "PARCIAL"}:
            row["sensibilidad"] = {"resultado": "NO_APLICA_BASE_NO_SATISFACTORIA"}
            output.append(row)
            continue
        previous_filter = Query.filter
        sensitivity = {}
        try:
            mutated = build_scenario(case)
            sensitivity["alteracion"] = install_mutation(case, capture, mutated)
            mutated.execute(case)
        except AssertionError:
            sensitivity["resultado"] = "DETECTADA_POR_ASERCION"
        except (ValidationError, PermissionDenied):
            sensitivity["resultado"] = "DETECTADA_POR_RECHAZO_DE_ENTRADA_VALIDA"
        except Exception:
            sensitivity["resultado"] = "INCONCLUSA_ERROR_O_MUTACION_NO_DISPONIBLE"
        else:
            sensitivity["resultado"] = "SOBREVIVE_ASERCIONES_INSUFICIENTES"
        finally:
            Query.filter = previous_filter
        if not sensitivity["resultado"].startswith("DETECTADA"):
            row["resultado"] = "PARCIAL"
            row["detalle"] = "LOGICA_BASE_EJECUTADA_SENSIBILIDAD_INSUFICIENTE"
        row["sensibilidad"] = sensitivity
        output.append(row)
    return output


def memory_snapshot():
    def scalar(value):
        if isinstance(value, Record):
            return type(value).__name__, value.pk
        return value
    return {name: {pk: {k: scalar(v) for k,v in row.__dict__.items()}
                   for pk,row in cls.objects.rows.items()}
            for name,cls in Record.registry.items()}
