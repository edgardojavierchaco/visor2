# Librerías estándar
import io
import logging
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from multiprocessing import context

# Librerías de terceros
import openpyxl
import qrcode
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

# Django
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.timezone import now
from django.views.generic import DetailView, ListView

# Local
from .models import EscuelasPrimariasMatematica, ExamenMatematicaQuintoGrado, RegistroAsistenciaMatematicaQuinto, VistaResultadoMatematicaQuinto


class ExamenMatematicaQuintoListView(LoginRequiredMixin, ListView):
    model = ExamenMatematicaQuintoGrado
    template_name = 'operativchaco/matematica/quinto/examen_quinto_list.html'
    context_object_name = 'examenes'
    #paginate_by = 20

    def get_queryset(self):
        usuario = self.request.user
        cueanexo_usuario = usuario.username 
        return ExamenMatematicaQuintoGrado.objects.filter(cueanexo=cueanexo_usuario)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        usuario = self.request.user
        cueanexo_usuario = usuario.username
        region= EscuelasPrimariasMatematica.objects.filter(
            cueanexo=cueanexo_usuario).values_list('region_loc', flat=True).first()
        print(f"Usuario: {usuario}, CUEAnexo: {cueanexo_usuario}")
        
        context['fecha_actual'] = now().strftime('%d/%m/%Y %H:%M')
        context['region_usuario'] = region
        print(f"Región del usuario: {context['region_usuario']}")
        return context
        

class ExamenMatematicaQuintoDetailView(LoginRequiredMixin, DetailView):
    model = ExamenMatematicaQuintoGrado
    template_name = 'operativchaco/matematica/quinto/examen_quinto_detail.html'
    context_object_name = 'examen'

@login_required
def exportar_excel_examenes_quinto(request):
    usuario = request.user
    cueanexo_usuario = usuario.username

    queryset = VistaResultadoMatematicaQuinto.objects.filter(cueanexo=cueanexo_usuario)

    # Agrupar exámenes por división
    examenes_por_division = defaultdict(list)
    for examen in queryset:
        examenes_por_division[examen.division].append(examen)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Exámenes Matemática 2025 - Quinto Grado"
    ws.sheet_properties.tabColor = "1072BA"

    # Ajustar ancho de columnas
    for col in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        ws.column_dimensions[col].width = 15

    # ENCABEZADO PERSONALIZADO
    fecha_actual = date.today().strftime("%d/%m/%Y")
    ws.append([f'{cueanexo_usuario} - Evaluación Matemática '])
    ws.append(['5° Grado - Ciclo 2025 - Fecha: ' + fecha_actual])
    ws.append([])  # Fila vacía para separar

    columnas = [
        'DNI', 'Apellidos', 'Nombres', 'Cueanexo', 'Grado', 'División', 'Región',
        'Preg 1 A', 'Preg 1 B', 'Preg 1 C', 'Preg 1 D',
        'Preg 2 A', 'Preg 2 B', 'Preg 2 C', 'Preg 2 D',
        'Preg 3 A', 'Preg 3 B', 'Preg 3 C', 'Preg 3 D',
        'Preg 4 A', 'Preg 4 B', 'Preg 4 C', 'Preg 4 D',
        'Preg 5', 
        'Preg 6 A', 'Preg 6 B', 'Preg 6 C', 
        'Preg 7 A', 'Preg 7 B', 'Preg 7 C', 'Preg 7 D',
        'Preg 8 A', 'Preg 8 B', 'Preg 8 C', 'Preg 8 D',
        'Preg 9 Planteo', 'Preg 9 Solución', 'Puntaje Total'
    ]

    ws.append(columnas)

    for division, examenes in examenes_por_division.items():
        ws.append([f'División: {division}'])
        for examen in examenes:
            fila = [
                examen.dni, examen.apellidos, examen.nombres, examen.cueanexo, examen.grado,
                examen.division, examen.region,
                examen.puntaje_preg1a, examen.puntaje_preg1b, examen.puntaje_preg1c, examen.puntaje_preg1d,
                examen.puntaje_preg2a, examen.puntaje_preg2b, examen.puntaje_preg2c, examen.puntaje_preg2d,
                examen.puntaje_preg3a, examen.puntaje_preg3b, examen.puntaje_preg3c, examen.puntaje_preg3d,
                examen.puntaje_preg4a, examen.puntaje_preg4b, examen.puntaje_preg4c, examen.puntaje_preg4d,
                examen.puntaje_preg5,
                examen.puntaje_preg6a, examen.puntaje_preg6b, examen.puntaje_preg6c,
                examen.puntaje_preg7a, examen.puntaje_preg7b, examen.puntaje_preg7c, examen.puntaje_preg7d,
                examen.puntaje_preg8a, examen.puntaje_preg8b, examen.puntaje_preg8c, examen.puntaje_preg8d,
                examen.puntaje_preg9a, examen.puntaje_preg9b,
                examen.puntaje_total,
            ]
            ws.append(fila)

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=examenes_matematica_quinto.xlsx'
    wb.save(response)
    return response

