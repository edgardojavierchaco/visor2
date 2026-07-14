from apps.evaluaciones_educativas.models.diagnostico_2026 import Establecimientos2026, EvaluacionDiagnostica2026, Año2026
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
from django.http import FileResponse, JsonResponse, Http404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
import io
import re
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from ..forms import MatematicaForm, LenguaForm, AlumnoForm
from ..models import Alumno2026, Matematica2026, Lengua2026, Seccion2026, TablaTemporalAlumno
from ..utils import utilidades
from django.core.paginator import Paginator
from apps.consultasge.models import CapaUnicaOfertas
from django.core.exceptions import PermissionDenied

def _orden_pregunta_field(field):
	numeros = re.findall(r'\d+', field.name)
	return [int(n) for n in numeros] if numeros else [0]


def _respuestas_formulario(form):
	"""Valores actuales de cada pregunta (para marcar radios en la plantilla)."""
	return {
		name: form[name].value()
		for name in form.fields
		if name.startswith('pregunta_')
	}


def _limpiar_preguntas_si_ausente(examen):
	"""Si el alumno estuvo ausente, no se guardan respuestas de ítems."""
	if examen.asistencia != 'AUSENTE':
		return
	for field in examen._meta.get_fields():
		if hasattr(field, 'name') and field.name.startswith('pregunta_'):
			setattr(examen, field.name, None)


def _guardar_examen(form, alumno):

	#========================== Lógica para guardar resultados de preguntas cerradas: =============================

	# ── Claves de respuesta por modelo ───────────────────────────────────────────

	CLAVE_MATEMATICA = {
		'A': {'pregunta_3': ('A', 7), 'pregunta_8': ('C', 8), 'pregunta_10': ('A', 11)},
		'B': {'pregunta_3': ('A', 7), 'pregunta_8': ('B', 8), 'pregunta_10': ('A', 11)},
	}

	CLAVE_LENGUA = {
		'A': {
			'pregunta_1':  ('B', 1.50), 'pregunta_2':  ('B', 1.50), 'pregunta_3':  ('B', 2.50),
			'pregunta_4':  ('A', 2.50), 'pregunta_5':  ('B', 4.50), 'pregunta_6':  ('C', 4.50),
			'pregunta_7':  ('B', 6.00), 'pregunta_8':  ('B', 1.50), 'pregunta_9':  ('D', 4.50),
			'pregunta_10': ('A', 5.50), 'pregunta_12': ('A', 1.50), 'pregunta_13': ('B', 2.50),
			'pregunta_14': ('B', 5.50), 'pregunta_15': ('A', 5.50), 'pregunta_16': ('D', 4.50),
			'pregunta_17': ('A', 4.50), 'pregunta_18': ('C', 2.50), 'pregunta_19': ('A', 4.50),
			'pregunta_20': ('A', 4.50), 'pregunta_21': ('A', 5.50),
		},
		'B': {
			'pregunta_1':  ('C', 1.50), 'pregunta_2':  ('D', 1.50), 'pregunta_3':  ('D', 2.50),
			'pregunta_4':  ('D', 2.50), 'pregunta_5':  ('C', 4.50), 'pregunta_6':  ('D', 4.50),
			'pregunta_7':  ('C', 6.00), 'pregunta_8':  ('A', 1.50), 'pregunta_9':  ('A', 4.50),
			'pregunta_10': ('D', 5.50), 'pregunta_12': ('D', 1.50), 'pregunta_13': ('C', 2.50),
			'pregunta_14': ('C', 5.50), 'pregunta_15': ('B', 5.50), 'pregunta_16': ('C', 4.50),
			'pregunta_17': ('C', 4.50), 'pregunta_18': ('B', 2.50), 'pregunta_19': ('C', 4.50),
			'pregunta_20': ('D', 4.50), 'pregunta_21': ('C', 5.50),
		},
	}


# ── Helpers para obtener el puntaje de cada pregunta ─────────────────────────

	def _puntaje_pregunta_matematica(examen, nombre_campo):
		"""
		Para preguntas cerradas (3, 8, 10): devuelve el puntaje si la respuesta es correcta.
		Para el resto: convierte el valor del CharField a float.
		"""
		valor = getattr(examen, nombre_campo, None)
		if valor is None:
			return 0.0

		clave = CLAVE_MATEMATICA.get(examen.modelo, {})
		if nombre_campo in clave:
			respuesta_correcta, puntos = clave[nombre_campo]
			return float(puntos) if valor == respuesta_correcta else 0.0

		# Preguntas numéricas: el valor ya es el puntaje (ej. "6,5" → 6.5)
		try:
			return float(str(valor).replace(',', '.'))
		except (ValueError, TypeError):
			return 0.0


	def _puntaje_pregunta_lengua(examen, nombre_campo):
		"""
		Para preguntas de opción múltiple (1-10, 12-21): puntaje si es correcta.
		Para preguntas compuestas (11_x, 22_x): el valor ya es el puntaje.
		"""
		valor = getattr(examen, nombre_campo, None)
		if valor is None:
			return 0.0

		clave = CLAVE_LENGUA.get(examen.modelo, {})
		if nombre_campo in clave:
			respuesta_correcta, puntos = clave[nombre_campo]
			return float(puntos) if valor == respuesta_correcta else 0.0

		# Preguntas compuestas (11_x, 22_x): el valor ya es el puntaje
		try:
			return float(str(valor).replace(',', '.'))
		except (ValueError, TypeError):
			return 0.0


	# ── Cálculo de correcciones ───────────────────────────────────────────────────

	def _calcular_correcciones_matematica(examen):
		"""Calcula y asigna los campos de corrección del examen de Matemática."""
		if examen.asistencia == 'AUSENTE':
			examen.correcion_comunicacion  = None
			examen.correcion_reconocimiento = None
			examen.correcion_resolucion    = None
			examen.total_puntaje           = None
			return

		p = lambda campo: _puntaje_pregunta_matematica(examen, campo)

		examen.correcion_comunicacion   = p('pregunta_2') + p('pregunta_5') + p('pregunta_12') + p('pregunta_10')
		examen.correcion_reconocimiento = p('pregunta_1') + p('pregunta_3') + p('pregunta_8')  + p('pregunta_11')
		examen.correcion_resolucion     = p('pregunta_4') + p('pregunta_6') + p('pregunta_7')  + p('pregunta_9')
		examen.total_puntaje = (
			examen.correcion_comunicacion +
			examen.correcion_reconocimiento +
			examen.correcion_resolucion
		)


	def _calcular_correcciones_lengua(examen):
		"""Calcula y asigna los campos de corrección del examen de Lengua."""
		if examen.asistencia == 'AUSENTE':
			examen.correcion_reflexion      = None
			examen.correcion_interpretacion = None
			examen.correcion_extraccion     = None
			examen.correcion_escritura      = None
			examen.total_puntaje            = None
			return

		p = lambda campo: _puntaje_pregunta_lengua(examen, campo)

		examen.correcion_reflexion = (
			p('pregunta_8')  + p('pregunta_10') + p('pregunta_16') + p('pregunta_18') +
			p('pregunta_19') + p('pregunta_20') + p('pregunta_21')
		)
		examen.correcion_interpretacion = (
			p('pregunta_3')  + p('pregunta_4')  + p('pregunta_6') +
			p('pregunta_7')  + p('pregunta_14') + p('pregunta_17')
		)
		examen.correcion_extraccion = (
			p('pregunta_1')  + p('pregunta_2')  + p('pregunta_5') + p('pregunta_9') +
			p('pregunta_12') + p('pregunta_13') + p('pregunta_15')
		)
		# Corrección escritura: preguntas compuestas 11 y 22
		examen.correcion_escritura = (
			p('pregunta_11_1') + p('pregunta_11_2') + p('pregunta_11_3') + p('pregunta_11_4') +
			p('pregunta_22_1') + p('pregunta_22_2') + p('pregunta_22_3')
		)
		examen.total_puntaje = (
			examen.correcion_reflexion +
			examen.correcion_interpretacion +
			examen.correcion_extraccion +
			examen.correcion_escritura
		)

	#========================== Fin de lógica para guardar resultados de preguntas cerradas: =============================

	examen = form.save(commit=False)
	examen.alumno = alumno
	if not examen.encargado_carga:
		examen.encargado_carga = 'DIRECTOR'
	_limpiar_preguntas_si_ausente(examen)

	if isinstance(examen, Matematica2026):
		_calcular_correcciones_matematica(examen)
	elif isinstance(examen, Lengua2026):
		_calcular_correcciones_lengua(examen)

	examen.save()
	return examen


def _obtener_estructura_preguntas_lengua():
	"""Retorna estructura de preguntas de Lengua con puntajes"""
	estructura = {
		'preguntas_simples': [
			{'num': i, 'puntajes': ['A', 'B', 'C', 'D', 'OMITIÓ']} 
			for i in range(1, 11)
		] + [
			{'num': i, 'puntajes': ['A', 'B', 'C', 'D', 'OMITIÓ']} 
			for i in range(12, 22)
		],
		'preguntas_compuestas': {
			11: {
				'titulo': 'Pregunta 11',
				'partes': {
					'11_1': {'label': '11.1. Elección de la opción', 'puntajes': [2, 0]},
					'11_2': {'label': '11.2. Justificación', 'puntajes': [5.65, 2.80, 0]},
					'11_3': {'label': '11.3. Normativa - Puntuación', 'puntajes': [2.30, 1.15, 0]},
					'11_4': {'label': '11.4. Normativa - Ortografía', 'puntajes': [2.30, 1.15, 0]},
				},
				'total': 13.25,
			},
			22: {
				'titulo': 'Pregunta 22',
				'partes': {
					'22_1': {'label': '22.1. Contenido, autores y obras', 'puntajes': [7.65, 3.80, 0]},
					'22_2': {'label': '22.2. Normativa - Puntuación', 'puntajes': [2.30, 1.15, 0]},
					'22_3': {'label': '22.3. Normativa - Ortografía', 'puntajes': [2.30, 1.15, 0]},
				},
				'total': 12.50,
			}
		},
		'total_puntos': 100
	}
	return estructura


def _obtener_estructura_preguntas_matematica():
	"""Retorna estructura de preguntas de Matemática con puntajes"""
	estructura = {
		'preguntas': [
			{'num': 1, 'puntajes': [6.5, 3.25, 0]},
			{'num': 2, 'puntajes': [6, 4, 2, 0]},
			{'num': 3, 'puntajes': ['A', 'B', 'C', 'OMITIÓ']},  # Respuesta libre, mostrar opciones
			{'num': 4, 'puntajes': [6, 3, 0]},
			{'num': 5, 'puntajes': [7, 3.5, 0]},
			{'num': 6, 'puntajes': [8, 4, 0]},
			{'num': 7, 'puntajes': [10, 5, 0]},
			{'num': 8, 'puntajes': ['A', 'B', 'C', 'OMITIÓ']},
			{'num': 9, 'puntajes': [11, 5.50, 0]},
			{'num': 10, 'puntajes': ['A', 'B', 'C', 'OMITIÓ']},
			{'num': 11, 'puntajes': [10.5, 7, 3.5, 0]},
			{'num': 12, 'puntajes': [9, 4.5, 0]},
		],
		'total_puntos': 100
	}
	return estructura


@login_required
def inicio(request):
	usuario = request.user
	name = usuario.username
	#--- logica para no permitir ingreso a no autorizados--------------
	cuil_con_caracter = f"{name[:2]}-{name[2:10]}-{name[10:]}"
	if not CapaUnicaOfertas.objects.filter(resploc_cuitcuil=cuil_con_caracter, oferta__icontains='Secundaria Completa req. 7 años').exists():
		raise PermissionDenied("No tienes permiso para acceder a esta sección.")
	user_cueanexos = utilidades.obtener_cueanexos(usuario.username)
	selected_cue = request.GET.get('cueanexo')
	if not selected_cue and user_cueanexos:
		selected_cue = str(user_cueanexos[0])

	if selected_cue not in [str(c) for c in user_cueanexos]:
		selected_cue = str(user_cueanexos[0]) if user_cueanexos else None

	print("CUEANEXOS del usuario:", user_cueanexos)
	print("CUE seleccionado:", selected_cue)

	search_query = request.GET.get('search', '').strip()
	pagina       = request.GET.get('pagina', 1)

	if selected_cue:
		lista_dnis = list(
			TablaTemporalAlumno.objects
			.filter(cueanexo=selected_cue)
			.values_list('numero_de_documento', flat=True)
		)
		lista = list(
			Alumno2026.objects
			.filter(~Q(dni__in=lista_dnis),seccion__año__Establecimiento__cueanexo=int(selected_cue))
			.select_related('seccion__año', 'seccion__año__Establecimiento')
			.values_list('dni', flat=True)
		)
		lista_dnis.extend(lista)

		alumnos_qs = Alumno2026.objects.filter(dni__in=lista_dnis)

		if search_query:
			alumnos_qs = alumnos_qs.filter(
				Q(nombre__icontains=search_query) |
				Q(apellido__icontains=search_query) |
				Q(dni__icontains=search_query)
			)

		alumnos_qs = alumnos_qs.order_by('apellido', 'nombre')
	else:
		alumnos_qs = Alumno2026.objects.none()

	print("Total alumnos encontrados:", alumnos_qs.count())

	# ── Paginación ANTES del loop para procesar solo 10 registros ─────────────
	paginator = Paginator(alumnos_qs, 10)
	
	try:
		page_obj = paginator.page(pagina)
	except Exception:
		page_obj = paginator.page(1)

	# ── Optimización: traer los exámenes de la página actual en 2 queries ─────
	#    en lugar de 2 queries por alumno (N*2 queries → 2 queries fijas)
	alumnos_pagina = list(page_obj.object_list)
	ids_pagina     = [a.pk for a in alumnos_pagina]

	ids_con_matematica = set(
		Matematica2026.objects.filter(alumno_id__in=ids_pagina)
		.values_list('alumno_id', flat=True)
	)
	ids_con_lengua = set(
		Lengua2026.objects.filter(alumno_id__in=ids_pagina)
		.values_list('alumno_id', flat=True)
	)

	lista_alumnos_procesada = []
	for alumno in alumnos_pagina:
		tiene_datos_completos = all([
			alumno.dni and len(alumno.dni) >= 7,
			alumno.nombre,
			alumno.apellido,
			alumno.discapacidad,
			alumno.comunidad_indigena,
		])
		tiene_matematica = alumno.pk in ids_con_matematica
		tiene_lengua     = alumno.pk in ids_con_lengua

		lista_alumnos_procesada.append({
			'objeto':          alumno,
			'datos_validados': tiene_datos_completos,
			'tiene_matematica': tiene_matematica,
			'tiene_lengua':     tiene_lengua,
			'examen_completo':  tiene_matematica and tiene_lengua,
		})

	# ── Secciones disponibles ─────────────────────────────────────────────────
	secciones_disponibles = {}
	if selected_cue:
		qs_secciones = Seccion2026.objects.filter(
			año__Establecimiento__cueanexo=selected_cue
		)
		secciones_disponibles = {
			'secciones': list(qs_secciones.values_list('seccion', flat=True).distinct()),
			'turnos':    list(qs_secciones.values_list('turno',   flat=True).distinct()),
		}

	context = {
		'alumnos':              lista_alumnos_procesada,
		'page_obj':             page_obj,
		'cue_escuela':          selected_cue,
		'user_cueanexos':       user_cueanexos,
		'selected_cue':         selected_cue,
		'search_query':         search_query,
		'opciones_seccion':     Seccion2026.OPCIONES_SECCION,
		'opciones_turno':       Seccion2026.OPCIONES_TURNO,
		'secciones_disponibles': secciones_disponibles,
		'opciones_comunidad_indigena': Alumno2026.OPCIONES_COMUNIDAD_INDIGENA,
		'opciones_discapacidad':       Alumno2026.OPCIONES_DISCAPACIDAD,   
	}

	return render(request, "diagnostico_2026/inicio.html", context)


