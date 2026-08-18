from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from openpyxl import Workbook

from .models import ABMSupervisores
from .services.catalogo_service import CatalogoService
from .services.permission_service import (
    get_regiones_usuario,
    get_responsable,
    puede_operar_supervisor,
    puede_ver_supervisores,
)
from .services.supervisor_query_service import SupervisorQueryService
from .services.supervisor_service import update


@ensure_csrf_cookie
@login_required
def dashboard(request):
    context = CatalogoService.contexto(request.user)
    context["responsable"] = get_responsable(request.user)
    return render(request, "supervisores/dashboard.html", context)


@login_required
def SupervisoresList(request):
    if not puede_ver_supervisores(request.user):
        return HttpResponseForbidden("Sin permisos para consultar supervisores.")

    context = CatalogoService.contexto(request.user)
    context.update({
        "texto": request.GET.get("q", ""),
        "region_seleccionada": request.GET.get("region", ""),
        "situacion_seleccionada": request.GET.get("situacion", ""),
        "nivel_seleccionado": request.GET.get("nivel", ""),
    })
    return render(request, "supervisores/listado_supervisores.html", context)


@login_required
def detalle_supervisor(request, pk):
    supervisor = get_object_or_404(
        ABMSupervisores.objects.select_related("usuario"),
        pk=pk,
        activo=True,
    )
    if not puede_operar_supervisor(request.user, supervisor, "ver"):
        return HttpResponseForbidden("Sin permisos para consultar este supervisor.")

    regiones = get_regiones_usuario(request.user)
    asignaciones = supervisor.asignaciones_regionales.filter(activo=True)
    if regiones is not None:
        asignaciones = asignaciones.filter(region_id__in=regiones)

    asignaciones = asignaciones.select_related("region").prefetch_related(
        "niveles__nivel", "ofertas"
    )

    escuelas = []
    for asignacion in asignaciones:
        for oferta in asignacion.ofertas.all():
            if not oferta.activo:
                continue
            escuelas.append({
                "region": asignacion.region.nombre,
                "cueanexo": oferta.cueanexo,
                "escuela": oferta.nom_est,
                "oferta": oferta.oferta,
                "acronimo": oferta.acronimo,
            })

    return render(request, "supervisores/detalle.html", {
        "supervisor": supervisor,
        "escuelas": escuelas,
    })


SupervisorDetalle = detalle_supervisor


@login_required
@require_http_methods(["GET", "POST"])
def SupervisorEditar(request, pk):
    supervisor = get_object_or_404(
        ABMSupervisores.objects.select_related("usuario"),
        pk=pk,
        activo=True,
    )
    if not puede_operar_supervisor(request.user, supervisor, "modificar"):
        return HttpResponseForbidden("Sin permisos para modificar este supervisor.")

    if request.method == "POST":
        update(
            supervisor,
            telefono=request.POST.get("telefono"),
            email=request.POST.get("email"),
        )
        messages.success(request, "Supervisor actualizado correctamente.")
        return redirect("supervisor_registro:detalle", pk=supervisor.pk)

    return render(request, "supervisores/editar.html", {"supervisor": supervisor})


@login_required
def exportar_excel(request):
    if not puede_ver_supervisores(request.user):
        return HttpResponseForbidden("Sin permisos para exportar supervisores.")

    regiones = get_regiones_usuario(request.user)
    queryset = SupervisorQueryService.base(regiones)
    queryset = SupervisorQueryService.por_regiones(queryset, regiones)
    queryset = SupervisorQueryService.filtros(
        queryset,
        q=request.GET.get("q", "").strip(),
        region=request.GET.get("region") or None,
        situacion=request.GET.get("situacion") or None,
        nivel=request.GET.get("nivel") or None,
    )

    wb = Workbook()
    ws = wb.active
    ws.title = "Supervisores"
    ws.append([
        "CUIL", "Apellido", "Nombres", "Regional", "Nivel",
        "Situación", "Email", "Teléfono",
    ])

    for supervisor in queryset:
        regiones_out = []
        niveles_out = []
        situaciones_out = []

        for asignacion in supervisor.asignaciones_regionales.all():
            regiones_out.append(asignacion.region.nombre)
            niveles_out.extend(
                str(nivel.nivel)
                for nivel in asignacion.niveles.all()
                if nivel.activo
            )

        situaciones_out.extend(
            str(s.situacion_revista)
            for s in supervisor.situaciones.all()
            if s.activo
        )

        ws.append([
            supervisor.usuario.username,
            supervisor.usuario.apellido,
            supervisor.usuario.nombres,
            ", ".join(dict.fromkeys(regiones_out)),
            ", ".join(dict.fromkeys(niveles_out)),
            ", ".join(dict.fromkeys(situaciones_out)),
            supervisor.email or "",
            supervisor.telefono or "",
        ])

    for column in ws.columns:
        max_length = max(len(str(cell.value or "")) for cell in column)
        ws.column_dimensions[column[0].column_letter].width = min(max_length + 2, 60)

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="supervisores_filtrados.xlsx"'
    wb.save(response)
    return response
