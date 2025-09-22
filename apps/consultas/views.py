from django.http import JsonResponse
from django.core.mail import send_mail, BadHeaderError, EmailMessage, get_connection
from django.conf import settings
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST
from django.utils import timezone
from .forms import ConsultaForm, ConsultaRenpeForm
from .models import Consulta, ConsultaRenpe
from apps.usuarios.models import UsuariosVisualizador
import datetime
from django.http import HttpResponse
from openpyxl import Workbook
from django.utils.dateparse import parse_date


def enviar_email(subject, message, from_user, password, recipient_list):
    connection = get_connection(
        backend=settings.EMAIL_BACKEND,
        host=settings.EMAIL_HOST,
        port=settings.EMAIL_PORT,
        username=from_user,
        password=password,
        use_tls=settings.EMAIL_USE_TLS
    )
    email = EmailMessage(subject, message, from_user, recipient_list, connection=connection)
    email.send()

def consulta_form_view(request):
    form = ConsultaForm()
    return render(request, 'consultas/consulta_form.html', {'form': form})

def consulta_renpe_form_view(request):
    form = ConsultaRenpeForm()
    return render(request, 'consultas/consulta_renpe_form.html', {'form': form})

@require_POST
def enviar_consulta_ajax(request):
    form = ConsultaForm(request.POST)
    if form.is_valid():
        consulta = form.save()
        try:
            enviar_email(
                subject=f"Nueva consulta de {consulta.apellido_nombre} - {consulta.cueanexo}",
                message=(
                    f"Nombre: {consulta.apellido_nombre}\n"
                    f"CUEANEXO: {consulta.cueanexo}\n"
                    f"Regional: {consulta.regional}\n"
                    f"Nivel: {consulta.nivel_modalidad}\n"
                    f"Módulo: {consulta.sge_modulo}\n"
                    f"Email: {consulta.email}\n\n"
                    f"Mensaje:\n{consulta.mensaje}"
                ),
                from_user=settings.EMAIL_HOST_USER1,
                password=settings.EMAIL_HOST_PASSWORD1,
                recipient_list=['sgechaco@gmail.com']
            )
        except BadHeaderError:
            return JsonResponse({'status': 'error', 'message': 'Error en el encabezado del correo.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Error al enviar correo: {str(e)}'})
        return JsonResponse({'status': 'success', 'message': 'La consulta se envió correctamente.'})
    return JsonResponse({'status': 'error', 'message': 'Por favor revisa los errores en el formulario.', 'errors': form.errors})

@require_POST
def enviar_consulta_renpe_ajax(request):
    form = ConsultaRenpeForm(request.POST)
    if form.is_valid():
        consulta = form.save()
        try:
            enviar_email(
                subject=f"Nueva consulta RENPE de {consulta.apellido_nombre} - {consulta.cueanexo}",
                message=(
                    f"Nombre: {consulta.apellido_nombre}\n"
                    f"CUEANEXO: {consulta.cueanexo}\n"
                    f"Regional: {consulta.regional}\n"
                    f"Módulo: {consulta.renpe_modulo}\n"
                    f"Email: {consulta.email}\n\n"
                    f"Mensaje:\n{consulta.mensaje}"
                ),
                from_user=settings.EMAIL_HOST_USER2,
                password=settings.EMAIL_HOST_PASSWORD2,
                recipient_list=['renpechaco@gmail.com']
            )
        except BadHeaderError:
            return JsonResponse({'status': 'error', 'message': 'Error en el encabezado del correo.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Error al enviar correo: {str(e)}'})
        return JsonResponse({'status': 'success', 'message': 'La consulta se envió correctamente.'})
    return JsonResponse({'status': 'error', 'message': 'Por favor revisa los errores en el formulario.', 'errors': form.errors})


def monitoreo_consultas(request):
    consultas = Consulta.objects.all().order_by('-fecha')
    return render(request, 'consultas/monitoreo_consultas.html', {'consultas': consultas})

def actualizar_estado(request, consulta_id):
    if request.method == 'POST':
        consulta = get_object_or_404(Consulta, id=consulta_id)
        
        # Obtenemos usuario desde la tabla personalizada
        usuario_logueado = None
        if request.user.is_authenticated:
            usuario_logueado = UsuariosVisualizador.objects.filter(
                username=request.user.username
            ).first()
            
        if consulta.estado == 'Pendiente':
            consulta.estado = 'Solucionado'
            consulta.estado_usuario = f"{usuario_logueado.apellido}, {usuario_logueado.nombres}" if usuario_logueado else "Anónimo"
            consulta.estado_fecha = timezone.now()
            consulta.save()
            return JsonResponse({
                'status': 'success',
                'nuevo_estado': consulta.estado,
                'usuario': consulta.estado_usuario,
                'fecha': consulta.estado_fecha.strftime('%d/%m/%Y %H:%M')
            })
        return JsonResponse({'status': 'error', 'message': 'El estado ya es Solucionado'})
    return JsonResponse({'status': 'error', 'message': 'Método no permitido'})


