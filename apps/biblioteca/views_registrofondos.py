from django.shortcuts import get_object_or_404, render, redirect
from django.http import JsonResponse
from django.urls import reverse, reverse_lazy
from django.views import View
from django.contrib import messages
from django.db.models import Func, F, Value
import re

from .models import DestinoFondos, RegistroDestinoFondos, GenerarInforme
from apps.consultasge.models import CapaUnicaOfertas


# =========================
# 🔹 REGISTRO CREATE
# =========================
class RegistroDestinoFondosView(View):
    template_name = 'biblioteca/pem/fondos/registro.html'

    def get_usuario_data(self, request):
        usuario = request.user.username
        usuario_limpio = re.sub(r'\D', '', usuario)

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

        cueanexo = cueanexo_qs.first()

        ultimo = GenerarInforme.objects.filter(
            cueanexo=cueanexo
        ).order_by('-annos', '-meses').first()

        return cueanexo, ultimo

    def get(self, request, *args, **kwargs):
        cueanexo, ultimo = self.get_usuario_data(request)

        context = {
            'cueanexo': cueanexo,
            'mes': ultimo.meses if ultimo else None,
            'anio': ultimo.annos if ultimo else None,
            'destino': DestinoFondos.objects.all(),
            'entity': 'Fondos',
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        cueanexo, ultimo = self.get_usuario_data(request)

        if not ultimo or not cueanexo:
            messages.error(request, "No se encontró información válida del usuario.")
            return redirect('bibliotecas:regfondos_list')

        mes = ultimo.meses
        anio = ultimo.annos

        registros = []

        for key in request.POST:
            if key.startswith('destino_'):
                index = key.split('_')[1]
                destino_id = request.POST.get(f'destino_{index}')
                desc = request.POST.get(f'descripcion_{index}')

                if destino_id and desc:
                    registros.append(
                        RegistroDestinoFondos(
                            cueanexo=cueanexo,
                            mes=mes,
                            anio=anio,
                            destino_id=destino_id,
                            descripcion=desc
                        )
                    )

        if not registros:
            messages.error(request, "Debe ingresar al menos un registro válido.")
            return redirect('bibliotecas:regfondos_list')

        # bulk insert (mejor rendimiento)
        RegistroDestinoFondos.objects.bulk_create(registros)

        messages.success(request, "Registros guardados correctamente.")
        return redirect('bibliotecas:regfondos_list')
    
# =========================
# 🔹 LIST VIEW (AJAX + HTML)
# =========================
class RegistroDestinoFondosListView(View):
    template_name = 'biblioteca/pem/fondos/registro_list.html'

    def get_usuario_data(self, request):
        usuario = request.user.username
        usuario_limpio = re.sub(r'\D', '', usuario)

        cueanexo = CapaUnicaOfertas.objects.annotate(
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
        ).values_list('cueanexo', flat=True).first()

        ultimo = GenerarInforme.objects.filter(
            cueanexo=cueanexo
        ).order_by('-annos', '-meses').first()

        return cueanexo, ultimo

    def get(self, request, *args, **kwargs):

        # ================= AJAX =================
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            cueanexo, ultimo = self.get_usuario_data(request)

            if not ultimo:
                return JsonResponse([], safe=False)

            registros = RegistroDestinoFondos.objects.filter(
                cueanexo=cueanexo,
                mes=ultimo.meses,
                anio=ultimo.annos
            )

            data = [
                {
                    "cueanexo": r.cueanexo,
                    "mes": r.mes,
                    "anio": r.anio,
                    "destino": str(r.destino),
                    "descripcion": r.descripcion,
                    "acciones": r.id
                }
                for r in registros
            ]

            return JsonResponse(data, safe=False)

        # ================= HTML =================
        context = {
            'create_url': reverse('bibliotecas:regfondos'),
            'list_url': reverse('bibliotecas:regfondos_list'),
            'title': 'Registro Destino Fondos',
            'entity': 'Fondos',
            'next_url': reverse_lazy('bibliotecas:bibliotecario_create'),
        }

        return render(request, self.template_name, context)


# =========================
# 🔹 DELETE
# =========================
class RegistroDestinoFondosDeleteView(View):
    def get(self, request, pk):
        obj = get_object_or_404(RegistroDestinoFondos, id=pk)
        obj.delete()
        return redirect('bibliotecas:regfondos_list')