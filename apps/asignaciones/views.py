import json

from django.db import transaction
from django.db.models import Count, Q, F
from django.http import JsonResponse, FileResponse
from django.shortcuts import get_object_or_404, render
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from .models import (
    EscuelaCapaOfertas,
    AsignacionSupervisorEscuela,
    AuditLog,
)

from .services import escuelas_permitidas
from .validators import validar_asignacion

from apps.supervisa2.models.supervisor import Supervisor2, RegionalUsuario
from apps.usuarios.models import UsuariosVisualizador

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, 
    Table, TableStyle, PageBreak
)

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

from apps.supervisa2.models.supervisor import Supervisor2, RegionalUsuario

from django.db.models import Value
from django.db.models.functions import Concat

from .models import AsignacionSupervisorEscuela

# =========================
# AJAX SELECT2
# =========================
def ajax_escuelas(request):
    supervisor = request.user.supervisores.get()
    term = request.GET.get("q", "")

    qs = escuelas_permitidas(supervisor)

    if term:
        qs = qs.filter(cueanexo__icontains=term)

    results = qs[:20]

    return JsonResponse({
        "results": [
            {
                "id": e.cueanexo,
                "text": f"{e.cueanexo} - {e.nom_est}"
            }
            for e in results
        ]
    })


# =========================
# HELPER FECHA
# =========================
def safe_date(value):
    if not value:
        return None
    return parse_date(str(value))


# =========================
# 🚀 UPSERT (CREATE + UPDATE)
# =========================
@require_POST
def ajax_asignar(request):

    supervisor = Supervisor2.objects.get(usuario=request.user.username)

    try:
        data = json.loads(request.POST.get("data", "[]"))
    except Exception:
        return JsonResponse({"ok": False, "error": "JSON inválido"})

    if not data:
        return JsonResponse({"ok": False, "error": "Sin datos"})

    creadas = 0
    actualizadas = 0
    errores = []

    try:
        with transaction.atomic():

            for i, item in enumerate(data, start=1):

                try:
                    cueanexo = item.get("cueanexo")
                    fd = safe_date(item.get("fecha_desde"))
                    fh = safe_date(item.get("fecha_hasta"))

                    if not cueanexo:
                        raise Exception("sin escuela")

                    if not fd or not fh:
                        raise Exception("fechas inválidas")

                    if fh < fd:
                        raise Exception("rango inválido")

                    escuela = EscuelaCapaOfertas.objects.get(cueanexo=cueanexo)

                    validar_asignacion(supervisor, escuela)

                    obj, created = AsignacionSupervisorEscuela.objects.update_or_create(
                        supervisor=supervisor,
                        cueanexo=cueanexo,
                        defaults={
                            "nom_est": escuela.nom_est,
                            "region_loc": escuela.region_loc,
                            "oferta": escuela.oferta,
                            "localidad": escuela.localidad,
                            "fecha_desde": fd,
                            "fecha_hasta": fh,
                            "activo": True,
                            "estado": "BORRADOR"
                        }
                    )

                    if created:
                        creadas += 1
                    else:
                        actualizadas += 1

                except EscuelaCapaOfertas.DoesNotExist:
                    errores.append(f"Fila {i}: escuela no existe")

                except Exception as e:
                    errores.append(f"Fila {i}: {str(e)}")

        return JsonResponse({
            "ok": True,
            "creadas": creadas,
            "actualizadas": actualizadas,
            "cantidad": len(data),
            "errores": errores
        })

    except Exception as e:
        return JsonResponse({
            "ok": False,
            "error": str(e)
        }, status=500)


# =========================
# VISTA CREAR
# =========================
def crear_asignacion(request):
    return render(request, "asignaciones/form.html", {
        "modo": "crear",
        "data_inicial": []
    })