def exportar_excel(request):
    desde = request.GET.get("desde")
    hasta = request.GET.get("hasta")

    try:
        fecha_desde = parse_date(desde)
        fecha_hasta = parse_date(hasta)
        # incluir todo el día final
        fecha_hasta = fecha_hasta + datetime.timedelta(days=1)
    except:
        return HttpResponse("Fechas inválidas", status=400)

    # Filtrar consultas por rango
    consultas = Consulta.objects.filter(fecha__range=[fecha_desde, fecha_hasta])

    # Crear workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Consultas"

    # Encabezados
    columnas = ["Fecha", "CUEANEXO", "Nombre", "Regional", "Nivel", "Módulo", "Email", "Mensaje", "Estado"]
    ws.append(columnas)

    # Filas
    for c in consultas:
        ws.append([
            c.fecha.strftime("%d/%m/%Y %H:%M"),
            c.cueanexo,
            c.apellido_nombre,
            c.regional,
            c.nivel_modalidad,
            c.sge_modulo,
            c.email,
            c.mensaje,
            c.estado,
        ])

    # Preparar respuesta HTTP
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response['Content-Disposition'] = f'attachment; filename=consultas_{desde}_a_{hasta}.xlsx'
    wb.save(response)
    return response


#################################################
#                       RENPE                   #
#################################################
def monitoreo_consultas_renpe(request):
    consultas_renpe = ConsultaRenpe.objects.all().order_by('-fecha')
    return render(request, 'consultas/monitoreo_consultas_renpe.html', {'consultas': consultas_renpe})

def actualizar_estado_renpe(request, consulta_id):
    if request.method == 'POST':
        consulta_renpe = get_object_or_404(ConsultaRenpe, id=consulta_id)
        
        # Obtenemos usuario desde la tabla personalizada
        usuario_logueado = None
        if request.user.is_authenticated:
            usuario_logueado = UsuariosVisualizador.objects.filter(
                username=request.user.username
            ).first()
            
        if consulta_renpe.estado == 'Pendiente':
            consulta_renpe.estado = 'Solucionado'
            consulta_renpe.estado_usuario = f"{usuario_logueado.apellido}, {usuario_logueado.nombres}" if usuario_logueado else "Anónimo"
            consulta_renpe.estado_fecha = timezone.now()
            consulta_renpe.save()
            return JsonResponse({
                'status': 'success',
                'nuevo_estado': consulta_renpe.estado,
                'usuario': consulta_renpe.estado_usuario,
                'fecha': consulta_renpe.estado_fecha.strftime('%d/%m/%Y %H:%M')
            })
        return JsonResponse({'status': 'error', 'message': 'El estado ya es Solucionado'})
    return JsonResponse({'status': 'error', 'message': 'Método no permitido'})


def exportar_excel_renpe(request):
    desde = request.GET.get("desde")
    hasta = request.GET.get("hasta")

    try:
        fecha_desde = parse_date(desde)
        fecha_hasta = parse_date(hasta)
        # incluir todo el día final
        fecha_hasta = fecha_hasta + datetime.timedelta(days=1)
    except:
        return HttpResponse("Fechas inválidas", status=400)

    # Filtrar consultas por rango
    consultas_renpe = ConsultaRenpe.objects.filter(fecha__range=[fecha_desde, fecha_hasta])

    # Crear workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Consultas"

    # Encabezados
    columnas = ["Fecha", "CUEANEXO", "Regional", "Módulo", "Apellido y Nombre", "Email", "Mensaje", "Estado"]
    ws.append(columnas)

    # Filas
    for c in consultas_renpe:
        ws.append([
            c.fecha.strftime("%d/%m/%Y %H:%M"),
            c.cueanexo,
            c.apellido_nombre,
            c.regional,
            c.renpe_modulo,
            c.email,
            c.mensaje,
            c.estado,
        ])

    # Preparar respuesta HTTP
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response['Content-Disposition'] = f'attachment; filename=consultas_{desde}_a_{hasta}.xlsx'
    wb.save(response)
    return response