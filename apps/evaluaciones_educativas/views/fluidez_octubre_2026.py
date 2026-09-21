from apps.evaluaciones_educativas.models.fluidez_octubre_2026 import *
# from apps.evaluaciones_educativas.models.modelo_oficial import  *
from apps.consultasge.models import CapaUnicaOfertas
from apps.evaluaciones_educativas.forms.fluidez_octubre_2026 import *
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.templatetags.static import static
from django.db.models import Count, Q, Avg, F
from datetime import date, datetime
import json
from openpyxl import Workbook
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.urls import reverse
from urllib.parse import urlencode


# def lista(request, fid_actual=None):
#     cuil = 27280062443

#     if not fid_actual:
#         fid_actual = request.GET.get("fid")
#     cueanexo_id = None
#     grado_public_id = None

#     alumnos_qs = None
#     qs_secciones = None
#     grado = None
#     # registros_pruba=V_Trayectoria_Alumnos_SGE.objects.using('test').filter(cueanexo='220037300')
#     # print('estoy aca')
#     # print(registros_pruba)
#     cueanexo_form = CueanexoFluidezOctubre2026ViewForm(cuil=cuil)
#     grado_form = GradoFluidezOctubre2026ViewForm()

#     if request.method == "POST":
#         cueanexo_nuevo = request.POST.get("cueanexo")
#         grado_nuevo = request.POST.get("grado")

#         datos_anteriores = request.session.get(f"filtro_oct_{fid_actual}", {})
#         cueanexo_anterior = datos_anteriores.get("cueanexo")

#         if cueanexo_nuevo != cueanexo_anterior:
#             grado_nuevo = None

#         request.session[f"filtro_oct_{fid_actual}"] = {
#             "cueanexo": cueanexo_nuevo,
#             "grado": grado_nuevo,
#         }
#         request.session.modified = True
#         return redirect(f"{request.path}?fid={fid_actual}")

#     else:
#         if fid_actual:
#             datos_guardados = request.session.get(f"filtro_oct_{fid_actual}")
#             if datos_guardados:
#                 cueanexo_id = datos_guardados.get("cueanexo")
#                 grado = datos_guardados.get("grado")
#                 cueanexo_form = CueanexoFluidezOctubre2026ViewForm(datos_guardados, cuil=cuil)
#                 if cueanexo_id:
#                     grado_form = GradoFluidezOctubre2026ViewForm(
#                         datos_guardados, cueanexo=cueanexo_id
#                     )

#     if cueanexo_id and grado:
#         # grado = GradoFluidez2026.objects.get(public_id=grado_public_id)

#         # if grado.nombre_grado == "2do Año/Grado":
#         #     nombre_grado = "2do Grado/Año"
#         # else:
#         #     nombre_grado = "3er Grado/Año"

#         # lista_dnis = list(
#         #     TablaTemporalAlumnoFluidez2026.objects.filter(
#         #         cueanexo=cueanexo_id, anio=nombre_grado
#         #     ).values_list("numero_de_documento", flat=True)
#         # )

#         # lista = list(
#         #     AlumnoFluidez2026.objects.filter(
#         #         ~Q(dni__in=lista_dnis),
#         #         seccion__grado__cueanexo=int(cueanexo_id),
#         #         seccion__grado__nombre_grado=grado.nombre_grado,
#         #     ).values_list("dni", flat=True)
#         # )

#         # lista_dnis.extend(lista)
#         # alumnos_qs = AlumnoFluidez2026.objects.filter(dni__in=lista_dnis)

#         # qs_secciones = SeccionFluidez2026.objects.filter(
#         #     grado__public_id=grado.public_id
#         # )

#         alumnos_qs=V_Trayectoria_Alumnos_SGE.objects.using('test').filter(cueanexo=cueanexo_id,anio_grado=grado).values_list('nombre','apellido','numero_documento','nombre_seccion','turno','comunidad_indigena','discapacidad')

#     contexto = {
#         "cueanexo_form": cueanexo_form,
#         "grado_form": grado_form,
#         "grado": grado,
#         "alumnos": alumnos_qs,
#         # "secciones_turnos_disponibles": qs_secciones,
#         # "opciones_comunidad_indigena": AlumnoFluidezOctubre2026Form.OPCIONES_COMUNIDAD_INDIGENA,
#         # "opciones_discapacidad": AlumnoFluidezOctubre2026Form.OPCIONES_DISCAPACIDAD,
#         "fid_actual": fid_actual,
#     }

#     return render(request, "fluidez_octubre_2026/lista.html", contexto)


# def actualizar_seccion(request, alumno_public_id):
#     """Actualiza la sección, turno, comunidad_indigena y discapacidad de un alumno."""
#     if request.method == "POST":
#         fid = request.POST.get("fid")

#         alumno = get_object_or_404(AlumnoFluidez2026, public_id=alumno_public_id)

#         nueva_seccion_turno_public_id = request.POST.get("seccion_turno")
#         comunidad = request.POST.get("comunidad_indigena")
#         discapacidad = request.POST.get("discapacidad")