@login_required
def realizar_carga(request):
	usuario = request.user
	user_cueanexos = utilidades.obtener_cueanexos(usuario.username)
	selected_cue = request.GET.get('cueanexo')
	if selected_cue not in [str(c) for c in user_cueanexos]:
		selected_cue = str(user_cueanexos[0]) if user_cueanexos else None

	return render(request, 'diagnostico_2026/realizar_carga.html', {
		'user_cueanexos': user_cueanexos,
		'selected_cue': selected_cue,
	})


@login_required
def examenes_lista(request, materia):
	usuario = request.user
	user_cueanexos = utilidades.obtener_cueanexos(usuario.username)
	selected_cue = request.GET.get('cueanexo')
	if selected_cue not in [str(c) for c in user_cueanexos]:
		selected_cue = str(user_cueanexos[0]) if user_cueanexos else None

	if materia == 'matematica':
		examen_model = Matematica2026
		materia_nombre = 'Matemática'
	elif materia == 'lengua':
		examen_model = Lengua2026
		materia_nombre = 'Lengua'
	else:
		return redirect('evaluaciones_educativas:diagnostico_2026:realizar_carga')
	estado_carga,numero = boton_completar_carga(selected_cue, materia_nombre)
	alumnos_qs = Alumno2026.objects.filter(
		seccion__año__Establecimiento__cueanexo=selected_cue
	).select_related('seccion__año').order_by('apellido', 'nombre') if selected_cue else Alumno2026.objects.none()

	pregunta_campos = [f for f in examen_model._meta.get_fields()
					   if hasattr(f, 'choices') and f.choices and f.name.startswith('pregunta_')]
	pregunta_campos = sorted(pregunta_campos, key=_orden_pregunta_field)
	pregunta_encabezados = [f.name.replace('_', ' ').title() for f in pregunta_campos]

	# ── Paginación ────────────────────────────────────────────────────────────
	try:
		pagina = int(request.GET.get('pagina', 1))
		if pagina < 1:
			pagina = 1
	except (ValueError, TypeError):
		pagina = 1

	paginator = Paginator(alumnos_qs, 10)
	page_obj  = paginator.get_page(pagina)

	# ── Traer exámenes solo de los alumnos de la página actual (1 query) ──────
	ids_pagina = [a.pk for a in page_obj.object_list]
	examenes_map = {
		e.alumno_id: e
		for e in examen_model.objects.filter(alumno_id__in=ids_pagina)
	}

	filas = []
	for alumno in page_obj.object_list:
		examen = examenes_map.get(alumno.pk)
		filas.append({
			'alumno':     alumno,
			'examen':     examen,
			'modelo':     examen.modelo    if examen else '',
			'ausentismo': examen.asistencia if examen else '',
			'preguntas':  [getattr(examen, campo.name) if examen else '' for campo in pregunta_campos],
		})

	return render(request, 'diagnostico_2026/examenes_lista.html', {
		'estado_carga':estado_carga,
		'numero':	numero,
		'filas':               filas,
		'page_obj':            page_obj,
		'materia_nombre':      materia_nombre,
		'materia':             materia,
		'selected_cue':        selected_cue,
		'pregunta_encabezados': pregunta_encabezados,
	})


@login_required
def descargar_examenes(request, materia):
	usuario = request.user
	user_cueanexos = utilidades.obtener_cueanexos(usuario.username)
	selected_cue = request.GET.get('cueanexo')
	if selected_cue not in [str(c) for c in user_cueanexos]:
		selected_cue = str(user_cueanexos[0]) if user_cueanexos else None

	if materia == 'matematica':
		examen_model = Matematica2026
		materia_nombre = 'Matemática'
	elif materia == 'lengua':
		examen_model = Lengua2026
		materia_nombre = 'Lengua'
	else:
		return redirect('evaluaciones_educativas:diagnostico_2026:realizar_carga')

	alumnos_qs = Alumno2026.objects.filter(
		seccion__año__Establecimiento__cueanexo=selected_cue
	).select_related('seccion__año').order_by('apellido', 'nombre') if selected_cue else Alumno2026.objects.none()

	pregunta_campos = [f for f in examen_model._meta.get_fields()
					   if hasattr(f, 'choices') and f.choices and f.name.startswith('pregunta_')]
	pregunta_campos = sorted(pregunta_campos, key=_orden_pregunta_field)
	
	pregunta_encabezados = []
	for f in pregunta_campos:
			nombre = f.name.replace('pregunta_', '')
			partes = nombre.split('_')
			if len(partes) == 1:
					encabezado = f'P{partes[0]}'
			else:
					encabezado = f'P{partes[0]}.{partes[1]}'
			pregunta_encabezados.append(encabezado)

	data = [
		['Apellido', 'Nombre', 'DNI', 'Sección', 'Turno', 'Modelo', 'Asistencia'] + pregunta_encabezados
	]

	for alumno in alumnos_qs:
		examen = examen_model.objects.filter(alumno=alumno).first()
		row = [
			alumno.apellido,
			alumno.nombre,
			alumno.dni,
			alumno.seccion.seccion if alumno.seccion else '',
			alumno.seccion.turno if alumno.seccion else '',
			examen.modelo if examen else '',
			examen.asistencia if examen else '',
		]
		row.extend([getattr(examen, campo.name) if examen else '' for campo in pregunta_campos])
		data.append(row)

	buffer = io.BytesIO()
	doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=20, rightMargin=20, topMargin=20, bottomMargin=20)
	styles = getSampleStyleSheet()
	story = []

	story.append(Paragraph(f"Lista de exámenes - {materia_nombre}", styles['Title']))
	story.append(Paragraph(f"CUE/ANEXO: {selected_cue or 'N/A'}", styles['Normal']))
	story.append(Spacer(1, 12))

	ancho_disponible = landscape(A4)[0] - 35
	ancho_fijos = 55 + 55 + 45 + 35 + 35 + 35 + 50
	ancho_preguntas = (ancho_disponible - ancho_fijos) / len(pregunta_campos)
	col_widths = [55, 55, 45, 35, 35, 35, 50] + [ancho_preguntas] * len(pregunta_campos)
	table = Table(data, colWidths=col_widths, repeatRows=1)
	table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E9ECEF')),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
    ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
    ('FONTSIZE', (0, 0), (-1, 0), 7),
    ('FONTSIZE', (0, 1), (-1, -1), 6),
    ('LEFTPADDING', (0, 0), (-1, -1), 2),
    ('RIGHTPADDING', (0, 0), (-1, -1), 2),
    ('TOPPADDING', (0, 0), (-1, -1), 2),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ('WORDWRAP', (0, 0), (-1, -1), True),
]))

	story.append(table)
	doc.build(story)
	buffer.seek(0)

	filename = f"examenes_{materia}_{selected_cue or 'todos'}.pdf"
	return FileResponse(buffer, as_attachment=True, filename=filename)


@login_required
def eliminar_examen(request, alumno_uuid, materia):
	alumno = get_object_or_404(Alumno2026, public_id=alumno_uuid)
	selected_cue = request.GET.get('cueanexo')

	if materia == 'matematica':
		examen = Matematica2026.objects.filter(alumno=alumno).first()
	elif materia == 'lengua':
		examen = Lengua2026.objects.filter(alumno=alumno).first()
	else:
		return redirect('evaluaciones_educativas:diagnostico_2026:realizar_carga')

	if examen:
		examen.delete()

	redirect_url = reverse('evaluaciones_educativas:diagnostico_2026:examenes_lista', kwargs={'materia': materia})
	if selected_cue:
		return redirect(f"{redirect_url}?cueanexo={selected_cue}")
	return redirect(redirect_url)


@login_required
def actualizar_seccion(request, alumno_uuid):
	"""Actualiza la sección, turno, comunidad_indigena y discapacidad de un alumno."""
	if request.method == 'POST':
		alumno = get_object_or_404(Alumno2026, public_id=alumno_uuid)

		nueva_seccion = request.POST.get('seccion')
		nuevo_turno   = request.POST.get('turno')
		comunidad     = request.POST.get('comunidad_indigena')
		discapacidad  = request.POST.get('discapacidad')

		# Actualizar sección y turno
		if nueva_seccion and nuevo_turno:
			if alumno.seccion:
					cueanexo = alumno.seccion.año.cueanexo
			else:
					cueanexo = request.POST.get('cueanexo')
					
			año_actual = Año2026.objects.get(cueanexo=cueanexo)
			seccion_obj = Seccion2026.objects.get(
					seccion=nueva_seccion,
					año=año_actual,
					turno=nuevo_turno
			)
			alumno.seccion = seccion_obj

		# Actualizar comunidad indígena (solo valores válidos)
		valores_comunidad = [v for v, _ in Alumno2026.OPCIONES_COMUNIDAD_INDIGENA]
		if comunidad in valores_comunidad:
			alumno.comunidad_indigena = comunidad

		# Actualizar discapacidad (solo valores válidos)
		valores_discapacidad = [v for v, _ in Alumno2026.OPCIONES_DISCAPACIDAD]
		if discapacidad in valores_discapacidad:
			alumno.discapacidad = discapacidad

		alumno.save()

	selected_cue = request.POST.get('cueanexo', '')
	url = reverse('evaluaciones_educativas:diagnostico_2026:inicio')
	return redirect(f"{url}?cueanexo={selected_cue}")


@login_required
def cargar_examen(request, alumno_uuid, materia):
	alumno = get_object_or_404(Alumno2026, public_id=alumno_uuid)
	return_cueanexo = request.GET.get('cueanexo') or request.POST.get('cueanexo')
	existing_examen = None

	if materia == 'matematica':
		existing_examen = Matematica2026.objects.filter(alumno=alumno).first()
		form_class = MatematicaForm
		template_materia = "Matemática"
		estructura_preguntas = _obtener_estructura_preguntas_matematica()
	elif materia == 'lengua':
		existing_examen = Lengua2026.objects.filter(alumno=alumno).first()
		form_class = LenguaForm
		template_materia = "Lengua"
		estructura_preguntas = _obtener_estructura_preguntas_lengua()
	else:
		return redirect('evaluaciones_educativas:diagnostico_2026:inicio')

	form = form_class(request.POST or None, instance=existing_examen)
	modo_edicion = bool(existing_examen)

	if request.method == 'POST':
		if form.is_valid():
			_guardar_examen(form, alumno)
			messages.success(request, f'Examen de {template_materia} guardado correctamente.')
			redirect_url = reverse('evaluaciones_educativas:diagnostico_2026:examenes_lista', kwargs={'materia': materia})
			if return_cueanexo:
				return redirect(f"{redirect_url}?cueanexo={return_cueanexo}")
			return redirect(redirect_url)
		messages.error(request, 'No se pudo guardar el examen. Revise los campos indicados.')

	if request.method == 'GET' and existing_examen:
		redirect_url = reverse('evaluaciones_educativas:diagnostico_2026:editar_examen', kwargs={'alumno_uuid': alumno_uuid, 'materia': materia})
		if return_cueanexo:
			return redirect(f"{redirect_url}?cueanexo={return_cueanexo}")
		return redirect(redirect_url)

	return render(request, 'diagnostico_2026/cargar_examen_v2.html', {
		'form': form,
		'materia': template_materia,
		'materia_slug': materia,
		'alumno': alumno,
		'return_cueanexo': return_cueanexo,
		'modo_edicion': modo_edicion,
		'estructura_preguntas': estructura_preguntas,
		'respuestas': _respuestas_formulario(form),
	})


@login_required
def editar_alumno(request, alumno_uuid):
	alumno = get_object_or_404(Alumno2026, public_id=alumno_uuid)
	return_cueanexo = request.GET.get('cueanexo') or request.POST.get('cueanexo')
	form = AlumnoForm(request.POST or None, instance=alumno)

	if request.method == 'POST' and form.is_valid():
		form.save()
		redirect_url = reverse('evaluaciones_educativas:diagnostico_2026:inicio')
		if return_cueanexo:
			return redirect(f"{redirect_url}?cueanexo={return_cueanexo}")
		return redirect(redirect_url)

	return render(request, 'diagnostico_2026/editar_alumno.html', {
		'form': form,
		'alumno': alumno,
		'return_cueanexo': return_cueanexo,
	})


@login_required
def agregar_alumno(request):
   # from ..models import Año2026
	usuario = request.user
	user_cueanexos = utilidades.obtener_cueanexos(usuario.username)
	
	# Obtener cueanexo del query parameter o usar el primero disponible
	selected_cue = request.GET.get('cueanexo') or request.POST.get('cueanexo')
	if selected_cue not in [str(c) for c in user_cueanexos]:
		selected_cue = str(user_cueanexos[0]) if user_cueanexos else None
	
	# Secciones disponibles para ese CUE
	secciones_qs = Seccion2026.objects.filter(
		año__Establecimiento__cueanexo=selected_cue
	).select_related('año').order_by('año__nombre_año', 'seccion')

	form = AlumnoForm(request.POST or None)

	if request.method == 'POST' and form.is_valid():
		seccion_id = request.POST.get('seccion_id')
		seccion_obj = Seccion2026.objects.filter(id=seccion_id).first()

		if seccion_obj:
			try:
				alumno = form.save(commit=False)
				alumno.seccion = seccion_obj
				alumno.save()
				redirect_url = reverse('evaluaciones_educativas:diagnostico_2026:inicio')
				if selected_cue:
					return redirect(f"{redirect_url}?cueanexo={selected_cue}")
				return redirect(redirect_url)
			except Exception as e:
				form.add_error(None, f'Error al guardar alumno: {str(e)}')
		else:
			form.add_error(None, 'Debes seleccionar una sección válida.')

	return render(request, 'diagnostico_2026/agregar_alumno.html', {
		'form': form,
		'secciones': secciones_qs,
		'selected_cue': selected_cue,
		'user_cueanexos': user_cueanexos,
	})


@login_required
def editar_examen(request, alumno_uuid, materia):
	alumno = get_object_or_404(Alumno2026, public_id=alumno_uuid)
	return_cueanexo = request.GET.get('cueanexo') or request.POST.get('cueanexo')

	if materia == 'matematica':
		examen = get_object_or_404(Matematica2026, alumno=alumno)
		form = MatematicaForm(request.POST or None, instance=examen)
		template_materia = "Matemática"
		estructura_preguntas = _obtener_estructura_preguntas_matematica()
	elif materia == 'lengua':
		examen = get_object_or_404(Lengua2026, alumno=alumno)
		form = LenguaForm(request.POST or None, instance=examen)
		template_materia = "Lengua"
		estructura_preguntas = _obtener_estructura_preguntas_lengua()
	else:
		return redirect('evaluaciones_educativas:diagnostico_2026:inicio')

	if request.method == 'POST':
		if form.is_valid():
			_guardar_examen(form, alumno)
			messages.success(request, f'Examen de {template_materia} actualizado correctamente.')
			redirect_url = reverse('evaluaciones_educativas:diagnostico_2026:examenes_lista', kwargs={'materia': materia})
			if return_cueanexo:
				return redirect(f"{redirect_url}?cueanexo={return_cueanexo}")
			return redirect(redirect_url)
		messages.error(request, 'No se pudo actualizar el examen. Revise los campos indicados.')

	return render(request, 'diagnostico_2026/cargar_examen_v2.html', {
		'form': form,
		'materia': template_materia,
		'materia_slug': materia,
		'alumno': alumno,
		'modo_edicion': True,
		'return_cueanexo': return_cueanexo,
		'estructura_preguntas': estructura_preguntas,
		'respuestas': _respuestas_formulario(form),
	})

