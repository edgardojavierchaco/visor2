from django.http import JsonResponse
from django.core.mail import send_mail, BadHeaderError
from django.conf import settings
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST
from .forms import ConsultaForm
from .models import Consulta

def consulta_form_view(request):
    form = ConsultaForm()
    return render(request, 'consultas/consulta_form.html', {'form': form})

@require_POST
def enviar_consulta_ajax(request):
    form = ConsultaForm(request.POST)
    if form.is_valid():
        consulta = form.save()

        try:
            # Enviar correo
            send_mail(
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
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=['sgechaco@gmail.com'],  # usar Gmail con app password
                fail_silently=False,
            )
        except BadHeaderError:
            return JsonResponse({'status': 'error', 'message': 'Error en el encabezado del correo.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Error al enviar correo: {str(e)}'})

        return JsonResponse({'status': 'success', 'message': 'La consulta se envió correctamente.'})
    else:
        return JsonResponse({'status': 'error', 'message': 'Por favor revisa los errores en el formulario.', 'errors': form.errors})


def monitoreo_consultas(request):
    consultas = Consulta.objects.all().order_by('-fecha')
    return render(request, 'consultas/monitoreo_consultas.html', {'consultas': consultas})

def actualizar_estado(request, consulta_id):
    if request.method == 'POST':
        consulta = get_object_or_404(Consulta, id=consulta_id)
        if consulta.estado == 'Pendiente':
            consulta.estado = 'Solucionado'
            consulta.save()
            return JsonResponse({'status': 'success', 'nuevo_estado': consulta.estado})
        return JsonResponse({'status': 'error', 'message': 'El estado ya es Solucionado'})
    return JsonResponse({'status': 'error', 'message': 'Método no permitido'})