#         if nueva_seccion_turno_public_id:
#             seccion_obj = get_object_or_404(
#                 SeccionFluidez2026, public_id=nueva_seccion_turno_public_id
#             )
#             alumno.seccion = seccion_obj
#         else:
#             alumno.seccion = None

#         valores_comunidad = [
#             str(v) for v, _ in AlumnoFluidez2026.OPCIONES_COMUNIDAD_INDIGENA
#         ]
#         if comunidad in valores_comunidad:
#             alumno.comunidad_indigena = comunidad
#         elif not comunidad:
#             alumno.comunidad_indigena = None

#         valores_discapacidad = [
#             str(v) for v, _ in AlumnoFluidez2026.OPCIONES_DISCAPACIDAD
#         ]
#         if discapacidad in valores_discapacidad:
#             alumno.discapacidad = discapacidad
#         elif not discapacidad:
#             alumno.discapacidad = None

#         alumno.save()

#         base_url = reverse("evaluaciones_educativas:fluidez_octubre_2026:lista")

#         if fid:
#             return redirect(f"{base_url}?fid={fid}")

#         return redirect(base_url)

#     return redirect("evaluaciones_educativas:fluidez_octubre_2026:lista")


# def lista_examen(request, fid_actual=None):
#     cuil = 27275780559
#     if not fid_actual:
#         fid_actual = request.GET.get("fid")

#     cueanexo_id = None
#     grado_public_id = None

#     alumnos_qs = None
#     qs_secciones = None
#     grado = None

#     cueanexo_form = CueanexoFluidezOctubre2026ViewForm(cuil=cuil)
#     grado_form = GradoFluidezOctubre2026ViewForm()

#     if request.method == "POST":
#         cueanexo_nuevo = request.POST.get("cueanexo")
#         grado_nuevo = request.POST.get("grado")

#         datos_anteriores = request.session.get(f"filtro_oct_{fid_actual}", {})
#         cueanexo_anterior = datos_anteriores.get("cueanexo")

#         if cueanexo_nuevo != cueanexo_anterior:
#             grado_nuevo = None

#         request.session[f"filtro_oct_{fid_actual}"] = {
#             "cueanexo": cueanexo_nuevo,
#             "grado": grado_nuevo,
#         }
#         request.session.modified = True
#         return redirect(f"{request.path}?fid={fid_actual}")

#     else:
#         if fid_actual:
#             datos_guardados = request.session.get(f"filtro_oct_{fid_actual}")
#             if datos_guardados:
#                 cueanexo_id = datos_guardados.get("cueanexo")
#                 grado_public_id = datos_guardados.get("grado")
#                 cueanexo_form = CueanexoFluidezOctubre2026ViewForm(datos_guardados, cuil=cuil)
#                 if cueanexo_id:
#                     grado_form = GradoFluidezOctubre2026ViewForm(
#                         datos_guardados, cueanexo=cueanexo_id
#                     )

#     if cueanexo_id and grado_public_id:
#         grado = GradoFluidez2026.objects.get(public_id=grado_public_id)

#         if grado.nombre_grado == "2do Año/Grado":
#             nombre_grado = "2do Grado/Año"
#         else:
#             nombre_grado = "3er Grado/Año"

#         lista_dnis = list(
#             TablaTemporalAlumnoFluidez2026.objects.filter(
#                 cueanexo=cueanexo_id, anio=nombre_grado
#             ).values_list("numero_de_documento", flat=True)
#         )

#         lista = list(
#             AlumnoFluidez2026.objects.filter(
#                 ~Q(dni__in=lista_dnis),
#                 seccion__grado__cueanexo=int(cueanexo_id),
#                 seccion__grado__nombre_grado=grado.nombre_grado,
#             ).values_list("dni", flat=True)
#         )

#         lista_dnis.extend(lista)
#         alumnos_qs = AlumnoFluidez2026.objects.filter(
#             dni__in=lista_dnis
#         ).select_related("fluidez_lectora_octubre_2026")

#     contexto = {
#         "cueanexo_form": cueanexo_form,
#         "grado_form": grado_form,
#         "grado": grado,
#         "alumnos": alumnos_qs,
#         "fid_actual": fid_actual,
#     }

#     return render(request, "fluidez_octubre_2026/lista_examen.html", contexto)


# def carga_alumno(request, fid_actual, grado_public_id):
#     cuil = 20422632264
#     grado = get_object_or_404(GradoFluidez2026, public_id=grado_public_id)
#     alumno_form = AlumnoFluidezOctubre2026Form()
#     grado_form = GradoFluidezOctubre2026Form(instance=grado)
#     seccion_form = SeccionFluidezOctubre2026Form(
#         cueanexo=grado.cueanexo, nombre_grado=grado.nombre_grado
#     )
#     if request.method == "POST":
#         alumno_form = AlumnoFluidezOctubre2026Form(request.POST)
#         seccion_form = SeccionFluidezOctubre2026Form(
#             request.POST, cueanexo=grado.cueanexo, nombre_grado=grado.nombre_grado
#         )
#         if alumno_form.is_valid() and seccion_form.is_valid():
#             with transaction.atomic():
#                 seccion_turno_id = seccion_form.cleaned_data["seccion_turno"]
#                 instancia_seccion, creado_seccion = (
#                     SeccionFluidez2026.objects.get_or_create(
#                         id=seccion_turno_id, grado=grado
#                     )
#                 )
#                 alumno = alumno_form.save(commit=False)
#                 alumno.seccion = instancia_seccion
#                 alumno.save()
#             return redirect(
#                 "evaluaciones_educativas:fluidez_octubre_2026:lista", fid_actual=fid_actual
#             )