def boton_completar_carga(cueanexo, materia_nombre):
	estado_carga=None
	lista_inicial_conteo=None
	lista_final_conteo=None
	numero=None
	lista_dnis = list(
			TablaTemporalAlumno.objects
			.filter(cueanexo=cueanexo)
			.values_list('numero_de_documento', flat=True)
		)
	lista = list(
			Alumno2026.objects
			.filter(~Q(dni__in=lista_dnis),seccion__año__Establecimiento__cueanexo=int(cueanexo))
			.select_related('seccion__año', 'seccion__año__Establecimiento')
			.values_list('dni', flat=True)
		)
	lista_dnis.extend(lista)
	alumnos_qs = Alumno2026.objects.filter(dni__in=lista_dnis)
	lista_inicial_conteo=alumnos_qs.count()
	if materia_nombre == 'Matemática':
		evaluaciones=Matematica2026.objects.filter(alumno__in=alumnos_qs).count()
		#evaluaciones_materia=evaluaciones
		lista_final_conteo=evaluaciones
	else:
		evaluaciones=Lengua2026.objects.filter(alumno__in=alumnos_qs).count()
		lista_final_conteo=evaluaciones
	#for i in alumnos_qs:
	if lista_inicial_conteo == lista_final_conteo:
		estado_carga=True
	else:
		estado_carga=False
		numero = lista_inicial_conteo - lista_final_conteo
	print(f'es numero{numero}')
	return estado_carga,numero


def monitoreo_evaluaciones_educativas(request):
	selected_dni = request.GET.get('dni')
	# establecimientos_cueanexo = Establecimientos2026.objects.values_list('cueanexo', flat=True)
	establecimientos_cueanexo = Establecimientos2026.objects.all()
	#alumnos_total= Alumno2026.objects.values_list('dni','nombre','apellido','seccion__seccion','seccion__año__cueanexo')
	if selected_dni:
		alumnos_query=EvaluacionDiagnostica2026.objects.filter(alumno__dni__icontains=selected_dni)
	else:
		alumnos_query=EvaluacionDiagnostica2026.objects.all()

	print(alumnos_query)
	alumnos_total = alumnos_query.values_list(
        'alumno__dni',
        'alumno__nombre',
        'alumno__apellido',
        'alumno__seccion__seccion',
        'alumno__seccion__año__cueanexo',
		'matematica2026',
		'lengua2026'
    )
	establecimientos_region= Establecimientos2026.objects.values_list('region', flat=True)
	monitoreo_total = []
	for i in establecimientos_cueanexo:
		lista_dnis = list(
			TablaTemporalAlumno.objects
			.filter(cueanexo=i.cueanexo)
			.values_list('numero_de_documento', flat=True)
		)
		lista = list(
			Alumno2026.objects
			.filter(~Q(dni__in=lista_dnis),seccion__año__Establecimiento__cueanexo=int(i.cueanexo))
			.select_related('seccion__año', 'seccion__año__Establecimiento')
			.values_list('dni', flat=True)
		)
		lista_dnis.extend(lista) 
		alumnos=Alumno2026.objects.filter(seccion__año__cueanexo=i)
		alumnos_conteo=len(lista_dnis)
		alumno_examen_matematica=Matematica2026.objects.filter(alumno__in=alumnos).count()
		alumno_examen_lengua= Lengua2026.objects.filter(alumno__in=alumnos).count()
		monitoreo_total.append({
					'cueanexo': i.cueanexo,
					'escuela': i.escuela,
					'region': i.region,
					'localidad': i.localidad,
					'departamento': i.departamento,
					'ambito':i.ambito,
					'sector': i.sector,
					'alumnos': alumnos_conteo,
					'matematica': alumno_examen_matematica,
					'lengua': alumno_examen_lengua
				})
		#print(f'cueanexo{i.cueanexo},Escuela:{i.escuela},Region:{i.region},Localidad{i.localidad},Departamento:{i.departamento}alumnos{alumnos_conteo},matematica{alumno_examen_matematica},lengua{alumno_examen_lengua}')
	contexto={'lista':monitoreo_total,
		   'regiones':establecimientos_region,
		   'alumnos_total':alumnos_total}
	return render(request, 'diagnostico_2026/monitoreo_diagnostico.html', contexto)

	#========================== Análisis evaluativos =============================

# def analisis_evaluacion(request):
# 	usuario = request.user
# 	name = usuario.username
# 	cuil_con_caracter = f"{name[:2]}-{name[2:10]}-{name[10:]}"
# 	#--- logica para no permitir ingreso a no autorizados--------------
# 	if not CapaUnicaOfertas.objects.filter(resploc_cuitcuil=cuil_con_caracter, oferta__icontains='Secundaria Completa req. 7 años').exists():
# 		raise PermissionDenied("No tienes permiso para acceder a esta sección.")
# 	user_cueanexos = utilidades.obtener_cueanexos(usuario.username)
# 	selected_cue = request.GET.get('cueanexo')
# 	if not selected_cue and user_cueanexos:
# 		selected_cue = str(user_cueanexos[0])

# 	if selected_cue not in [str(c) for c in user_cueanexos]:
# 		selected_cue = str(user_cueanexos[0]) if user_cueanexos else None


# 	anios = Seccion2026.objects.filter(año_cueanexo=selected_cue).values('añoid', 'año_nombre_año').distinct()

# 	anio_id = request.GET.get('anio_id')
# 	secciones = Seccion2026.objects.filter(año__cueanexo=selected_cue, año_id=anio_id).values_list('seccion', flat=True).distinct()

# 	anio_id = request.GET.get('anio_id')
# 	seccion = request.GET.get('seccion')
# 	turnos = Seccion2026.objects.filter(
# 					año__cueanexo=selected_cue, 
# 					año_id=anio_id, 
# 					seccion=seccion
# 			).values_list('turno', flat=True).distinct()

# 	context = {
# 		'user_cueanexos': user_cueanexos,
# 		'cueanexo': selected_cue,
# 	}

# 	return render(request, 'diagnostico_2026/analisis_evaluacion.html', context)

#========================= Nueva vista para diagnóstico 2026 =========================
# @login_required
# def analisis_evaluacion(request):
#     usuario = request.user
#     name = usuario.username
#     cuil_con_caracter = f"{name[:2]}-{name[2:10]}-{name[10:]}"
    
#     lista_usuarios_jerarquicos = ['Regional', 'Funcionario', 'Ministro', 'Subse']
#     rol_dennied = 'Director/a'
#     rol_usuario = usuario.nivelacceso_id
    
#     # ── PROTECCIÓN DE ACCESO ─────────────────────────────────────
#     if rol_usuario == rol_dennied:
#         raise PermissionDenied("No tienes permiso para acceder a esta sección.")

#     if rol_usuario not in lista_usuarios_jerarquicos:
#         has_oferta = CapaUnicaOfertas.objects.filter(
#             resploc_cuitcuil=cuil_con_caracter, 
#             offer__icontains='Secundaria Completa req. 7 años'
#         ).exists()
#         if not has_oferta:
#             raise PermissionDenied("No tienes permiso para acceder a esta sección.")
          
#     # ── 1. DETERMINACIÓN DEL UNIVERSO DE CUEs PERMITIDOS ────────────────────
#     filtro_sector = request.GET.get('sector', '').strip()
#     filtro_ambito = request.GET.get('ambito', '').strip()
#     filtro_region = request.GET.get('region', '').strip()
    
#     # NUEVO FILTRO CONDICIONAL
#     filtro_condicion = request.GET.get('condicion', '').strip()

#     user_cueanexos = []

#     if rol_usuario in lista_usuarios_jerarquicos:
#         filtros_establecimiento = Q()
#         if filtro_sector and filtro_sector != 'TODOS':
#             filtros_establecimiento &= Q(sector=filtro_sector)
#         if filtro_ambito and filtro_ambito != 'TODOS':
#             filtros_establecimiento &= Q(ambito=filtro_ambito)
#         if filtro_region and filtro_region != 'TODOS':
#             filtros_establecimiento &= Q(region=filtro_region)
            
#         cues_permitidos = Establecimientos2026.objects.filter(filtros_establecimiento).values_list('cueanexo', flat=True).distinct()
#         user_cueanexos = [str(c) for c in cues_permitidos]
#     else:
#         user_cueanexos_raw = utilidades.obtener_cueanexos(usuario.username)
#         user_cueanexos = [str(c) for c in user_cueanexos_raw]

#     selected_cue = request.GET.get('cueanexo')
#     if not selected_cue and user_cueanexos:
#         selected_cue = str(user_cueanexos[0])

#     if selected_cue not in user_cueanexos:
#         selected_cue = str(user_cueanexos[0]) if user_cueanexos else None

#     selected_cue_int = None
#     if selected_cue and selected_cue.isdigit():
#         selected_cue_int = int(selected_cue)

#     escuelas_objs = Establecimientos2026.objects.filter(cueanexo__in=user_cueanexos).values('cueanexo', 'escuela')
#     mapa_escuelas = {str(e['cueanexo']): e['escuela'] for e in escuelas_objs}
    
#     lista_escuelas = []
#     for cue in user_cueanexos:
#         nombre_escuela = mapa_escuelas.get(cue, "Establecimiento sin nombre")
#         lista_escuelas.append({
#             'cue': cue,
#             'label': f"{cue} - {nombre_escuela}"
#         })

#     # ── 2. PETICIONES AJAX PARA CASCADA DINÁMICA ─────────────────────────────
#     action = request.GET.get('action')
#     if action and selected_cue_int is not None:
#         if action == 'cargar_anios':
#             anios = Seccion2026.objects.filter(año__cueanexo=selected_cue_int).values('año__id', 'año__nombre_año').distinct()
#             return JsonResponse(list(anios), safe=False)
            
#         elif action == 'cargar_secciones_turnos':
#             anio_id = request.GET.get('anio_id', 0) or 0
#             combinaciones = Seccion2026.objects.filter(
#                 año__cueanexo=selected_cue_int, 
#                 año_id=int(str(anio_id).strip() or 0)
#             ).values('seccion', 'turno').distinct().order_by('seccion', 'turno')
            
#             resultados = [
#                 {
#                     'id': f"{c['seccion']}|{c['turno']}", 
#                     'label': f"Sección: {c['seccion']} - Turno: {str(c['turno']).upper()}"
#                 } 
#                 for c in combinaciones
#             ]
#             return JsonResponse(resultados, safe=False)

#     # ── 3. CAPTURA DE FILTROS PEDAGÓGICOS ────────────────────────────────────
#     filtro_anio = request.GET.get('anio')
#     filtro_seccion = request.GET.get('seccion')
#     filtro_turno = request.GET.get('turno')
#     filtro_materia = request.GET.get('materia')

#     anio_nombre_sel = filtro_anio
#     if filtro_anio and filtro_anio.isdigit():
#         seccion_ref = Seccion2026.objects.filter(año_id=int(filtro_anio)).select_related('año').first()
#         if seccion_ref:
#             anio_nombre_sel = seccion_ref.año.nombre_año

#     alumnos_con_examenes = []
#     columnas_preguntas = []
#     total_presentes = total_ausentes = 0
#     desempenos = {}

#     presentes_indigena = 0
#     presentes_discapacidad = 0
#     presentes_ambas = 0
#     presentes_ninguna = 0

#     # ── 4. PROCESAMIENTO DE EXÁMENES Y CAPACIDADES ───────────────────────────
#     if filtro_materia and (filtro_condicion or (selected_cue_int and filtro_anio and filtro_seccion and filtro_turno)):
#         if filtro_materia == 'matematica':
#             ModeloExamen = Matematica2026
#             desempenos = {
#                 'general': [0, 0, 0, 0], 'reconocimiento': [0, 0, 0, 0],
#                 'comunicacion': [0, 0, 0, 0], 'resolucion': [0, 0, 0, 0]
#             }
#         elif filtro_materia == 'lengua':
#             ModeloExamen = Lengua2026
#             desempenos = {
#                 'general': [0, 0, 0, 0], 'extraer': [0, 0, 0, 0],
#                 'interpretar': [0, 0, 0, 0], 'reflexionar': [0, 0, 0, 0],
#                 'escribir': [0, 0, 0, 0]
#             }
#         else:
#             ModeloExamen = None

#         if ModeloExamen:
#             if filtro_condicion:
#                 q_objs = Q(alumno__seccion__año__cueanexo__in=user_cueanexos)
                
#                 if filtro_condicion == 'discapacidad':
#                     q_objs &= ~Q(alumno__discapacidad__in=['', 'NO', 'NINGUNA', 'NINGUNO', 'FALSE']) & Q(alumno__discapacidad__isnull=False)
#                 elif filtro_condicion == 'descendencia':
#                     q_objs &= ~Q(alumno__comunidad_indigena__in=['', 'NO', 'NINGUNA', 'NINGUNO', 'FALSE']) & Q(alumno__comunidad_indigena__isnull=False)
#                 elif filtro_condicion == 'ambos':
#                     q_objs &= ~Q(alumno__discapacidad__in=['', 'NO', 'NINGUNA', 'NINGUNO', 'FALSE']) & Q(alumno__discapacidad__isnull=False)
#                     q_objs &= ~Q(alumno__comunidad_indigena__in=['', 'NO', 'NINGUNA', 'NINGUNO', 'FALSE']) & Q(alumno__comunidad_indigena__isnull=False)
                    
#                 examenes = ModeloExamen.objects.filter(q_objs).select_related('alumno', 'alumno__seccion__año').order_by('alumno__apellido', 'alumno__nombre')
#             else:
#                 examenes = ModeloExamen.objects.filter(
#                     alumno__seccion__año__cueanexo=selected_cue_int,
#                     alumno__seccion__año_id=int(filtro_anio),
#                     alumno__seccion__seccion=filtro_seccion,
#                     alumno__seccion__turno=filtro_turno
#                 ).select_related('alumno', 'alumno__seccion__año').order_by('alumno__apellido', 'alumno__nombre')

#             campos_preguntas = [f for f in ModeloExamen._meta.fields if f.name.startswith('pregunta_')]
            
#             def ordenar_por_numero(campo):
#                 numeros = re.findall(r'\d+', campo.name)
#                 return [int(n) for n in numeros]
            
#             campos_preguntas.sort(key=ordenar_por_numero)
#             columnas_preguntas = [f.name.replace('pregunta_', 'P').replace('_', '.') for f in campos_preguntas]

#             for ex in examenes:
#                 asistencia_status = str(ex.asistencia).upper() if ex.asistencia else 'AUSENTE'
                
#                 if asistencia_status == 'PRESENTE':
#                     total_presentes += 1

#                     val_ind = str(ex.alumno.comunidad_indigena).strip().upper() if ex.alumno.comunidad_indigena else 'NO'
#                     val_disc = str(ex.alumno.discapacidad).strip().upper() if ex.alumno.discapacidad else 'NO'
                    
#                     es_indigena = val_ind not in ['NO', 'NINGUNA', 'NINGUNO', 'FALSE', '']
#                     es_discapacitado = val_disc not in ['NO', 'NINGUNA', 'NINGUNO', 'FALSE', '']
                    
#                     if es_indigena and es_discapacitado:
#                         presentes_ambas += 1
#                     elif es_indigena:
#                         presentes_indigena += 1
#                     elif es_discapacitado:
#                         presentes_discapacidad += 1
#                     else:
#                         presentes_ninguna += 1

