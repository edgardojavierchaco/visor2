"""Adaptador del alcance institucional BNH Personas para el Observatorio SNU.

No concede acceso mediante is_staff o por simplemente estar autenticado.
Las autorizaciones dependen de resolve_scope(), con la lógica jurisdiccional
existente. Ningún usuario recibe un alcance más amplio aquí.
"""
from dataclasses import dataclass
from django.core.exceptions import PermissionDenied
from apps.bnhpersonas.monitoring.access import resolve_scope


@dataclass(frozen=True)
class SnuScope:
    kind: str
    regiones: tuple = ()
    cueanexos: tuple = ()


def get_scope(user):
    if not user or not getattr(user, 'is_authenticated', False) or not getattr(user, 'is_active', False):
        raise PermissionDenied('Cuenta no autenticada o deshabilitada.')

    alcance = resolve_scope(user)
    if not alcance.has_access:
        raise PermissionDenied('No posee permisos habilitados para el Observatorio SNU.')

    if alcance.kind == 'global':
        return SnuScope(kind='global')
    if alcance.kind == 'regional':
        regiones = tuple(sorted({str(r).strip() for r in alcance.regiones if str(r).strip()}))
        if regiones:
            return SnuScope(kind='regional', regiones=regiones)
    if alcance.kind == 'supervisor':
        cues = tuple(sorted({str(c).strip() for c in alcance.cueanexos if str(c).strip()}))
        if cues:
            return SnuScope(kind='supervisor', cueanexos=cues)

    raise PermissionDenied('No tiene regiones o establecimientos asignados.')