# =========================
# VISTA EDITAR
# =========================
def editar_asignacion(request, pk):

    asignacion = get_object_or_404(AsignacionSupervisorEscuela, pk=pk)

    return render(request, "asignaciones/form.html", {
        "modo": "editar",
        "data_inicial": [{
            "cueanexo": asignacion.cueanexo,
            "nom_est": asignacion.nom_est,
            "fecha_desde": asignacion.fecha_desde,
            "fecha_hasta": asignacion.fecha_hasta,
            "estado": asignacion.estado
        }]
    })


# =========================
# ENVIAR
# =========================
@require_POST
def enviar_asignacion(request):

    obj = AsignacionSupervisorEscuela.objects.get(
        id=request.POST.get("id")
    )

    if obj.estado in ["ENVIADO", "APROBADO"]:
        return JsonResponse({"ok": False})

    obj.estado = "ENVIADO"
    obj.save()

    return JsonResponse({"ok": True})

def listar_asignaciones(request):

    supervisor = Supervisor2.objects.get(usuario=request.user.username)

    data = AsignacionSupervisorEscuela.objects.filter(
        supervisor=supervisor
    ).values(
        "id",
        "cueanexo",
        "nom_est",
        "fecha_desde",
        "fecha_hasta",
        "estado"
    )

    return JsonResponse(list(data), safe=False)

def panel_asignaciones(request):

    supervisor = Supervisor2.objects.get(usuario=request.user.username)
    
    # 🔥 TRAER DATOS PERSONALES
    try:
        usuario_extra = UsuariosVisualizador.objects.get(
            username=request.user.username
        )
    except UsuariosVisualizador.DoesNotExist:
        usuario_extra = None

    asignaciones = AsignacionSupervisorEscuela.objects.filter(
        supervisor=supervisor
    ).order_by("-id")

    # 🔥 RESUMEN PRO
    resumen_qs = asignaciones.values("estado").annotate(total=Count("id"))

    resumen = {
        "BORRADOR": 0,
        "ENVIADO": 0,
        "RECHAZADO": 0,
        "APROBADO": 0
    }

    for r in resumen_qs:
        resumen[r["estado"]] = r["total"]

    # 🔥 DETECTAR RECHAZOS CON OBSERVACIÓN
    rechazadas = asignaciones.filter(
        estado="RECHAZADO"
    ).exclude(observacion__isnull=True).exclude(observacion="")

    return render(request, "asignaciones/panel.html", {
        "asignaciones": asignaciones,
        "supervisor": supervisor,
        "usuario_extra": usuario_extra,
        "resumen": resumen,
        "rechazadas": rechazadas
    })



# =========================================================
# 🏢 PANEL REGIONAL
# =========================================================
def panel_regional(request):

    regiones = RegionalUsuario.objects.filter(
        usuario=request.user.username
    ).values_list("region_loc", flat=True)

    asignaciones = AsignacionSupervisorEscuela.objects.filter(
        region_loc__in=regiones
    ).select_related("supervisor").order_by("-id")

    return render(request, "asignaciones/panel_regional.html", {
        "asignaciones": asignaciones
    })


# =========================================================
# ✔️ APROBAR ASIGNACIÓN
# =========================================================
@require_POST
def aprobar_asignacion(request):

    obj = AsignacionSupervisorEscuela.objects.get(
        id=request.POST.get("id")
    )

    obj.estado = "APROBADO"
    obj.observacion = ""
    obj.save()

    return JsonResponse({"ok": True})


# =========================================================
# ❌ RECHAZAR ASIGNACIÓN
# =========================================================
@require_POST
def rechazar_asignacion(request):

    obj = AsignacionSupervisorEscuela.objects.get(
        id=request.POST.get("id")
    )

    obj.estado = "RECHAZADO"
    obj.observacion = request.POST.get("observacion", "")
    obj.save()

    return JsonResponse({"ok": True})


# =========================================================
# 🏛 PANEL ADMIN POWERBI
# =========================================================
def panel_admin_powerbi(request):
    return render(request, "asignaciones/admin/panel_powerbi.html")