#                     # Solo omite del gráfico a los discapacitados si NO se filtró explícitamente por ellos
#                     if not es_discapacitado or filtro_condicion:
#                         tp = ex.total_puntaje or 0.0
#                         if tp < 40: desempenos['general'][0] += 1
#                         elif tp < 67: desempenos['general'][1] += 1
#                         elif tp < 90: desempenos['general'][2] += 1
#                         else: desempenos['general'][3] += 1

#                         if filtro_materia == 'matematica':
#                             rec = ex.correcion_reconocimiento or 0.0
#                             if rec < 12.8: desempenos['reconocimiento'][0] += 1
#                             elif rec < 21.4: desempenos['reconocimiento'][1] += 1
#                             elif rec < 28.8: desempenos['reconocimiento'][2] += 1
#                             else: desempenos['reconocimiento'][3] += 1
                            
#                             com = ex.correcion_comunicacion or 0.0
#                             if com < 13.2: desempenos['comunicacion'][0] += 1
#                             elif com < 22.1: desempenos['comunicacion'][1] += 1
#                             elif com < 29.7: desempenos['comunicacion'][2] += 1
#                             else: desempenos['comunicacion'][3] += 1
                            
#                             res = ex.correcion_resolucion or 0.0
#                             if res < 14: desempenos['resolucion'][0] += 1
#                             elif res < 23.4: desempenos['resolucion'][1] += 1
#                             elif res < 31.4: desempenos['resolucion'][2] += 1
#                             else: desempenos['resolucion'][3] += 1

#                         elif filtro_materia == 'lengua':
#                             ext = ex.correcion_extraccion or 0.0
#                             if ext < 8.4: desempenos['extraer'][0] += 1
#                             elif ext < 14.4: desempenos['extraer'][1] += 1
#                             elif ext < 19.3: desempenos['extraer'][2] += 1
#                             else: desempenos['extraer'][3] += 1
                            
#                             intp = ex.correcion_interpretacion or 0.0
#                             if intp < 10.1: desempenos['interpretar'][0] += 1
#                             elif intp < 17.1: desempenos['interpretar'][1] += 1
#                             elif intp < 22.9: desempenos['interpretar'][2] += 1
#                             else: desempenos['interpretar'][3] += 1
                            
#                             ref = ex.correcion_reflexion or 0.0
#                             if ref < 11.4: desempenos['reflexionar'][0] += 1
#                             elif ref < 19.1: desempenos['reflexionar'][1] += 1
#                             elif ref < 25.6: desempenos['reflexionar'][2] += 1
#                             else: desempenos['reflexionar'][3] += 1
                            
#                             esc = ex.correcion_escritura or 0.0
#                             if esc < 9.8: desempenos['escribir'][0] += 1
#                             elif esc < 16.4: desempenos['escribir'][1] += 1
#                             elif esc < 22: desempenos['escribir'][2] += 1
#                             else: desempenos['escribir'][3] += 1
#                 else:
#                     total_ausentes += 1

#                 datos_alumno = {
#                     'dni': ex.alumno.dni, 'apellido': ex.alumno.apellido, 'nombre': ex.alumno.nombre,
#                     'seccion': ex.alumno.seccion.seccion, 'turno': ex.alumno.seccion.turno,
#                     'modelo': ex.modelo, 'asistencia': ex.asistencia,
#                     'respuestas': [getattr(ex, f.name) for f in campos_preguntas], 'total_puntaje': ex.total_puntaje,
#                 }

#                 if filtro_materia == 'matematica':
#                     datos_alumno.update({
#                         'nota_reconocimiento': ex.correcion_reconocimiento,
#                         'nota_comunicacion': ex.correcion_comunicacion, 'nota_resolucion': ex.correcion_resolucion,
#                     })
#                 elif filtro_materia == 'lengua':
#                     datos_alumno.update({
#                         'nota_extraer': ex.correcion_extraccion, 'nota_interpretar': ex.correcion_interpretacion,
#                         'nota_reflexionar': ex.correcion_reflexion, 'nota_escribir': ex.correcion_escritura,
#                     })
#                 alumnos_con_examenes.append(datos_alumno)

#     SECTORES_CHOICES = ['TODOS', 'Estatal', 'Gestión social/cooperativa', 'Privado']
#     AMBITOS_CHOICES = ['TODOS', 'Rural Aglomerado', 'Rural Disperso', 'Urbano']
#     REGIONES_CHOICES = ['TODOS', 'R.E. 1', 'SUB. R.E. 1-A', 'SUB. R.E. 1-B', 'R.E. 2', 'SUB. R.E. 2', 'R.E. 3', 'SUB. R.E. 3', 'R.E. 4-A', 'R.E. 4-B', 'R.E. 5', 'SUB. R.E. 5', 'R.E. 6', 'R.E. 7', 'R.E. 8-A', 'R.E. 8-B', 'R.E. 9', 'R.E. 10-A', 'R.E. 10-B', 'R.E. 10-C']

#     context = {
#         'rol': rol_usuario,
#         'lista_escuelas': lista_escuelas,
#         'cueanexo': selected_cue,
#         'alumnos': alumnos_con_examenes,
#         'columnas_preguntas': columnas_preguntas,
#         'anio_sel': filtro_anio,
#         'anio_nombre_sel': anio_nombre_sel,
#         'seccion_sel': filtro_seccion,
#         'turno_sel': filtro_turno,
#         'materia_sel': filtro_materia,
#         'condicion_sel': filtro_condicion,
#         'asistencia_presentes': total_presentes,
#         'asistencia_ausentes': total_ausentes,
#         'desempenos': desempenos,
#         'sector_sel': filtro_sector or 'TODOS',
#         'ambito_sel': filtro_ambito or 'TODOS',
#         'region_sel': filtro_region or 'TODOS',
#         'sectores_opciones': SECTORES_CHOICES,
#         'ambitos_opciones': AMBITOS_CHOICES,
#         'regiones_opciones': REGIONES_CHOICES,
#         'presentes_indigena': presentes_indigena,
#         'presentes_discapacidad': presentes_discapacidad,
#         'presentes_ambas': presentes_ambas,
#         'presentes_ninguna': presentes_ninguna,
#     }
#     return render(request, 'diagnostico_2026/analisis_evaluacion.html', context)

# @login_required
# def analisis_evaluacion(request):
#     usuario = request.user
#     name = usuario.username
#     cuil_con_caracter = f"{name[:2]}-{name[2:10]}-{name[10:]}"
    
#     lista_usuarios_jerarquicos = ['Regional', 'Funcionario', 'Ministro', 'Subse']
#     rol_dennied = 'Director/a'
#     rol_usuario = usuario.nivelacceso_id
    
#     # ── PROTECCIÓN DE ACCESO ─────────────────────────────────────
#     if rol_usuario == rol_dennied:
#         raise PermissionDenied("No tienes permiso para acceder a esta sección.")

#     if rol_usuario not in lista_usuarios_jerarquicos:
#         has_oferta = CapaUnicaOfertas.objects.filter(
#             resploc_cuitcuil=cuil_con_caracter, 
#             offer__icontains='Secundaria Completa req. 7 años'
#         ).exists()
#         if not has_oferta:
#             raise PermissionDenied("No tienes permiso para acceder a esta sección.")
          
#     # ── 1. DETERMINACIÓN DEL UNIVERSO DE CUEs PERMITIDOS ────────────────────
#     filtro_sector = request.GET.get('sector', '').strip()
#     filtro_ambito = request.GET.get('ambito', '').strip()
#     filtro_region = request.GET.get('region', '').strip()
    
#     filtro_condicion = request.GET.get('condicion', '').strip()

#     user_cueanexos = []

#     if rol_usuario in lista_usuarios_jerarquicos:
#         filtros_establecimiento = Q()
#         if filtro_sector and filtro_sector != 'TODOS':
#             filtros_establecimiento &= Q(sector=filtro_sector)
#         if filtro_ambito and filtro_ambito != 'TODOS':
#             filtros_establecimiento &= Q(ambito=filtro_ambito)
#         if filtro_region and filtro_region != 'TODOS':
#             filtros_establecimiento &= Q(region=filtro_region)
            
#         cues_permitidos = Establecimientos2026.objects.filter(filtros_establecimiento).values_list('cueanexo', flat=True).distinct()
#         user_cueanexos = [str(c) for c in cues_permitidos]
#     else:
#         user_cueanexos_raw = utilidades.obtener_cueanexos(usuario.username)
#         user_cueanexos = [str(c) for c in user_cueanexos_raw]

#     selected_cue = request.GET.get('cueanexo')
#     if not selected_cue and user_cueanexos:
#         selected_cue = str(user_cueanexos[0])

#     if selected_cue not in user_cueanexos and selected_cue != 'TODOS':
#         selected_cue = str(user_cueanexos[0]) if user_cueanexos else None

#     selected_cue_int = None
#     if selected_cue and selected_cue.isdigit():
#         selected_cue_int = int(selected_cue)

#     # Convertimos los CUEs permitidos a enteros para que Postgres no falle en consultas masivas
#     cues_permitidos_int = [int(c) for c in user_cueanexos if c.isdigit()]

#     escuelas_objs = Establecimientos2026.objects.filter(cueanexo__in=user_cueanexos).values('cueanexo', 'escuela')
#     mapa_escuelas = {str(e['cueanexo']): e['escuela'] for e in escuelas_objs}
    
#     lista_escuelas = []
#     for cue in user_cueanexos:
#         nombre_escuela = mapa_escuelas.get(cue, "Establecimiento sin nombre")
#         lista_escuelas.append({
#             'cue': cue,
#             'label': f"{cue} - {nombre_escuela}"
#         })

#     # ── 2. PETICIONES AJAX PARA CASCADA DINÁMICA ─────────────────────────────
#     action = request.GET.get('action')
#     if action and selected_cue_int is not None:
#         if action == 'cargar_anios':
#             anios = Seccion2026.objects.filter(año__cueanexo=selected_cue_int).values('año__id', 'año__nombre_año').distinct()
#             return JsonResponse(list(anios), safe=False)
            
#         elif action == 'cargar_secciones_turnos':
#             anio_id = request.GET.get('anio_id', 0) or 0
#             combinaciones = Seccion2026.objects.filter(
#                 año__cueanexo=selected_cue_int, 
#                 año_id=int(str(anio_id).strip() or 0)
#             ).values('seccion', 'turno').distinct().order_by('seccion', 'turno')
            
#             resultados = [
#                 {
#                     'id': f"{c['seccion']}|{c['turno']}", 
#                     'label': f"Sección: {c['seccion']} - Turno: {str(c['turno']).upper()}"
#                 } 
#                 for c in combinaciones
#             ]
#             return JsonResponse(resultados, safe=False)

#     # ── 3. CAPTURA DE FILTROS PEDAGÓGICOS ────────────────────────────────────
#     filtro_anio = request.GET.get('anio')
#     filtro_seccion = request.GET.get('seccion')
#     filtro_turno = request.GET.get('turno')
#     filtro_materia = request.GET.get('materia')

#     anio_nombre_sel = filtro_anio
#     if filtro_anio and filtro_anio.isdigit():
#         seccion_ref = Seccion2026.objects.filter(año_id=int(filtro_anio)).select_related('año').first()
#         if seccion_ref:
#             anio_nombre_sel = seccion_ref.año.nombre_año

#     alumnos_con_examenes = []
#     columnas_preguntas = []
#     total_presentes = total_ausentes = 0
#     desempenos = {}

#     presentes_indigena = 0
#     presentes_discapacidad = 0
#     presentes_ambas = 0
#     presentes_ninguna = 0

#     # ── 4. PROCESAMIENTO DE EXÁMENES Y CAPACIDADES ───────────────────────────
#     es_masivo = (filtro_condicion != "") or (selected_cue == 'TODOS')
#     es_individual = (selected_cue_int is not None and filtro_anio and filtro_seccion and filtro_turno)

#     if filtro_materia and (es_masivo or es_individual):
#         if filtro_materia == 'matematica':
#             ModeloExamen = Matematica2026
#             desempenos = {
#                 'general': [0, 0, 0, 0], 'reconocimiento': [0, 0, 0, 0],
#                 'comunicacion': [0, 0, 0, 0], 'resolucion': [0, 0, 0, 0]
#             }
#         elif filtro_materia == 'lengua':
#             ModeloExamen = Lengua2026
#             desempenos = {
#                 'general': [0, 0, 0, 0], 'extraer': [0, 0, 0, 0],
#                 'interpretar': [0, 0, 0, 0], 'reflexionar': [0, 0, 0, 0],
#                 'escribir': [0, 0, 0, 0]
#             }
#         else:
#             ModeloExamen = None

#         if ModeloExamen:
#             if es_masivo:
#                 q_objs = Q(alumno__seccion__año__cueanexo__in=cues_permitidos_int)
                
#                 if filtro_condicion == 'discapacidad':
#                     q_objs &= ~Q(alumno__discapacidad__in=['', 'NO', 'NINGUNA', 'NINGUNO', 'FALSE']) & Q(alumno__discapacidad__isnull=False)
#                 elif filtro_condicion == 'descendencia':
#                     q_objs &= ~Q(alumno__comunidad_indigena__in=['', 'NO', 'NINGUNA', 'NINGUNO', 'FALSE']) & Q(alumno__comunidad_indigena__isnull=False)
#                 elif filtro_condicion == 'ambos':
#                     q_objs &= (
#                         (~Q(alumno__discapacidad__in=['', 'NO', 'NINGUNA', 'NINGUNO', 'FALSE']) & Q(alumno__discapacidad__isnull=False)) |
#                         (~Q(alumno__comunidad_indigena__in=['', 'NO', 'NINGUNA', 'NINGUNO', 'FALSE']) & Q(alumno__comunidad_indigena__isnull=False))
#                     )
                    
#                 examenes = ModeloExamen.objects.filter(q_objs).select_related('alumno', 'alumno__seccion__año').order_by('alumno__apellido', 'alumno__nombre')
#             else:
#                 examenes = ModeloExamen.objects.filter(
#                     alumno__seccion__año__cueanexo=selected_cue_int,
#                     alumno__seccion__año_id=int(filtro_anio),
#                     alumno__seccion__seccion=filtro_seccion,
#                     alumno__seccion__turno=filtro_turno
#                 ).select_related('alumno', 'alumno__seccion__año').order_by('alumno__apellido', 'alumno__nombre')

#             campos_preguntas = [f for f in ModeloExamen._meta.fields if f.name.startswith('pregunta_')]
            
#             def ordenar_por_numero(campo):
#                 numeros = re.findall(r'\d+', campo.name)
#                 return [int(n) for n in numeros]
            
#             campos_preguntas.sort(key=ordenar_por_numero)
#             columnas_preguntas = [f.name.replace('pregunta_', 'P').replace('_', '.') for f in campos_preguntas]

#             for ex in examenes:
#                 asistencia_status = str(ex.asistencia).upper() if ex.asistencia else 'AUSENTE'
                
#                 if asistencia_status == 'PRESENTE':
#                     total_presentes += 1

#                     val_ind = str(ex.alumno.comunidad_indigena).strip().upper() if ex.alumno.comunidad_indigena else 'NO'
#                     val_disc = str(ex.alumno.discapacidad).strip().upper() if ex.alumno.discapacidad else 'NO'
                    
#                     es_indigena = val_ind not in ['NO', 'NINGUNA', 'NINGUNO', 'FALSE', '']
#                     es_discapacitado = val_disc not in ['NO', 'NINGUNA', 'NINGUNO', 'FALSE', '']
                    
#                     if es_indigena and es_discapacitado:
#                         presentes_ambas += 1
#                     elif es_indigena:
#                         presentes_indigena += 1
#                     elif es_discapacitado:
#                         presentes_discapacidad += 1
#                     else:
#                         presentes_ninguna += 1

