"""Continuidad anual offline: reutiliza lógica real AST, nunca una BD descartable.

Se conserva el nombre del archivo por compatibilidad de la batería anterior.
No hay perfil descartable, SQL, driver, settings ni funciones de conexión.
"""
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from offline_support import Record, ValidationError, Atomic, memory_snapshot

ACTIONS = {
    "G04": "students", "G05": "teachers", "G06": "enrollments",
    "G07": "assignments", "G08": "dates", "G09": "source",
    "G10": "attendance", "G11": "atomic", "G12": "duplicate",
}
DESTINATION_START = date(2025, 3, 31)
TODAY = date(2025, 4, 5)


class AnnualScenarios:
    def __init__(self, m, annual, context):
        self.m, self.annual, self.ctx = m, annual, context

    def check(self, condition):
        if not condition:
            raise AssertionError("EXPECTATIVA_ANUAL_NO_CUMPLIDA")

    def fixture(self):
        m, cat = self.m, self.ctx["catalog"]
        # Sólo diccionarios privados de esta prueba; jamás tablas.
        for name, cls in Record.registry.items():
            if name not in ("Alumno",) and name not in {
                "CefActividad", "CefEje", "CefCodigoRa", "CefNivelActividad",
                "CefRangoEtario", "CefTurno", "CefDiaSemana"}:
                cls.objects.rows.clear()
                cls.objects.sequence = 0
        source = m.CefCiclo.objects.create(
            anio=2024, fecha_inicio=date(2024,3,31), cerrado=True, actual=False)
        group = m.CefGrupo.objects.create(
            ciclo=source, cueanexo=self.ctx["cues"][0], actividad=cat["actividad"],
            nivel=cat["nivel"], rango_etario=cat["rango"], turno=cat["turno"],
            hora_inicio=cat["start"], hora_fin=cat["end"], numero=1, cupo_maximo=4)
        m.CefGrupoDiaFuncionamiento.objects.create(grupo=group, dia_semana=cat["dia"])
        pupil = m.Alumno.objects.all().first()
        cuil = "00000000000"  # Ficticio y exclusivamente en RAM.
        day = date(2024,4,1)
        m.CefAlumnoCef.objects.bulk_create([
            m.CefAlumnoCef(ciclo=source, cueanexo=group.cueanexo, alumno=pupil,
                          fecha_alta=day),
            m.CefAlumnoCef(ciclo=source, cueanexo=group.cueanexo, alumno=pupil,
                          estado="baja", fecha_alta=day, fecha_baja=day)])
        m.CefDocenteCef.objects.bulk_create([
            m.CefDocenteCef(ciclo=source, cueanexo=group.cueanexo, docente_cuil=cuil,
                           fecha_alta=day),
            m.CefDocenteCef(ciclo=source, cueanexo=group.cueanexo, docente_cuil=cuil,
                           estado="baja", fecha_alta=day, fecha_baja=day)])
        enrollment = m.CefInscripcion.objects.create(
            grupo=group, alumno=pupil, fecha_inscripcion=day)
        m.CefInscripcion.objects.bulk_create([
            m.CefInscripcion(grupo=group, alumno=pupil, fecha_inscripcion=day,
                             estado="baja", fecha_baja=day)])
        m.CefDocenteGrupo.objects.bulk_create([
            m.CefDocenteGrupo(grupo=group, docente_cuil=cuil, rol="titular", fecha_desde=day),
            m.CefDocenteGrupo(grupo=group, docente_cuil=cuil, rol="titular", fecha_desde=day,
                             estado="baja", fecha_hasta=day)])
        jornada = m.CefJornadaAsistencia(grupo=group, fecha=day)
        m.CefJornadaAsistencia.objects.bulk_create([jornada])
        attendance = m.CefAsistencia(jornada=jornada, inscripcion=enrollment, estado="presente")
        m.CefAsistencia.objects.bulk_create([attendance])
        m.CefAsistenciaMovimiento.objects.bulk_create([
            m.CefAsistenciaMovimiento(asistencia=attendance, estado_nuevo="presente")])
        return source, group, SimpleNamespace(get_username=lambda: "SINTETICO")

    def generate(self, source, actor):
        return self.annual.generar_ciclo_siguiente(
            source, actor, fecha_inicio=DESTINATION_START, fecha_fin=date(2025,12,31))

    def atomic_failures(self):
        from offline_support import Query, IntegrityError
        class InjectedFailure(Exception):
            pass
        stages = ('CefCiclo', 'CefGrupo', 'CefGrupoDiaFuncionamiento', 'CefAlumnoCef',
                  'CefDocenteCef', 'CefInscripcion', 'CefDocenteGrupo', 'marca_actual')
        for stage in stages:
            source, group, actor = self.fixture()
            original = memory_snapshot()
            sequences = {name: cls.objects.sequence for name, cls in Record.registry.items()}
            hit, boundaries = [], []
            store, bulk = Record.store, Query.bulk_create
            enter, leave = Atomic.__enter__, Atomic.__exit__
            def tracked_enter(transaction):
                boundaries.append('enter')
                return enter(transaction)
            def tracked_leave(transaction, *args):
                boundaries.append('rollback' if args[0] else 'commit_simulado')
                return leave(transaction, *args)
            def fail():
                self.check(Atomic.depth > 0)
                hit.append(stage)
                if stage == 'CefDocenteGrupo':
                    raise IntegrityError('FALLO_SINTETICO')
                raise InjectedFailure('FALLO_SINTETICO')
            def save_record(record, *args, **kwargs):
                result = store(record, *args, **kwargs)
                if type(record).__name__ == 'CefCiclo' and record.anio == 2025:
                    if (stage == 'CefCiclo' and not record.actual) or (stage == 'marca_actual' and record.actual):
                        fail()
                return result
            def copy_records(query, objects, **kwargs):
                result = bulk(query, objects, **kwargs)
                if query.model.__name__ == stage:
                    self.check(len(objects) > 0)
                    fail()
                return result
            with patch.object(Record, 'store', save_record), patch.object(Query, 'bulk_create', copy_records), \
                    patch.object(Atomic, '__enter__', tracked_enter), patch.object(Atomic, '__exit__', tracked_leave):
                try:
                    self.generate(source, actor)
                except (InjectedFailure, ValidationError):
                    pass
                else:
                    raise AssertionError('FALLO_INYECTADO_NO_PROPAGADO')
            self.check(hit == [stage] and boundaries == ['enter', 'rollback'])
            self.check(Atomic.depth == 0 and memory_snapshot() == original)
            self.check({name: cls.objects.sequence for name, cls in Record.registry.items()} == sequences)

    def execute(self, case):
        if case.code == 'G11':
            with patch.object(self.annual.timezone, 'localdate', return_value=TODAY):
                self.atomic_failures()
            return
        with patch.object(self.annual.timezone, "localdate", return_value=TODAY):
            source, group, actor = self.fixture()
            original = memory_snapshot()
            generated = self.generate(source, actor)
            target = generated["ciclo_destino"]
            action = ACTIONS[case.code]
            self.check(target.anio == 2025 and target.actual and not target.cerrado)
            if action in ("students", "teachers"):
                cls = self.m.CefAlumnoCef if action == "students" else self.m.CefDocenteCef
                self.check(cls.objects.filter(ciclo=target).count() == 1)
                copied = cls.objects.filter(ciclo=target).get()
                self.check(copied.estado == "activo" and copied.fecha_baja is None)
                self.check(copied.cueanexo == group.cueanexo)
                identity = "alumno_id" if action == "students" else "docente_cuil"
                original_row = cls.objects.filter(ciclo=source, estado="activo").get()
                self.check(getattr(copied, identity) == getattr(original_row, identity))
                self.check(copied.fecha_alta == DESTINATION_START)
            elif action in ("enrollments", "assignments"):
                cls = self.m.CefInscripcion if action == "enrollments" else self.m.CefDocenteGrupo
                rows = list(cls.objects.filter(grupo__ciclo=target))
                self.check(len(rows) == 1 and rows[0].grupo.grupo_origen_id == group.pk)
                copied = rows[0]
                self.check(copied.estado == "activo" and copied.grupo.cueanexo == group.cueanexo)
                if action == "enrollments":
                    self.check(copied.alumno_id == cls.objects.filter(grupo=group, estado="activo").get().alumno_id)
                    self.check(copied.fecha_inscripcion == DESTINATION_START and copied.fecha_baja is None)
                else:
                    original_row = cls.objects.filter(grupo=group, estado="activo").get()
                    self.check(copied.docente_cuil == original_row.docente_cuil and copied.rol == original_row.rol)
                    self.check(copied.fecha_desde == DESTINATION_START and copied.fecha_hasta is None)
            elif action == "dates":
                for cls, scope, field in (
                    (self.m.CefAlumnoCef, "ciclo", "fecha_alta"),
                    (self.m.CefDocenteCef, "ciclo", "fecha_alta"),
                    (self.m.CefInscripcion, "grupo__ciclo", "fecha_inscripcion"),
                    (self.m.CefDocenteGrupo, "grupo__ciclo", "fecha_desde")):
                    self.check(list(cls.objects.filter(**{scope:target}).values_list(
                        field,flat=True)) == [DESTINATION_START])
            elif action == "attendance":
                self.check(not self.m.CefJornadaAsistencia.objects.filter(grupo__ciclo=target).exists())
                self.check(not self.m.CefAsistencia.objects.filter(jornada__grupo__ciclo=target).exists())
                self.check(self.m.CefAsistenciaMovimiento.objects.count() == 1)
                self.check(self.m.CefJornadaAsistencia.objects.filter(grupo__ciclo=source).count() == 1)
            elif action == "duplicate":
                before = memory_snapshot()
                try:
                    self.generate(source, actor)
                except ValidationError:
                    pass
                else:
                    raise AssertionError("GENERACION_DUPLICADA_ADMITIDA")
                self.check(before == memory_snapshot())
            # Sólo se comparan filas de origen ya existentes en el diccionario inicial.
            after = memory_snapshot()
            self.check(all(after[name][pk] == values for name, rows in original.items()
                           for pk, values in rows.items()))
