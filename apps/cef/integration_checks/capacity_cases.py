"""Cupo: lógica CEF original con fixtures ficticias y sin conexiones.

H11 observa límites/orden de llamadas; no simula ni certifica concurrencia PostgreSQL.
H12 ejecuta bloques originales de mensajes, sin afirmar integración HTTP/Django.
"""
import ast
import copy
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from annual_disposable import AnnualScenarios, DESTINATION_START, TODAY
from extended_cases import ExtendedScenarios, PreparedInput
from offline_support import Query, Record, Atomic, ValidationError, IntegrityError, memory_snapshot

PARTIAL = {'H01', 'H11', 'H12'}
OPTIONS = (
    ('Cupo obligatorio y entero positivo; compatibilidad histórica', 'required'),
    ('Cupo disponible, última vacante y grupo completo', 'vacancies'),
    ('Baja libera vacante y reinscripción respeta cupo sin perder historia', 'history'),
    ('Aumento y reducción de cupo con guardado completo o rechazo completo', 'edit'),
    ('Grupo heredado sin cupo o con valor inválido bloquea nuevas altas', 'legacy'),
    ('Ocupación excluye bajas, bancos y otros grupos/CUE', 'independence'),
    ('Continuidad anual con cupo suficiente hereda límite y activos', 'annual_valid'),
    ('Continuidad anual excedida: prevalidación y defensa de copia', 'annual_exceeded'),
    ('Continuidad anual sin cupo con inscripciones bloqueada', 'annual_missing'),
    ('Continuidad anual de grupo vacío sin cupo conserva NULL', 'annual_empty'),
    ('Coordinación transaccional y orden de bloqueos observado offline', 'locks'),
    ('Rechazo sin éxito en mensajes normales/AJAX y error junto a cupo', 'messages'),
)


