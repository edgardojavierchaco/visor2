"""96 expectativas reutilizadas; sólo lógica AST y dependencias sintéticas en memoria."""
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from safety import Blocked, Skipped
from offline_support import ValidationError, PermissionDenied, Atomic


@dataclass(frozen=True)
class Case:
    code: str
    category: str
    description: str
    action: str
    option: str = ""
    scope: str = "logica_AST_con_dependencias_simuladas"
    blocked: str = ""


def build_cases():
    cases = []
    def add(cat, description, action, option="", scope="logica_AST_con_dependencias_simuladas", blocked=""):
        n = 1 + sum(c.category == cat for c in cases)
        cases.append(Case(f"{cat}{n:02d}", cat, description, action, option, scope, blocked))

    for label, option in (
        ("Inicio oficial obligatorio", "required"),
        ("Inicio en año del ciclo", "year"),
        ("Fin previsto válido", "end_valid"),
        ("Fin anterior al inicio", "end_invalid"),
        ("Fecha inexistente", "invalid"),
        ("Fecha anterior al inicio", "before"),
        ("Fecha futura", "future"),
        ("Retroactividad posterior al inicio", "retro"),
        ("Fin previsto no cierra automáticamente", "no_auto_close"),
    ):
        add("A", label, "dates", option, "validador_real_AST_aislado")
    add("A", "Cargas bloqueadas antes del inicio real", "cycle_gate", "before")
    add("A", "Cargas habilitadas en el inicio real", "cycle_gate", "start")
    add("A", "Modificación incompatible del inicio rechazada sin guardar", "start_change")

    for label, option in (
        ("Crear grupo con formulario y guardado reales", "create"),
        ("Actividad activa permitida", "activity"),
        ("Turno y horario permitidos", "turn"),
        ("Horario fuera del turno rechazado", "bad_turn"),
        ("Días requeridos", "missing_days"),
        ("Día fuera de catálogo rechazado", "bad_day"),
        ("Editar observaciones conservando días", "edit"),
        ("Baja del grupo vacío", "close"),
        ("Reactivar grupo vacío", "reactivate"),
        ("Historial de movimientos conservado", "history"),
        ("Baja bloqueada por inscripción activa", "student_active"),
        ("Baja bloqueada por asignación activa", "teacher_active"),
        ("Edición horaria con conflicto de alumnos", "edit_conflict"),
        ("Actividad con historia inmutable", "activity_history"),
        ("Fin horario debe ser posterior al inicio", "bad_order"),
    ):
        add("B", label, "groups", option)

    for label, option in (
        ("Inscribir alumno sintético", "create"),
        ("Inscripción retroactiva válida", "retro"),
        ("Inscripción anterior al inicio", "before_start"),
        ("Inscripción futura", "future"),
        ("Duplicado activo rechazado", "duplicate"),
        ("Piso de alta del banco", "bank_floor"),
        ("Piso de activación del grupo", "group_floor"),
        ("Baja de inscripción temporal", "close"),
        ("Reinscripción crea nuevo período", "rejoin"),
        ("Historial conserva período anterior", "history"),
        ("Conflicto de horarios", "conflict"),
        ("Horarios contiguos permitidos", "adjacent"),
        ("Cupo máximo operativo", "capacity"),
        ("Independencia entre ambos CEF", "independent"),
        ("Banco de otro CEF no habilita inscripción", "foreign"),
    ):
        add("C", label, "students", option)

    for label, option in (
        ("Asignar Titular", "titular"),
        ("Asignar Suplente", "suplente"),
        ("Asignar Interino", "interino"),
        ("Asignación retroactiva válida", "retro"),
        ("Asignación anterior al inicio", "before_start"),
        ("Asignación futura", "future"),
        ("Duplicado docente activo", "duplicate"),
        ("Titular exclusivo", "exclusive_titular"),
        ("Interino exclusivo", "exclusive_interino"),
        ("Múltiples Suplentes permitidos", "multiple_suplente"),
        ("Rol desconocido rechazado", "bad_role"),
        ("Baja de asignación temporal", "close"),
        ("Reasignación crea nuevo período", "rejoin"),
        ("Historial conserva período anterior", "history"),
        ("Piso de alta del banco", "bank_floor"),
        ("Piso de activación del grupo", "group_floor"),
        ("Independencia entre ambos CEF", "independent"),
        ("Banco de otro CEF no habilita asignación", "foreign"),
    ):
        add("D", label, "teachers", option)

    for label, option in (
        ("Registrar Presente", "presente"),
        ("Registrar Ausente", "ausente"),
        ("Registrar Justificada", "justificada"),
        ("Carga incompleta rechazada", "incomplete"),
        ("Jornada anterior al inicio", "before_start"),
        ("Jornada futura", "future"),
        ("Rectificación de estado", "rectify"),
        ("Historial conserva movimientos", "history"),
        ("Sólo inscripciones vigentes en fecha", "validity"),
        ("Nueva jornada anterior a última rechazada", "chronology"),
        ("Rectificación de jornada existente anterior", "existing"),
        ("Inscripción de otro grupo rechazada", "foreign"),
        ("Rectificación BAJA con autoridad simulada", "historical"),
    ):
        add("E", label, "attendance", option,
            "parcial_autoridad_simulada" if option == "historical" else "logica_AST_con_dependencias_simuladas")

    for role in ("Director", "Administrador", "Director de Servicios Complementarios",
                 "profesorcef", "No autorizado"):
        add("F", f"Matriz funcional del rol {role}", "permissions", role,
            "parcial_rol_y_scope_simulados")
        add("F", f"Alcance propio/ajeno del rol {role}", "scope", role,
            "parcial_rol_y_scope_simulados")
    add("F", "Autenticación y permisos de usuarios reales", "", blocked="AUTENTICACION_REAL_NO_CUBIERTA")

    add("G", "Prevalidación anual sin escrituras", "annual_preview")
    add("G", "Generación requiere cierre manual", "annual_open")
    add("G", "Inicio oficial de destino obligatorio", "annual_date", scope="validador_real_AST_aislado")
    for label in (
        "Traslado de alumnos activos", "Traslado de profesores activos",
        "Traslado de inscripciones", "Traslado de asignaciones",
        "Cuatro fechas heredadas iguales al inicio destino", "Preservación del origen",
        "No copia de asistencias", "Generación anual atómica", "Generación duplicada rechazada",
    ):
        add("G", label, "", scope="copia_anual_solo_en_memoria", blocked="COPIA_SOLO_EN_MEMORIA_PERSISTENCIA_NO_CUBIERTA")
    from capacity_cases import OPTIONS
    for label, option in OPTIONS:
        add("H", label, "capacity", option, "cupo_logica_original_AST_sin_BD")
    return cases