#     context = {
#         "alumno_form": alumno_form,
#         "grado_form": grado_form,
#         "seccion_form": seccion_form,
#         "fid_actual": fid_actual,
#     }
#     return render(request, "fluidez_octubre_2026/alumno.html", context)


# def editar_alumno(request, alumno_public_id, fid_actual):
#     instancia_alumno = get_object_or_404(AlumnoFluidez2026, public_id=alumno_public_id)
#     if not instancia_alumno.seccion.grado.cueanexo:
#         alumno_datos = get_object_or_404(
#             TablaTemporalAlumnoFluidez2026, numero_de_documento=instancia_alumno.dni
#         )
#         cueanexo = alumno_datos.cueanexo
#         anio = alumno_datos.anio
#     cueanexo = instancia_alumno.seccion.grado.cueanexo
#     anio = instancia_alumno.seccion.grado.nombre_grado
#     seccion = instancia_alumno.seccion.id

#     instancia_grado = get_object_or_404(
#         GradoFluidez2026, cueanexo=cueanexo, nombre_grado=anio
#     )
#     alumno_form = AlumnoFluidezOctubre2026Form(instance=instancia_alumno)
#     seccion_form = SeccionFluidezOctubre2026Form(
#         cueanexo=instancia_grado.cueanexo,
#         nombre_grado=instancia_grado.nombre_grado,
#         initial={"seccion_turno": seccion},
#     )
#     grado_form = GradoFluidezOctubre2026Form(instance=instancia_grado)
#     if request.method == "POST":
#         alumno_form = AlumnoFluidezOctubre2026Form(request.POST, instance=instancia_alumno)
#         grado_form = GradoFluidezOctubre2026Form(request.POST, instance=instancia_grado)
#         seccion_form = SeccionFluidezOctubre2026Form(
#             request.POST, cueanexo=cueanexo, nombre_grado=instancia_grado.nombre_grado
#         )
#         if alumno_form.is_valid() and grado_form.is_valid() and seccion_form.is_valid():
#             with transaction.atomic():
#                 instancia_grado, creado_grado = GradoFluidez2026.objects.get_or_create(
#                     nombre_grado=anio, cueanexo=cueanexo
#                 )
#                 seccion_turno_id = seccion_form.cleaned_data["seccion_turno"]
#                 instancia_seccion, creado_seccion = (
#                     SeccionFluidez2026.objects.get_or_create(
#                         id=seccion_turno_id, grado=instancia_grado
#                     )
#                 )
#                 alumno = alumno_form.save(commit=False)
#                 alumno.seccion = instancia_seccion
#                 alumno.save()
#             return redirect(
#                 "evaluaciones_educativas:fluidez_octubre_2026:lista", fid_actual=fid_actual
#             )
#     context = {
#         "alumno_form": alumno_form,
#         "grado_form": grado_form,
#         "seccion_form": seccion_form,
#         "grado_public": instancia_grado.public_id,
#         "fid_actual": fid_actual,
#     }
#     return render(request, "fluidez_octubre_2026/alumno.html", context)


# def _obtener_o_crear_evaluacion_padre():
#     """Obtiene o crea un Operativo y Evaluacion padre para Fluidez Octubre 2026."""
#     operativo, _ = Operativo.objects.get_or_create(
#         tipo_operativo="Fluidez Lectora",
#         anio=2026,
#         mes=10,
#     )
#     evaluacion = Evaluacion.objects.create(operativo=operativo)
#     return evaluacion


# def carga_evaluacion(request, alumno_public_id, fid_actual):
#     alumno_id = get_object_or_404(AlumnoFluidez2026, public_id=alumno_public_id)
#     instancia_seccion = get_object_or_404(SeccionFluidez2026, id=alumno_id.seccion_id)
#     instancia_grado = get_object_or_404(GradoFluidez2026, id=instancia_seccion.grado_id)
#     grado_public = instancia_grado.public_id
#     if instancia_grado.nombre_grado == "2do Año/Grado":
#         cantidad_palabra_maxima = 196
#     else:
#         cantidad_palabra_maxima = 265

#     evaluacion_existente = None
#     try:
#         evaluacion_existente = Fluidez_Lectora_Octubre_2026.objects.get(
#             alumno=alumno_id
#         )
#     except Fluidez_Lectora_Octubre_2026.DoesNotExist:
#         pass

