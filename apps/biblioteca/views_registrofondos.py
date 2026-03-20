from django.shortcuts import get_object_or_404, render, redirect
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.views import View
from .models import DestinoFondos, RegistroDestinoFondos, GenerarInforme
from django.shortcuts import render, redirect
from django.contrib import messages  # Para usar mensajes en Django
from apps.consultasge.models import CapaUnicaOfertas
from django.db.models import Func, F, Value 
import re

#Registro Destino Fondos
class RegistroDestinoFondosView(View):
    template_name = 'biblioteca/pem/fondos/registro.html'

    def get(self, request, *args, **kwargs):
        usuario_logueado = self.request.user.username

        # Limpiar caracteres no numéricos del CUIT/CUIL
        usuario_limpio = re.sub(r'\D', '', usuario_logueado)

        # Obtener primer cueanexo del usuario
        cueanexo_qs = CapaUnicaOfertas.objects.annotate(
            cuit_limpio=Func(
                F('resploc_cuitcuil'),
                Value('-'),
                Value(''),
                function='REPLACE'
            )
        ).filter(
            cuit_limpio=usuario_limpio,
            oferta='Común - Servicios complementarios ',
            acronimo='BI'
        ).values_list('cueanexo', flat=True)  
             
        cueanexo = cueanexo_qs.first() if cueanexo_qs.exists() else None
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
            'destino': DestinoFondos.objects.all(),
            'entity': 'Fondos',
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        print('POST data:', request.POST)  # Verificar qué datos llegan
        usuario_logueado = self.request.user.username

        # Limpiar caracteres no numéricos del CUIT/CUIL
        usuario_limpio = re.sub(r'\D', '', usuario_logueado)

        # Obtener primer cueanexo del usuario
        cueanexo_qs = CapaUnicaOfertas.objects.annotate(
            cuit_limpio=Func(
                F('resploc_cuitcuil'),
                Value('-'),
                Value(''),
                function='REPLACE'
            )
        ).filter(
            cuit_limpio=usuario_limpio,
            oferta='Común - Servicios complementarios ',
            acronimo='BI'
        ).values_list('cueanexo', flat=True)       
       
        cueanexo = cueanexo_qs.first() if cueanexo_qs.exists() else None
        
        ultimo_informe = GenerarInforme.objects.filter(cueanexo=cueanexo).order_by('-annos', '-meses').first()

        if not ultimo_informe:
            messages.error(request, 'No se encontró un informe válido para este usuario.')
            return redirect('bibliotecas:regfondos')  # Redirige nuevamente al formulario

        mes = ultimo_informe.meses
        anio = ultimo_informe.annos

        # Obtener los valores de destino y descripcion
        destinos = []
        descripciones = []

        for i in range(0, len(request.POST)//2):  # Iterar hasta el final de los datos del formulario
            destino_id = request.POST.get(f'destino_{i}')
            descripcion = request.POST.get(f'descripcion_{i}')
            
            if destino_id and descripcion:
                destinos.append(destino_id)
                descripciones.append(descripcion)

        # Verificar si hay al menos un destino y descripción
        if not destinos or not descripciones:
            messages.error(request, 'Debe agregar al menos una fila con destino y descripción.')
            return redirect('bibliotecas:regfondos')

        registros_creados = 0
        for destino_id, desc in zip(destinos, descripciones):
            try:
                destino_obj = DestinoFondos.objects.get(id=destino_id)
                # Crear un nuevo registro
                RegistroDestinoFondos.objects.create(
                    cueanexo=cueanexo,
                    mes=mes,
                    anio=anio,
                    destino=destino_obj,
                    descripcion=desc
                )
                registros_creados += 1
            except DestinoFondos.DoesNotExist:
                continue  # Si no se encuentra el destino, omite y sigue con los demás

        if registros_creados == 0:
            messages.error(request, 'No se guardaron registros válidos.')
            return redirect('bibliotecas:regfondos')  # Redirige nuevamente al formulario

        # Si todo ha ido bien, redirigimos al usuario
        return redirect('bibliotecas:regfondos_list')



#Listar Registro Destino Fondos
class RegistroDestinoFondosListView(View):
    template_name = 'biblioteca/pem/fondos/registro_list.html'

    def get(self, request, *args, **kwargs):
        # 🔹 Obtener usuario logueado correctamente
        usuario_logueado = self.request.user.username  
        usuario_limpio = re.sub(r'\D', '', usuario_logueado)
        print("Usuario logueado:", usuario_logueado)  # Debug: Verificar el usuario logueado
        
        # 🔹 Obtener todos los cueanexos que cumplan la condición
        cueanexos_qs = CapaUnicaOfertas.objects.annotate(
            cuit_limpio=Func(
                F('resploc_cuitcuil'),
                Value('-'),
                Value(''),
                function='REPLACE'
            )
        ).filter(
            cuit_limpio=usuario_limpio,
            oferta='Común - Servicios complementarios ',
            acronimo='BI'
        ).values_list('cueanexo', flat=True)
        
        cueanexos = list(cueanexos_qs)
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':  # Verifica si es una petición AJAX
            cueanexo = cueanexos[0] if cueanexos else None
            ultimo_informe = GenerarInforme.objects.filter(cueanexo=cueanexo).order_by('-annos', '-meses').first()

            if not ultimo_informe:
                messages.error(request, 'No se encontró un informe válido para este usuario.')
                return redirect('bibliotecas:regfondos')

            mes = ultimo_informe.meses
            anio = ultimo_informe.annos
            registros = RegistroDestinoFondos.objects.filter(cueanexo=cueanexo, mes=mes, anio=anio)

            # Convierte cada registro a JSON y agrega un campo 'acciones' con el id
            data = []
            for registro in registros:
                registro_json = registro.toJSON()  # Convierte el registro a JSON
                registro_json['acciones'] = registro.id  # Agrega el campo 'acciones' con el id
                data.append(registro_json)

            return JsonResponse(data, safe=False)  # Devuelve los datos como JSON


        context = {
            'create_url': reverse('bibliotecas:regfondos'),  # URL para el botón de nuevo registro
            'list_url': reverse('bibliotecas:regfondos_list'),
            'title': 'Registro Destino Fondos',
            'hide_lock_button': False, 
            'generar_pdf_button' : True,
            'entity': 'Fondos',
            'next_url':reverse_lazy('bibliotecas:bibliotecario_create'),
            
        }            
        
        return render(request, self.template_name, context)
    

# Eliminar Registro Destino Fondos
class RegistroDestinoFondosDeleteView(View):
    def get(self, request, *args, **kwargs):
        # Obtener el objeto a eliminar
        registro_id = kwargs.get('pk')
        registros = get_object_or_404(RegistroDestinoFondos, id=registro_id)

        # Eliminar el objeto
        registros.delete()

        return redirect('bibliotecas:regfondos_list')  # Redirige al listado de planillas anexas