# =========================================================
# 📡 REALTIME API (SALA DE SITUACIÓN MINISTERIAL)
# =========================================================
def dashboard_realtime_api(request):

    region = request.GET.get("region")
    supervisor = request.GET.get("supervisor")
    oferta = request.GET.get("oferta")

    qs = (
        AsignacionSupervisorEscuela.objects
        .select_related("supervisor", "supervisor__usuario")
    )

    # =========================
    # FILTROS
    # =========================
    if region:
        qs = qs.filter(region_loc=region)

    if supervisor:
        qs = qs.filter(supervisor_id=supervisor)

    if oferta:
        qs = qs.filter(oferta=oferta)

    # =========================
    # KPI
    # =========================
    resumen_qs = qs.values("estado").annotate(total=Count("id"))

    resumen = {
        "BORRADOR": 0,
        "ENVIADO": 0,
        "RECHAZADO": 0,
        "APROBADO": 0,
    }

    for r in resumen_qs:
        estado = (r["estado"] or "BORRADOR").upper()
        resumen[estado] = r["total"]

    # =========================
    # LOGS
    # =========================
    logs = list(
        AuditLog.objects.order_by("-timestamp")[:20]
        .values("usuario", "accion", "objeto", "timestamp")
    )

    # =========================
    # ESCUELAS IDS
    # =========================
    escuelas_ids = list(qs.values_list("cueanexo", flat=True))
    escuelas_ids = [str(x) for x in escuelas_ids if x is not None]

    escuelas = list(
        EscuelaCapaOfertas.objects.filter(cueanexo__in=escuelas_ids)
        .exclude(Q(lat__isnull=True) | Q(long__isnull=True))
        .values(
            "cueanexo",
            "nom_est",
            "lat",
            "long",
            "region_loc",
            "oferta",
        )
    )

    # =========================
    # MAPA ESTADOS
    # =========================
    estado_map = {
        str(a["cueanexo"]): a["estado"]
        for a in qs.values("cueanexo", "estado")
    }

    for e in escuelas:
        e["estado"] = estado_map.get(str(e["cueanexo"]), "BORRADOR")

        try:
            e["lat"] = float(e["lat"])
            e["long"] = float(e["long"])
        except:
            e["lat"] = None
            e["long"] = None

    # =========================================================
    # 🔥 NUEVO: DATOS PARA FILTROS FRONTEND
    # =========================================================

    regiones = list(
        qs.values_list("region_loc", flat=True).distinct()
    )

    ofertas = list(
        qs.values_list("oferta", flat=True).distinct()
    )

    supervisores = list(
        qs.values(
            "supervisor_id",
            "supervisor__usuario__apellido",
            "supervisor__usuario__nombres",
        ).distinct()
    )

    supervisores_formateados = [
        {
            "supervisor_id": s["supervisor_id"],
            "label": f"{s['supervisor__usuario__apellido']}, {s['supervisor__usuario__nombres']}"
        }
        for s in supervisores
        if s["supervisor_id"]
    ]

    # =========================
    # RESPONSE FINAL
    # =========================
    return JsonResponse({
        "resumen": resumen,
        "logs": logs,
        "escuelas": escuelas,

        # 🔥 ESTO ES LO QUE TE FALTABA
        "regiones": regiones,
        "ofertas": ofertas,
        "supervisores": supervisores_formateados,
    })