#     if request.method == "POST":
#         form = EvaluacionFluidezOctubre2026Form(
#             request.POST,
#             max_cantidad_palabra=cantidad_palabra_maxima,
#             instance=evaluacion_existente,
#         )
#         if form.is_valid():
#             with transaction.atomic():
#                 evaluacion = form.save(commit=False)
#                 if not evaluacion_existente:
#                     # Crear evaluacion padre si es nueva
#                     eval_padre = _obtener_o_crear_evaluacion_padre()
#                     evaluacion.evaluacion = eval_padre
#                 evaluacion.alumno = alumno_id
#                 evaluacion.encargado_carga = "DIRECTOR"
#                 evaluacion.save()
#             return redirect(
#                 "evaluaciones_educativas:fluidez_octubre_2026:lista_examen",
#                 fid_actual=fid_actual,
#             )
#     else:
#         form = EvaluacionFluidezOctubre2026Form(max_cantidad_palabra=cantidad_palabra_maxima)

#     context = {"form": form, "alumno": alumno_id, "fid_actual": fid_actual}
#     return render(request, "fluidez_octubre_2026/evaluacion.html", context)


# def editar_evaluacion(request, alumno_public_id, fid_actual):
#     alumno_id = get_object_or_404(AlumnoFluidez2026, public_id=alumno_public_id)
#     instancia_seccion = get_object_or_404(SeccionFluidez2026, id=alumno_id.seccion_id)
#     instancia_grado = get_object_or_404(GradoFluidez2026, id=instancia_seccion.grado_id)
#     grado_public = instancia_grado.public_id
#     instancia_evaluacion = get_object_or_404(
#         Fluidez_Lectora_Octubre_2026, alumno=alumno_id
#     )
#     if instancia_grado.nombre_grado == "2do Año/Grado":
#         cantidad_palabra_maxima = 196
#     else:
#         cantidad_palabra_maxima = 265
#     form = EvaluacionFluidezOctubre2026Form(
#         instance=instancia_evaluacion, max_cantidad_palabra=cantidad_palabra_maxima
#     )
#     if request.method == "POST":
#         form = EvaluacionFluidezOctubre2026Form(
#             request.POST,
#             instance=instancia_evaluacion,
#             max_cantidad_palabra=cantidad_palabra_maxima,
#         )
#         if form.is_valid():
#             with transaction.atomic():
#                 evaluacion = form.save(commit=False)
#                 evaluacion.alumno = alumno_id
#                 evaluacion.encargado_carga = "DIRECTOR"
#                 if form.cleaned_data["asistencia"] == "AUSENTE":
#                     evaluacion = ausentismo_evaluacion(instancia_evaluacion)
#                 else:
#                     evaluacion.asistencia = "PRESENTE"
#                 evaluacion.save()
#             return redirect(
#                 "evaluaciones_educativas:fluidez_octubre_2026:lista_examen",
#                 fid_actual=fid_actual,
#             )
#     context = {
#         "form": form,
#         "alumno": alumno_id,
#         "fid_actual": fid_actual,
#     }
#     return render(request, "fluidez_octubre_2026/evaluacion.html", context)


# def borrar_registro_alumno(request, alumno_public_id, fid_actual):
#     alumno_id = get_object_or_404(AlumnoFluidez2026, public_id=alumno_public_id)
#     if request.method == "POST":
#         form = BorrarRegistroAlumnoOctubre2026Form(request.POST)
#         if form.is_valid():
#             with transaction.atomic():
#                 eleccion = form.cleaned_data["borrar"]
#                 if eleccion:
#                     if alumno_id.dni:
#                         if TablaTemporalAlumnoFluidez2026.objects.filter(
#                             numero_de_documento=alumno_id.dni
#                         ).exists():
#                             TablaTemporalAlumnoFluidez2026.objects.filter(
#                                 numero_de_documento=alumno_id.dni
#                             ).delete()
#                     alumno_id.delete()
#             return redirect("evaluaciones_educativas:fluidez_octubre_2026:monitoreo_alumno")
#     else:
#         form = BorrarRegistroAlumnoOctubre2026Form()
#     context = {"form": form, "alumno": alumno_id, "fid_actual": fid_actual}
#     return render(request, "fluidez_octubre_2026/borrar_registro_alumno.html", context)


# def monitoreo(request):
#     filtro_escuela = request.GET.get("escuela", "").strip()
#     filtro_sector = request.GET.get("sector", "").strip()
#     filtro_ambito = request.GET.get("ambito", "").strip()
#     filtro_region = request.GET.get("region", "").strip()
#     filtro_cueanexo = request.GET.get("cueanexo", "").strip()

#     queryset = EstablecimientosFluidez2026.objects.prefetch_related(
#         "gradofluidez2026_set"
#     )

#     if filtro_escuela:
#         queryset = queryset.filter(escuela__icontains=filtro_escuela)
#     if filtro_sector:
#         queryset = queryset.filter(sector=filtro_sector)
#     if filtro_ambito:
#         queryset = queryset.filter(ambito=filtro_ambito)
#     if filtro_region:
#         queryset = queryset.filter(region=filtro_region)
#     if filtro_cueanexo:
#         queryset = queryset.filter(cueanexo__icontains=filtro_cueanexo)

#     paginator = Paginator(queryset.order_by("escuela"), 100)
#     page_number = request.GET.get("page")
#     page_obj = paginator.get_page(page_number)