class CapacityScenarios:
    def __init__(self, base):
        self.base = base
        self.m, self.s, self.annual, self.ctx = base.m, base.s, base.annual, base.ctx
        self.editor = ExtendedScenarios(base)
        self.v = self.editor.v
        self.mutate_handler = False

    def required(self):
        b = self.base
        group = b.group(activate=False)
        for value in (None, 0, -1, 1.5, True, '2'):
            candidate = copy.deepcopy(group)
            candidate.pk, candidate.cupo_maximo = None, value
            b.reject(candidate.full_clean)
        candidate = copy.deepcopy(group)
        candidate.pk, candidate.cupo_maximo = None, 1
        candidate.full_clean()
        # Ejecuta __init__ original sobre campos aislados: required True, sin afirmar ModelForm.
        self.editor.activity()

    def vacancies(self):
        b = self.base
        group = b.group(capacity=2)
        first = b.student(group)
        b.check(self.m.CefInscripcion.objects.filter(grupo=group, estado='activo').count() == 1)
        last = b.student(group, index=1)
        b.check(first.pk != last.pk)
        b.check(self.m.CefInscripcion.objects.filter(grupo=group, estado='activo').count() == 2)
        b.reject(b.student, group, index=2, expect_message='2 de 2')

    def history(self):
        b = self.base
        group = b.group(capacity=1)
        first = b.student(group)
        self.s.dar_baja_inscripcion(first, None, 'BAJA_SINTETICA', b.base)
        first.refresh_from_db()
        second = b.student(group, index=1)
        b.reject(self.s.reinscribir_alumno, first, None, b.base, expect_message='1 de 1')
        self.s.dar_baja_inscripcion(second, None, 'BAJA_SINTETICA', b.base)
        new = self.s.reinscribir_alumno(first, None, b.base)
        first.refresh_from_db()
        b.check(new.pk not in (first.pk, second.pk) and first.estado == 'baja')
        b.check(first.fecha_baja == b.base and first.fecha_inscripcion == b.base)
        b.check(self.m.CefInscripcion.objects.filter(grupo=group).count() == 3)
        b.check(self.m.CefInscripcion.objects.filter(grupo=group, estado='activo').count() == 1)
        group.refresh_from_db()
        b.check(group.cupo_maximo == 1)
        # Rectificar una baja no crea alta ni consume vacante, aun con el grupo lleno.
        with patch.object(self.s, 'usuario_puede_rectificar_cef', return_value=True):
            self.s.rectificar_inscripcion_historica(first, None, b.base, b.base,
                                                    observaciones='RECTIFICACION_SINTETICA')
        first.refresh_from_db()
        b.check(first.estado == 'baja' and first.observaciones == 'RECTIFICACION_SINTETICA')
        b.check(self.m.CefInscripcion.objects.filter(grupo=group, estado='activo').count() == 1)

    def edit(self):
        b = self.base
        group = b.group(capacity=3)
        b.student(group)
        b.student(group, index=1)
        for capacity in (5, 2):
            proposed = copy.deepcopy(group)
            proposed.cupo_maximo, proposed.observaciones = capacity, 'EDICION_VALIDA'
            group = self.editor.save(proposed)
            b.check(group.cupo_maximo == capacity and group.observaciones == 'EDICION_VALIDA')
        proposed = copy.deepcopy(group)
        proposed.cupo_maximo, proposed.observaciones = 1, 'NO_DEBE_GUARDARSE'
        b.reject(self.editor.save, proposed, expect_message='2 inscripciones activas')
        group.refresh_from_db()
        b.check(group.cupo_maximo == 2 and group.observaciones == 'EDICION_VALIDA')
        # Estado heredado sobreocupado: no se borra ni da de baja nadie automáticamente.
        self.m.CefGrupo.objects.rows[group.pk].cupo_maximo = 1
        group.refresh_from_db()
        b.reject(b.student, group, index=2)
        proposed = copy.deepcopy(group)
        proposed.cupo_maximo = 3
        group = self.editor.save(proposed)
        b.student(group, index=2)
        b.check(self.m.CefInscripcion.objects.filter(grupo=group, estado='activo').count() == 3)

    def legacy(self):
        b = self.base
        group = b.group(activate=False, capacity=1)
        group.cupo_maximo = None
        group.save()  # Fila preexistente: no reescribe su historia ni inventa cupo.
        b.reject(b.student, group, expect_message='todavía no tiene un cupo')
        self.s.dar_baja_grupo(group, None, 'BAJA_SINTETICA', b.base)
        group = self.s.reactivar_grupo(group, None, b.base)
        pupil = self.ctx['students'][group.cueanexo][0].alumno
        old = self.m.CefInscripcion(grupo=group, alumno=pupil, estado='baja',
                                    fecha_inscripcion=b.base, fecha_baja=b.base)
        old.store(validate=False)
        b.reject(self.s.reinscribir_alumno, old, None, b.base)
        for invalid in (0, -1, 1.5, True, '2'):
            self.m.CefGrupo.objects.rows[group.pk].cupo_maximo = invalid
            group.refresh_from_db()
            b.reject(b.student, group)
        proposed = copy.deepcopy(group)
        proposed.cupo_maximo = 2
        group = self.editor.save(proposed)
        b.student(group)
        b.check(self.m.CefInscripcion.objects.get(pk=old.pk).estado == 'baja')
        b.check(self.m.CefInscripcion.objects.filter(grupo=group).count() == 2)

    def independence(self):
        b = self.base
        group = b.group(capacity=1)
        old = b.student(group)
        self.s.dar_baja_inscripcion(old, None, 'BAJA_SINTETICA', b.base)
        b.student(group, index=1)
        neighbor = b.group(capacity=1, start=self.ctx['catalog']['end'],
                           end=self.ctx['catalog']['second_end'])
        b.student(neighbor)
        foreign = b.group(cue=self.ctx['cues'][1], capacity=1)
        b.student(foreign)
        b.check(self.m.CefInscripcion.objects.filter(estado='activo').count() == 3)
        self.s.validar_cupo_grupo(group, 1)
        b.reject(b.student, group, index=2)
        b.check(self.m.CefInscripcion.objects.filter(grupo=group, estado='baja').count() == 1)

    def annual_fixture(self, capacity):
        fixture = AnnualScenarios(self.m, self.annual, self.ctx)
        source, group, actor = fixture.fixture()
        group.cupo_maximo = capacity
        group.save()
        return fixture, source, group, actor

    def annual_valid(self):
        with patch.object(self.annual.timezone, 'localdate', return_value=TODAY):
            fixture, source, group, actor = self.annual_fixture(1)
            preview = self.annual.prevalidar_generacion_anual(source)
            self.base.check(not preview['bloqueado'])
            result = fixture.generate(source, actor)
            copied = self.m.CefGrupo.objects.filter(ciclo=result['ciclo_destino']).get()
            self.base.check(copied.cupo_maximo == 1 and copied.grupo_origen_id == group.pk)
            self.base.check(self.m.CefInscripcion.objects.filter(grupo=copied, estado='activo').count() == 1)
            self.base.check(self.m.CefInscripcion.objects.filter(grupo=group).count() == 2)

    def annual_exceeded(self):
        b = self.base
        with patch.object(self.annual.timezone, 'localdate', return_value=TODAY):
            fixture, source, group, actor = self.annual_fixture(1)
            first = self.m.CefInscripcion.objects.filter(grupo=group, estado='activo').get()
            pupil = self.m.Alumno.objects.exclude(pk=first.alumno_id).first()
            self.m.CefAlumnoCef(ciclo=source, cueanexo=group.cueanexo, alumno=pupil,
                                fecha_alta=date(2024,4,1)).store(validate=False)
            self.m.CefInscripcion(grupo=group, alumno=pupil,
                                 fecha_inscripcion=date(2024,4,1)).store(validate=False)
            preview = self.annual.prevalidar_generacion_anual(source)
            conflicts = [item for item in preview['errores'] if item['codigo'] == f'grupo_cupo_excedido_{group.pk}']
            b.check(preview['bloqueado'] and len(conflicts) == 1)
            b.check('2 inscripciones activas' in conflicts[0]['mensaje'] and 'cupo es 1' in conflicts[0]['mensaje'])
            b.reject(fixture.generate, source, actor)
            # Defensa independiente: una prevalidación incompleta no puede habilitar bulk_create.
            original = self.annual.prevalidar_generacion_anual
            def incomplete_preview(origin):
                result = original(origin)
                b.check(all('cupo' in item['codigo'] for item in result['errores']))
                result['errores'] = []
                result['bloqueado'] = False
                return result
            with patch.object(self.annual, 'prevalidar_generacion_anual', incomplete_preview):
                b.reject(fixture.generate, source, actor)

    def annual_missing(self):
        with patch.object(self.annual.timezone, 'localdate', return_value=TODAY):
            fixture, source, group, actor = self.annual_fixture(None)
            preview = self.annual.prevalidar_generacion_anual(source)
            self.base.check(preview['bloqueado'])
            self.base.check(any(item['codigo'] == f'grupo_cupo_invalido_{group.pk}' for item in preview['errores']))
            self.base.reject(fixture.generate, source, actor)
            group.refresh_from_db()
            self.base.check(group.cupo_maximo is None)

    def annual_empty(self):
        with patch.object(self.annual.timezone, 'localdate', return_value=TODAY):
            fixture, source, group, actor = self.annual_fixture(None)
            for row in self.m.CefInscripcion.objects.filter(grupo=group):
                row.estado, row.fecha_baja = 'baja', date(2024,4,2)
                row.store(validate=False)
            self.base.check(not self.annual.prevalidar_generacion_anual(source)['bloqueado'])
            result = fixture.generate(source, actor)
            target = self.m.CefGrupo.objects.filter(ciclo=result['ciclo_destino']).get()
            self.base.check(target.cupo_maximo is None)
            self.base.check(not self.m.CefInscripcion.objects.filter(grupo=target).exists())
            pupil = self.m.Alumno.objects.first()
            self.base.reject(self.s.crear_inscripcion_activa, target, pupil, None, DESTINATION_START,
                             expect_message='todavía no tiene un cupo')

    def locks(self):
        b, m, events = self.base, self.m, []
        group = b.group(capacity=2)
        locked, counted, created, stored = Query.select_for_update, Query.count, Query.create, Record.store
        def lock(query, *args, **kwargs):
            if query.model is m.CefGrupo:
                b.check(Atomic.depth > 0)
                events.append('group_lock')
            return locked(query, *args, **kwargs)
        def count(query):
            if query.model is m.CefInscripcion:
                b.check(Atomic.depth > 0)
                events.append('count')
            return counted(query)
        def create(query, **kwargs):
            if query.model is m.CefInscripcion:
                events.append('insert')
            return created(query, **kwargs)
        def store(record, *args, **kwargs):
            if isinstance(record, m.CefGrupo):
                events.append('save_group')
            return stored(record, *args, **kwargs)
        with patch.object(Query, 'select_for_update', lock), patch.object(Query, 'count', count), \
                patch.object(Query, 'create', create), patch.object(Record, 'store', store):
            b.student(group)
            b.check(events.index('group_lock') < events.index('count') < events.index('insert'))
            events.clear()
            proposed = copy.deepcopy(group)
            proposed.cupo_maximo = 1
            self.editor.save(proposed)
            b.check(events.index('group_lock') < events.index('count') < events.index('save_group'))
        fixture, source, group, actor = self.annual_fixture(2)
        events.clear()
        preview = self.annual.prevalidar_generacion_anual
        def observed(origin):
            events.append('preview')
            return preview(origin)
        with patch.object(Query, 'select_for_update', lock), \
                patch.object(self.annual, 'prevalidar_generacion_anual', observed), \
                patch.object(self.annual.timezone, 'localdate', return_value=TODAY):
            fixture.generate(source, actor)
        b.check(events.index('group_lock') < events.index('preview'))

    def original_try(self, filename, function_name, called_name):
        path = Path(__file__).resolve().parent.parent / filename
        tree = ast.parse(path.read_text('utf-8-sig'))
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == function_name)
        blocks = [n for n in ast.walk(function) if isinstance(n, ast.Try) and any(
            isinstance(child, ast.Call) and isinstance(child.func, ast.Name) and child.func.id == called_name
            for child in ast.walk(n))]
        return path, copy.deepcopy(min(blocks, key=lambda n: n.end_lineno - n.lineno))

    def run_try(self, path, block, namespace, result):
        body = ast.parse('ajax_ok = False\najax_message = ""').body + [block] + ast.parse('return ' + result).body
        wrapper = ast.FunctionDef(name='exercise_original', args=ast.arguments(
            posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[], defaults=[]), body=body, decorator_list=[])
        exec(compile(ast.fix_missing_locations(ast.Module(body=[wrapper], type_ignores=[])), str(path), 'exec'), namespace)
        return namespace['exercise_original']()

    def messages(self):
        b, m = self.base, self.m
        group = b.group(capacity=2)
        b.student(group)
        b.student(group, index=1)
        pupil = self.ctx['students'][group.cueanexo][2].alumno
        for ajax in (False, True):
            errors, successes = [], []
            sink = SimpleNamespace(error=lambda req, value: errors.append(value),
                                   success=lambda req, value: successes.append(value))
            namespace = dict(self.s.__dict__, grupo=group, alumno=pupil,
                             request=SimpleNamespace(user=None), fecha_inscripcion=b.base,
                             _is_ajax=lambda request: ajax, messages=sink,
                             OperationalError=type('OfflineOperationalError', (Exception,), {}),
                             ProgrammingError=type('OfflineProgrammingError', (Exception,), {}))
            path, block = self.original_try('views_inscripcion_grupo.py', 'inscripcion_grupo', 'crear_inscripcion_activa')
            ok, message = self.run_try(path, block, namespace, '(ajax_ok, ajax_message)')
            b.check(not ok and '2 de 2' in message and not successes)
            b.check(bool(errors) == (not ajax))
        for function_name in ('_inscribir_alumno_grupo_desde_banco', '_inscribir_alumno_grupo_desde_historial'):
            errors, successes = [], []
            namespace = dict(self.s.__dict__, grupo=group, request=SimpleNamespace(user=None,
                             POST={'fecha_inscripcion': b.base}), alumno_banco=SimpleNamespace(alumno=pupil),
                             periodo=SimpleNamespace(alumno=pupil), messages=SimpleNamespace(
                             error=lambda req, value: errors.append(value),
                             success=lambda req, value: successes.append(value)))
            path, block = self.original_try('views_alumnos.py', function_name, 'crear_inscripcion_activa')
            self.run_try(path, block, namespace, 'None')
            b.check(len(errors) == 1 and '2 de 2' in errors[0] and not successes)
        errors, successes = {}, []
        proposed = copy.deepcopy(group)
        proposed.cupo_maximo, proposed.observaciones = 1, 'NO_GUARDAR'
        form = PreparedInput(proposed)
        form.fields = {name: None for name in form.Meta.fields}
        form.add_error = lambda field, value: errors.setdefault(field, value)
        namespace = dict(self.s.__dict__, form=form, dias_form=SimpleNamespace(
                         cleaned_data={'dias': [self.ctx['catalog']['dia']]}),
                         cef_context={'cueanexo': group.cueanexo, 'ciclo': group.ciclo},
                         request=SimpleNamespace(user=None), _guardar_grupo=self.v._guardar_grupo,
                         messages=SimpleNamespace(error=lambda req, value: None,
                         success=lambda req, value: successes.append(value)))
        path, block = self.original_try('views_carga_grupo.py', 'carga_grupo_form', '_guardar_grupo')
        if self.mutate_handler:
            for node in ast.walk(block):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'add_error':
                    node.args[0] = ast.Constant(value=None)
        before = memory_snapshot()
        self.run_try(path, block, namespace, 'None')
        b.check('cupo_maximo' in errors and not successes and memory_snapshot() == before)
        # Expresión original del resumen: no depende de la pestaña ni cuenta bajas.
        tree = ast.parse(path.read_text('utf-8-sig'))
        context_dict = next(n for n in ast.walk(tree) if isinstance(n, ast.Dict) and any(
            isinstance(key, ast.Constant) and key.value == 'inscripciones_activas' for key in n.keys))
        expression = next(value for key, value in zip(context_dict.keys, context_dict.values)
                          if isinstance(key, ast.Constant) and key.value == 'inscripciones_activas')
        rows = [SimpleNamespace(estado='activo'), SimpleNamespace(estado='baja'), SimpleNamespace(estado='activo')]
        total = eval(compile(ast.Expression(body=expression), str(path), 'eval'),
                     {'CefInscripcion': m.CefInscripcion, 'inscripciones_todas': rows})
        b.check(total == 2)


    def execute(self, case):
        with self.base.simulate(self.base.base):
            getattr(self, case.option)()


