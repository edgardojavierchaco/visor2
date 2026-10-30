"""Inventario dinámico y mutaciones exclusivamente en copias/objetos de RAM.

Un mutante sobreviviente o que sólo causa un error interno limita a PARCIAL.
La detección no certifica cobertura de todas las ramas ni fidelidad SQL.
"""
import ast
import copy
from datetime import timedelta, time
from pathlib import Path
import sys
from types import FunctionType

from offline_support import ValidationError, PermissionDenied, Record, Query

_RAISE_LINES = {}

SOURCES = {'models.py', 'services.py', 'services_asistencia.py', 'services_anual.py',
           'forms.py', 'permisos.py', 'views_carga_grupo.py'}


def location(code):
    return (code.co_filename.replace(chr(92), "/").rsplit("/", 1)[-1], code.co_name, code.co_firstlineno)


class Capture:
    def __init__(self):
        self.functions, self.raises = set(), []
        self.paths = {str(Path(__file__).resolve().parent.parent / name) for name in SOURCES}

    def trace(self, frame, event, arg):
        if frame.f_code.co_filename not in self.paths:
            return None
        key = location(frame.f_code)
        if event == 'call':
            self.functions.add(key)
        elif event == 'exception' and isinstance(arg[1], (ValidationError, PermissionDenied)):
            # Sólo el punto que realmente ejecutó raise, no propagaciones por llamadas.
            if key[0] not in _RAISE_LINES:
                source = Path(__file__).resolve().parent.parent / key[0]
                tree = ast.parse(source.read_text('utf-8-sig'))
                _RAISE_LINES[key[0]] = {n.lineno for n in ast.walk(tree) if isinstance(n, ast.Raise)}
            if frame.f_lineno in _RAISE_LINES[key[0]]:
                self.raises.append((key, frame.f_lineno))
        return self.trace

    def __enter__(self):
        self.previous = sys.gettrace()
        sys.settrace(self.trace)
        return self

    def __exit__(self, *args):
        sys.settrace(self.previous)

    def report(self):
        return ['%s:%s:%s' % key for key in sorted(self.functions)]


def namespaces(scenario):
    base = scenario.__dict__.get('base', scenario)
    found = []
    for name in ('m', 's', 'a', 'annual', 'p', 'v'):
        obj = getattr(base, name, None) or getattr(scenario, name, None)
        if obj is not None:
            found.append(vars(obj))
    # Las funciones AST de una vista comparten un diccionario distinto al namespace expuesto.
    for namespace in list(found):
        for function in list(namespace.values()):
            if isinstance(function, FunctionType) and Path(function.__code__.co_filename).name in SOURCES:
                if not any(function.__globals__ is item for item in found):
                    found.append(function.__globals__)
    return found


def replace(scenario, key, transform):
    spaces = namespaces(scenario)
    candidates = []
    for namespace in spaces:
        candidates.extend(value for value in namespace.values()
                          if isinstance(value, FunctionType) and location(value.__code__) == key)
    for cls in Record.registry.values():
        if location(cls.clean.__code__) == key:
            candidates.append(cls.clean)
    if not candidates:
        raise LookupError('FUNCION_MUTANTE_NO_LOCALIZADA')
    original = candidates[0]
    mutant = transform(original)
    for namespace in spaces:
        for name, value in list(namespace.items()):
            if isinstance(value, FunctionType) and location(value.__code__) == key:
                namespace[name] = mutant
    for cls in Record.registry.values():
        if location(cls.clean.__code__) == key:
            cls.clean = mutant