#     query_params = request.GET.copy()
#     if "page" in query_params:
#         del query_params["page"]
#     params_url = query_params.urlencode()

#     cueanexos_pagina = [est.cueanexo for est in page_obj]

#     temporal_qs = TablaTemporalAlumnoFluidez2026.objects.filter(
#         cueanexo__in=cueanexos_pagina
#     ).values("cueanexo", "anio", "numero_de_documento")

#     temporal_dict = {}
#     for item in temporal_qs:
#         k = (str(item["cueanexo"]), item["anio"])
#         if k not in temporal_dict:
#             temporal_dict[k] = set()
#         if item["numero_de_documento"]:
#             temporal_dict[k].add(item["numero_de_documento"])

#     alumnos_qs = AlumnoFluidez2026.objects.filter(
#         seccion__grado__Establecimiento__cueanexo__in=cueanexos_pagina
#     ).values(
#         "dni",
#         "seccion__grado__cueanexo",
#         "seccion__grado__nombre_grado",
#         "fluidez_lectora_octubre_2026__evaluacion_id",
#     )

#     alumnos_por_grado = {}
#     for al in alumnos_qs:
#         k = (al["seccion__grado__cueanexo"], al["seccion__grado__nombre_grado"])
#         if k not in alumnos_por_grado:
#             alumnos_por_grado[k] = []
#         alumnos_por_grado[k].append(al)

#     for est in page_obj:
#         for grado in est.gradofluidez2026_set.all():
#             cueanexo = est.cueanexo
#             nombre_grado = grado.nombre_grado
#             anio_temporal = (
#                 "2do Grado/Año" if nombre_grado == "2do Año/Grado" else "3er Grado/Año"
#             )
#             dnis_temporales = temporal_dict.get((cueanexo, anio_temporal), set())
#             grado.alumnos_esperados = len(dnis_temporales)
#             alumnos_del_grado = alumnos_por_grado.get((cueanexo, nombre_grado), [])

#             dnis_extras = {
#                 al["dni"]
#                 for al in alumnos_del_grado
#                 if al["dni"] and al["dni"] not in dnis_temporales
#             }

#             dnis_interes = dnis_temporales.union(dnis_extras)
#             alumnos_existentes = [
#                 al for al in alumnos_del_grado if al["dni"] in dnis_interes
#             ]

#             grado.alumnos_esperados = len(dnis_temporales)
#             grado.total_alumnos = len(alumnos_existentes)
#             grado.total_evaluados = sum(
#                 1
#                 for al in alumnos_existentes
#                 if al["fluidez_lectora_octubre_2026__evaluacion_id"] is not None
#             )

#     sectores = (
#         EstablecimientosFluidez2026.objects.values_list("sector", flat=True)
#         .distinct()
#         .order_by("sector")
#     )
#     ambitos = (
#         EstablecimientosFluidez2026.objects.values_list("ambito", flat=True)
#         .distinct()
#         .order_by("ambito")
#     )
#     regiones = (
#         EstablecimientosFluidez2026.objects.values_list("region", flat=True)
#         .distinct()
#         .order_by("region")
#     )

#     contexto = {
#         "establecimientos": page_obj,
#         "page_obj": page_obj,
#         "params_url": params_url,
#         "sectores": sectores,
#         "ambitos": ambitos,
#         "regiones": regiones,
#         "valores_filtros": {
#             "escuela": filtro_escuela,
#             "sector": filtro_sector,
#             "ambito": filtro_ambito,
#             "region": filtro_region,
#             "cueanexo": filtro_cueanexo,
#         },
#     }
#     return render(request, "fluidez_octubre_2026/monitoreo.html", contexto)


# def monitoreo_alumno(request):
#     buscar = request.GET.get("buscar", "").strip()
#     alumnos_qs = None

#     if buscar:
#         buscar_limpio = buscar.replace(".", "").replace(" ", "")

#         lista_dnis = list(
#             TablaTemporalAlumnoFluidez2026.objects.filter(
#                 numero_de_documento=buscar_limpio
#             ).values_list("numero_de_documento", flat=True)
#         )

#         lista = list(
#             AlumnoFluidez2026.objects.filter(dni=buscar_limpio).values_list(
#                 "dni", flat=True
#             )
#         )

#         lista_dnis.extend(lista)
#         lista_dnis = list(set(filter(None, lista_dnis)))

#         alumnos_qs = list(
#             AlumnoFluidez2026.objects.filter(dni__in=lista_dnis).select_related(
#                 "seccion__grado__Establecimiento", "fluidez_lectora_octubre_2026"
#             )
#         )

#         temporal_dict = {
#             t.numero_de_documento: t.nombre_institucion
#             for t in TablaTemporalAlumnoFluidez2026.objects.filter(
#                 numero_de_documento__in=lista_dnis
#             ).only("numero_de_documento", "nombre_institucion")
#         }

#         for alumno in alumnos_qs:
#             alumno.establecimiento_original = temporal_dict.get(alumno.dni, "-")

#     contexto = {"alumnos_resultados": alumnos_qs}
#     return render(request, "fluidez_octubre_2026/monitoreo_alumno.html", contexto)