#                     if not es_discapacitado or filtro_condicion:
#                         tp = ex.total_puntaje or 0.0
#                         if tp < 40: desempenos['general'][0] += 1
#                         elif tp < 67: desempenos['general'][1] += 1
#                         elif tp < 90: desempenos['general'][2] += 1
#                         else: desempenos['general'][3] += 1

#                         if filtro_materia == 'matematica':
#                             rec = ex.correcion_reconocimiento or 0.0
#                             if rec < 12.8: desempenos['reconocimiento'][0] += 1
#                             elif rec < 21.4: desempenos['reconocimiento'][1] += 1
#                             elif rec < 28.8: desempenos['reconocimiento'][2] += 1
#                             else: desempenos['reconocimiento'][3] += 1
                            
#                             com = ex.correcion_comunicacion or 0.0
#                             if com < 13.2: desempenos['comunicacion'][0] += 1
#                             elif com < 22.1: desempenos['comunicacion'][1] += 1
#                             elif com < 29.7: desempenos['comunicacion'][2] += 1
#                             else: desempenos['comunicacion'][3] += 1
                            
#                             res = ex.correcion_resolucion or 0.0
#                             if res < 14: desempenos['resolucion'][0] += 1
#                             elif res < 23.4: desempenos['resolucion'][1] += 1
#                             elif res < 31.4: desempenos['resolucion'][2] += 1
#                             else: desempenos['resolucion'][3] += 1

#                         elif filtro_materia == 'lengua':
#                             ext = ex.correcion_extraccion or 0.0
#                             if ext < 8.4: desempenos['extraer'][0] += 1
#                             elif ext < 14.4: desempenos['extraer'][1] += 1
#                             elif ext < 19.3: desempenos['extraer'][2] += 1
#                             else: desempenos['extraer'][3] += 1
                            
#                             intp = ex.correcion_interpretacion or 0.0
#                             if intp < 10.1: desempenos['interpretar'][0] += 1
#                             elif intp < 17.1: desempenos['interpretar'][1] += 1
#                             elif intp < 22.9: desempenos['interpretar'][2] += 1
#                             else: desempenos['interpretar'][3] += 1
                            
#                             ref = ex.correcion_reflexion or 0.0
#                             if ref < 11.4: desempenos['reflexionar'][0] += 1
#                             elif ref < 19.1: desempenos['reflexionar'][1] += 1
#                             elif ref < 25.6: desempenos['reflexionar'][2] += 1
#                             else: desempenos['reflexionar'][3] += 1
                            
#                             esc = ex.correcion_escritura or 0.0
#                             if esc < 9.8: desempenos['escribir'][0] += 1
#                             elif esc < 16.4: desempenos['escribir'][1] += 1
#                             elif esc < 22: desempenos['escribir'][2] += 1
#                             else: desempenos['escribir'][3] += 1
#                 else:
#                     total_ausentes += 1

#                 datos_alumno = {
#                     'dni': ex.alumno.dni, 'apellido': ex.alumno.apellido, 'nombre': ex.alumno.nombre,
#                     'seccion': ex.alumno.seccion.seccion, 'turno': ex.alumno.seccion.turno,
#                     'modelo': ex.modelo, 'asistencia': ex.asistencia,
#                     'respuestas': [getattr(ex, f.name) for f in campos_preguntas], 'total_puntaje': ex.total_puntaje,
#                 }

#                 if filtro_materia == 'matematica':
#                     datos_alumno.update({
#                         'nota_reconocimiento': ex.correcion_reconocimiento,
#                         'nota_comunicacion': ex.correcion_comunicacion, 'nota_resolucion': ex.correcion_resolucion,
#                     })
#                 elif filtro_materia == 'lengua':
#                     datos_alumno.update({
#                         'nota_extraer': ex.correcion_extraccion, 'nota_interpretar': ex.correcion_interpretacion,
#                         'nota_reflexionar': ex.correcion_reflexion, 'nota_escribir': ex.correcion_escritura,
#                     })
#                 alumnos_con_examenes.append(datos_alumno)

#     SECTORES_CHOICES = ['TODOS', 'Estatal', 'Gestión social/cooperativa', 'Privado']
#     AMBITOS_CHOICES = ['TODOS', 'Rural Aglomerado', 'Rural Disperso', 'Urbano']
#     REGIONES_CHOICES = ['TODOS', 'R.E. 1', 'SUB. R.E. 1-A', 'SUB. R.E. 1-B', 'R.E. 2', 'SUB. R.E. 2', 'R.E. 3', 'SUB. R.E. 3', 'R.E. 4-A', 'R.E. 4-B', 'R.E. 5', 'SUB. R.E. 5', 'R.E. 6', 'R.E. 7', 'R.E. 8-A', 'R.E. 8-B', 'R.E. 9', 'R.E. 10-A', 'R.E. 10-B', 'R.E. 10-C']

#     context = {
#         'rol': rol_usuario,
#         'lista_escuelas': lista_escuelas,
#         'cueanexo': selected_cue,
#         'alumnos': alumnos_con_examenes,
#         'columnas_preguntas': columnas_preguntas,
#         'anio_sel': filtro_anio,
#         'anio_nombre_sel': anio_nombre_sel,
#         'seccion_sel': filtro_seccion,
#         'turno_sel': filtro_turno,
#         'materia_sel': filtro_materia,
#         'condicion_sel': filtro_condicion,
#         'asistencia_presentes': total_presentes,
#         'asistencia_ausentes': total_ausentes,
#         'desempenos': desempenos,
#         'sector_sel': filtro_sector or 'TODOS',
#         'ambito_sel': filtro_ambito or 'TODOS',
#         'region_sel': filtro_region or 'TODOS',
#         'sectores_opciones': SECTORES_CHOICES,
#         'ambitos_opciones': AMBITOS_CHOICES,
#         'regiones_opciones': REGIONES_CHOICES,
#         'presentes_indigena': presentes_indigena,
#         'presentes_discapacidad': presentes_discapacidad,
#         'presentes_ambas': presentes_ambas,
#         'presentes_ninguna': presentes_ninguna,
#     }
#     return render(request, 'diagnostico_2026/analisis_evaluacion.html', context)

# @login_required
# def analisis_evaluacion(request):
#     usuario = request.user
#     name = usuario.username
#     cuil_con_caracter = f"{name[:2]}-{name[2:10]}-{name[10:]}"
    
#     lista_usuarios_jerarquicos = ['Regional', 'Funcionario', 'Ministro', 'Subse']
#     rol_dennied = 'Director/a'
#     rol_usuario = usuario.nivelacceso_id
    
#     if rol_usuario == rol_dennied:
#         raise PermissionDenied("No tienes permiso para acceder a esta sección.")

#     if rol_usuario not in lista_usuarios_jerarquicos:
#         has_oferta = CapaUnicaOfertas.objects.filter(
#             resploc_cuitcuil=cuil_con_caracter, 
#             offer__icontains='Secundaria Completa req. 7 años'
#         ).exists()
#         if not has_oferta:
#             raise PermissionDenied("No tienes permiso para acceder a esta sección.")
          
#     # ── 1. DETERMINACIÓN DEL UNIVERSO DE CUEs PERMITIDOS ────────────────────
#     filtro_sector = request.GET.get('sector', '').strip()
#     filtro_ambito = request.GET.get('ambito', '').strip()
#     filtro_region = request.GET.get('region', '').strip()
#     filtro_condicion = request.GET.get('condicion', '').strip()

#     filtros_establecimiento = Q()
#     if rol_usuario in lista_usuarios_jerarquicos:
#         if filtro_sector and filtro_sector != 'TODOS':
#             filtros_establecimiento &= Q(sector=filtro_sector)
#         if filtro_ambito and filtro_ambito != 'TODOS':
#             filtros_establecimiento &= Q(ambito=filtro_ambito)
#         if filtro_region and filtro_region != 'TODOS':
#             filtros_establecimiento &= Q(region=filtro_region)
        
#         cues_permitidos_qs = Establecimientos2026.objects.filter(filtros_establecimiento).values_list('cueanexo', flat=True).distinct()
#     else:
#         user_cueanexos_raw = utilidades.obtener_cueanexos(usuario.username)
#         cues_permitidos_qs = list(user_cueanexos_raw)

#     user_cueanexos = [str(c) for c in cues_permitidos_qs]

#     selected_cue = request.GET.get('cueanexo')
#     if not selected_cue and user_cueanexos:
#         selected_cue = str(user_cueanexos[0])

#     if selected_cue not in user_cueanexos and selected_cue != 'TODOS':
#         selected_cue = str(user_cueanexos[0]) if user_cueanexos else None

#     selected_cue_int = None
#     if selected_cue and selected_cue.isdigit():
#         selected_cue_int = int(selected_cue)

#     cues_permitidos_int = [int(c) for c in user_cueanexos if c.isdigit()]

#     escuelas_objs = Establecimientos2026.objects.filter(cueanexo__in=cues_permitidos_int).values('cueanexo', 'escuela')
#     mapa_escuelas = {str(e['cueanexo']): e['escuela'] for e in escuelas_objs}
    
#     lista_escuelas = []
#     for cue in user_cueanexos:
#         nombre_escuela = mapa_escuelas.get(cue, "Establecimiento sin nombre")
#         lista_escuelas.append({
#             'cue': cue,
#             'label': f"{cue} - {nombre_escuela}"
#         })

#     # ── 2. PETICIONES AJAX PARA CASCADA DINÁMICA ─────────────────────────────
#     action = request.GET.get('action')
#     if action and selected_cue_int is not None:
#         if action == 'cargar_anios':
#             anios = Seccion2026.objects.filter(año__cueanexo=selected_cue_int).values('año__id', 'año__nombre_año').distinct()
#             return JsonResponse(list(anios), safe=False)
            
#         elif action == 'cargar_secciones_turnos':
#             anio_id = request.GET.get('anio_id', 0) or 0
#             combinaciones = Seccion2026.objects.filter(
#                 año__cueanexo=selected_cue_int, 
#                 año_id=int(str(anio_id).strip() or 0)
#             ).values('seccion', 'turno').distinct().order_by('seccion', 'turno')
            
#             resultados = [
#                 {
#                     'id': f"{c['seccion']}|{c['turno']}", 
#                     'label': f"Sección: {c['seccion']} - Turno: {str(c['turno']).upper()}"
#                 } 
#                 for c in combinaciones
#             ]
#             return JsonResponse(resultados, safe=False)

#     # ── 3. CAPTURA DE FILTROS PEDAGÓGICOS ────────────────────────────────────
#     filtro_anio = request.GET.get('anio')
#     filtro_seccion = request.GET.get('seccion')
#     filtro_turno = request.GET.get('turno')
#     filtro_materia = request.GET.get('materia')

#     anio_nombre_sel = filtro_anio
#     if filtro_anio and filtro_anio.isdigit():
#         seccion_ref = Seccion2026.objects.filter(año_id=int(filtro_anio)).select_related('año').first()
#         if seccion_ref:
#             anio_nombre_sel = seccion_ref.año.nombre_año

#     alumnos_con_examenes = []
#     columnas_preguntas = []
#     total_presentes = total_ausentes = 0
#     desempenos = {}

#     presentes_indigena = presentes_discapacidad = presentes_ambas = presentes_ninguna = 0

#     # ── 4. PROCESAMIENTO DE EXÁMENES Y CAPACIDADES ───────────────────────────
#     es_masivo = (filtro_condicion != "") or (selected_cue == 'TODOS')
#     es_individual = (selected_cue_int is not None and filtro_anio and filtro_seccion and filtro_turno)

#     if filtro_materia and (es_masivo or es_individual):
#         if filtro_materia == 'matematica':
#             ModeloExamen = Matematica2026
#             desempenos = {
#                 'general': [0, 0, 0, 0], 'reconocimiento': [0, 0, 0, 0],
#                 'comunicacion': [0, 0, 0, 0], 'resolucion': [0, 0, 0, 0]
#             }
#         elif filtro_materia == 'lengua':
#             ModeloExamen = Lengua2026
#             desempenos = {
#                 'general': [0, 0, 0, 0], 'extraer': [0, 0, 0, 0],
#                 'interpretar': [0, 0, 0, 0], 'reflexionar': [0, 0, 0, 0],
#                 'escribir': [0, 0, 0, 0]
#             }
#         else:
#             ModeloExamen = None

#         if ModeloExamen:
#             if es_masivo:
#                 q_objs = Q(alumno__seccion__año__cueanexo__in=cues_permitidos_int)
                
#                 if filtro_condicion == 'discapacidad':
#                     q_objs &= ~Q(alumno__discapacidad__in=['', 'NO', 'NINGUNA', 'NINGUNO', 'FALSE']) & Q(alumno__discapacidad__isnull=False)
#                 elif filtro_condicion == 'descendencia':
#                     q_objs &= ~Q(alumno__comunidad_indigena__in=['', 'NO', 'NINGUNA', 'NINGUNO', 'FALSE']) & Q(alumno__comunidad_indigena__isnull=False)
#                 elif filtro_condicion == 'ambos':
#                     q_objs &= (
#                         (~Q(alumno__discapacidad__in=['', 'NO', 'NINGUNA', 'NINGUNO', 'FALSE']) & Q(alumno__discapacidad__isnull=False)) |
#                         (~Q(alumno__comunidad_indigena__in=['', 'NO', 'NINGUNA', 'NINGUNO', 'FALSE']) & Q(alumno__comunidad_indigena__isnull=False))
#                     )
                
#                 # OPTIMIZACIÓN: Si es masivo, quitamos el order_by para que SQL vuele.
#                 examenes = ModeloExamen.objects.filter(q_objs).select_related('alumno', 'alumno__seccion__año')
#             else:
#                 examenes = ModeloExamen.objects.filter(
#                     alumno__seccion__año__cueanexo=selected_cue_int,
#                     alumno__seccion__año_id=int(filtro_anio),
#                     alumno__seccion__seccion=filtro_seccion,
#                     alumno__seccion__turno=filtro_turno
#                 ).select_related('alumno', 'alumno__seccion__año').order_by('alumno__apellido', 'alumno__nombre')

#             campos_preguntas = [f for f in ModeloExamen._meta.fields if f.name.startswith('pregunta_')]
#             def ordenar_por_numero(campo):
#                 numeros = re.findall(r'\d+', campo.name)
#                 return [int(n) for n in numeros]
            
#             campos_preguntas.sort(key=ordenar_por_numero)
#             columnas_preguntas = [f.name.replace('pregunta_', 'P').replace('_', '.') for f in campos_preguntas]

#             for ex in examenes:
#                 asistencia_status = str(ex.asistencia).upper() if ex.asistencia else 'AUSENTE'
                
#                 if asistencia_status == 'PRESENTE':
#                     total_presentes += 1

#                     val_ind = str(ex.alumno.comunidad_indigena).strip().upper() if ex.alumno.comunidad_indigena else 'NO'
#                     val_disc = str(ex.alumno.discapacidad).strip().upper() if ex.alumno.discapacidad else 'NO'
                    
#                     es_indigena = val_ind not in ['NO', 'NINGUNA', 'NINGUNO', 'FALSE', '']
#                     es_discapacitado = val_disc not in ['NO', 'NINGUNA', 'NINGUNO', 'FALSE', '']
                    
#                     if es_indigena and es_discapacitado:
#                         presentes_ambas += 1
#                     elif es_indigena:
#                         presentes_indigena += 1
#                     elif es_discapacitado:
#                         presentes_discapacidad += 1
#                     else:
#                         presentes_ninguna += 1

