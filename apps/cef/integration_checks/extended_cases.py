"""Cobertura adicional AST; no sustituye ModelForm ni decoradores Django."""
import ast
import copy
from contextlib import nullcontext
from functools import wraps
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from offline_support import functions, memory_snapshot, ValidationError, PermissionDenied

CODES = {'B01', 'B02', 'B07', 'F11'}


def view_logic(m, s):
    namespace = dict(s.__dict__)
    namespace['Max'] = lambda field: SimpleNamespace(field=field)
    functions(Path(__file__).resolve().parent.parent / 'views_carga_grupo.py', namespace,
              {'_guardar_grupo', '_guardar_dias', '_proximo_numero_grupo',
               '_actividad_cambio', '_preparar_numero_nombre'})
    return SimpleNamespace(**namespace)


class PreparedInput:
    """Entrada ya normalizada; NO implementa ni afirma validación de formulario."""
    def __init__(self, instance):
        self.instance = copy.deepcopy(instance)
        tree = ast.parse((Path(__file__).resolve().parent.parent / 'forms.py').read_text('utf-8-sig'))
        form = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'CefGrupoForm')
        meta = next(n for n in form.body if isinstance(n, ast.ClassDef) and n.name == 'Meta')
        fields = ast.literal_eval(next(n.value for n in meta.body if isinstance(n, ast.Assign)
                                      and n.targets[0].id == 'fields'))
        self.Meta = SimpleNamespace(fields=fields)

    def save(self, commit=True):
        assert commit is False
        return copy.deepcopy(self.instance)