# def completar_carga(request, grado_public_id):
#     estado_carga = True
#     lista_inicial_conteo = None
#     lista_final_conteo = None
#     numero = None
#     instancia_grado = GradoFluidez2026.objects.get(public_id=grado_public_id)

#     if instancia_grado.nombre_grado == "2do Año/Grado":
#         nombre_grado = "2do Grado/Año"
#     else:
#         nombre_grado = "3er Grado/Año"

#     lista_dnis = list(
#         TablaTemporalAlumnoFluidez2026.objects.filter(
#             cueanexo=instancia_grado.cueanexo, anio=nombre_grado
#         ).values_list("numero_de_documento", flat=True)
#     )

#     lista = list(
#         AlumnoFluidez2026.objects.filter(
#             ~Q(dni__in=lista_dnis),
#             seccion__grado__cueanexo=int(instancia_grado.cueanexo),
#             seccion__grado__nombre_grado=instancia_grado.nombre_grado,
#         ).values_list("dni", flat=True)
#     )
#     lista_dnis.extend(lista)
#     alumnos_qs = AlumnoFluidez2026.objects.filter(dni__in=lista_dnis)
#     lista_inicial_conteo = alumnos_qs.count()
#     evaluaciones = Fluidez_Lectora_Octubre_2026.objects.filter(
#         alumno__in=alumnos_qs
#     ).count()
#     lista_final_conteo = evaluaciones
#     if instancia_grado.estado_carga == True:
#         instancia_grado.estado_carga = False
#         instancia_grado.save()
#     else:
#         if lista_inicial_conteo == lista_final_conteo:
#             instancia_grado.estado_carga = True
#             instancia_grado.save()
#         else:
#             estado_carga = False
#             numero = lista_inicial_conteo - lista_final_conteo
#     return JsonResponse(
#         {
#             "es_valido": estado_carga,
#             "nuevo_estado": instancia_grado.estado_carga,
#             "faltantes": numero,
#         }
#     )


# def ausentismo_evaluacion(instancia_evaluacion):
#     evaluacion_campos = instancia_evaluacion._meta.fields
#     for i in evaluacion_campos:
#         if i.name == "asistencia":
#             setattr(instancia_evaluacion, i.name, "AUSENTE")
#         if not i.primary_key and i.null:
#             setattr(instancia_evaluacion, i.name, None)
#     return instancia_evaluacion

#-------------------------------------------------CARGA Y SELECCION DE TABULADOR-------------------------------------------------------------


@login_required
def gestion_tabuladores(request):
    """Página central de gestión de tabuladores para el rol Regional."""
    nivel_acceso = request.user.nivelacceso_id
    if nivel_acceso != "Regional":
        messages.error(request, 'No tienes permiso para acceder a esta página.')
        return redirect(reverse('evaluaciones_educativas:dashboard'))

    cuil = str(request.user.username)
    regiones = obtener_regional(cuil)
    print(regiones)
    if 'R.E. 2' in regiones:
        regiones = ['R.E. 2','SUB. R.E. 2-B']

    # Si el usuario no tiene ninguna región asignada
    if not regiones:
        messages.error(request, 'No se encontró una región asignada a tu usuario.')
        return redirect(reverse('evaluaciones_educativas:dashboard'))

    # ── Selector de región ──────────────────────────────────────────
    # Si viene ?region=X en la URL y es una región válida del usuario → guardar en sesión
    region_solicitada = request.GET.get('region')
    if region_solicitada and region_solicitada in regiones:
        request.session['tab_fluidez_oct26_region'] = region_solicitada

    # Leer la región activa desde sesión; si no hay o ya no es válida, usar la primera
    region = request.session.get('tab_fluidez_oct26_region')
    if not region or region not in regiones:
        region = regiones[0]
        request.session['tab_fluidez_oct26_region'] = region

    # Cupo habilitado para esta región
    cupo_obj = TemporalCargaTabuladoresFluidez2026Eliminar.objects.filter(region=region).first()
    tabuladores_permitidos = cupo_obj.tabuladores_permitidos if cupo_obj else 0

    # Cuántos ya fueron cargados para esta región
    tabuladores_cargados = TabuladoresFluidezOctubre2026.objects.filter(region=region).count()

    puede_cargar = tabuladores_permitidos > 0 and tabuladores_cargados < tabuladores_permitidos

    # Lista de tabuladores ya cargados para mostrar en la tabla
    tabuladores_list = TabuladoresFluidezOctubre2026.objects.filter(region=region).order_by('apellido', 'nombre')

    context = {
        'region':                 region,
        'regiones':               regiones,          # todas las regiones del usuario
        'multiples_regiones':     len(regiones) > 1,
        'tabuladores_permitidos': tabuladores_permitidos,
        'tabuladores_cargados':   tabuladores_cargados,
        'puede_cargar':           puede_cargar,
        'tabuladores_list':       tabuladores_list,
    }
    return render(request, 'fluidez_octubre_2026/gestion_tabuladores.html', context)


