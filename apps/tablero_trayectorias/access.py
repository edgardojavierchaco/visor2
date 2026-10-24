"""Permisos para los indicadores: rol desde BNH + asignaciones efectivas.
No consulta el padrón como fuente estadística; solo como servicio de autorización.
"""
import re
from django.core.exceptions import PermissionDenied
from apps.bnhpersonas.monitoring.roles import user_role, normalize_role

PROVINCIAL = {'administrador','admin','ministro','ministra','ministro/a','subsecretario','subsecretaria','subsecretario/a','director general','directora general','director/a general'}
DIRECTOR = {'director','directora','director/a'}
REGIONAL = {'regional','director regional','directora regional','referente regional'}
SUPERVISOR = {'supervisor','supervisora'}

def _codes(values):
    result=set()
    for value in values:
        s=str(value or '').strip()
        if s.isdigit(): s=s.zfill(9)
        if re.fullmatch(r'\d{9}',s): result.add(s)
    return sorted(result)

def resolve_scope(user):
    if not getattr(user,'is_authenticated',False) or not getattr(user,'is_active',False):
        raise PermissionDenied('Usuario no habilitado.')
    role=normalize_role(user_role(user))
    perfil=getattr(user,'perfil',None)
    categoria=normalize_role(getattr(getattr(perfil,'rol',None),'categoria_acceso',''))
    if getattr(user,'is_superuser',False) or role in PROVINCIAL:
        return {'kind':'all','cues':[],'label':'Provincial'}
    if role in DIRECTOR or categoria=='propio':
        from apps.bnhpersonas.domain.access import get_user_cueanexos
        return {'kind':'cues','cues':_codes(get_user_cueanexos(user)),'label':'Institucional'}
    if role in SUPERVISOR or categoria=='supervisor':
        from apps.bnhpersonas.monitoring.access import supervisor_cueanexos
        return {'kind':'cues','cues':_codes(supervisor_cueanexos(user)),'label':'Supervisión'}
    if role in REGIONAL or categoria in ('regional','refestadistica'):
        from apps.bnhpersonas.monitoring.access import resolve_scope as monitoring_scope, scoped_offers
        scope=monitoring_scope(user)
        if scope.kind!='regional': raise PermissionDenied('No existe alcance regional válido para el usuario.')
        return {'kind':'cues','cues':_codes(scoped_offers(user).values_list('cueanexo',flat=True).distinct()),'label':'Regional'}
    raise PermissionDenied('Perfil sin acceso a Trayectorias: %s' % (role or 'no identificado'))