#                     if not es_discapacitado or filtro_condicion:
#                         tp = ex.total_puntaje or 0.0
#                         if tp < 40: desempenos['general'][0] += 1
#                         elif tp < 67: desempenos['general'][1] += 1
#                         elif tp < 90: desempenos['general'][2] += 1
#                         else: desempenos['general'][3] += 1

#                         if filtro_materia == 'matematica':
#                             rec = ex.correcion_reconocimiento or 0.0
#                             if rec < 12.8: desempenos['reconocimiento'][0] += 1
#                             elif rec < 21.4: desempenos['reconocimiento'][1] += 1
#                             elif rec < 28.8: desempenos['reconocimiento'][2] += 1
#                             else: desempenos['reconocimiento'][3] += 1
                            
#                             com = ex.correcion_comunicacion or 0.0
#                             if com < 13.2: desempenos['comunicacion'][0] += 1
#                             elif com < 22.1: desempenos['comunicacion'][1] += 1
#                             elif com < 29.7: desempenos['comunicacion'][2] += 1
#                             else: desempenos['comunicacion'][3] += 1
                            
#                             res = ex.correcion_resolucion or 0.0
#                             if res < 14: desempenos['resolucion'][0] += 1
#                             elif res < 23.4: desempenos['resolucion'][1] += 1
#                             elif res < 31.4: desempenos['resolucion'][2] += 1
#                             else: desempenos['resolucion'][3] += 1

#                         elif filtro_materia == 'lengua':
#                             ext = ex.correcion_extraccion or 0.0
#                             if ext < 8.4: desempenos['extraer'][0] += 1
#                             elif ext < 14.4: desempenos['extraer'][1] += 1
#                             elif ext < 19.3: desempenos['extraer'][2] += 1
#                             else: desempenos['extraer'][3] += 1
                            
#                             intp = ex.correcion_interpretacion or 0.0
#                             if intp < 10.1: desempenos['interpretar'][0] += 1
#                             elif intp < 17.1: desempenos['interpretar'][1] += 1
#                             elif intp < 22.9: desempenos['interpretar'][2] += 1
#                             else: desempenos['interpretar'][3] += 1
                            
#                             ref = ex.correcion_reflexion or 0.0
#                             if ref < 11.4: desempenos['reflexionar'][0] += 1
#                             elif ref < 19.1: desempenos['reflexionar'][1] += 1
#                             elif ref < 25.6: desempenos['reflexionar'][2] += 1
#                             else: desempenos['reflexionar'][3] += 1
                            
#                             esc = ex.correcion_escritura or 0.0
#                             if esc < 9.8: desempenos['escribir'][0] += 1
#                             elif esc < 16.4: desempenos['escribir'][1] += 1
#                             elif esc < 22: desempenos['escribir'][2] += 1
#                             else: desempenos['escribir'][3] += 1
#                 else:
#                     total_ausentes += 1

#                 # OPTIMIZACIÓN: Solo armamos el diccionario y lo agregamos si NO es masivo.
#                 if not es_masivo:
#                     datos_alumno = {
#                         'dni': ex.alumno.dni, 'apellido': ex.alumno.apellido, 'nombre': ex.alumno.nombre,
#                         'seccion': ex.alumno.seccion.seccion, 'turno': ex.alumno.seccion.turno,
#                         'modelo': ex.modelo, 'asistencia': ex.asistencia,
#                         'respuestas': [getattr(ex, f.name) for f in campos_preguntas], 'total_puntaje': ex.total_puntaje,
#                     }

#                     if filtro_materia == 'matematica':
#                         datos_alumno.update({
#                             'nota_reconocimiento': ex.correcion_reconocimiento,
#                             'nota_comunicacion': ex.correcion_comunicacion, 'nota_resolucion': ex.correcion_resolucion,
#                         })
#                     elif filtro_materia == 'lengua':
#                         datos_alumno.update({
#                             'nota_extraer': ex.correcion_extraccion, 'nota_interpretar': ex.correcion_interpretacion,
#                             'nota_reflexionar': ex.correcion_reflexion, 'nota_escribir': ex.correcion_escritura,
#                         })
#                     alumnos_con_examenes.append(datos_alumno)

#     SECTORES_CHOICES = ['TODOS', 'Estatal', 'Gestión social/cooperativa', 'Privado']
#     AMBITOS_CHOICES = ['TODOS', 'Rural Aglomerado', 'Rural Disperso', 'Urbano']
#     REGIONES_CHOICES = ['TODOS', 'R.E. 1', 'SUB. R.E. 1-A', 'SUB. R.E. 1-B', 'R.E. 2', 'SUB. R.E. 2', 'R.E. 3', 'SUB. R.E. 3', 'R.E. 4-A', 'R.E. 4-B', 'R.E. 5', 'SUB. R.E. 5', 'R.E. 6', 'R.E. 7', 'R.E. 8-A', 'R.E. 8-B', 'R.E. 9', 'R.E. 10-A', 'R.E. 10-B', 'R.E. 10-C']

#     context = {
#         'rol': rol_usuario,
#         'lista_escuelas': lista_escuelas,
#         'cueanexo': selected_cue,
#         'alumnos': alumnos_con_examenes, # Estará vacía si es masivo
#         'es_masivo': es_masivo, # Nueva bandera para el HTML
#         'hay_datos': (total_presentes + total_ausentes) > 0, # Verifica si hubo resultados, aun sin la lista
#         'columnas_preguntas': columnas_preguntas,
#         'anio_sel': filtro_anio,
#         'anio_nombre_sel': anio_nombre_sel,
#         'seccion_sel': filtro_seccion,
#         'turno_sel': filtro_turno,
#         'materia_sel': filtro_materia,
#         'condicion_sel': filtro_condicion,
#         'asistencia_presentes': total_presentes,
#         'asistencia_ausentes': total_ausentes,
#         'desempenos': desempenos,
#         'sector_sel': filtro_sector or 'TODOS',
#         'ambito_sel': filtro_ambito or 'TODOS',
#         'region_sel': filtro_region or 'TODOS',
#         'sectores_opciones': SECTORES_CHOICES,
#         'ambitos_opciones': AMBITOS_CHOICES,
#         'regiones_opciones': REGIONES_CHOICES,
#         'presentes_indigena': presentes_indigena,
#         'presentes_discapacidad': presentes_discapacidad,
#         'presentes_ambas': presentes_ambas,
#         'presentes_ninguna': presentes_ninguna,
#     }
#     return render(request, 'diagnostico_2026/analisis_evaluacion.html', context)

@login_required
def analisis_evaluacion(request):
    usuario = request.user
    name = usuario.username
    cuil_con_caracter = f"{name[:2]}-{name[2:10]}-{name[10:]}"
    
    lista_usuarios_jerarquicos = ['Regional', 'Funcionario', 'Ministro', 'Subse']
    rol_dennied = 'Director/a'
    rol_usuario = usuario.nivelacceso_id
    print(rol_usuario)
    
    # ── PROTECCIÓN DE ACCESO ─────────────────────────────────────
    if rol_usuario == rol_dennied:
        raise PermissionDenied("No tienes permiso para acceder a esta sección.")

    if rol_usuario not in lista_usuarios_jerarquicos:
        has_oferta = CapaUnicaOfertas.objects.filter(
            resploc_cuitcuil=cuil_con_caracter, 
            offer__icontains='Secundaria Completa req. 7 años'
        ).exists()
        if not has_oferta:
            raise PermissionDenied("No tienes permiso para acceder a esta sección.")
          
    # ── 1. DETERMINACIÓN DEL UNIVERSO DE CUEs PERMITIDOS ────────────────────
    filtro_sector = request.GET.get('sector', '').strip()
    filtro_ambito = request.GET.get('ambito', '').strip()
    filtro_region = request.GET.get('region', '').strip()
    filtro_condicion = request.GET.get('condicion', '').strip()

    user_cueanexos = []

    if rol_usuario in lista_usuarios_jerarquicos:
        filtros_establecimiento = Q()
        if filtro_sector and filtro_sector != 'TODOS':
            filtros_establecimiento &= Q(sector=filtro_sector)
        if filtro_ambito and filtro_ambito != 'TODOS':
            filtros_establecimiento &= Q(ambito=filtro_ambito)
        if filtro_region and filtro_region != 'TODOS':
            filtros_establecimiento &= Q(region=filtro_region)
            
        cues_permitidos = Establecimientos2026.objects.filter(filtros_establecimiento).values_list('cueanexo', flat=True).distinct()
        user_cueanexos = [str(c) for c in cues_permitidos]
    else:
        user_cueanexos_raw = utilidades.obtener_cueanexos(usuario.username)
        user_cueanexos = [str(c) for c in user_cueanexos_raw]

    selected_cue = request.GET.get('cueanexo')
    if not selected_cue and user_cueanexos:
        selected_cue = str(user_cueanexos[0])

    if selected_cue not in user_cueanexos and selected_cue != 'TODOS':
        selected_cue = str(user_cueanexos[0]) if user_cueanexos else None

    selected_cue_int = None
    if selected_cue and selected_cue.isdigit():
        selected_cue_int = int(selected_cue)

    cues_permitidos_int = [int(c) for c in user_cueanexos if c.isdigit()]

    escuelas_objs = Establecimientos2026.objects.filter(cueanexo__in=user_cueanexos).values('cueanexo', 'escuela')
    mapa_escuelas = {str(e['cueanexo']): e['escuela'] for e in escuelas_objs}
    
    lista_escuelas = []
    for cue in user_cueanexos:
        nombre_escuela = mapa_escuelas.get(cue, "Establecimiento sin nombre")
        lista_escuelas.append({
            'cue': cue,
            'label': f"{cue} - {nombre_escuela}"
        })

    # ── 2. PETICIONES AJAX PARA CASCADA DINÁMICA ─────────────────────────────
    action = request.GET.get('action')
    if action and selected_cue_int is not None:
        if action == 'cargar_anios':
            anios = Seccion2026.objects.filter(año__cueanexo=selected_cue_int).values('año__id', 'año__nombre_año').distinct()
            return JsonResponse(list(anios), safe=False)
            
        elif action == 'cargar_secciones_turnos':
            anio_id = request.GET.get('anio_id', 0) or 0
            combinaciones = Seccion2026.objects.filter(
                año__cueanexo=selected_cue_int, 
                año_id=int(str(anio_id).strip() or 0)
            ).values('seccion', 'turno').distinct().order_by('seccion', 'turno')
            
            resultados = [
                {'id': 'TODOS|TODOS', 'label': '--- TODOS ---'},
            ]
            resultados.extend([
                {
                    'id': f"{c['seccion']}|{c['turno']}", 
                    'label': f"Sección: {c['seccion']} - Turno: {str(c['turno']).upper()}"
                } 
                for c in combinaciones
            ])
            return JsonResponse(resultados, safe=False)

    # ── 3. CAPTURA DE FILTROS PEDAGÓGICOS ────────────────────────────────────
    filtro_anio = request.GET.get('anio')
    filtro_seccion = request.GET.get('seccion')
    filtro_turno = request.GET.get('turno')
    filtro_materia = request.GET.get('materia')

    if filtro_seccion == 'TODOS':
        filtro_turno = filtro_turno or 'TODOS'

    anio_nombre_sel = filtro_anio
    if filtro_anio and filtro_anio.isdigit():
        seccion_ref = Seccion2026.objects.filter(año_id=int(filtro_anio)).select_related('año').first()
        if seccion_ref:
            anio_nombre_sel = seccion_ref.año.nombre_año

    lista_secciones_turnos = []
    if selected_cue_int is not None and filtro_anio and str(filtro_anio).isdigit():
        combinaciones = Seccion2026.objects.filter(
            año__cueanexo=selected_cue_int,
            año_id=int(filtro_anio),
        ).values('seccion', 'turno').distinct().order_by('seccion', 'turno')
        lista_secciones_turnos.append({
            'id': 'TODOS|TODOS',
            'label': '--- TODOS ---',
            'seccion': 'TODOS',
            'turno': 'TODOS',
        })
        for c in combinaciones:
            lista_secciones_turnos.append({
                'id': f"{c['seccion']}|{c['turno']}",
                'label': f"Sección: {c['seccion']} - Turno: {str(c['turno']).upper()}",
                'seccion': c['seccion'],
                'turno': c['turno'],
            })

    alumnos_con_examenes = []
    columnas_preguntas = []
    total_presentes = total_ausentes = 0
    desempenos = {}
    presentes_indigena = presentes_discapacidad = presentes_ambas = presentes_ninguna = 0

    # ── 4. PROCESAMIENTO DE EXÁMENES Y CAPACIDADES ───────────────────────────
    es_busqueda_condicion = filtro_condicion != ""
    es_busqueda_todos = selected_cue == 'TODOS'
    
    # NUEVAS EVALUACIONES DE ESTADO
    es_busqueda_seccion_todos = selected_cue_int is not None and filtro_anio and filtro_seccion == 'TODOS'
    es_busqueda_individual = selected_cue_int is not None and filtro_anio and filtro_seccion and filtro_turno and filtro_seccion != 'TODOS'

    # La tabla solo se oculta si es consulta regional masiva por TODOS los establecimientos
    ocultar_listado = es_busqueda_todos and not es_busqueda_condicion

    if filtro_materia and (es_busqueda_condicion or es_busqueda_todos or es_busqueda_seccion_todos or es_busqueda_individual):
        if filtro_materia == 'matematica':
            ModeloExamen = Matematica2026
            desempenos = {
                'general': [0, 0, 0, 0], 'reconocimiento': [0, 0, 0, 0],
                'comunicacion': [0, 0, 0, 0], 'resolucion': [0, 0, 0, 0]
            }
        elif filtro_materia == 'lengua':
            ModeloExamen = Lengua2026
            desempenos = {
                'general': [0, 0, 0, 0], 'extraer': [0, 0, 0, 0],
                'interpretar': [0, 0, 0, 0], 'reflexionar': [0, 0, 0, 0],
                'escribir': [0, 0, 0, 0]
            }
        else:
            ModeloExamen = None

        if ModeloExamen:
            if es_busqueda_condicion or es_busqueda_todos:
                q_objs = Q(alumno__seccion__año__cueanexo__in=cues_permitidos_int)
                
                if filtro_condicion == 'discapacidad':
                    q_objs &= ~Q(alumno__discapacidad__in=['', 'NO', 'NINGUNA', 'NINGUNO', 'FALSE']) & Q(alumno__discapacidad__isnull=False)
                elif filtro_condicion == 'descendencia':
                    q_objs &= ~Q(alumno__comunidad_indigena__in=['', 'NO', 'NINGUNA', 'NINGUNO', 'FALSE']) & Q(alumno__comunidad_indigena__isnull=False)
                elif filtro_condicion == 'ambos':
                    q_objs &= (
                        (~Q(alumno__discapacidad__in=['', 'NO', 'NINGUNA', 'NINGUNO', 'FALSE']) & Q(alumno__discapacidad__isnull=False)) |
                        (~Q(alumno__comunidad_indigena__in=['', 'NO', 'NINGUNA', 'NINGUNO', 'FALSE']) & Q(alumno__comunidad_indigena__isnull=False))
                    )
                
                if not ocultar_listado:
                    examenes = ModeloExamen.objects.filter(q_objs).select_related('alumno', 'alumno__seccion__año').order_by('alumno__apellido', 'alumno__nombre')
                else:
                    examenes = ModeloExamen.objects.filter(q_objs).select_related('alumno', 'alumno__seccion__año')
            
            # NUEVA CONDICIÓN: Traer todas las secciones y turnos de una escuela y año específicos
            elif es_busqueda_seccion_todos:
                examenes = ModeloExamen.objects.filter(
                    alumno__seccion__año__cueanexo=selected_cue_int,
                    alumno__seccion__año_id=int(filtro_anio)
                ).select_related('alumno', 'alumno__seccion__año').order_by('alumno__apellido', 'alumno__nombre')
                
            else:
                examenes = ModeloExamen.objects.filter(
                    alumno__seccion__año__cueanexo=selected_cue_int,
                    alumno__seccion__año_id=int(filtro_anio),
                    alumno__seccion__seccion=filtro_seccion,
                    alumno__seccion__turno=filtro_turno
                ).select_related('alumno', 'alumno__seccion__año').order_by('alumno__apellido', 'alumno__nombre')

            campos_preguntas = [f for f in ModeloExamen._meta.fields if f.name.startswith('pregunta_')]
            
            def ordenar_por_numero(campo):
                numeros = re.findall(r'\d+', campo.name)
                return [int(n) for n in numeros]
            
            campos_preguntas.sort(key=ordenar_por_numero)
            columnas_preguntas = [f.name.replace('pregunta_', 'P').replace('_', '.') for f in campos_preguntas]

            for ex in examenes:
                asistencia_status = str(ex.asistencia).upper() if ex.asistencia else 'AUSENTE'
                
                if asistencia_status == 'PRESENTE':
                    total_presentes += 1

                    val_ind = str(ex.alumno.comunidad_indigena).strip().upper() if ex.alumno.comunidad_indigena else 'NO'
                    val_disc = str(ex.alumno.discapacidad).strip().upper() if ex.alumno.discapacidad else 'NO'
                    
                    es_indigena = val_ind not in ['NO', 'NINGUNA', 'NINGUNO', 'FALSE', '']
                    es_discapacitado = val_disc not in ['NO', 'NINGUNA', 'NINGUNO', 'FALSE', '']
                    
                    if es_indigena and es_discapacitado:
                        presentes_ambas += 1
                    elif es_indigena:
                        presentes_indigena += 1
                    elif es_discapacitado:
                        presentes_discapacidad += 1
                    else:
                        presentes_ninguna += 1

                    if not es_discapacitado or filtro_condicion:
                        tp = ex.total_puntaje or 0.0
                        if tp < 40: desempenos['general'][0] += 1
                        elif tp < 67: desempenos['general'][1] += 1
                        elif tp < 90: desempenos['general'][2] += 1
                        else: desempenos['general'][3] += 1

                        if filtro_materia == 'matematica':
                            rec = ex.correcion_reconocimiento or 0.0
                            if rec < 12.8: desempenos['reconocimiento'][0] += 1
                            elif rec < 21.4: desempenos['reconocimiento'][1] += 1
                            elif rec < 28.8: desempenos['reconocimiento'][2] += 1
                            else: desempenos['reconocimiento'][3] += 1
                            
                            com = ex.correcion_comunicacion or 0.0
                            if com < 13.2: desempenos['comunicacion'][0] += 1
                            elif com < 22.1: desempenos['comunicacion'][1] += 1
                            elif com < 29.7: desempenos['comunicacion'][2] += 1
                            else: desempenos['comunicacion'][3] += 1
                            
                            res = ex.correcion_resolucion or 0.0
                            if res < 14: desempenos['resolucion'][0] += 1
                            elif res < 23.4: desempenos['resolucion'][1] += 1
                            elif res < 31.4: desempenos['resolucion'][2] += 1
                            else: desempenos['resolucion'][3] += 1

                        elif filtro_materia == 'lengua':
                            ext = ex.correcion_extraccion or 0.0
                            if ext < 8.4: desempenos['extraer'][0] += 1
                            elif ext < 14.4: desempenos['extraer'][1] += 1
                            elif ext < 19.3: desempenos['extraer'][2] += 1
                            else: desempenos['extraer'][3] += 1
                            
                            intp = ex.correcion_interpretacion or 0.0
                            if intp < 10.1: desempenos['interpretar'][0] += 1
                            elif intp < 17.1: desempenos['interpretar'][1] += 1
                            elif intp < 22.9: desempenos['interpretar'][2] += 1
                            else: desempenos['interpretar'][3] += 1
                            
                            ref = ex.correcion_reflexion or 0.0
                            if ref < 11.4: desempenos['reflexionar'][0] += 1
                            elif ref < 19.1: desempenos['reflexionar'][1] += 1
                            elif ref < 25.6: desempenos['reflexionar'][2] += 1
                            else: desempenos['reflexionar'][3] += 1
                            
                            esc = ex.correcion_escritura or 0.0
                            if esc < 9.8: desempenos['escribir'][0] += 1
                            elif esc < 16.4: desempenos['escribir'][1] += 1
                            elif esc < 22: desempenos['escribir'][2] += 1
                            else: desempenos['escribir'][3] += 1
                else:
                    total_ausentes += 1

                if not ocultar_listado:
                    datos_alumno = {
                        'dni': ex.alumno.dni, 'apellido': ex.alumno.apellido, 'nombre': ex.alumno.nombre,
                        'seccion': ex.alumno.seccion.seccion, 'turno': ex.alumno.seccion.turno,
                        'modelo': ex.modelo, 'asistencia': ex.asistencia,
                        'respuestas': [getattr(ex, f.name) for f in campos_preguntas], 'total_puntaje': ex.total_puntaje,
                    }

                    if filtro_materia == 'matematica':
                        datos_alumno.update({
                            'nota_reconocimiento': ex.correcion_reconocimiento,
                            'nota_comunicacion': ex.correcion_comunicacion, 'nota_resolucion': ex.correcion_resolucion,
                        })
                    elif filtro_materia == 'lengua':
                        datos_alumno.update({
                            'nota_extraer': ex.correcion_extraccion, 'nota_interpretar': ex.correcion_interpretacion,
                            'nota_reflexionar': ex.correcion_reflexion, 'nota_escribir': ex.correcion_escritura,
                        })
                    alumnos_con_examenes.append(datos_alumno)

    SECTORES_CHOICES = ['TODOS', 'Estatal', 'Gestión social/cooperativa', 'Privado']
    AMBITOS_CHOICES = ['TODOS', 'Rural Aglomerado', 'Rural Disperso', 'Urbano']
    REGIONES_CHOICES = ['TODOS', 'R.E. 1', 'SUB. R.E. 1-A', 'SUB. R.E. 1-B', 'R.E. 2', 'SUB. R.E. 2', 'R.E. 3', 'SUB. R.E. 3', 'R.E. 4-A', 'R.E. 4-B', 'R.E. 5', 'SUB. R.E. 5', 'R.E. 6', 'R.E. 7', 'R.E. 8-A', 'R.E. 8-B', 'R.E. 9', 'R.E. 10-C', 'R.E. 10-AB']

    context = {
        'rol': rol_usuario,
        'lista_escuelas': lista_escuelas,
        'cueanexo': selected_cue,
        'alumnos': alumnos_con_examenes,
        'ocultar_listado': ocultar_listado, 
        'hay_datos': (total_presentes + total_ausentes) > 0,
        'columnas_preguntas': columnas_preguntas,
        'anio_sel': filtro_anio,
        'anio_nombre_sel': anio_nombre_sel,
        'lista_secciones_turnos': lista_secciones_turnos,
        'seccion_sel': filtro_seccion,
        'turno_sel': filtro_turno,
        'materia_sel': filtro_materia,
        'condicion_sel': filtro_condicion,
        'asistencia_presentes': total_presentes,
        'asistencia_ausentes': total_ausentes,
        'desempenos': desempenos,
        'sector_sel': filtro_sector or 'TODOS',
        'ambito_sel': filtro_ambito or 'TODOS',
        'region_sel': filtro_region or 'TODOS',
        'sectores_opciones': SECTORES_CHOICES,
        'ambitos_opciones': AMBITOS_CHOICES,
        'regiones_opciones': REGIONES_CHOICES,
        'presentes_indigena': presentes_indigena,
        'presentes_discapacidad': presentes_discapacidad,
        'presentes_ambas': presentes_ambas,
        'presentes_ninguna': presentes_ninguna,
    }
    return render(request, 'diagnostico_2026/analisis_evaluacion.html', context)