@login_required
def carga_tabulador(request):
    """Formulario para cargar un nuevo tabulador (solo Regional con cupo disponible)."""
    nivel_acceso = request.user.nivelacceso_id
    if nivel_acceso != "Regional":
        messages.error(request, 'No tienes permiso para acceder a esta página.')
        return redirect(reverse('evaluaciones_educativas:dashboard'))

    cuil = str(request.user.username)
    regiones = obtener_regional(cuil)
    #print(regiones)
    

    if not regiones:
        messages.error(request, 'No se encontró una región asignada a tu usuario.')
        return redirect(reverse('evaluaciones_educativas:fluidez_octubre_2026:gestion_tabuladores'))

    # Leer la región activa desde sesión (coherente con gestion_tabuladores)
    region = request.session.get('tab_fluidez_oct26_region')
    if not region or region not in regiones:
        region = regiones[0]
        request.session['tab_fluidez_oct26_region'] = region

    # Verificar cupo
    cupo_obj = TemporalCargaTabuladoresFluidez2026Eliminar.objects.filter(region=region).first()
    tabuladores_permitidos = cupo_obj.tabuladores_permitidos if cupo_obj else 0
    tabuladores_cargados   = TabuladoresFluidezOctubre2026.objects.filter(region=region).count()

    if tabuladores_permitidos == 0 or tabuladores_cargados >= tabuladores_permitidos:
        messages.error(request, f'No podés cargar más tabuladores. La región {region} ya tiene el cupo completo ({tabuladores_cargados}/{tabuladores_permitidos}).')
        return redirect(reverse('evaluaciones_educativas:fluidez_octubre_2026:gestion_tabuladores'))

    if request.method == 'POST':
        form = TabuladorFluidezOctubreForm(request.POST)
        if form.is_valid():
            tabulador = form.save(commit=False)
            tabulador.region = region          # asignar la región automáticamente
            tabulador.lista_cueanexos = []     # inicializar vacío, se completa en el 2do botón
            tabulador.save()
            messages.success(request, f'Tabulador {tabulador.apellido}, {tabulador.nombre} (CUIL: {tabulador.cuil}) cargado correctamente.')
            return redirect(reverse('evaluaciones_educativas:fluidez_octubre_2026:gestion_tabuladores'))
    else:
        form = TabuladorFluidezOctubreForm()

    context = {
        'form':                   form,
        'region':                 region,
        'tabuladores_permitidos': tabuladores_permitidos,
        'tabuladores_cargados':   tabuladores_cargados,
        'cupo_restante':          tabuladores_permitidos - tabuladores_cargados,
    }
    return render(request, 'fluidez_octubre_2026/carga_tabulador.html', context)



@login_required
def eliminar_tabulador(request, cuil_tabulador):
    """Elimina un tabulador cargado (solo Regional, y solo de su propia región)."""
    nivel_acceso = request.user.nivelacceso_id
    if nivel_acceso != "Regional":
        messages.error(request, 'No tienes permiso para acceder a esta página.')
        return redirect(reverse('evaluaciones_educativas:dashboard'))

    cuil_usuario = str(request.user.username)
    regiones = obtener_regional(cuil_usuario)
    if not regiones:
        messages.error(request, 'No se encontró una región asignada a tu usuario.')
        return redirect(reverse('evaluaciones_educativas:dashboard'))

    region = request.session.get('tab_fluidez_oct26_region')
    if not region or region not in regiones:
        region = regiones[0]
        request.session['tab_fluidez_oct26_region'] = region

    if request.method == 'POST':
        tabulador = TabuladoresFluidezOctubre2026.objects.filter(cuil=cuil_tabulador, region=region).first()
        if tabulador:
            nombre_completo = f'{tabulador.apellido}, {tabulador.nombre}'
            tabulador.delete()
            messages.success(request, f'Tabulador {nombre_completo} (CUIL: {cuil_tabulador}) eliminado correctamente.')
        else:
            messages.warning(request, 'El tabulador ya no existe.')

    return redirect(reverse('evaluaciones_educativas:fluidez_octubre_2026:gestion_tabuladores'))