def ast_mutant(original, raise_line=None, remove_atomic=False, ignore_foreign=False):
    path = Path(__file__).resolve().parent.parent / Path(original.__code__.co_filename).name
    tree = ast.parse(path.read_text('utf-8-sig'))
    node = copy.deepcopy(next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                             and n.name == original.__name__ and n.lineno == original.__code__.co_firstlineno))
    changed = []
    class Mutate(ast.NodeTransformer):
        def visit_Raise(self, item):
            if item.lineno == raise_line:
                changed.append(True)
                if ignore_foreign:
                    replacement = ast.parse("estados_normalizados = {key: value for key, value in estados_normalizados.items() if key in inscripciones_por_id}").body[0]
                    return ast.copy_location(replacement, item)
                return ast.copy_location(ast.Pass(), item)
            return item
        def visit_With(self, item):
            self.generic_visit(item)
            if remove_atomic and any('transaction.atomic' in ast.unparse(x.context_expr) for x in item.items):
                changed.append(True)
                return item.body
            return item
    node = Mutate().visit(node)
    if not changed:
        raise LookupError('MUTACION_NO_APLICADA')
    namespace = dict(original.__globals__)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), str(path), 'exec'), namespace)
    result = FunctionType(namespace[node.name].__code__, original.__globals__, original.__name__, original.__defaults__)
    result.__kwdefaults__ = original.__kwdefaults__
    return result


def pick(capture, name, source=None):
    return next(key for key in capture.functions if key[1] == name and (source is None or key[0] == source))


