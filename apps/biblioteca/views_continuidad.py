from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from apps.consultasge.models import CapaUnicaOfertas
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F, Func, Value
import re

from .models import (
    GenerarInforme,
    MaterialBibliografico,
    ServicioReferencia,
    ServicioReferenciaVirtual,
    ServicioPrestamo,
    InformePedagogico,
    AsistenciaUsuarios,
    InstitucionesPrestaServicios,
    ProcesosTecnicos,
    Aguapey,
    DestinoFondos,
    BibliotecariosCue
)


class ContinuarCargaView(LoginRequiredMixin, View):

    def get_cueanexo(self, request):
        usuario = request.user.username
        usuario_limpio = re.sub(r'\D', '', usuario)

        return CapaUnicaOfertas.objects.annotate(
            cuit_limpio=Func(
                F('resploc_cuitcuil'),
                Value('-'),
                Value(''),
                function='REPLACE'
            )
        ).filter(
            cuit_limpio=usuario_limpio,
            oferta='Común - Servicios complementarios ',
            acronimo__startswith='BI'
        ).values_list('cueanexo', flat=True).first()

    def get(self, request, *args, **kwargs):

        cue = self.get_cueanexo(request)

        if not cue:
            return redirect('bibliotecas:materialbibliografico_list')

        # =========================
        # 🔥 ÚLTIMO INFORME
        # =========================
        ultimo = GenerarInforme.objects.filter(
            cueanexo=cue
        ).order_by('-annos', '-meses').first()

        anio = ultimo.annos if ultimo else None
        mes = ultimo.meses if ultimo else None

        params = f"?anio={anio}&mes={mes}" if anio and mes else ""

        # =========================
        # 🔥 FLUJO SECUENCIAL
        # =========================

        if not MaterialBibliografico.objects.filter(cueanexo=cue, anio=anio, mes=mes).exists():
            return redirect('bibliotecas:materialbibliografico_create')

        if not ServicioReferencia.objects.filter(cueanexo=cue, anio=anio, mes=mes).exists():
            return redirect('bibliotecas:servref_create')

        if not ServicioReferenciaVirtual.objects.filter(cueanexo=cue, anio=anio, mes=mes).exists():
            return redirect('bibliotecas:servrefvirtual_create')

        if not ServicioPrestamo.objects.filter(cueanexo=cue, anio=anio, mes=mes).exists():
            return redirect('bibliotecas:servprestamo_create')

        if not InformePedagogico.objects.filter(cueanexo=cue, anio=anio, mes=mes).exists():
            return redirect('bibliotecas:infopedagogico_create')

        if not AsistenciaUsuarios.objects.filter(cueanexo=cue, anio=anio, mes=mes).exists():
            return redirect('bibliotecas:asistenciausuarios_create')

        if not InstitucionesPrestaServicios.objects.filter(cueanexo=cue, anio=anio, mes=mes).exists():
            return redirect('bibliotecas:instituciones_create')

        if not ProcesosTecnicos.objects.filter(cueanexo=cue, anio=anio, mes=mes).exists():
            return redirect('bibliotecas:procesostecnicos_create')

        if not Aguapey.objects.filter(cueanexo=cue, anio=anio, mes=mes).exists():
            return redirect('bibliotecas:aguapey_create')

        if not DestinoFondos.objects.filter(cueanexo=cue, anio=anio, mes=mes).exists():
            return redirect('bibliotecas:destinofondos_create')

        if not BibliotecariosCue.objects.filter(cueanexo=cue, anio=anio, mes=mes).exists():
            return redirect('bibliotecas:bibliotecarios_create')

        # =========================
        # ✅ TODO COMPLETO
        # =========================
        return redirect(f"{reverse_lazy('bibliotecas:generar_pdf')}{params}")