@login_required
def examen_quinto_detalle_modal(request, pk):
    examen = get_object_or_404(ExamenMatematicaQuintoGrado, pk=pk)
    items = list(range(1, 32))  # del 1 al 32
    print(examen)
    return render(request, 'operativchaco/matematica/quinto/examen_detalle_modal.html', {
        'examen': examen,
        'items': items,
    })


@login_required
def cerrar_carga_matematica_quinto(request):  
    user = request.user
    cueanexo = user.username
    fecha_actual = now().strftime('%d/%m/%Y %H:%M')
    region_usuario= EscuelasPrimariasMatematica.objects.filter(cueanexo=request.user.username).values_list('region_loc', flat=True).first()
    total_registros = ExamenMatematicaQuintoGrado.objects.filter(cueanexo=cueanexo).count()
    
    
 
    # ⚠️ Validar si ya se cerró la carga
    if RegistroAsistenciaMatematicaQuinto.objects.filter(cueanexo=cueanexo).exists():
        return HttpResponse("⚠️ La carga ya fue cerrada previamente.")

    # ✅ Obtener los ausentes del formulario
    try:
        ausentes = int(request.POST.get('alumnos_ausentes', 0))
    except (ValueError, TypeError):
        ausentes = 0
            
    # ✅ Guardar el registro del cierre
    RegistroAsistenciaMatematicaQuinto.objects.create(
        cueanexo=cueanexo,
        fecha=fecha_actual,
        region=region_usuario,
        total_registros=total_registros,
        ausentes=ausentes,
    )
    
    # ✅ Actualizar el estado de carga de quinto en EscuelasPrimariasMatematica
    EscuelasPrimariasMatematica.objects.filter(cueanexo=cueanexo).update(quinto="CARGADO")

    # ✅ Crear el contenido para el código QR
    qr_data = f"CUEANEXO: {cueanexo}\nFecha: {fecha_actual}\nTotal registros: {total_registros}"
    qr_img = qrcode.make(qr_data)
    qr_io = BytesIO()
    qr_img.save(qr_io, format='PNG')
    qr_io.seek(0)

    # ✅ Crear el PDF con estilo
    pdf_buffer = BytesIO()
    p = canvas.Canvas(pdf_buffer, pagesize=A4)
    width, height = A4

    # Título
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, height - 100, "📘 Evaluación Matemática - 5° Grado - 2025")

    # Detalles
    p.setFont("Helvetica", 12)
    p.drawString(100, height - 140, f"CUEANEXO: {cueanexo}")
    p.drawString(100, height - 160, f"Fecha de cierre: {fecha_actual}")
    p.drawString(100, height - 180, f"Cantidad de registros: {total_registros}")

    # Imagen QR
    qr_image = ImageReader(qr_io)
    p.drawImage(qr_image, 100, height - 400, width=150, height=150)

    # Finalizar
    p.showPage()
    p.save()
    pdf_buffer.seek(0)

    return FileResponse(pdf_buffer, as_attachment=True, filename=f'cierre_{cueanexo}.pdf')


import io
import logging
from datetime import datetime

import qrcode
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from django.http import FileResponse
from django.contrib.auth.decorators import login_required

from .models import VistaResultadoMatematicaQuinto

logger = logging.getLogger(__name__)


