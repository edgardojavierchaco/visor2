"""Controles negativos de aislamiento y contratos acotados del adaptador."""
import importlib
import os
from pathlib import Path
import socket
import subprocess
import threading

from safety import Blocked


def security_checks():
    """Se llama ya dentro de offline_guard y antes de cualquier escenario."""
    checked = []
    # Si una barrera regresa, la prueba falla sin crear restos ni tocar archivos existentes.
    probe = Path(__file__).resolve().parent / '__OFFLINE_PROBE_PARENT_AUSENTE__' / 'NO_CREAR_SINTETICO'
    if probe.parent.exists():
        raise Blocked('DIRECTORIO_DE_PROBE_DEBE_ESTAR_AUSENTE')
    def denied(name, callback):
        try:
            callback()
        except Blocked:
            checked.append(name)
        else:
            raise AssertionError('BARRERA_NO_RECHAZO_OPERACION')
    for module in ('django', 'apps', 'settings', 'psycopg', 'psycopg2', 'sqlite3',
                   '_sqlite3', 'asyncpg', 'sqlalchemy', 'pymysql', 'MySQLdb'):
        denied('import_' + module, lambda name=module: __import__(name))
        denied('importlib_' + module, lambda name=module: importlib.import_module(name))
    denied('dns', lambda: socket.getaddrinfo('offline.invalid', 1))
    with socket.socket() as client:
        denied('socket_connect', lambda: client.connect(('127.0.0.1', 1)))
        denied('socket_sendto', lambda: client.sendto(b'SINTETICO', ('127.0.0.1', 1)))
    denied('process', lambda: subprocess.Popen(['NO_EJECUTAR_SINTETICO']))
    denied('thread', lambda: threading.Thread(target=lambda: None).start())
    denied('file_write', lambda: open(probe, 'w'))
    denied('path_write', lambda: probe.write_text('SINTETICO'))
    denied('os_open', lambda: os.open(probe, os.O_CREAT | os.O_WRONLY))
    denied('file_delete', lambda: os.remove(probe))
    denied('sensitive_read', lambda: open(probe.parent / 'NO_LEER_SINTETICO.txt', 'r'))
    return {'resultado': 'PASS', 'controles': checked, 'cantidad': len(checked),
            'accesos_bd': 0, 'alcance': 'rechazos previos a importar motores o contactar destinos'}


def adapter_checks():
    from types import SimpleNamespace
    from offline_support import environment, context, Query, Atomic, Record, memory_snapshot
    m, s, a, annual, p = environment()
    ctx = context(m)
    model = m.CefActividad
    rows = Query(model, [SimpleNamespace(pk=1, rank=None), SimpleNamespace(pk=2, rank=2),
                         SimpleNamespace(pk=3, rank=1), SimpleNamespace(pk=4, rank=1)])
    assert [x.pk for x in rows.order_by('rank', 'pk')] == [3, 4, 2, 1]
    assert [x.pk for x in rows.order_by('-rank', 'pk')] == [1, 2, 3, 4]
    assert rows.filter(rank__isnull=True).count() == 1
    assert rows.exclude(rank__gte=1).get().pk == 1
    assert not rows.filter(rank__in=[None]).exists()
    assert rows.filter(rank=1).count() == 2
    assert list(rows.values_list('rank', flat=True).distinct()) == [None, 2, 1]
    try:
        rows.get(rank=1)
    except model.MultipleObjectsReturned:
        pass
    else:
        raise AssertionError('GET_DUPLICADO_NO_RECHAZADO')
    try:
        rows.get(pk=99)
    except model.DoesNotExist:
        pass
    else:
        raise AssertionError('GET_INEXISTENTE_NO_RECHAZADO')
    related = Query(model, [SimpleNamespace(pk=1, name='A'), SimpleNamespace(pk=2, name='B')])
    parent = Query(model, [SimpleNamespace(children=related)])
    assert not parent.filter(children__pk=1, children__name='B').exists()
    assert parent.filter(children__pk=1, children__name='A').exists()
    assert list(parent.values_list('children__pk', 'children__name')) == [(1, 'A'), (2, 'B')]
    parent.prefetch_related(SimpleNamespace(lookup='children', queryset=related.order_by('-pk'), to_attr='ordered'))
    assert [item.pk for item in parent.get().ordered] == [2, 1]
    before = memory_snapshot()
    sequences = {name: cls.objects.sequence for name, cls in Record.registry.items()}
    class Rollback(Exception):
        pass
    try:
        with Atomic():
            kept = model.objects.create(nombre='EXTERIOR_SINTETICO')
            try:
                with Atomic():
                    model.objects.create(nombre='INTERIOR_SINTETICO')
                    raise Rollback()
            except Rollback:
                pass
            assert model.objects.filter(pk=kept.pk).exists()
            assert not model.objects.filter(nombre='INTERIOR_SINTETICO').exists()
            raise Rollback()
    except Rollback:
        pass
    assert memory_snapshot() == before and Atomic.depth == 0
    assert {name: cls.objects.sequence for name, cls in Record.registry.items()} == sequences
    return {'resultado': 'PASS', 'alcance': 'contratos de memoria; sin comparación con ORM/SQL real',
            'comprobaciones': ['NULL y orden PostgreSQL por defecto', 'get ausente/duplicado',
                              'filter/exclude/exists/count/distinct', 'correlación de una relación y prefetch ordenado',
                              'savepoints anidados y secuencias sólo en RAM']}