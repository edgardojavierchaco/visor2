import json
import logging
import re
from django.db import connection
from django.shortcuts import render
from django.http import JsonResponse
from pyparsing import C
from .models import GenerarInforme
from apps.consultasge.models import CapaUnicaOfertas
from django.db.models import Func, F, Value
from django.db.models import Count, Q, Subquery, OuterRef
from django.views.decorators.cache import cache_page
from django.db.models.functions import Cast
from django.db.models import CharField
from django.db.models.expressions import RawSQL
from django.utils import timezone
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

def generar_informe(request):
    # 🔹 Obtener usuario logueado correctamente
    usuario_logueado = request.user.username  
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
            acronimo__startswith='BI'
        ).values_list('cueanexo', flat=True)
        
    cueanexos = list(cueanexos_qs)
    cue=cueanexos[0] if cueanexos else None
    
    # 🔥 DEFAULTS IMPORTANTES
    mes = None
    anio = None

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT DISTINCT cueanexo FROM public.v_capa_unica_ofertas_ant WHERE acronimo ILIKE 'BI%'")
            ofertas = cursor.fetchall()
            print("✅ Ofertas encontradas:", ofertas)  # Depuración
    except Exception as e:
        print("❌ Error en la consulta SQL:", e)  # Depuración
        
    cant_ofertas=len(ofertas)
    print("✅ Cantidad de ofertas:", cant_ofertas)  # Depuración
    
    ultimo_informe = GenerarInforme.objects.filter(cueanexo=cue).order_by('-annos', '-meses').first()

    if ultimo_informe:
        mes = ultimo_informe.meses
        anio = ultimo_informe.annos
            
    informes = GenerarInforme.objects.filter(cueanexo=cue, meses=mes, annos=anio)
    total_generados = informes.filter(estado='GENERADO').count()
    total_enviados = informes.filter(estado='ENVIADO').count()
    total_faltantes=cant_ofertas-total_enviados

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':  # Detecta AJAX
        informes_data = list(informes.values('cueanexo', 'meses', 'annos', 'estado', 'f_generacion', 'f_envio'))
        return JsonResponse({
            'informes': informes_data,
            'total_generados': total_generados,
            'total_enviados': total_enviados,
            'total_faltantes': total_faltantes,
            'no_registros_message': "No hay registros disponibles" if not informes_data else "",
        })

    context = {
        'informes': informes,
        'total_generados': total_generados,
        'total_enviados': total_enviados,
        'total_faltantes': total_faltantes,
    }
    return render(request, 'biblioteca/generar_informe_list.html', context)

def generar_informe_list(request):
    print("📌 La vista se ejecutó")  # Depuración
    cue = request.GET.get('cueanexo', '').strip()
    meses = request.GET.get('meses', '').strip()
    annos = request.GET.get('annos', '').strip()
    
    print('datos enviados',cue, meses, annos)  # Debugging

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT DISTINCT cueanexo FROM v_capa_unica_ofertas WHERE acronimo ILIKE 'BI%'")
            ofertas = cursor.fetchall()
            print("✅ Ofertas encontradas:", ofertas)  # Depuración
    except Exception as e:
        print("❌ Error en la consulta SQL:", e)  # Depuración
        
    cant_ofertas=len(ofertas)
    print("✅ Cantidad de ofertas:", cant_ofertas)  # Depuración
    
    
    # Construcción dinámica de filtros
    filtros = {}
    if cue:
        filtros["cueanexo"] = cue
    if meses:
        filtros["meses"] = meses
    if annos.isdigit():  # Verifica que el año sea un número válido
        filtros["annos"] = int(annos)

    informes = GenerarInforme.objects.filter(**filtros)
    total_generados = informes.filter(estado='GENERADO').count()
    total_enviados = informes.filter(estado='ENVIADO').count()
    total_faltantes=cant_ofertas-total_enviados
    
    print('informes',informes)  # Debugging
    print("Informes encontrados:", informes.count())

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':  # Detecta AJAX
        informes_data = list(informes.values('cueanexo', 'meses', 'annos', 'estado', 'f_generacion', 'f_envio'))
        return JsonResponse({
            'informes': informes_data,
            'total_generados': total_generados,
            'total_enviados': total_enviados,
            'total_faltantes': total_faltantes,
            'no_registros_message': "No hay registros disponibles" if not informes_data else "",
        })

    context = {
        'informes': informes,
        'total_generados': total_generados,
        'total_enviados': total_enviados,
        'total_faltantes': total_faltantes
    }
    return render(request, 'biblioteca/generar_informe_list.html', context)


# ==========================================
# 🌐 VISTA HTML
# ==========================================
def dashboard_informes_view(request):
    return render(request, "biblioteca/dashboard_informes.html")