@login_required
def exportar_pdf_quinto(request, n_dni):
    try:
        examen = VistaResultadoMatematicaQuinto.objects.get(dni=n_dni)
    except VistaResultadoMatematicaQuinto.DoesNotExist:
        logger.error(f"No se encontró examen para DNI: {n_dni}")
        return FileResponse(io.BytesIO(b"No se encontro el examen."), content_type='application/pdf')

    # Campos de ítems
    item_fields = [
    "puntaje_preg1a", "puntaje_preg1b", "puntaje_preg1c", "puntaje_preg1d",
    "puntaje_preg2a", "puntaje_preg2b", "puntaje_preg2c", "puntaje_preg2d",
    "puntaje_preg3a", "puntaje_preg3b", "puntaje_preg3c", "puntaje_preg3d",
    "puntaje_preg4a", "puntaje_preg4b", "puntaje_preg4c", "puntaje_preg4d",
    "puntaje_preg5",
    "puntaje_preg6a", "puntaje_preg6b", "puntaje_preg6c",
    "puntaje_preg7a", "puntaje_preg7b", "puntaje_preg7c", "puntaje_preg7d",
    "puntaje_preg8a", "puntaje_preg8b", "puntaje_preg8c", "puntaje_preg8d",
    "puntaje_preg9a", "puntaje_preg9b"
]


    # Calcular puntaje total
    total_puntaje = sum(getattr(examen, campo, 0) or 0 for campo in item_fields)

    # Logging detallado
    logger.info(f"""
Examen obtenido:
DNI: {examen.dni}
Apellido: {examen.apellidos}
Nombre: {examen.nombres}
CUE: {examen.cueanexo}
Región: {examen.region}
Grado: {examen.grado}
División: {examen.division}
Puntaje total: {total_puntaje}
""")
    for i, campo in enumerate(item_fields, start=1):
        valor = getattr(examen, campo, 0) or 0
        simbolo = "✔️" if valor else "❌"
        logger.info(f"Ítem {i}: {simbolo} ({valor})")

    # Crear texto QR
    qr_data = f"""DNI: {examen.dni}
Apellidos: {examen.apellidos}
Nombres: {examen.nombres}
CUE: {examen.cueanexo}
Región: {examen.region}
Año: {examen.grado}
División: {examen.division}
Puntaje total: {total_puntaje}
Fecha de generación: {datetime.now().strftime('%d/%m/%Y %H:%M')}
Puntajes por ítem:"""

    for campo in item_fields:
        valor = getattr(examen, campo, 0) or 0
        simbolo = "✔️" if valor else "❌"
        qr_data += f"\n{campo}: {simbolo} ({valor})"

    # Crear imagen QR
    qr_img = qrcode.make(qr_data)
    qr_io = io.BytesIO()
    qr_img.save(qr_io, format='PNG')
    qr_io.seek(0)
    qr_pil = Image.open(qr_io)

    # Crear PDF
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 50
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Informe de Evaluación Matemática - 5° Grado - 2025")
    y -= 30

    p.setFont("Helvetica", 12)
    datos = [
        f"DNI: {examen.dni}",
        f"Apellidos: {examen.apellidos}",
        f"Nombres: {examen.nombres}",
        f"CUE: {examen.cueanexo}",
        f"Región: {examen.region}",
        f"Año: {examen.grado}",
        f"División: {examen.division}",
        f"Puntaje total: {total_puntaje}",
        f"Fecha de generación: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "Puntajes por ítem:"
    ]

    for linea in datos:
        p.drawString(50, y, linea)
        y -= 20

    # Tabla de ítems en dos columnas
    col1_x = 60
    col2_x = 300
    line_height = 18
    p.setFont("Helvetica", 12)

    for idx in range(0, len(item_fields), 2):
        campo1 = item_fields[idx]
        valor1 = getattr(examen, campo1, 0) or 0
        simbolo1 = "✔️" if valor1 else "❌"
        texto1 = f"{campo1}: {simbolo1} ({valor1})"
        p.drawString(col1_x, y, texto1)

        if idx + 1 < len(item_fields):
            campo2 = item_fields[idx + 1]
            valor2 = getattr(examen, campo2, 0) or 0
            simbolo2 = "✔️" if valor2 else "❌"
            texto2 = f"{campo2}: {simbolo2} ({valor2})"
            p.drawString(col2_x, y, texto2)

        y -= line_height

        if y < 100:
            p.showPage()
            y = height - 50
            p.setFont("Helvetica", 12)

    # Insertar QR
    p.drawInlineImage(qr_pil, width - 200, 50, width=150, height=150)

    p.showPage()
    p.save()
    buffer.seek(0)

    logger.info(f"PDF generado correctamente para DNI {examen.dni}")

    return FileResponse(buffer, as_attachment=True, filename='Evaluacion_matematica_quinto_2025.pdf')