# ─────────────────────────────────────────────────────────────────────────────
# Vista: Progreso Alumnos (2025 → 2026)
# Endpoint AJAX que cruza datos de diagnostico_2025 con diagnostico_2026 por DNI
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def progreso_alumnos(request):
    """
    Compara el desempeño de cada alumno entre el diagnóstico 2025 y 2026.
    Recibe los mismos filtros que analisis_evaluacion (cueanexo, anio, seccion, turno, materia).
    Retorna JSON con:
      - lista de alumnos con delta
      - promedios generales y por capacidad de ambos años
      - distribución de tendencias (mejoró / empeoró / igual / sin datos)
    """
    from apps.evaluaciones_educativas.models.analisis_evaluacion import (
        ExamenLenguaAlumno,
        ExamenMatematicaAlumno,
    )

    usuario = request.user
    name = usuario.username
    cuil_con_caracter = f"{name[:2]}-{name[2:10]}-{name[10:]}"

    lista_usuarios_jerarquicos = ['Regional', 'Funcionario', 'Ministro']
    rol_usuario = usuario.nivelacceso_id

    # ── Protección de acceso ──────────────────────────────────────────────────
    if rol_usuario == 'Director/a':
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("No tienes permiso para acceder a esta sección.")

    if rol_usuario not in lista_usuarios_jerarquicos:
        has_oferta = CapaUnicaOfertas.objects.filter(
            resploc_cuitcuil=cuil_con_caracter,
            offer__icontains='Secundaria Completa req. 7 años'
        ).exists()
        if not has_oferta:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("No tienes permiso para acceder a esta sección.")

    # ── Parámetros de filtro ──────────────────────────────────────────────────
    cueanexo   = request.GET.get('cueanexo', '').strip()
    anio_id    = request.GET.get('anio', '').strip()
    seccion    = request.GET.get('seccion', '').strip()
    turno      = request.GET.get('turno', '').strip()
    materia    = request.GET.get('materia', '').strip()

    UMBRAL_IGUAL = 1.0  # diferencia máxima para considerar "sin cambio"

    if not materia or not cueanexo or not anio_id:
        return JsonResponse({'error': 'Faltan parámetros: cueanexo, anio, materia'}, status=400)

    cueanexo_int = int(cueanexo) if cueanexo.isdigit() else None
    anio_int     = int(anio_id)  if anio_id.isdigit()  else None

    if cueanexo_int is None or anio_int is None:
        return JsonResponse({'error': 'Parámetros inválidos'}, status=400)

    # ── 1. Obtener alumnos + puntajes 2026 ───────────────────────────────────
    if materia == 'matematica':
        Modelo2026 = Matematica2026
    elif materia == 'lengua':
        Modelo2026 = Lengua2026
    else:
        return JsonResponse({'error': 'Materia no válida'}, status=400)

    q_2026 = Q(alumno__seccion__año__cueanexo=cueanexo_int, alumno__seccion__año_id=anio_int)
    if seccion and turno and seccion != 'TODOS':
        q_2026 &= Q(alumno__seccion__seccion=seccion, alumno__seccion__turno=turno)

    examenes_2026 = (
        Modelo2026.objects.filter(q_2026, asistencia='PRESENTE')
        .select_related('alumno')
        .values('alumno__dni', 'alumno__apellido', 'alumno__nombre', 'total_puntaje',
                *(['correcion_reconocimiento', 'correcion_comunicacion', 'correcion_resolucion']
                  if materia == 'matematica'
                  else ['correcion_extraccion', 'correcion_interpretacion',
                        'correcion_reflexion', 'correcion_escritura']))
    )

    # Mapa: dni → datos 2026
    mapa_2026 = {}
    for ex in examenes_2026:
        dni = str(ex['alumno__dni']).strip()
        mapa_2026[dni] = ex

    if not mapa_2026:
        return JsonResponse({'sin_datos': True, 'mensaje': 'No hay alumnos presentes en 2026 con estos filtros.'})

    # ── 2. Obtener puntajes 2025 para esos mismos DNIs ────────────────────────
    dnis_2026 = list(mapa_2026.keys())
    Modelo2025 = ExamenMatematicaAlumno if materia == 'matematica' else ExamenLenguaAlumno

    if materia == 'matematica':
        campos_2025 = ['dni', 'total', 'reconocimiento_conceptos', 'comunicacion', 'resolucion_situaciones']
    else:
        campos_2025 = ['dni', 'total', 'extraer', 'interpretar', 'reflexionar_evaluar', 'escribir']

    examenes_2025 = Modelo2025.objects.filter(
        dni__in=dnis_2026,
        cueanexo=cueanexo
    ).values(*campos_2025)

    # Mapa: dni → datos 2025
    def _sf(v):
        try:
            return round(float(str(v or '').replace(',', '.')), 2)
        except (ValueError, TypeError):
            return None

    mapa_2025 = {}
    for ex in examenes_2025:
        dni = str(ex['dni']).strip()
        mapa_2025[dni] = ex

    # ── 3. Cruce y cálculo de deltas ─────────────────────────────────────────
    alumnos_resultado = []
    mejoro = empeoro = igual = sin_datos = 0
    suma_2026 = suma_2025 = n_cruce = 0

    # Promedios por capacidad
    CAP_KEYS_2026 = (
        ['correcion_reconocimiento', 'correcion_comunicacion', 'correcion_resolucion']
        if materia == 'matematica'
        else ['correcion_extraccion', 'correcion_interpretacion', 'correcion_reflexion', 'correcion_escritura']
    )
    CAP_KEYS_2025 = (
        ['reconocimiento_conceptos', 'comunicacion', 'resolucion_situaciones']
        if materia == 'matematica'
        else ['extraer', 'interpretar', 'reflexionar_evaluar', 'escribir']
    )
    CAP_LABELS = (
        ['Reconocimiento', 'Comunicación', 'Resolución']
        if materia == 'matematica'
        else ['Extraer', 'Interpretar', 'Reflexionar/Eval.', 'Escritura']
    )

    sumas_cap_2026 = [0.0] * len(CAP_KEYS_2026)
    sumas_cap_2025 = [0.0] * len(CAP_KEYS_2025)
    ns_cap         = [0]   * len(CAP_KEYS_2026)

    for dni, d26 in mapa_2026.items():
        apellido = d26['alumno__apellido'] or ''
        nombre   = d26['alumno__nombre']   or ''
        tp_2026  = d26.get('total_puntaje')
        tp_2026f = round(float(tp_2026), 2) if tp_2026 is not None else None

        d25 = mapa_2025.get(dni)
        tp_2025f = _sf(d25.get('total')) if d25 else None

        # Tendencia
        if tp_2025f is None or d25 is None:
            tendencia = 'sin_datos'
            delta     = None
            sin_datos += 1
        else:
            delta = round(tp_2026f - tp_2025f, 2) if tp_2026f is not None else None
            if delta is None:
                tendencia = 'sin_datos'; sin_datos += 1
            elif delta > UMBRAL_IGUAL:
                tendencia = 'mejoro';  mejoro    += 1
            elif delta < -UMBRAL_IGUAL:
                tendencia = 'empeoro'; empeoro   += 1
            else:
                tendencia = 'igual';   igual     += 1

            if tp_2026f is not None:
                suma_2026 += tp_2026f
                suma_2025 += tp_2025f
                n_cruce   += 1

        # Capacidades
        caps_2026_vals = {}
        caps_2025_vals = {}
        for i, (k26, k25) in enumerate(zip(CAP_KEYS_2026, CAP_KEYS_2025)):
            v26 = d26.get(k26)
            v26f = round(float(v26), 2) if v26 is not None else None
            caps_2026_vals[CAP_LABELS[i]] = v26f

            v25f = _sf(d25.get(k25)) if d25 else None
            caps_2025_vals[CAP_LABELS[i]] = v25f

            if v26f is not None:
                sumas_cap_2026[i] += v26f
                ns_cap[i]         += 1
            if v25f is not None:
                sumas_cap_2025[i] += v25f

        alumnos_resultado.append({
            'dni':         dni,
            'apellido':    apellido,
            'nombre':      nombre,
            'nota_2025':   tp_2025f,
            'nota_2026':   tp_2026f,
            'delta':       delta,
            'tendencia':   tendencia,
            'caps_2026':   caps_2026_vals,
            'caps_2025':   caps_2025_vals,
        })

    # Ordenar: primero los con datos 2025, luego sin datos; dentro, mayor delta desc
    alumnos_resultado.sort(
        key=lambda x: (x['tendencia'] == 'sin_datos', -(x['delta'] or 0))
    )

    # Promedios globales
    prom_2026 = round(suma_2026 / n_cruce, 2) if n_cruce else None
    prom_2025 = round(suma_2025 / n_cruce, 2) if n_cruce else None

    prom_cap_2026 = [
        round(sumas_cap_2026[i] / ns_cap[i], 2) if ns_cap[i] else None
        for i in range(len(CAP_LABELS))
    ]
    prom_cap_2025 = [
        round(sumas_cap_2025[i] / ns_cap[i], 2) if ns_cap[i] else None
        for i in range(len(CAP_LABELS))
    ]

    return JsonResponse({
        'sin_datos':    False,
        'materia':      materia,
        'total_alumnos_2026': len(mapa_2026),
        'total_cruce':  n_cruce,
        'tendencias': {
            'mejoro':    mejoro,
            'empeoro':   empeoro,
            'igual':     igual,
            'sin_datos': sin_datos,
        },
        'promedios': {
            'general_2026': prom_2026,
            'general_2025': prom_2025,
            'capacidades_labels': CAP_LABELS,
            'capacidades_2026':   prom_cap_2026,
            'capacidades_2025':   prom_cap_2025,
        },
        'alumnos': alumnos_resultado,
    })