class ExtendedScenarios:
    def __init__(self, base):
        self.base = base
        self.m, self.s, self.ctx = base.m, base.s, base.ctx
        self.v = view_logic(self.m, self.s)

    def save(self, proposed, days=None):
        return self.v._guardar_grupo(PreparedInput(proposed), SimpleNamespace(cleaned_data={
            'dias': days if days is not None else [self.ctx['catalog']['dia']]}),
            {'cueanexo': self.ctx['cues'][0], 'ciclo': self.ctx['cycle']}, None)

    def create(self):
        m, cat = self.m, self.ctx['catalog']
        item = m.CefGrupo(actividad=cat['actividad'], nivel=cat['nivel'],
                          rango_etario=cat['rango'], turno=cat['turno'],
                          hora_inicio=cat['start'], hora_fin=cat['end'], cupo_maximo=3)
        saved = self.save(item)
        self.base.check(saved.pk is not None and saved.numero == 1)
        self.base.check(saved.nombre == cat['actividad'].nombre + ' 1')
        self.base.check(saved.cueanexo == self.ctx['cues'][0] and saved.ciclo == self.ctx['cycle'])
        self.base.check(saved.actividad_nombre_snapshot == cat['actividad'].nombre)
        self.base.check(saved.codigo_ra_snapshot == cat['actividad'].codigo_ra.codigo)
        self.base.check(saved.turno_hora_desde_snapshot == cat['turno'].hora_desde_referencia)
        self.base.check(m.CefGrupoDiaFuncionamiento.objects.filter(grupo=saved).get().dia_semana == cat['dia'])
        # Entradas inválidas ejercitan clean original y atomic del guardado original.
        bad = copy.deepcopy(item)
        bad.hora_fin = bad.hora_inicio
        self.base.reject(self.save, bad)
        bad = copy.deepcopy(item)
        bad.cupo_maximo = 0
        self.base.reject(self.save, bad)
        self.base.check(m.CefGrupo.objects.count() == 1)

    def activity(self):
        m = self.m
        inactive = m.CefActividad.objects.create(nombre='INACTIVA_SINTETICA', activo=False)
        class BaseFields:
            def __init__(self, *args, **kwargs):
                self.instance = kwargs['instance']
                self.fields = {name: SimpleNamespace(required=True, error_messages={}) for name in
                               ('actividad', 'nivel', 'rango_etario', 'turno', 'cupo_maximo')}
        namespace = dict(m.__dict__, forms=SimpleNamespace(ModelForm=BaseFields),
                         _aplicar_clases_bootstrap=lambda field: None)
        path = Path(__file__).resolve().parent.parent / 'forms.py'
        functions(path, namespace, {'_queryset_activos'})
        tree = ast.parse(path.read_text('utf-8-sig'))
        node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'CefGrupoForm')
        # Sólo __init__ original. La clase base suministra campos; NO ModelForm.
        node.body = [n for n in node.body if isinstance(n, ast.FunctionDef) and n.name == '__init__']
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), namespace)
        cls = namespace['CefGrupoForm']
        new = cls(instance=m.CefGrupo())
        active_ids = set(m.CefActividad.objects.filter(activo=True).values_list('pk', flat=True))
        self.base.check({row.pk for row in new.fields['actividad'].queryset} == active_ids)
        self.base.check(inactive.pk not in {row.pk for row in new.fields['actividad'].queryset})
        existing = m.CefGrupo(pk=10, actividad=inactive, nivel=self.ctx['catalog']['nivel'],
                              rango_etario=self.ctx['catalog']['rango'], turno=self.ctx['catalog']['turno'])
        edited = cls(instance=existing)
        self.base.check({row.pk for row in edited.fields['actividad'].queryset} == active_ids | {inactive.pk})
        self.base.check(new.fields['cupo_maximo'].required is True)

    def edit(self):
        b, m = self.base, self.m
        item = self.save(b.group())
        b.student(item)
        history = list(item.movimientos_estado.order_by('pk').values('pk', 'fecha', 'estado_resultante'))
        days = list(item.dias_funcionamiento.values_list('pk', 'dia_semana_id'))
        proposed = copy.deepcopy(item)
        proposed.observaciones = 'EDICION_SINTETICA'
        result = self.save(proposed)
        b.check(result.pk == item.pk and result.observaciones == 'EDICION_SINTETICA')
        for field in ('actividad_id', 'hora_inicio', 'hora_fin', 'numero', 'nombre',
                      'actividad_nombre_snapshot', 'eje_nombre_snapshot', 'codigo_ra_snapshot',
                      'codigo_ra_descripcion_snapshot', 'turno_nombre_snapshot',
                      'turno_hora_desde_snapshot', 'turno_hora_hasta_snapshot',
                      'nivel_nombre_snapshot', 'rango_etario_nombre_snapshot'):
            b.check(getattr(result, field) == getattr(item, field))
        b.check(list(result.dias_funcionamiento.values_list('pk', 'dia_semana_id')) == days)
        b.check(list(result.movimientos_estado.order_by('pk').values('pk', 'fecha', 'estado_resultante')) == history)
        self.save(proposed)
        b.check(list(result.dias_funcionamiento.values_list('pk', 'dia_semana_id')) == days)
        proposed.actividad = m.CefActividad.objects.exclude(pk=item.actividad_id).first()
        b.reject(self.save, proposed)
        other = b.group(start=self.ctx['catalog']['end'], end=self.ctx['catalog']['second_end'])
        b.student(other)
        proposed = copy.deepcopy(item)
        proposed.hora_inicio, proposed.hora_fin = other.hora_inicio, other.hora_fin
        b.reject(self.save, proposed)

    def authorization(self):
        b = self.base
        namespace = dict(b.p.__dict__)
        markers, finished, calls = [], [], []
        def decorator(name):
            def wrap(function):
                markers.append(name)
                return function
            return wrap
        namespace.update(wraps=wraps, login_required=decorator('login_required_sustituido'),
                         never_cache=decorator('never_cache_sustituido'),
                         perf_begin=lambda request: request.profile,
                         perf_capture_queries=lambda request: nullcontext(),
                         perf_finish=lambda request, **kwargs: finished.append(kwargs))
        functions(Path(__file__).resolve().parent.parent / 'permisos.py', namespace,
                  {'_cef_required', 'cef_required', 'cef_inicio_required', 'cef_asistencia_required'})
        def view(request):
            calls.append(request)
            return 'RESPUESTA_SINTETICA'
        for profile in (False, True):
            for role in ('Administrador', 'profesorcef', 'No autorizado'):
                user = SimpleNamespace(is_authenticated=True)
                with patch.object(self.m, 'obtener_rol_usuario_cef', return_value=role):
                    perms = self.m.obtener_permisos_usuario_cef(user)
                request = SimpleNamespace(user=user, profile=profile, _cef_permisos_usuario=perms)
                for name, allowed in (('cef_required', role == 'Administrador'),
                                      ('cef_asistencia_required', role != 'No autorizado')):
                    protected = namespace[name](view)
                    count = len(calls)
                    try:
                        response = protected(request)
                    except PermissionDenied:
                        b.check(not allowed and len(calls) == count)
                    else:
                        b.check(allowed and response == 'RESPUESTA_SINTETICA' and len(calls) == count + 1)
        b.check(set(markers) == {'login_required_sustituido', 'never_cache_sustituido'})
        b.check(len(finished) == 6 and sum(item['error'] is not None for item in finished) == 3)
        # El rol de un anónimo se resuelve con la función productiva, antes de consultar grupos.
        anonymous = SimpleNamespace(is_authenticated=False)
        perms = self.m.obtener_permisos_usuario_cef(anonymous)
        b.check(not perms['puede_ver'])

    def execute(self, case):
        with self.base.simulate(self.base.base):
            {'B01': self.create, 'B02': self.activity, 'B07': self.edit,
             'F11': self.authorization}[case.code]()