@login_required
def asignacion_tabulador(request, cuil_tabulador):
    """Vista para asignar/quitar escuelas a un tabulador específico."""
    nivel_acceso = request.user.nivelacceso_id
    if nivel_acceso != "Regional":
        messages.error(request, 'No tienes permiso para acceder a esta página.')
        return redirect(reverse('evaluaciones_educativas:dashboard'))

    # Obtener región activa desde sesión
    cuil_usuario = str(request.user.username)
    regiones = obtener_regional(cuil_usuario)
    if not regiones:
        messages.error(request, 'No se encontró una región asignada a tu usuario.')
        return redirect(reverse('evaluaciones_educativas:dashboard'))
    

    region = request.session.get('tab_fluidez_oct26_region')
    if not region or region not in regiones:
        region = regiones[0]
        request.session['tab_fluidez_oct26_region'] = region

    # Obtener el tabulador — debe pertenecer a la región activa
    tabulador = get_object_or_404(TabuladoresFluidezOctubre2026, cuil=cuil_tabulador, region=region)

    # ── POST: agregar o quitar una escuela ────────────────────────────
    if request.method == 'POST':
        accion   = request.POST.get('accion')
        cueanexo = request.POST.get('cueanexo', '').strip()

        nivel, texto = 'error', 'Acción no válida.'

        if accion == 'agregar' and cueanexo:
            ya_asignada = TabuladoresFluidezOctubre2026.objects.filter(
                region=region,
                lista_cueanexos__contains=[cueanexo]
            ).exclude(cuil=cuil_tabulador).exists()

            if ya_asignada:
                nivel, texto = 'error', f'La escuela {cueanexo} ya está asignada a otro tabulador de esta región.'
            else:
                lista = list(tabulador.lista_cueanexos or [])
                if cueanexo not in lista:
                    lista.append(cueanexo)
                    tabulador.lista_cueanexos = lista
                    tabulador.save(update_fields=['lista_cueanexos'])
                    nivel, texto = 'success', f'Escuela {cueanexo} asignada correctamente.'
                else:
                    nivel, texto = 'warning', f'La escuela {cueanexo} ya estaba en la lista.'

        elif accion == 'quitar' and cueanexo:
            lista = list(tabulador.lista_cueanexos or [])
            if cueanexo in lista:
                lista.remove(cueanexo)
                tabulador.lista_cueanexos = lista
                tabulador.save(update_fields=['lista_cueanexos'])
                nivel, texto = 'success', f'Escuela {cueanexo} quitada correctamente.'
            else:
                nivel, texto = 'warning', f'La escuela {cueanexo} no estaba en la lista.'

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'ok': nivel in ('success', 'warning'),
                'nivel': nivel,
                'mensaje': texto,
                'cueanexo': cueanexo,
                'accion': accion,
            }, status=200 if nivel != 'error' else 409)

        getattr(messages, nivel)(request, texto)
        return redirect(reverse(
            'evaluaciones_educativas:fluidez_octubre_2026:asignacion_tabulador',
            kwargs={'cuil_tabulador': cuil_tabulador}
        ))

    # ── GET: construir listas de escuelas ────────────────────────────
    # Refrescar el tabulador desde DB para tener el estado más reciente
    tabulador.refresh_from_db()
    cueanexos_propios = [str(c) for c in (tabulador.lista_cueanexos or [])]

    #print(f"[asignacion] GET region={region} cueanexos_propios={cueanexos_propios}")

    # Todos los cueanexos ocupados en la región (por cualquier tabulador)
    cueanexos_ocupados = set()
    for tab in TabuladoresFluidezOctubre2026.objects.filter(region=region):
        for c in (tab.lista_cueanexos or []):
            cueanexos_ocupados.add(str(c))

    # Escuelas disponibles en la región con la oferta requerida
    todas_escuelas = list(
        CapaUnicaOfertas.objects.filter(
            region_loc=region,
            oferta__icontains='Común - Primaria de 7 años'
        ).values('cueanexo', 'nom_est', 'localidad').distinct().order_by('nom_est')
    )
    # Normalizar cueanexo a string: la columna puede devolver int/Decimal
    # según el driver de DB, mientras que lista_cueanexos siempre guarda strings.
    for e in todas_escuelas:
        e['cueanexo'] = str(e['cueanexo']).strip()

    #print(f"[asignacion] todas_escuelas count={len(todas_escuelas)}")

    # ── Escuelas asignadas: buscar directamente por cueanexo (sin filtro región)
    # para no depender de que region_loc coincida exactamente.
    if cueanexos_propios:
        escuelas_asignadas_qs = list(
            CapaUnicaOfertas.objects.filter(
                cueanexo__in=cueanexos_propios,
                oferta__icontains='Común - Primaria de 7 años'
            ).values('cueanexo', 'nom_est', 'localidad').distinct().order_by('nom_est')
        )
        for e in escuelas_asignadas_qs:
            e['cueanexo'] = str(e['cueanexo']).strip()
        # Incluir cueanexos que no se encuentren en la tabla (como fallback)
        cueanexos_encontrados = {e['cueanexo'] for e in escuelas_asignadas_qs}
        for c in cueanexos_propios:
            if c not in cueanexos_encontrados:
                escuelas_asignadas_qs.append({'cueanexo': c, 'nom_est': f'(Escuela {c})', 'localidad': ''})
        escuelas_asignadas = escuelas_asignadas_qs
    else:
        escuelas_asignadas = []

    # Disponibles: las que no están ocupadas por ningún tabulador
    escuelas_disponibles = [e for e in todas_escuelas if e['cueanexo'] not in cueanexos_ocupados]

    #print(f"[asignacion] asignadas={len(escuelas_asignadas)} disponibles={len(escuelas_disponibles)}")

    context = {
        'tabulador':            tabulador,
        'region':               region,
        'regiones':             regiones,
        'multiples_regiones':   len(regiones) > 1,
        'escuelas_asignadas':   escuelas_asignadas,
        'escuelas_disponibles': escuelas_disponibles,
        'total_asignadas':      len(escuelas_asignadas),
        'total_disponibles':    len(escuelas_disponibles),
    }
    return render(request, 'fluidez_octubre_2026/asignacion_tabulador.html', context)