def install_mutation(case, baseline, scenario):
    """Devuelve descripción concreta; jamás escribe la fuente productiva."""
    base = scenario.__dict__.get('base', scenario)
    m = base.m
    if case.category == 'H':
        from capacity_cases import install_capacity_mutation
        return install_capacity_mutation(case, baseline, scenario)
    if case.code == 'G11':
        key = pick(baseline, 'generar_ciclo_siguiente')
        replace(scenario, key, lambda fn: ast_mutant(fn, remove_atomic=True))
        return 'omitir atomic en copia AST del generador'
    if case.code in {'C15', 'D18'}:
        model = m.CefAlumnoCef if case.code == 'C15' else m.CefDocenteCef
        original = Query.filter
        def filter_changed(query, *args, **kwargs):
            if query.model is model and 'cueanexo' in kwargs:
                kwargs = {key: value for key, value in kwargs.items() if key != 'cueanexo'}
            return original(query, *args, **kwargs)
        Query.filter = filter_changed
        return 'respuesta de banco omite filtro CUE y admite período ajeno'
    if baseline.raises:
        key, line = baseline.raises[-1]
        replace(scenario, key, lambda fn: ast_mutant(fn, raise_line=line, ignore_foreign=case.code == 'E12'))
        return ('ignorar inscripción ajena en copia AST' if case.code == 'E12' else
                'omitir raise productivo %s:%s:%s' % (key[0], key[1], line))
    if case.code == 'B02':
        original = Query.filter
        def filter_changed(query, *args, **kwargs):
            if query.model is m.CefActividad and args:
                return Query(query.model, query.model.objects.rows.values())
            return original(query, *args, **kwargs)
        # Restaura en finally mediante el objeto retornado por run_offline.
        Query.filter = filter_changed
        return 'respuesta de queryset incluye actividad inactiva'
    if case.code == 'B03':
        key = location(m.CefGrupo.clean.__code__)
        def clean_changed(fn):
            def wrapped(item, *args, **kwargs):
                result = fn(item, *args, **kwargs)
                item.hora_inicio = time(7)
                return result
            return wrapped
        replace(scenario, key, clean_changed)
        return 'respuesta de clean con horario fuera de turno'

    name, tamper = None, None
    def persist(item):
        if item.pk in type(item).objects.rows:
            type(item).objects.rows[item.pk] = copy.deepcopy(item)
    def attribute(field, value, stored=True):
        def alter(result, args):
            setattr(result, field, value(result) if callable(value) else value)
            if stored:
                persist(result)
            return result
        return alter
    if case.category == 'A':
        if case.option == 'end_valid':
            name = 'validar_fechas_oficiales_ciclo'
            tamper = lambda result, args: (result[0], result[1] + timedelta(days=1))
        elif case.option == 'retro':
            name = 'validar_fecha_operativa_ciclo'
            tamper = lambda result, args: result + timedelta(days=1)
        elif case.option in ('no_auto_close', 'start'):
            name = 'motivo_bloqueo_inicio_ciclo'
            tamper = lambda result, args: 'BLOQUEO_SINTETICO_INCORRECTO'
    elif case.category == 'B':
        name = 'dar_baja_grupo' if case.option == 'close' else 'reactivar_grupo'
        tamper = attribute('estado', 'activo' if case.option == 'close' else 'baja')
        if case.option == 'history':
            def tamper(result, args):
                rows = m.CefGrupoEstadoMovimiento.objects.rows
                rows.pop(min(rows))
                return result
    elif case.category == 'C':
        name = 'crear_inscripcion_activa'
        tamper = attribute('alumno_id', -1)
        if case.option == 'close':
            name, tamper = 'dar_baja_inscripcion', attribute('fecha_baja', lambda x: x.fecha_baja + timedelta(days=1))
        elif case.option in ('rejoin', 'history'):
            name, tamper = 'reinscribir_alumno', attribute('fecha_inscripcion', lambda x: x.fecha_inscripcion + timedelta(days=1))
    elif case.category == 'D':
        name, tamper = 'crear_asignacion_docente_activa', attribute('rol', 'rol_incorrecto_sintetico')
        if case.option == 'close':
            name, tamper = 'dar_baja_asignacion_docente', attribute('fecha_hasta', lambda x: x.fecha_hasta + timedelta(days=1))
        elif case.option in ('rejoin', 'history'):
            name, tamper = 'reasignar_docente_grupo', attribute('fecha_desde', lambda x: x.fecha_desde + timedelta(days=1))
    elif case.category == 'E':
        name = 'registrar_asistencias_jornada'
        def tamper(result, args):
            if case.option in ('presente', 'ausente', 'justificada'):
                for item in m.CefAsistencia.objects.rows.values():
                    item.estado = 'estado_incorrecto_sintetico'
            else:
                result['cambios'] += 1
            return result
        if case.option == 'validity':
            name, tamper = 'inscripciones_vigentes_jornada', lambda result, args: result[1:]
    elif case.category == 'F':
        if case.action == 'scope':
            name, tamper = 'usuario_puede_cargar_cueanexo', lambda result, args: not result
        else:
            name = 'obtener_permisos_usuario_cef'
            def tamper(result, args):
                result['puede_ver'] = not result['puede_ver']
                return result
    elif case.category == 'G':
        if case.code == 'G01':
            name = 'prevalidar_generacion_anual'
            def tamper(result, args):
                result['proyeccion']['alumnos_origen_ids'] = []
                return result
        else:
            name = 'generar_ciclo_siguiente'
            def tamper(result, args):
                target = result['ciclo_destino']
                if case.code in ('G04', 'G05', 'G06', 'G07', 'G08'):
                    cls = {'G04': m.CefAlumnoCef, 'G05': m.CefDocenteCef,
                           'G06': m.CefInscripcion, 'G07': m.CefDocenteGrupo,
                           'G08': m.CefAlumnoCef}[case.code]
                    scope = 'ciclo' if case.code in ('G04', 'G05', 'G08') else 'grupo__ciclo'
                    item = cls.objects.filter(**{scope: target}).get()
                    field, value = {'G04': ('alumno_id', -1), 'G05': ('docente_cuil', 'ALTERADO'),
                                    'G06': ('alumno_id', -1), 'G07': ('rol', 'suplente'),
                                    'G08': ('fecha_alta', target.fecha_inicio + timedelta(days=1))}[case.code]
                    setattr(item, field, value)
                    persist(item)
                elif case.code == 'G09':
                    result['ciclo_origen'].observaciones = 'ALTERADO_SINTETICO'
                    persist(result['ciclo_origen'])
                elif case.code == 'G10':
                    group = m.CefGrupo.objects.filter(ciclo=target).get()
                    m.CefJornadaAsistencia(grupo=group, fecha=target.fecha_inicio).store(validate=False)
                return result
    if name is None or tamper is None:
        raise LookupError('MUTACION_NO_DEFINIDA')
    key = pick(baseline, name)
    def decorate(function):
        def changed(*args, **kwargs):
            return tamper(function(*args, **kwargs), args)
        return changed
    replace(scenario, key, decorate)
    return 'alterar respuesta/estado en RAM de ' + name