@login_required
def descargar_examen_individual(request, materia):
    usuario = request.user
    name = usuario.username
    cuil_con_caracter = f"{name[:2]}-{name[2:10]}-{name[10:]}"
    lista_usuarios_jerarquicos = ['Regional', 'Funcionario', 'Ministro', 'Subse']
    rol_usuario = usuario.nivelacceso_id

    
    # ── 1. SEGURIDAD Y PERMISOS ───────────────────────────────────────────────
    if rol_usuario not in lista_usuarios_jerarquicos:
        has_oferta = CapaUnicaOfertas.objects.filter(
            resploc_cuitcuil=cuil_con_caracter, 
            oferta__icontains='Secundaria Completa req. 7 años'
        ).exists()
        if not has_oferta:
            raise PermissionDenied("No tienes permiso para acceder a esta sección.")

    selected_cue = request.GET.get('cueanexo')
    dni_alumno = request.GET.get('dni')
    
    if not selected_cue or not dni_alumno:
        raise Http404("Faltan parámetros requeridos (CUE o DNI).")

    if rol_usuario not in lista_usuarios_jerarquicos:
        user_cueanexos_raw = utilidades.obtener_cueanexos(usuario.username)
        user_cueanexos = [str(c) for c in user_cueanexos_raw]
        if selected_cue not in user_cueanexos:
            raise PermissionDenied("No tienes acceso a los registros de este establecimiento.")

    # ── 2. CONFIGURACIÓN DE LA MATERIA ────────────────────────────────────────
    if materia == 'matematica':
        examen_model = Matematica2026
        materia_nombre = 'Matemática'
    elif materia == 'lengua':
        examen_model = Lengua2026
        materia_nombre = 'Lengua'
    else:
        return redirect('evaluaciones_educativas:diagnostico_2026:inicio')

    # ── 3. FILTRADO DEL ALUMNO ESPECÍFICO ─────────────────────────────────────
    alumno = get_object_or_404(Alumno2026, dni=dni_alumno, seccion__año__Establecimiento__cueanexo=selected_cue)
    examen = examen_model.objects.filter(alumno=alumno).first()

    if not examen:
        messages.warning(request, "El alumno no tiene este examen cargado.")
        return redirect('evaluaciones_educativas:diagnostico_2026:inicio')

    # ── 4. CONSTRUCCIÓN DEL BOLETÍN PDF EN FORMATO VERTICAL ───────────────────
    buffer = io.BytesIO()
    # Usamos A4 vertical (portrait) para que se lea mejor como una ficha
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    story = []

    # Título Principal
    story.append(Paragraph(f"Ficha Individual de Examen: {materia_nombre}", styles['Title']))
    story.append(Spacer(1, 15))

    # Tabla 1: Datos Personales
    datos_alumno = [
        [Paragraph("<b>DNI:</b>"), alumno.dni],
        [Paragraph("<b>Alumno:</b>"), f"{alumno.apellido}, {alumno.nombre}"],
        [Paragraph("<b>Establecimiento CUE:</b>"), selected_cue],
        [Paragraph("<b>Sección y Turno:</b>"), f"{alumno.seccion.seccion} - {alumno.seccion.turno.upper()}" if alumno.seccion else "N/A"],
        [Paragraph("<b>Asistencia:</b>"), examen.asistencia or "N/A"],
        [Paragraph("<b>Modelo Rendido:</b>"), examen.modelo or "-"],
    ]
    
    t_datos = Table(datos_alumno, colWidths=[130, 350])
    t_datos.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E9ECEF')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t_datos)
    story.append(Spacer(1, 20))

    if str(examen.asistencia).upper() == 'PRESENTE':
        # Tabla 2: Detalle de TODAS las Preguntas Individuales
        story.append(Paragraph("<b>Detalle de Respuestas Individuales:</b>", styles['Heading3']))
        story.append(Spacer(1, 10))
        
        data_respuestas = [['Ítem / Pregunta', 'Respuesta Seleccionada']]
        
        # Filtramos y ordenamos los campos que empiezan con 'pregunta_'
        pregunta_campos = [f for f in examen_model._meta.get_fields() if f.name.startswith('pregunta_')]
        pregunta_campos.sort(key=_orden_pregunta_field)

        for campo in pregunta_campos:
            nombre_limpio = campo.name.replace('pregunta_', 'P').replace('_', '.')
            respuesta = getattr(examen, campo.name)
            data_respuestas.append([nombre_limpio, str(respuesta) if respuesta else '-'])

        t_resp = Table(data_respuestas, colWidths=[130, 350])
        t_resp.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(t_resp)
        story.append(Spacer(1, 20))

        # Tabla 3: Resultados Generales y Puntos de Corte
        # story.append(Paragraph("<b>Resultados y Puntos de Corte por Capacidad:</b>", styles['Heading3']))
        # story.append(Spacer(1, 10))
        
        # if materia == 'matematica':
        #     data_puntajes = [
        #         ['Capacidad Evaluada', 'Puntaje Obtenido'],
        #         ['Reconocimiento de Conceptos', round(float(examen.correcion_reconocimiento or 0), 2)],
        #         ['Comunicación en Matemática', round(float(examen.correcion_comunicacion or 0), 2)],
        #         ['Resolución de Situaciones', round(float(examen.correcion_resolucion or 0), 2)],
        #         ['PUNTAJE FINAL TOTAL', round(float(examen.total_puntaje or 0), 2)]
        #     ]
        # else:
        #     data_puntajes = [
        #         ['Capacidad Evaluada', 'Puntaje Obtenido'],
        #         ['Extraer', round(float(examen.correcion_extraccion or 0), 2)],
        #         ['Interpretar', round(float(examen.correcion_interpretacion or 0), 2)],
        #         ['Reflexionar y Evaluar', round(float(examen.correcion_reflexion or 0), 2)],
        #         ['Escribir', round(float(examen.correcion_escritura or 0), 2)],
        #         ['PUNTAJE FINAL TOTAL', round(float(examen.total_puntaje or 0), 2)]
        #     ]
            
        # t_punt = Table(data_puntajes, colWidths=[280, 200])
        # t_punt.setStyle(TableStyle([
        #     ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
        #     ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        #     ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        #     ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        #     ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        #     ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'), # Pone la fila TOTAL en negrita
        #     ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#d4e6f1')), # Color de fondo para el Total
        #     ('PADDING', (0, 0), (-1, -1), 6),
        # ]))
        # story.append(t_punt)

    # Construimos el PDF y lo preparamos para descarga
    doc.build(story)
    buffer.seek(0)

    filename = f"Ficha_Examen_{materia}_{alumno.dni}.pdf"
    return FileResponse(buffer, as_attachment=True, filename=filename)

@login_required
def descargar_reporte_listado(request, materia):
    usuario = request.user
    name = usuario.username
    cuil_con_caracter = f"{name[:2]}-{name[2:10]}-{name[10:]}"
    lista_usuarios_jerarquicos = ['Regional', 'Funcionario', 'Ministro', 'Subse']
    rol_usuario = usuario.nivelacceso_id  
    
    # ── 1. SEGURIDAD Y PERMISOS ───────────────────────────────────────────────
    if rol_usuario not in lista_usuarios_jerarquicos:
        has_oferta = CapaUnicaOfertas.objects.filter(
            resploc_cuitcuil=cuil_con_caracter, 
            oferta__icontains='Secundaria Completa req. 7 años'
        ).exists()
        if not has_oferta:
            raise PermissionDenied("No tienes permiso para acceder a esta sección.")

    selected_cue = request.GET.get('cueanexo')
    filtro_anio = request.GET.get('anio')
    filtro_seccion = request.GET.get('seccion')
    filtro_turno = request.GET.get('turno')

    if not all([selected_cue, filtro_anio, filtro_seccion, filtro_turno]):
        messages.warning(request, "Faltan filtros para generar el reporte.")
        return redirect('evaluaciones_educativas:diagnostico_2026:inicio')

    # ── 2. CONFIGURACIÓN DE LA MATERIA ────────────────────────────────────────
    if materia == 'matematica':
        examen_model = Matematica2026
        materia_nombre = 'Matemática'
    elif materia == 'lengua':
        examen_model = Lengua2026
        materia_nombre = 'Lengua'
    else:
        return redirect('evaluaciones_educativas:diagnostico_2026:inicio')

    # ── 3. CONSULTA DE EXÁMENES ───────────────────────────────────────────────
    filtros_examen = {
        'alumno__seccion__año__cueanexo': int(selected_cue),
        'alumno__seccion__año_id': int(filtro_anio),
    }
    if filtro_seccion != 'TODOS':
        filtros_examen['alumno__seccion__seccion'] = filtro_seccion
        filtros_examen['alumno__seccion__turno'] = filtro_turno

    examenes = examen_model.objects.filter(**filtros_examen).select_related(
        'alumno', 'alumno__seccion'
    ).order_by('alumno__apellido', 'alumno__nombre')

    # ── 4. FUNCIÓN AUXILIAR DE DESEMPEÑOS ─────────────────────────────────────
    def evaluar(nota, cortes):
        if nota is None: return "-"
        try:
            val = float(nota)
            if val < cortes[0]: return "D. Básico"
            elif val < cortes[1]: return "Básico"
            elif val < cortes[2]: return "Satisfac."
            else: return "Avanzado"
        except:
            return "-"

    # ── 5. ARMADO DE LA TABLA PDF (CON AJUSTE DE SALTOS DE LÍNEA) ─────────────
    # Inicializamos el estilo para que el texto haga salto de línea automático
    styles = getSampleStyleSheet()
    style_celda = styles['Normal']
    style_celda.fontSize = 7
    style_celda.leading = 8 # Espaciado entre las líneas si el nombre salta

    data = []
    
    if materia == 'matematica':
        cabeceras = ['DNI', 'Alumno', 'Asist.', 'Reconoc.', 'Des. Rec.', 'Comunic.', 'Des. Com.', 'Resoluc.', 'Des. Res.', 'Nota Gral', 'Desempeño Gral']
        data.append(cabeceras)
        for ex in examenes:
            al = ex.alumno
            # Envolvemos el nombre en Paragraph para forzar el salto de línea
            nombre_alumno = Paragraph(f"{al.apellido}, {al.nombre}", style_celda)
            
            row = [
                al.dni, nombre_alumno, ex.asistencia or "-",
                round(float(ex.correcion_reconocimiento or 0), 2) if ex.correcion_reconocimiento != None else "-",
                evaluar(ex.correcion_reconocimiento, [12.8, 21.4, 28.8]),
                round(float(ex.correcion_comunicacion or 0), 2) if ex.correcion_comunicacion != None else "-",
                evaluar(ex.correcion_comunicacion, [13.2, 22.1, 29.7]),
                round(float(ex.correcion_resolucion or 0), 2) if ex.correcion_resolucion != None else "-",
                evaluar(ex.correcion_resolucion, [14, 23.4, 31.4]),
                round(float(ex.total_puntaje or 0), 2) if ex.total_puntaje != None else "-",
                evaluar(ex.total_puntaje, [40, 67, 90])
            ]
            data.append(row)
        # Se aumentó el ancho de la columna 1 (Alumno) de 120 a 160
        col_widths = [55, 160, 45, 55, 60, 55, 60, 55, 60, 55, 65]
        
    else: # LENGUA
        cabeceras = ['DNI', 'Alumno', 'Asist.', 'Extraer', 'Des. Ext.', 'Interpret.', 'Des. Int.', 'Reflex.', 'Des. Ref.', 'Escribir', 'Des. Esc.', 'Nota Gral', 'Desemp Gral.']
        data.append(cabeceras)
        for ex in examenes:
            al = ex.alumno
            # Envolvemos el nombre en Paragraph para forzar el salto de línea
            nombre_alumno = Paragraph(f"{al.apellido}, {al.nombre}", style_celda)
            
            row = [
                al.dni, nombre_alumno, ex.asistencia or "-",
                round(float(ex.correcion_extraccion or 0), 2) if ex.correcion_extraccion != None else "-",
                evaluar(ex.correcion_extraccion, [8.4, 14.4, 19.3]),
                round(float(ex.correcion_interpretacion or 0), 2) if ex.correcion_interpretacion != None else "-",
                evaluar(ex.correcion_interpretacion, [10.1, 17.1, 22.9]),
                round(float(ex.correcion_reflexion or 0), 2) if ex.correcion_reflexion != None else "-",
                evaluar(ex.correcion_reflexion, [11.4, 19.1, 25.6]),
                round(float(ex.correcion_escritura or 0), 2) if ex.correcion_escritura != None else "-",
                evaluar(ex.correcion_escritura, [9.8, 16.4, 22]),
                round(float(ex.total_puntaje or 0), 2) if ex.total_puntaje != None else "-",
                evaluar(ex.total_puntaje, [40, 67, 90])
            ]
            data.append(row)
        # Se aumentó el ancho de la columna 1 (Alumno) de 110 a 140
        col_widths = [50, 140, 40, 45, 55, 45, 55, 45, 55, 45, 55, 40, 55]

    # ── 6. CONSTRUCCIÓN DEL PDF ───────────────────────────────────────────────
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=15, rightMargin=15, topMargin=20, bottomMargin=20)
    story = []

    story.append(Paragraph(f"Reporte de Desempeños - {materia_nombre}", styles['Title']))
    story.append(Paragraph(f"CUE: {selected_cue} | Sección: {filtro_seccion} | Turno: {filtro_turno.upper()}", styles['Normal']))
    story.append(Spacer(1, 15))

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('PADDING', (0, 0), (-1, -1), 3),
    ]))

    story.append(table)
    doc.build(story)
    buffer.seek(0)

    filename = f"Reporte_Desempenos_{materia}_{filtro_seccion}_{filtro_turno}.pdf"
    return FileResponse(buffer, as_attachment=True, filename=filename)