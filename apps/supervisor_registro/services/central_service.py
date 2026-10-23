"""Administración central: operaciones explícitas, atómicas y sin borrado físico."""
from django.core.exceptions import ValidationError
from django.db import transaction
from apps.consultasge.models_padron import CapaUnicaOfertas
from ..models import (SupervisorRegional, SupervisorRegionalNivel, SupervisorRegionalOferta)
from ..audit.services import log_change
from ..audit.utils import snapshot

MAX_BATCH = 200

def buscar_ofertas(sr, texto='', limit=80):
    """La oferta debe pertenecer a regional y competencia activa de ESA regional."""
    niveles = list(SupervisorRegionalNivel.objects.filter(supervisor_regional=sr, activo=True)
                    .values_list('nivel__nombre', flat=True))
    if not niveles:
        return []
    qs = CapaUnicaOfertas.objects.filter(region_loc=sr.region.nombre, oferta__in=niveles)
    if texto:
        from django.db.models import Q
        qs = qs.filter(Q(cueanexo__icontains=texto) | Q(nom_est__icontains=texto))
    return list(qs.values('cueanexo','nom_est','oferta','acronimo').distinct().order_by('cueanexo','oferta')[:limit])

def validar_seleccion(sr, claves):
    if len(claves)>MAX_BATCH:
        raise ValidationError('Máximo 200 ofertas por operación.')
    if len(set(claves)) != len(claves):
        raise ValidationError('La selección contiene duplicados.')
    niveles = list(SupervisorRegionalNivel.objects.filter(supervisor_regional=sr, activo=True)
                    .values_list('nivel__nombre',flat=True))
    if not niveles and claves:
        raise ValidationError('Primero debe asignar niveles/ofertas habilitadas a esta regional.')
    # Filtrado por región + oferta (misma asignación), nunca se confía en la UI.
    validos = {}
    solicitadas=set(claves)
    for row in CapaUnicaOfertas.objects.filter(region_loc=sr.region.nombre, oferta__in=niveles).values(
        'cueanexo','nom_est','oferta','acronimo').iterator(chunk_size=1000):
        key=(str(row['cueanexo']).strip(),str(row['oferta']).strip())
        if key in solicitadas:
            validos[key]=row
            if len(validos)==len(claves):
                break
    faltantes=set(claves)-set(validos)
    if faltantes:
        raise ValidationError('Hay CUEANEXO/ofertas que no corresponden a la regional y competencia seleccionadas.')
    return validos

@transaction.atomic
def aplicar_cambios(request, sr_id, agregar, quitar, confirmar=False):
    sr=SupervisorRegional.objects.select_for_update().select_related('region').get(pk=sr_id,activo=True)
    agregar=[(str(x['cueanexo']).strip(),str(x['oferta']).strip()) for x in agregar]
    quitar=[int(x) for x in quitar]
    if len(set(quitar))!=len(quitar) or len(quitar)>MAX_BATCH:
        raise ValidationError('Selección de bajas duplicada o demasiado grande.')
    datos=validar_seleccion(sr,agregar)
    existentes=list(SupervisorRegionalOferta.objects.select_for_update().filter(supervisor_regional=sr,id__in=quitar,activo=True))
    if len(existentes)!=len(quitar):
        raise ValidationError('Las asignaciones a retirar no corresponden a esta regional o ya están inactivas.')
    if set(agregar) & {(str(o.cueanexo),o.oferta) for o in existentes}:
        raise ValidationError('Una misma oferta no puede agregarse y retirarse simultáneamente.')
    plan={'agregar':[{'cueanexo':x[0],'oferta':x[1],'nom_est':datos[x].get('nom_est','')} for x in agregar],
          'quitar':[{'id':o.pk,'cueanexo':o.cueanexo,'oferta':o.oferta} for o in existentes]}
    if not confirmar:
        return {'aplicado':False,'plan':plan}
    hechos=[]
    for key in agregar:
        row=datos[key]
        obj,created=SupervisorRegionalOferta.objects.get_or_create(
            supervisor_regional=sr,cueanexo=key[0],oferta=key[1],
            defaults={'nom_est':row.get('nom_est') or '', 'acronimo':row.get('acronimo') or None,'activo':True})
        before=None if created else snapshot(obj)
        if not created:
            obj.activo=True
            obj.nom_est=row.get('nom_est') or obj.nom_est
            obj.acronimo=row.get('acronimo') or obj.acronimo
            obj.save(update_fields=['activo','nom_est','acronimo'])
        log_change(user=request.user,action='CREATE' if created else 'UPDATE',instance=obj,before=before,
                   after=snapshot(obj),request=request,extra={'origen':'SIGSE_CENTRAL','regional_id':sr.pk})
        hechos.append(obj.pk)
    for obj in existentes:
        before=snapshot(obj)
        obj.activo=False
        obj.save(update_fields=['activo'])
        log_change(user=request.user,action='DELETE',instance=obj,before=before,after=snapshot(obj),
                   request=request,extra={'origen':'SIGSE_CENTRAL','baja_logica':True})
    return {'aplicado':True,'plan':plan,'ids_agregados':hechos}