# ==========================================
# 📊 API MINISTERIAL PRO (ESTABLE)
# ==========================================
@cache_page(60 * 5)
def dashboard_informes_api(request):

    cue = request.GET.get('cueanexo', '').strip()
    meses = request.GET.get('meses', '').strip()
    annos = request.GET.get('annos', '').strip()
    region = request.GET.get('region_loc', '').strip()

    filtros = Q()

    if cue:
        filtros &= Q(cueanexo=cue)

    if meses:
        filtros &= Q(meses=meses)

    if annos.isdigit():
        filtros &= Q(annos=int(annos))

    ofertas = []
    
    try:

        # =========================
        # 🏛️ TOTAL OFERTAS
        # =========================
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(DISTINCT cueanexo)
                FROM v_capa_unica_ofertas_ant
                WHERE acronimo ILIKE 'BI%'
            """)
            total_ofertas = cursor.fetchone()[0] or 0

        # =========================
        # 🌍 MAPA REGION (SIN ORM)
        # =========================
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT cueanexo, region_loc, nom_est
                FROM v_capa_unica_ofertas_ant
                WHERE region_loc IS NOT NULL
            """)
            region_map = {
                str(row[0]): {
                    "region_loc": row[1],
                    "nom_est": row[2]
                }
                
                for row in cursor.fetchall()
            }

        # =========================
        # 📊 DATA BASE
        # =========================
        qs = GenerarInforme.objects.filter(filtros)

        data = list(qs.values(
            "id",
            "cueanexo",
            "meses",
            "annos",
            "estado"
        ))

        # =========================
        # 🔥 INYECTAR REGION
        # =========================
        for d in data:
            info = region_map.get(str(d["cueanexo"]), {})
            
            d["region_loc"] = region_map.get(str(d["cueanexo"]), "SIN REGIÓN")
            d["nom_est"] = info.get("nom_est", "SIN NOMBRE")

        # =========================
        # 🌍 FILTRO REGION
        # =========================
        if region:
            data = [d for d in data if d["region_loc"] == region]

        # =========================
        # 📊 KPI
        # =========================
        generados = sum(1 for d in data if d["estado"] == "GENERADO")
        enviados = sum(1 for d in data if d["estado"] == "ENVIADO")
        faltantes = max(total_ofertas - enviados, 0)

        # =========================
        # 📈 ESTADOS
        # =========================
        por_estado = {}
        for d in data:
            por_estado[d["estado"]] = por_estado.get(d["estado"], 0) + 1

        # =========================
        # 📅 MES
        # =========================
        por_mes = {}
        for d in data:
            por_mes[d["meses"]] = por_mes.get(d["meses"], 0) + 1

        """ # =========================
        # 🏫 RANKING
        # =========================
        ranking = {}
        for d in data:
            key = d["cueanexo"]
            ranking[key] = ranking.get(key, 0) + 1

        ranking = [
            {
                "cueanexo": k,
                "meses": next((x["meses"] for x in data if x["cueanexo"] == k), ""),
                "annos": next((x["annos"] for x in data if x["cueanexo"] == k), ""),
                "total": v,
                "estado": next((x["estado"] for x in data if x["cueanexo"] == k), ""),
                "region_loc": next((x["region_loc"] for x in data if x["cueanexo"] == k), "")
            }
            for k, v in sorted(ranking.items(), key=lambda x: x[1], reverse=True)[:15]
        ] """

        # =========================
        # 📋 TABLA REAL
        # =========================
        ranking = []

        for d in data:
            ranking.append({
                "cueanexo": d["cueanexo"],
                "nom_est": d["nom_est"],
                "meses": d["meses"],
                "annos": d["annos"],
                "estado": d["estado"],
                "region_loc": d["region_loc"],
                "total": 1
            })
        
        # =========================
        # 🌍 REGIONES
        # =========================
        regiones = sorted(set(
            v["region_loc"]
            for v in region_map.values()
            if v.get("region_loc")
        ))

        return JsonResponse({
            "success": True,
            "kpis": {
                "ofertas": total_ofertas,
                "generados": generados,
                "enviados": enviados,
                "faltantes": faltantes,
                "cumplimiento": round((enviados / total_ofertas) * 100, 2) if total_ofertas else 0
            },
            "graficos": {
                "por_estado": [{"estado": k, "total": v} for k, v in por_estado.items()],
                "por_mes": [{"meses": k, "total": v} for k, v in por_mes.items()]
            },
            "ranking": ranking,
            "regiones": regiones
        })

    except Exception as e:
        import traceback
        print(traceback.format_exc())

        return JsonResponse({
            "success": False,
            "error": "Error interno"
        }, status=500)


@require_POST
def reabrir_informe(request):
    try:
        data = json.loads(request.body)

        cueanexo = data.get("cueanexo")
        meses = data.get("meses")
        annos = data.get("annos")

        if not (cueanexo and meses and annos):
            return JsonResponse({"success": False, "msg": "Datos incompletos"})

        try:
            informe = GenerarInforme.objects.get(
                cueanexo=cueanexo,
                meses=meses,
                annos=annos
            )
        except GenerarInforme.DoesNotExist:
            return JsonResponse({"success": False, "msg": "No existe el informe"})

        if informe.estado != "ENVIADO":
            return JsonResponse({"success": False, "msg": "Solo se pueden reabrir enviados"})

        # 🔥 REAPERTURA
        informe.estado = "GENERADO"
        informe.rehab = True
        informe.f_rehab = timezone.now()
        informe.save()

        return JsonResponse({
            "success": True,
            "msg": "Informe reabierto correctamente"
        })

    except Exception as e:
        return JsonResponse({"success": False, "msg": str(e)})