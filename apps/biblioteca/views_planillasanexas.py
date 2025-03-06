from django.shortcuts import get_object_or_404, render, redirect
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.views import View
from .models import PlanillasAnexas, ServiciosMatBiblio, GenerarInforme

#Cargar Planillas Anexas
class PlanillasAnexasView(View):
    template_name = 'biblioteca/pem/anexas/planillas_anexas.html'

    def get(self, request, *args, **kwargs):
        cueanexo = request.user.username
        ultimo_informe = GenerarInforme.objects.filter(cueanexo=cueanexo).order_by('-annos', '-meses').first()
        
        if ultimo_informe:
            mes = ultimo_informe.meses
            anio = ultimo_informe.annos
        else:
            mes = "No disponible"
            anio = "No disponible"

        context = {
            'cueanexo': cueanexo,
            'mes': mes,
            'anio': anio,
            'servicios': ServiciosMatBiblio.objects.filter(cod_servicio__gt=710),
            'entity': 'Anexas'
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        cueanexo = request.user.username
        ultimo_informe = GenerarInforme.objects.filter(cueanexo=cueanexo).order_by('-annos', '-meses').first()

        if not ultimo_informe:
            return JsonResponse({'error': 'No se encontró un informe válido para este usuario.'}, status=400)

        mes = ultimo_informe.meses
        anio = ultimo_informe.annos
        servicios = request.POST.getlist('servicio')
        cantidades = request.POST.getlist('cantidad')

        if not servicios or not cantidades:
            return JsonResponse({'error': 'Debe agregar al menos una fila'}, status=400)

        registros_creados = 0
        for servicio_id, cantidad in zip(servicios, cantidades):
            if cantidad.isdigit() and int(cantidad) > 0:  # Validar cantidad
                try:
                    servicio = ServiciosMatBiblio.objects.get(id=servicio_id)
                    PlanillasAnexas.objects.create(
                        cueanexo=cueanexo,
                        mes=mes,
                        anio=anio,
                        servicio=servicio,
                        cantidad=int(cantidad)
                    )
                    registros_creados += 1
                except ServiciosMatBiblio.DoesNotExist:
                    continue  # Si el servicio no existe, se omite y sigue con los demás.

        if registros_creados == 0:
            return JsonResponse({'error': 'No se guardaron registros válidos.'}, status=400)

        return redirect('bibliotecas:anexas_list')

#Listar Planillas Anexas
class PlanillasAnexasListView(View):
    template_name = 'biblioteca/pem/anexas/planillas_anexas_list.html'

    def get(self, request, *args, **kwargs):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':  # Verifica si es una petición AJAX
            cueanexo = request.user.username
            ultimo_informe = GenerarInforme.objects.filter(cueanexo=cueanexo).order_by('-annos', '-meses').first()

            if not ultimo_informe:
                return JsonResponse({'error': 'No se encontró un informe válido para este usuario.'}, status=400)

            mes = ultimo_informe.meses
            anio = ultimo_informe.annos
            planillas = PlanillasAnexas.objects.filter(cueanexo=cueanexo, mes=mes, anio=anio)

            data = [planilla.toJSON() for planilla in planillas]  # Convierte cada planilla a JSON
            
            return JsonResponse(data, safe=False)            

        context = {
            'create_url': reverse('bibliotecas:plan_anexas'),  # URL para el botón de nuevo registro
            'list_url': reverse('bibliotecas:anexas_list'),
            'title': 'Planillas Anexas',
            'hide_lock_button': True, 
            'generar_pdf_button' : False,
            'entity': 'Anexas',
            'generar_pdf_url': reverse_lazy('bibliotecas:generar_pdf'), 
            
        }            
        
        return render(request, self.template_name, context)
    
#Actualizar Planillas Anexas
class PlanillasAnexasUpdateView(View):
    template_name = 'biblioteca/pem/anexas/planillas_anexas.html'  # Crea este template

    def get(self, request, *args, **kwargs):
        # Obtener el objeto que se desea editar
        planilla_id = kwargs.get('pk')
        planilla = get_object_or_404(PlanillasAnexas, id=planilla_id)
        
        # Obtener los servicios disponibles
        servicios = ServiciosMatBiblio.objects.filter(cod_servicio__gt=710)
        
        # Crear el contexto para el formulario de edición
        context = {
            'planilla': planilla,
            'servicios': servicios,
            'entity': 'Anexas',
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        # Obtener el objeto a actualizar
        planilla_id = kwargs.get('pk')
        planilla = get_object_or_404(PlanillasAnexas, id=planilla_id)

        # Obtener los datos del formulario
        servicio_id = request.POST.get('servicio')
        cantidad = request.POST.get('cantidad')

        # Validar y actualizar
        if not servicio_id or not cantidad.isdigit() or int(cantidad) <= 0:
            return JsonResponse({'error': 'Datos inválidos para la actualización.'}, status=400)

        try:
            servicio = ServiciosMatBiblio.objects.get(id=servicio_id)
            planilla.servicio = servicio
            planilla.cantidad = int(cantidad)
            planilla.save()
        except ServiciosMatBiblio.DoesNotExist:
            return JsonResponse({'error': 'Servicio no encontrado.'}, status=400)

        return redirect('bibliotecas:anexas_list')  # Redirige al listado de planillas anexas

#Eliminar Planillas Anexas
class PlanillasAnexasDeleteView(View):
    def get(self, request, *args, **kwargs):
        # Obtener el objeto a eliminar
        planilla_id = kwargs.get('pk')
        planilla = get_object_or_404(PlanillasAnexas, id=planilla_id)

        # Eliminar el objeto
        planilla.delete()

        return redirect('bibliotecas:anexas_list')  # Redirige al listado de planillas anexas