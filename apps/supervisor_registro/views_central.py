import csv, io, json
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction, IntegrityError
from django.core.validators import validate_email
from apps.usuarios.models import UsuariosVisualizador
from django.views.decorators.http import require_GET, require_POST
from apps.supervisa2.models import Region, NivelModalidad, SituacionRevista
from .models import ABMSupervisores, SupervisorRegional, SupervisorRegionalOferta, SupervisorRegionalNivel, SupervisorSituacionRevista
from .services.permission_service import puede_administrar_supervisores
from .services.central_service import buscar_ofertas, aplicar_cambios
from .audit.models import AuditLog

def _deny(request):
    return None if puede_administrar_supervisores(request.user) else HttpResponseForbidden('Acceso exclusivo para el administrador central.')

@login_required
@require_GET
def inicio(request):
    denied=_deny(request)
    if denied:return denied
    return render(request,'supervisores/central/inicio.html',{
        'total':ABMSupervisores.objects.count(),
        'activos':ABMSupervisores.objects.filter(activo=True).count(),
        'regionales':SupervisorRegional.objects.filter(activo=True).count(),
        'ofertas':SupervisorRegionalOferta.objects.filter(activo=True).count(),
    })

@login_required
@require_GET
def listado(request):
    denied=_deny(request)
    if denied:return denied
    texto=request.GET.get('q','').strip()[:80]
    qs=ABMSupervisores.objects.select_related('usuario').order_by('usuario__apellido','usuario__nombres')
    if texto:
        qs=qs.filter(Q(usuario__apellido__icontains=texto)|Q(usuario__nombres__icontains=texto)|Q(usuario__username__icontains=texto))
    return render(request,'supervisores/central/listado.html',{'items':qs[:150], 'q':texto})

@login_required
@require_GET
def gestor(request, pk):
    denied=_deny(request)
    if denied:return denied
    s=get_object_or_404(ABMSupervisores.objects.select_related('usuario'),pk=pk)
    regionales=list(SupervisorRegional.objects.filter(supervisor=s,activo=True).select_related('region'))
    return render(request,'supervisores/central/gestor.html',{
        'supervisor':s,'regionales':regionales,
        'catalogo_regiones':Region.objects.all().order_by('nombre'),
        'catalogo_niveles':NivelModalidad.objects.all().order_by('nombre'),
        'catalogo_situaciones':SituacionRevista.objects.all().order_by('nombre'),
        'situaciones_actuales':SupervisorSituacionRevista.objects.filter(supervisor=s).select_related('situacion_revista').order_by('-fecha_desde'),
    })

@login_required
@require_GET
def detalle_asignacion(request, sr_id):
    denied=_deny(request)
    if denied:return denied
    sr=get_object_or_404(SupervisorRegional.objects.select_related('region'),pk=sr_id,activo=True)
    niveles=list(SupervisorRegionalNivel.objects.filter(supervisor_regional=sr,activo=True).values('nivel_id','nivel__nombre'))
    asignadas=list(SupervisorRegionalOferta.objects.filter(supervisor_regional=sr,activo=True).values('id','cueanexo','nom_est','oferta').order_by('cueanexo','oferta')[:1000])
    return JsonResponse({'ok':True,'regional':sr.region.nombre,'niveles':niveles,'asignadas':asignadas})

@login_required
@require_GET
def buscar_disponibles(request, sr_id):
    denied=_deny(request)
    if denied:return denied
    sr=get_object_or_404(SupervisorRegional.objects.select_related('region'),pk=sr_id,activo=True)
    texto=request.GET.get('q','').strip()[:70]
    if len(texto)<2:return JsonResponse({'ok':True,'resultados':[],'mensaje':'Escriba al menos dos caracteres.'})
    return JsonResponse({'ok':True,'resultados':buscar_ofertas(sr,texto)})

@login_required
@require_POST
def cambios_masivos(request, sr_id):
    denied=_deny(request)
    if denied:return denied
    try:
        payload=json.loads(request.body)
        if not isinstance(payload,dict):raise ValueError('Formato inválido')
        agregar=payload.get('agregar',[]); quitar=payload.get('quitar',[])
        if not isinstance(agregar,list) or not isinstance(quitar,list):raise ValueError('Las listas son obligatorias')
        if any(not isinstance(x,dict) or not {'cueanexo','oferta'}<=x.keys() for x in agregar):raise ValueError('Oferta inválida')
        result=aplicar_cambios(request,sr_id,agregar,quitar,confirmar=payload.get('confirmar') is True)
        return JsonResponse({'ok':True,**result})
    except (ValidationError,ValueError,TypeError,KeyError) as exc:
        message='; '.join(exc.messages) if isinstance(exc,ValidationError) else str(exc)
        return JsonResponse({'ok':False,'error':message},status=400)

