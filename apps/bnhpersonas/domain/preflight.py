"""Sólo lectura y compatible con el esquema previo a 0018."""
import re
from collections import defaultdict
from django.db.models import F, Q


def inspect_data(Personas, RegistroActividades, HorarioActividad, using='default'):
    issues = {}
    identities = defaultdict(list)
    malformed = []
    for pk, cuil in Personas.objects.using(using).values_list('pk', 'cuil').iterator(chunk_size=2000):
        if not cuil:
            continue
        normalized = re.sub(r'[^0-9]', '', cuil)
        identities[normalized].append(pk)
        if cuil != normalized or len(normalized) != 11:
            malformed.append(pk)
    duplicates = [ids for ids in identities.values() if len(ids) > 1]
    if duplicates:
        issues['personas_cuil_duplicado_ids'] = duplicates
    if malformed:
        issues['personas_cuil_no_canonico_ids'] = malformed
    activity = RegistroActividades.objects.using(using)
    checks = {
        'cargos_carga_no_positiva_ids': activity.filter(carga_horaria__lte=0),
        'cargos_fechas_invertidas_ids': activity.filter(f_hasta__lt=F('f_desde')),
        'funciones_fechas_invertidas_ids': activity.filter(f_hasta_funciones__lt=F('f_desde_funciones')),
        'horarios_invalidos_ids': HorarioActividad.objects.using(using).filter(hora_hasta__lte=F('hora_desde')),
    }
    for key, qs in checks.items():
        ids = list(qs.values_list('pk', flat=True))
        if ids:
            issues[key] = ids
    return issues