# =========================================================
# 📄 EXPORT PDF
# =========================================================
def export_pdf_admin(request):

    supervisor_id = request.GET.get("supervisor")
    region = request.GET.get("region")
    oferta = request.GET.get("oferta")

    file_path = "/tmp/reporte_supervisor_final.pdf"
    doc = SimpleDocTemplate(file_path)

    styles = getSampleStyleSheet()
    story = []

    # =========================================================
    # 🔵 QUERY BASE (CORREGIDA)
    # =========================================================
    qs = AsignacionSupervisorEscuela.objects.select_related(
        "supervisor",
        "supervisor__usuario"   # ✅ CORRECTO (no usuariosvisualizador)
    )

    if supervisor_id:
        qs = qs.filter(supervisor_id=supervisor_id)

    if region:
        qs = qs.filter(region_loc=region)

    if oferta:
        qs = qs.filter(oferta=oferta)

    # =========================================================
    # 🔵 VALIDACIÓN
    # =========================================================
    if not qs.exists():
        story.append(Paragraph("Sin datos para el reporte", styles["Title"]))
        doc.build(story)
        return FileResponse(open(file_path, "rb"), as_attachment=True)

    # =========================================================
    # 🔵 SUPERVISOR + PERFIL REAL
    # =========================================================
    first_row = qs.first()
    supervisor = first_row.supervisor

    perfil = getattr(supervisor, "usuario", None)  # ✅ CORRECTO

    nombre_completo = " ".join(filter(None, [
        getattr(perfil, "apellido", "") if perfil else "",
        getattr(perfil, "nombres", "") if perfil else ""
    ])).strip()

    usuario = getattr(supervisor, "usuario", "")

    if not nombre_completo:
        nombre_completo = str(usuario) or "Supervisor no identificado"

    total_escuelas = qs.count()

    # =========================================================
    # 🔵 PORTADA PROFESIONAL
    # =========================================================
    story.append(Paragraph(
        "MINISTERIO DE EDUCACIÓN, CULTURA, CIENCIA Y TECNOLOGÍA DEL CHACO",
        styles["Title"]
    ))
    story.append(Spacer(1, 12))

    story.append(Paragraph("REPORTE DE SUPERVISIÓN", styles["Heading1"]))
    story.append(Spacer(1, 18))

    story.append(Paragraph(
        f"<b>Supervisor:</b> {nombre_completo}",
        styles["Heading2"]
    ))

    story.append(Paragraph(
        f"<b>Usuario:</b> {usuario}",
        styles["Normal"]
    ))

    story.append(Paragraph(
        f"<b>Total de escuelas asignadas:</b> {total_escuelas}",
        styles["Normal"]
    ))

    story.append(Spacer(1, 20))
    story.append(PageBreak())

    # =========================================================
    # 🔵 TABLA PROFESIONAL
    # =========================================================
    table_data = [[
        "ESCUELA (CUEANEXO)",
        "REGIÓN",
        "OFERTA",
        "ESTADO"
    ]]

    for d in qs:
        table_data.append([
            d.cueanexo or "-",
            d.region_loc or "-",
            d.oferta or "-",
            d.estado or "-"
        ])

    table = Table(table_data, repeatRows=1)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),

        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")]),

        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    story.append(table)

    doc.build(story)

    return FileResponse(open(file_path, "rb"), as_attachment=True)


# =========================================================
# 📦 CATALOGO FILTROS (ENDPOINT OPCIONAL)
# =========================================================
def filtros_catalogo(request):

    regiones = list(
        EscuelaCapaOfertas.objects
        .exclude(region_loc__isnull=True)
        .values_list("region_loc", flat=True)
        .distinct()
        .order_by("region_loc")
    )

    supervisores_raw = list(
        Supervisor2.objects
        .select_related("usuario")
        .values(
            "id",
            "usuario__username",
            "usuario__apellido",
            "usuario__nombres",
        )
        .distinct()
    )

    supervisores = [
        {
            "supervisor_id": s["id"],
            "label": f'{s["usuario__apellido"]}, {s["usuario__nombres"]} ({s["usuario__username"]})'
        }
        for s in supervisores_raw
    ]

    ofertas = list(
        EscuelaCapaOfertas.objects
        .exclude(oferta__isnull=True)
        .values_list("oferta", flat=True)
        .distinct()
        .order_by("oferta")
    )

    return JsonResponse({
        "regiones": regiones,
        "supervisores": supervisores,
        "ofertas": ofertas
    })