@login_required
@require_GET
def auditoria(request):
    denied=_deny(request)
    if denied:return denied
    qs=AuditLog.objects.select_related('user').order_by('-timestamp')[:200]
    return render(request,'supervisores/central/auditoria.html',{'logs':qs})

@login_required
@require_GET
def calidad(request):
    denied=_deny(request)
    if denied:return denied
    sin_niveles=SupervisorRegional.objects.filter(activo=True).exclude(niveles__activo=True).distinct()
    sin_ofertas=SupervisorRegional.objects.filter(activo=True).exclude(ofertas__activo=True).distinct()
    duplicados=(SupervisorRegionalOferta.objects.filter(activo=True).values('cueanexo','oferta')
                .annotate(n=Count('supervisor_regional__supervisor_id',distinct=True)).filter(n__gt=1).order_by('-n')[:100])
    return render(request,'supervisores/central/calidad.html',{'sin_niveles':sin_niveles[:100],
        'sin_ofertas':sin_ofertas[:100],'duplicados':duplicados})

@login_required
@require_GET
def exportar_asignaciones(request):
    denied=_deny(request)
    if denied:return denied
    response=HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition']='attachment; filename="sigse_asignaciones.csv"'
    response.write('\ufeff')
    writer=csv.writer(response,delimiter=';')
    writer.writerow(['CUIL','Apellido','Nombres','Regional','CUEANEXO','Establecimiento','Oferta','Activa'])
    qs=SupervisorRegionalOferta.objects.filter(activo=True,supervisor_regional__activo=True).select_related(
        'supervisor_regional__supervisor__usuario','supervisor_regional__region')
    for obj in qs.iterator(chunk_size=500):
        r=obj.supervisor_regional; u=r.supervisor.usuario
        writer.writerow([u.username,u.apellido,u.nombres,r.region.nombre,obj.cueanexo,obj.nom_est,obj.oferta,'SI'])
    return response


def _contacto_institucional(usuario):
    """Lee únicamente campos reales del modelo institucional, sin suponer su esquema.

    No hace consultas adicionales ni modifica el usuario.
    """
    campos = {f.name for f in usuario._meta.concrete_fields}
    def primero(nombres):
        for nombre in nombres:
            if nombre in campos:
                valor = getattr(usuario, nombre, None)
                if valor is not None and str(valor).strip():
                    return str(valor).strip()
        return ''
    return {
        'email': primero(('email', 'correo_electronico', 'correo', 'mail', 'e_mail')),
        'telefono': primero(('telefono', 'telefono_celular', 'celular', 'telefono_contacto', 'telefono_movil', 'tel', 'movil', 'whatsapp')),
    }


@login_required
@require_GET
def buscar_usuario_alta(request):
    """Resuelve el CUIL sobre el usuario institucional, sin alterar ningún registro."""
    denied = _deny(request)
    if denied: return denied
    cuil = request.GET.get('cuil', '').strip()
    if not (cuil.isdigit() and len(cuil) == 11):
        return JsonResponse({'ok': False, 'error': 'Ingresá los 11 dígitos del CUIL.'}, status=400)
    usuario = UsuariosVisualizador.objects.filter(username=cuil).first()
    if not usuario:
        return JsonResponse({'ok': True, 'existe_usuario': False, 'mensaje': 'El CUIL no corresponde a un usuario registrado en Visor Educativo.'})
    existente = ABMSupervisores.objects.filter(usuario=usuario).first()
    return JsonResponse({'ok': True, 'existe_usuario': True,
        'apellido': usuario.apellido or '', 'nombres': usuario.nombres or '',
        **_contacto_institucional(usuario),
        'supervisor_id': existente.pk if existente else None,
        'activo': existente.activo if existente else None})