CASES = build_cases()


class Scenarios:
    def __init__(self, m, s, attendance, annual, forms, views, permissions, context):
        self.m, self.s, self.a, self.annual = m, s, attendance, annual
        self.f, self.v, self.p, self.ctx = forms, views, permissions, context
        self.last_date = None

    def check(self, condition):
        if not condition:
            raise AssertionError("EXPECTATIVA_NO_CUMPLIDA")

    def reject(self, function, *args, expect_message=None, **kwargs):
        # El servicio debe restaurar por sí mismo; un atomic exterior ocultaría fallos.
        from offline_support import memory_snapshot
        before = memory_snapshot()
        try:
            function(*args, **kwargs)
        except ValidationError as exc:
            self.check(memory_snapshot() == before)
            if expect_message:
                self.check(expect_message.casefold() in " ".join(exc.messages).casefold())
            return
        raise AssertionError("RECHAZO_ESPERADO_NO_OCURRIO")

    def later(self, day):
        if day == date(day.year, 12, 31):
            raise Skipped("SIN_DIA_POSTERIOR_EN_CICLO")
        return day + timedelta(days=1)

    def simulate(self, day):
        self.last_date = day
        return patch.object(self.s.timezone, "localdate", return_value=day)

    @property
    def cycle(self):
        return self.ctx["cycle"]

    @property
    def base(self):
        return self.ctx["base"]

    def group(self, cue=None, *, activate=True, start=None, end=None, capacity=4):
        cue = cue or self.ctx["cues"][0]
        catalog = self.ctx["catalog"]
        # Fixture sólo de Record/Manager sintéticos; no usa formularios ni ORM Django.
        group = self.m.CefGrupo.objects.create(
            cueanexo=cue, ciclo=self.cycle, actividad=catalog["actividad"],
            nivel=catalog["nivel"], rango_etario=catalog["rango"], turno=catalog["turno"],
            hora_inicio=start or catalog["start"], hora_fin=end or catalog["end"],
            cupo_maximo=capacity, numero=self.m.CefGrupo.objects.count()+1)
        self.m.CefGrupoDiaFuncionamiento.objects.create(grupo=group, dia_semana=catalog["dia"])
        if activate:
            self.s.dar_baja_grupo(group, None, "Prueba temporal", fecha_baja=self.base)
            group = self.s.reactivar_grupo(group, None, fecha_reactivacion=self.base)
        return group

    def student(self, group, index=0, day=None):
        seed = self.ctx["students"][group.cueanexo][index]
        # Referencia sintética; el servicio real se extrae por AST y recibe sólo objetos de memoria.
        model = self.m.CefAlumnoCef._meta.get_field("alumno").remote_field.model
        item = self.s.crear_inscripcion_activa(
            group, model(pk=seed.alumno_id), None, day or self.base, incorporar_banco=False)
        self.check(item.grupo_id == group.pk and item.alumno_id == seed.alumno_id)
        self.check(item.fecha_inscripcion == (day or self.base) and item.estado == 'activo')
        stored = self.m.CefInscripcion.objects.get(pk=item.pk)
        self.check(stored.grupo_id == group.pk and stored.alumno_id == seed.alumno_id)
        return item

    def teacher(self, group, index=0, day=None, role="titular"):
        cuil = self.ctx["teachers"][group.cueanexo][index].docente_cuil
        item = self.s.crear_asignacion_docente_activa(
            group, cuil, role, None, day or self.base, incorporar_banco=False)
        self.check(item.grupo_id == group.pk and item.docente_cuil == cuil and item.rol == role)
        self.check(item.fecha_desde == (day or self.base) and item.estado == 'activo')
        stored = self.m.CefDocenteGrupo.objects.get(pk=item.pk)
        self.check(stored.grupo_id == group.pk and stored.docente_cuil == cuil and stored.rol == role)
        return item

    def dates(self, option):
        start, end = date(2024, 3, 31), date(2024, 4, 5)
        cycle = self.m.CefCiclo(anio=2024, fecha_inicio=start, fecha_fin=end,
                                cerrado=False, activo=True, actual=True)
        with self.simulate(end):
            if option == "required":
                self.reject(self.s.validar_fechas_oficiales_ciclo, 2024, None)
            elif option == "year":
                self.reject(self.s.validar_fechas_oficiales_ciclo, 2024, date(2023, 3, 31))
            elif option == "end_valid":
                self.check(self.s.validar_fechas_oficiales_ciclo(2024, start, end) == (start, end))
            elif option == "end_invalid":
                self.reject(self.s.validar_fechas_oficiales_ciclo, 2024, start, start - timedelta(days=1))
            elif option == "invalid":
                self.reject(self.s.validar_fechas_oficiales_ciclo, 2024, "2024-02-30")
            elif option == "before":
                self.reject(self.s.validar_fecha_operativa_ciclo, cycle, start - timedelta(days=1))
            elif option == "future":
                self.reject(self.s.validar_fecha_operativa_ciclo, cycle, end + timedelta(days=1))
            elif option == "retro":
                self.check(self.s.validar_fecha_operativa_ciclo(cycle, start) == start)
            elif option == "no_auto_close":
                with self.simulate(end + timedelta(days=1)):
                    self.check(not self.s.motivo_bloqueo_inicio_ciclo(cycle))
                    self.check(not cycle.cerrado)
                    self.check(self.s.validar_fecha_interactiva_ciclo(
                        cycle, end + timedelta(days=1)) == end + timedelta(days=1))

    def cycle_gate(self, option):
        day = self.cycle.fecha_inicio
        if option == "before":
            day -= timedelta(days=1)
        with self.simulate(day):
            if option == "before":
                self.reject(self.s.validar_ciclo_escribible, self.cycle.pk)
            else:
                self.check(self.s.validar_ciclo_escribible(self.cycle.pk).pk == self.cycle.pk)

    def start_change(self, _):
        # Sólo se ejecuta el validador de lectura; nunca se guarda el ciclo.
        first = min(seed.fecha_alta for rows in self.ctx["students"].values() for seed in rows)
        proposed = self.later(first)
        self.reject(self.s.validar_cambio_inicio_ciclo, self.cycle, proposed,
                    fecha_inicio_anterior=self.cycle.fecha_inicio)

    def groups(self, option):
        group = self.group(activate=False)
        if option == "turn":
            group.full_clean()
            self.check(group.hora_inicio >= group.turno.hora_desde_referencia)
            self.check(group.hora_fin <= group.turno.hora_hasta_referencia)
            self.check(group.hora_inicio < group.hora_fin)
        elif option == "bad_order":
            group.hora_fin = group.hora_inicio
            self.reject(group.full_clean)
        elif option == "bad_turn":
            turn = group.turno
            reference = datetime.combine(date(2000, 1, 1), turn.hora_hasta_referencia)
            outside = reference + timedelta(minutes=1)
            if outside.date() == reference.date():
                group.hora_fin = outside.time()
            else:
                reference = datetime.combine(date(2000, 1, 1), turn.hora_desde_referencia)
                outside = reference - timedelta(minutes=1)
                if outside.date() != reference.date():
                    raise Skipped("TURNO_CUBRE_TODO_EL_DIA")
                group.hora_inicio = outside.time()
            self.reject(group.full_clean)
        elif option in {"close", "reactivate", "history"}:
            self.s.dar_baja_grupo(group, None, "Prueba temporal", self.base)
            group.refresh_from_db()
            self.check(group.estado == "baja" and group.fecha_baja == self.base)
            if option != "close":
                self.s.reactivar_grupo(group, None, self.base)
                group.refresh_from_db()
                self.check(group.estado == "activo" and group.fecha_baja is None)
                self.check(list(group.movimientos_estado.order_by("pk").values_list(
                    "estado_resultante", flat=True)) == ["baja", "activo"])
        elif option in {"student_active", "teacher_active"}:
            self.student(group) if option == "student_active" else self.teacher(group)
            self.reject(self.s.dar_baja_grupo, group, None, "Prueba temporal", self.base)
            group.refresh_from_db()
            self.check(group.estado == "activo")
        elif option == "edit_conflict":
            second = self.group(start=self.ctx["catalog"]["end"],
                                end=self.ctx["catalog"]["second_end"])
            first = self.student(group)
            self.student(second)
            self.reject(self.s.validar_conflictos_horarios_edicion_grupo, second,
                        hora_inicio=group.hora_inicio, hora_fin=group.hora_fin,
                        dias_ids=[self.ctx["catalog"]["dia"].pk], alumnos_ids=[first.alumno_id])
        elif option == "activity_history":
            self.student(group)
            other = self.m.CefActividad.objects.filter(activo=True).exclude(
                pk=group.actividad_id).order_by("pk").first()
            if other is None:
                raise Skipped("FALTA_SEGUNDA_ACTIVIDAD_ACTIVA")
            proposed = self.m.CefGrupo.objects.get(pk=group.pk)
            proposed.actividad = other
            self.reject(self.s.validar_estructura_grupo_con_historia,
                        group, proposed, [self.ctx["catalog"]["dia"].pk])

    def students(self, option):
        group = self.group(capacity=1 if option == "capacity" else 4)
        if option in {"before_start", "future", "bank_floor", "group_floor"}:
            day = self.cycle.fecha_inicio - timedelta(days=1)
            if option == "future":
                day = self.base + timedelta(days=1)
            elif option == "bank_floor":
                day = self.ctx["students"][group.cueanexo][0].fecha_alta - timedelta(days=1)
                if day < self.cycle.fecha_inicio:
                    raise Skipped("PISO_BANCO_NO_SEPARABLE_DEL_INICIO")
                # Grupo sin movimiento inicial para aislar el piso del banco.
                group = self.group(activate=False)
            elif option == "group_floor":
                later = self.later(self.base)
                with self.simulate(later):
                    self.s.dar_baja_grupo(group, None, "Prueba temporal", later)
                    group = self.s.reactivar_grupo(group, None, later)
                day = self.base
            if option == 'before_start':
                # Aísla la regla de fecha antes de sumar pisos de banco/activación.
                self.reject(self.s.validar_fecha_inscripcion_grupo, group, day)
            if option == 'group_floor':
                with self.simulate(later):
                    self.reject(self.student, group, day=day)
                    self.check(self.student(group, day=later).fecha_inscripcion == later)
            else:
                self.reject(self.student, group, day=day)
            return
        if option == "retro":
            with self.simulate(self.later(self.base)):
                item = self.student(group, day=self.base)
                self.check(item.fecha_inscripcion == self.base)
            return
        if option == "foreign":
            other = self.ctx["cues"][1]
            seed = next((row for row in self.ctx["students"][other]
                         if row.alumno_id not in self.ctx["student_ids"][group.cueanexo]), None)
            if seed is None:
                raise Skipped("MISMAS_PERSONAS_EN_AMBOS_BANCOS")
            model = self.m.CefAlumnoCef._meta.get_field("alumno").remote_field.model
            self.reject(self.s.crear_inscripcion_activa, group, model(pk=seed.alumno_id),
                        None, self.base, incorporar_banco=False)
            return
        first = self.student(group)
        self.check(first.estado == "activo" and first.fecha_inscripcion == self.base)
        if option == "duplicate":
            self.reject(self.student, group)
        elif option in {"close", "rejoin", "history"}:
            self.s.dar_baja_inscripcion(first, None, "Prueba temporal", self.base)
            first.refresh_from_db()
            self.check(first.estado == "baja" and first.fecha_baja == self.base)
            if option != "close":
                second = self.s.reinscribir_alumno(first, None, self.base)
                first.refresh_from_db()
                self.check(second.pk != first.pk and first.estado == "baja")
                self.check(first.fecha_inscripcion == self.base and first.fecha_baja == self.base
                           and second.fecha_inscripcion == self.base and second.fecha_baja is None)
                self.check(self.m.CefInscripcion.objects.filter(grupo=group).count() == 2)
        elif option in {"conflict", "adjacent"}:
            if option == "conflict":
                second = self.group()
                self.reject(self.student, second)
            else:
                second = self.group(start=self.ctx["catalog"]["end"],
                                    end=self.ctx["catalog"]["second_end"])
                self.check(self.student(second).pk is not None)
        elif option == "capacity":
            # Expectativa solicitada. Si el servicio no controla cupos informa FAIL;
            # nunca se simula ese control ni se cambia producción.
            self.reject(self.student, group, index=1)
        elif option == "independent":
            second = self.group(cue=self.ctx["cues"][1])
            self.student(second)
            self.check(self.m.CefInscripcion.objects.filter(grupo=group).count() == 1)
            self.check(self.m.CefInscripcion.objects.filter(grupo=second).count() == 1)

    def teachers(self, option):
        group = self.group()
        if option in {"before_start", "future", "bank_floor", "group_floor"}:
            day = self.cycle.fecha_inicio - timedelta(days=1)
            if option == "future":
                day = self.base + timedelta(days=1)
            elif option == "bank_floor":
                day = self.ctx["teachers"][group.cueanexo][0].fecha_alta - timedelta(days=1)
                if day < self.cycle.fecha_inicio:
                    raise Skipped("PISO_BANCO_NO_SEPARABLE_DEL_INICIO")
                group = self.group(activate=False)
            elif option == "group_floor":
                later = self.later(self.base)
                with self.simulate(later):
                    self.s.dar_baja_grupo(group, None, "Prueba temporal", later)
                    group = self.s.reactivar_grupo(group, None, later)
                day = self.base
            if option == 'before_start':
                self.reject(self.s.validar_fecha_interactiva_ciclo, group.ciclo, day)
            if option == 'group_floor':
                with self.simulate(later):
                    self.reject(self.teacher, group, day=day)
                    self.check(self.teacher(group, day=later).fecha_desde == later)
            else:
                self.reject(self.teacher, group, day=day)
            return
        if option == "retro":
            with self.simulate(self.later(self.base)):
                self.check(self.teacher(group, day=self.base).fecha_desde == self.base)
            return
        if option == "foreign":
            other = self.ctx["cues"][1]
            seed = next((row for row in self.ctx["teachers"][other]
                         if row.docente_cuil not in self.ctx["teacher_ids"][group.cueanexo]), None)
            if seed is None:
                raise Skipped("MISMAS_PERSONAS_EN_AMBOS_BANCOS")
            self.reject(self.s.crear_asignacion_docente_activa, group, seed.docente_cuil,
                        "titular", None, self.base, incorporar_banco=False)
            return
        role = option if option in {"titular", "suplente", "interino"} else "titular"
        if option in {"exclusive_interino", "multiple_suplente", "duplicate"}:
            role = "interino" if option == "exclusive_interino" else "suplente"
        if option == "bad_role":
            self.reject(self.teacher, group, role="rol_inexistente")
            return
        first = self.teacher(group, role=role)
        self.check(first.estado == "activo" and first.rol == role)
        if option == "duplicate":
            self.reject(self.teacher, group, role=role)
        elif option in {"exclusive_titular", "exclusive_interino"}:
            self.reject(self.teacher, group, index=1, role=role)
        elif option == "multiple_suplente":
            self.check(self.teacher(group, index=1, role=role).pk != first.pk)
        elif option in {"close", "rejoin", "history"}:
            self.s.dar_baja_asignacion_docente(first, None, "Prueba temporal", self.base)
            first.refresh_from_db()
            self.check(first.estado == "baja" and first.fecha_hasta == self.base)
            if option != "close":
                second = self.s.reasignar_docente_grupo(first, None, self.base)
                first.refresh_from_db()
                self.check(second.pk != first.pk and first.estado == "baja")
                self.check(first.fecha_desde == self.base and first.fecha_hasta == self.base
                           and second.fecha_desde == self.base and second.fecha_hasta is None)
                self.check(self.m.CefDocenteGrupo.objects.filter(grupo=group).count() == 2)
        elif option == "independent":
            second = self.group(cue=self.ctx["cues"][1])
            self.teacher(second)
            self.check(self.m.CefDocenteGrupo.objects.filter(grupo=group).count() == 1)
            self.check(self.m.CefDocenteGrupo.objects.filter(grupo=second).count() == 1)

    def attendance(self, option):
        group = self.group()
        first, second = self.student(group), self.student(group, index=1)
        mapping = {first.pk: "presente", second.pk: "ausente"}
        day = self.base
        if option in {"before_start", "future"}:
            day = (self.cycle.fecha_inicio - timedelta(days=1) if option == "before_start"
                   else self.base + timedelta(days=1))
            if option == 'before_start':
                self.reject(self.a._validar_fecha_jornada, group, day)
            self.reject(self.a.registrar_asistencias_jornada, group, day, mapping, None)
            return
        if option == "incomplete":
            self.reject(self.a.registrar_asistencias_jornada, group, day, {first.pk: "presente"}, None)
            self.check(not self.m.CefJornadaAsistencia.objects.filter(grupo=group).exists())
            return
        if option == "foreign":
            other = self.group()
            foreign = self.student(other, index=2)
            self.reject(self.a.registrar_asistencias_jornada, group, day,
                        {**mapping, foreign.pk: "presente"}, None)
            return
        if option == "validity":
            later = self.later(day)
            self.s.dar_baja_inscripcion(second, None, "Prueba temporal", day)
            with self.simulate(later):
                actual = self.a.inscripciones_vigentes_jornada(group, later)
                self.check({x.pk for x in actual} == {first.pk})
                result = self.a.registrar_asistencias_jornada(
                    group, later, {first.pk: "presente"}, None)
                self.check(result["altas"] == 1)
            return
        if option == "chronology":
            later = self.later(day)
            with self.simulate(later):
                self.a.registrar_asistencias_jornada(group, later, mapping, None)
                self.reject(self.a.registrar_asistencias_jornada, group, day, mapping, None)
            return
        if option in {"presente", "ausente", "justificada"}:
            mapping[first.pk] = option
        result = self.a.registrar_asistencias_jornada(group, day, mapping, None)
        self.check(result["altas"] == 2)
        if option in {"presente", "ausente", "justificada"}:
            self.check(self.m.CefAsistencia.objects.get(inscripcion=first).estado == option)
        if option in {"rectify", "history", "existing", "historical"}:
            mapping[first.pk] = "justificada"
            if option == "existing":
                with self.simulate(self.later(day)):
                    self.a.registrar_asistencias_jornada(group, self.later(day), mapping, None)
            if option == "historical":
                self.s.dar_baja_inscripcion(first, None, "Prueba temporal", day)
                self.s.dar_baja_inscripcion(second, None, "Prueba temporal", day)
                group = self.s.dar_baja_grupo(group, None, "Prueba temporal", day)
                # Autoridad y almacenamiento simulados; funciones de vigencia/movimientos originales.
                with patch.object(self.a, "usuario_puede_rectificar_cef", return_value=True):
                    result = self.a.registrar_asistencias_jornada(group, day, mapping, None)
            else:
                result = self.a.registrar_asistencias_jornada(group, day, mapping, None)
            self.check(result["cambios"] == 1 and result["altas"] == 0)
            attendance = self.m.CefAsistencia.objects.get(jornada__fecha=day, inscripcion=first)
            self.check(attendance.estado == "justificada")
            self.check(list(attendance.movimientos.order_by("pk").values_list(
                "estado_nuevo", flat=True)) == ["presente", "justificada"])
            self.check(list(attendance.movimientos.order_by("pk").values_list(
                "estado_anterior", flat=True)) == [None, "presente"])

    def permissions(self, role):
        user = SimpleNamespace(is_authenticated=True, username="", pk=None)
        with patch.object(self.m, "obtener_rol_usuario_cef", return_value=role):
            permissions = self.m.obtener_permisos_usuario_cef(user)
        request = SimpleNamespace(user=user, _cef_permisos_usuario=permissions)
        if role == "No autorizado":
            try:
                self.p._validar_acceso_cef(request, permitir_solo_asistencia=True)
            except PermissionDenied:
                return
            raise AssertionError("PERMISO_INDEBIDO")
        self.p._validar_acceso_cef(request, permitir_solo_asistencia=True)
        self.check(permissions["puede_rectificar_cef"] ==
                   (role in {"Administrador", "Director de Servicios Complementarios"}))
        if role == "profesorcef":
            try:
                self.p._validar_acceso_cef(request)
            except PermissionDenied:
                return
            raise AssertionError("PROFESOR_ACCESO_GENERAL_INDEBIDO")

    def scope(self, role):
        # Prueba parcial: no afirma resolver responsables ni autenticar usuarios.
        user = SimpleNamespace(is_authenticated=True, username="", pk=None)
        with patch.object(self.m, "obtener_rol_usuario_cef", return_value=role):
            permissions = self.m.obtener_permisos_usuario_cef(user)
        own, foreign = self.ctx["cues"]
        allowed = [own, foreign] if role == "Administrador" else (
            [] if role == "No autorizado" else [own])
        with patch.object(self.m, "get_cueanexos_cargables_usuario", return_value=allowed):
            self.check(self.m.usuario_puede_cargar_cueanexo(user, own, permissions) ==
                       (role != "No autorizado"))
            self.check(self.m.usuario_puede_cargar_cueanexo(user, foreign, permissions) ==
                       (role == "Administrador"))
            self.check(self.m.usuario_puede_rectificar_cef(
                user, permissions, cueanexo=foreign) == (role == "Administrador"))
    def annual_preview(self, _):
        from offline_support import memory_snapshot
        before = memory_snapshot()
        result = self.annual.prevalidar_generacion_anual(self.cycle)
        self.check(isinstance(result, dict) and "proyeccion" in result)
        self.check(result['destino_anio'] == self.cycle.anio + 1 and result['requiere_cierre'])
        self.check(result['origen']['id'] == self.cycle.pk)
        self.check(set(result['proyeccion']['alumnos_origen_ids']) ==
                   set(self.m.CefAlumnoCef.objects.filter(ciclo=self.cycle, estado='activo').values_list('pk', flat=True)))
        self.check(set(result['proyeccion']['docentes_origen_ids']) ==
                   set(self.m.CefDocenteCef.objects.filter(ciclo=self.cycle, estado='activo').values_list('pk', flat=True)))
        self.check(memory_snapshot() == before)

    def annual_open(self, _):
        self.check(not self.cycle.cerrado)
        actor = SimpleNamespace(get_username=lambda: 'SINTETICO')
        self.reject(self.annual.generar_ciclo_siguiente, self.cycle, actor,
                    fecha_inicio=date(2025,3,31), fecha_fin=date(2025,12,31),
                    expect_message="Cerralo antes")

    def annual_date(self, _):
        self.reject(self.s.validar_fechas_oficiales_ciclo, self.cycle.anio + 1, None)

    def execute(self, case):
        self.last_date = self.base
        with self.simulate(self.base):
            getattr(self, case.action)(case.option)