def install_capacity_mutation(case, baseline, scenario):
    from robustness import replace, pick, ast_mutant
    if case.option == 'required':
        replace(scenario, pick(baseline, 'validar_cupo_maximo'), lambda fn: lambda *a, **k: None)
        return 'omitir validación de entero positivo en copia en memoria'
    if case.option in {'vacancies', 'history', 'edit', 'legacy', 'independence'}:
        replace(scenario, pick(baseline, 'validar_cupo_grupo'), lambda fn: lambda *a, **k: None)
        return 'omitir control central de cupo en copia en memoria'
    if case.option in {'annual_exceeded', 'annual_missing'}:
        replace(scenario, pick(baseline, '_conflictos_cupo_proyectado'), lambda fn: lambda *a, **k: [])
        return 'omitir conflictos de cupo tanto en proyección como en copia'
    if case.option in {'annual_valid', 'annual_empty'}:
        def altered(fn):
            def generate(*args, **kwargs):
                result = fn(*args, **kwargs)
                target = scenario.m.CefGrupo.objects.filter(ciclo=result['ciclo_destino']).get()
                target.cupo_maximo = 0 if case.option == 'annual_valid' else 1
                target.store(validate=False)
                return result
            return generate
        replace(scenario, pick(baseline, 'generar_ciclo_siguiente'), altered)
        return 'alterar cupo heredado en respuesta de memoria'
    if case.option == 'locks':
        replace(scenario, pick(baseline, 'crear_inscripcion_activa'), lambda fn: ast_mutant(fn, remove_atomic=True))
        return 'omitir atomic del servicio en copia AST; no prueba de carrera real'
    if case.option == 'messages':
        scenario.mutate_handler = True
        return 'desviar error de cupo al formulario general en copia AST del handler'
    raise LookupError('MUTACION_CUPO_NO_DEFINIDA')