@login_required
def alta_supervisor(request):
    """Alta exclusivamente centralizada; no crea usuarios ni altera supervisores existentes."""
    denied = _deny(request)
    if denied: return denied
    if request.method == 'POST':
        cuil = request.POST.get('cuil', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        email = request.POST.get('email', '').strip()
        if not cuil.isdigit() or len(cuil) != 11:
            messages.error(request, 'El CUIL debe contener exactamente 11 dígitos.')
        else:
            try:
                if email: validate_email(email)
                usuario = UsuariosVisualizador.objects.filter(username=cuil).first()
                if usuario is None:
                    messages.error(request, 'No existe ese usuario en Visor Educativo. No se creó ningún registro.')
                else:
                    existente = ABMSupervisores.objects.filter(usuario=usuario).first()
                    if existente:
                        messages.info(request, 'Ya existe una ficha de supervisor para este CUIL; no se duplicaron datos.')
                        return redirect('supervisor_registro:central_gestor', pk=existente.pk)
                    with transaction.atomic():
                        contacto = _contacto_institucional(usuario)
                        obj = ABMSupervisores(usuario=usuario, telefono=telefono or contacto['telefono'] or None,
                                             email=email or contacto['email'] or None)
                        obj.full_clean()
                        obj.save()
                    messages.success(request, 'Supervisor registrado. Ahora podés gestionar sus asignaciones.')
                    return redirect('supervisor_registro:central_gestor', pk=obj.pk)
            except (ValidationError, ValueError) as exc:
                msg = '; '.join(exc.messages) if isinstance(exc, ValidationError) else str(exc)
                messages.error(request, msg)
            except IntegrityError:
                messages.error(request, 'El supervisor ya fue registrado en otra operación. Volvé a buscarlo.')
    return render(request, 'supervisores/central/alta.html', {'cuil': request.POST.get('cuil','') if request.method == 'POST' else '',
        'telefono':request.POST.get('telefono','') if request.method == 'POST' else '',
        'email':request.POST.get('email','') if request.method == 'POST' else ''})


# SIGSE · Gestión integral centralizada, sin bajas físicas.
from django.views.decorators.http import require_http_methods
from .audit.services import log_change
from .audit.utils import snapshot
from datetime import date

def _redir_ficha(pk):
    return redirect('supervisor_registro:central_gestor', pk=pk)

@login_required
@require_POST
def agregar_regional(request, pk):
    denied=_deny(request)
    if denied: return denied
    supervisor=get_object_or_404(ABMSupervisores, pk=pk)
    region=get_object_or_404(Region, pk=request.POST.get('region_id'))
    with transaction.atomic():
        regional, creada=SupervisorRegional.objects.select_for_update().get_or_create(supervisor=supervisor, region=region)
        antes=None if creada else snapshot(regional)
        if not regional.activo:
            regional.activo=True;regional.save(update_fields=['activo'])
        if creada or antes.get('activo') is False:
            log_change(user=request.user,action='CREATE' if creada else 'UPDATE',instance=regional,before=antes,after=snapshot(regional),request=request,extra={'origen':'SIGSE_CENTRAL','operacion':'ampliacion_regional'})
            messages.success(request,'Regional incorporada sin modificar las existentes.')
        else: messages.info(request,'La regional ya estaba asignada.')
    return _redir_ficha(pk)

@login_required
@require_POST
def agregar_competencia(request, pk):
    denied=_deny(request)
    if denied:return denied
    with transaction.atomic():
        regional=get_object_or_404(SupervisorRegional.objects.select_for_update(),pk=request.POST.get('regional_id'),supervisor_id=pk,activo=True)
        nivel=get_object_or_404(NivelModalidad,pk=request.POST.get('nivel_id'))
        relacion, creada=SupervisorRegionalNivel.objects.select_for_update().get_or_create(supervisor_regional=regional,nivel=nivel)
        antes=None if creada else snapshot(relacion)
        if not relacion.activo:
            relacion.activo=True;relacion.save(update_fields=['activo'])
        if creada or antes.get('activo') is False:
            log_change(user=request.user,action='CREATE' if creada else 'UPDATE',instance=relacion,before=antes,after=snapshot(relacion),request=request,extra={'origen':'SIGSE_CENTRAL','operacion':'ampliacion_competencia'})
            messages.success(request,'Competencia incorporada. Ahora se pueden asignar establecimientos de esa oferta.')
        else: messages.info(request,'La competencia ya estaba habilitada para esa regional.')
    return _redir_ficha(pk)

@login_required
@require_POST
def finalizar_competencia(request, pk, nivel_id):
    denied=_deny(request)
    if denied:return denied
    with transaction.atomic():
        relacion=get_object_or_404(SupervisorRegionalNivel.objects.select_for_update(),pk=nivel_id,supervisor_regional__supervisor_id=pk,activo=True)
        # No desactivar competencias que mantienen establecimientos activos de esa oferta.
        if SupervisorRegionalOferta.objects.filter(supervisor_regional=relacion.supervisor_regional,oferta=relacion.nivel.nombre,activo=True).exists():
            messages.error(request,'Primero finalizá explícitamente los establecimientos asignados a esta competencia.')
            return _redir_ficha(pk)
        antes=snapshot(relacion);relacion.activo=False;relacion.save(update_fields=['activo'])
        log_change(user=request.user,action='UPDATE',instance=relacion,before=antes,after=snapshot(relacion),request=request,extra={'origen':'SIGSE_CENTRAL','operacion':'finalizar_competencia'})
    messages.success(request,'Competencia finalizada; no se borró el registro.')
    return _redir_ficha(pk)

@login_required
@require_POST
def finalizar_regional(request, pk, sr_id):
    denied=_deny(request)
    if denied:return denied
    with transaction.atomic():
        regional=get_object_or_404(SupervisorRegional.objects.select_for_update(),pk=sr_id,supervisor_id=pk,activo=True)
        if SupervisorRegionalOferta.objects.filter(supervisor_regional=regional,activo=True).exists() or SupervisorRegionalNivel.objects.filter(supervisor_regional=regional,activo=True).exists():
            messages.error(request,'Primero finalizá las ofertas y competencias de la regional. No se realizaron cambios.')
            return _redir_ficha(pk)
        antes=snapshot(regional);regional.activo=False;regional.save(update_fields=['activo'])
        log_change(user=request.user,action='UPDATE',instance=regional,before=antes,after=snapshot(regional),request=request,extra={'origen':'SIGSE_CENTRAL','operacion':'finalizar_regional'})
    messages.success(request,'Regional finalizada conservando su historial.')
    return _redir_ficha(pk)

@login_required
@require_POST
def crear_situacion(request, pk):
    denied=_deny(request)
    if denied:return denied
    supervisor=get_object_or_404(ABMSupervisores,pk=pk)
    situacion=get_object_or_404(SituacionRevista,pk=request.POST.get('situacion_id'))
    desde=request.POST.get('fecha_desde','')
    hasta=request.POST.get('fecha_hasta','')
    try:
        desde=date.fromisoformat(desde)
        hasta=date.fromisoformat(hasta) if hasta else None
        if hasta and hasta < desde:raise ValueError('La fecha hasta no puede ser anterior a desde.')
        with transaction.atomic():
            obj=SupervisorSituacionRevista(supervisor=supervisor,situacion_revista=situacion,fecha_desde=desde,fecha_hasta=hasta)
            obj.full_clean();obj.save()
            log_change(user=request.user,action='CREATE',instance=obj,before=None,after=snapshot(obj),request=request,extra={'origen':'SIGSE_CENTRAL'})
        messages.success(request,'Situación de revista registrada.')
    except (ValueError,ValidationError) as exc:messages.error(request,str(exc))
    return _redir_ficha(pk)

@login_required
@require_POST
def editar_situacion(request, pk, situacion_id):
    denied=_deny(request)
    if denied:return denied
    try:
        desde=date.fromisoformat(request.POST.get('fecha_desde',''))
        hasta=date.fromisoformat(request.POST['fecha_hasta']) if request.POST.get('fecha_hasta') else None
        if hasta and hasta < desde:raise ValueError('Fecha de finalización incorrecta.')
        with transaction.atomic():
            obj=get_object_or_404(SupervisorSituacionRevista.objects.select_for_update(),pk=situacion_id,supervisor_id=pk)
            antes=snapshot(obj)
            obj.fecha_desde=desde;obj.fecha_hasta=hasta
            obj.full_clean();obj.save(update_fields=['fecha_desde','fecha_hasta'])
            log_change(user=request.user,action='UPDATE',instance=obj,before=antes,after=snapshot(obj),request=request,extra={'origen':'SIGSE_CENTRAL'})
        messages.success(request,'Fechas actualizadas y auditadas.')
    except (ValueError,ValidationError) as exc: messages.error(request,str(exc))
    return _redir_ficha(pk)

@login_required
@require_POST
def finalizar_situacion(request, pk, situacion_id):
    denied=_deny(request)
    if denied:return denied
    with transaction.atomic():
        obj=get_object_or_404(SupervisorSituacionRevista.objects.select_for_update(),pk=situacion_id,supervisor_id=pk,activo=True)
        antes=snapshot(obj);obj.activo=False;obj.save(update_fields=['activo'])
        log_change(user=request.user,action='UPDATE',instance=obj,before=antes,after=snapshot(obj),request=request,extra={'origen':'SIGSE_CENTRAL','baja_logica':True})
    messages.success(request,'Situación finalizada sin eliminar información.')
    return _redir_ficha(pk)

@login_required
@require_POST
def actualizar_contacto(request, pk):
    denied=_deny(request)
    if denied:return denied
    with transaction.atomic():
        supervisor=get_object_or_404(ABMSupervisores.objects.select_for_update(),pk=pk)
        antes=snapshot(supervisor)
        supervisor.email=request.POST.get('email','').strip() or None
        supervisor.telefono=request.POST.get('telefono','').strip() or None
        try: supervisor.full_clean()
        except ValidationError as exc:
            messages.error(request,'Datos de contacto no válidos: '+str(exc))
            return _redir_ficha(pk)
        supervisor.save(update_fields=['email','telefono','fecha_modificacion'])
        log_change(user=request.user,action='UPDATE',instance=supervisor,before=antes,after=snapshot(supervisor),request=request,extra={'origen':'SIGSE_CENTRAL','operacion':'contacto'})
    messages.success(request,'Contacto actualizado, sin modificar el usuario institucional.')
    return _redir_ficha(pk)
