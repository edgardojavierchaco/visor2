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
from .models import EscuelasSecundariasMatematica, ExamenMatematicaSegundoAnio, RegistroAsistenciaMatematicaSegundoAnio, VistaResultadoMatematicaSegundoAnio


class ExamenMatematicaSegundoAnioListView(LoginRequiredMixin, ListView):
    model = ExamenMatematicaSegundoAnio
    template_name = 'operativchaco/matematica/segundo/examen_segundo_list.html'
    context_object_name = 'examenes'
    #paginate_by = 20

    def get_queryset(self):
        usuario = self.request.user
        cueanexo_usuario = usuario.username 
        return ExamenMatematicaSegundoAnio.objects.filter(cueanexo=cueanexo_usuario)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        usuario = self.request.user
        cueanexo_usuario = usuario.username
        region= EscuelasSecundariasMatematica.objects.filter(
            cueanexo=cueanexo_usuario).values_list('region_loc', flat=True).first()
        print(f"Usuario: {usuario}, CUEAnexo: {cueanexo_usuario}")
        
        context['fecha_actual'] = now().strftime('%d/%m/%Y %H:%M')
        context['region_usuario'] = region
        print(f"Región del usuario: {context['region_usuario']}")
        return context
        

class ExamenMatematicaSegundoAnioDetailView(LoginRequiredMixin, DetailView):
    model = ExamenMatematicaSegundoAnio
    template_name = 'operativchaco/matematica/segundo/examen_segundo_detail.html'
    context_object_name = 'examen'

@login_required
def exportar_excel_examenes_segundo_anio(request):
    usuario = request.user
    cueanexo_usuario = usuario.username

    queryset = VistaResultadoMatematicaSegundoAnio .objects.filter(cueanexo=cueanexo_usuario)

    # Agrupar exámenes por división
    examenes_por_division = defaultdict(list)
    for examen in queryset:
        examenes_por_division[examen.division].append(examen)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Exámenes Matemática 2025 - Segundo Año"
    ws.sheet_properties.tabColor = "1072BA"

    # Ajustar ancho de columnas
    for col in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        ws.column_dimensions[col].width = 15

    # ENCABEZADO PERSONALIZADO
    fecha_actual = date.today().strftime("%d/%m/%Y")
    ws.append([f'{cueanexo_usuario} - Evaluación Matemática '])
    ws.append(['2° Año - Ciclo 2025 - Fecha: ' + fecha_actual])
    ws.append([])  # Fila vacía para separar

    columnas = [
        'DNI', 'Apellidos', 'Nombres', 'Cueanexo', 'Año', 'División', 'Región',
        'Preg 1', 'Preg 2', 
        'Preg 3', 'Preg 4', 
        'Preg 5', 'Preg 6 A', 'Preg 6 B', 
        'Preg 7', 'Preg 8 A', 'Preg 8 B', 
        'Preg 9', 'Preg 10', 
    ]

    ws.append(columnas)

    for division, examenes in examenes_por_division.items():
        ws.append([f'División: {division}'])
        for examen in examenes:
            fila = [
                examen.dni, examen.apellidos, examen.nombres, examen.cueanexo, examen.grado,
                examen.division, examen.region,
                examen.preg1, examen.preg2, 
                examen.preg3, examen.preg4, 
                examen.preg5, examen.preg6a, examen.preg6b, 
                examen.preg7, examen.preg8a, examen.preg8b, 
                examen.preg9, examen.preg10,
            ]
            ws.append(fila)

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=examenes_matematica_segundo_anio.xlsx'
    wb.save(response)
    return response
    
@login_required
def examen_segundo_detalle_modal(request, pk):
    examen = get_object_or_404(ExamenMatematicaSegundoAnio, pk=pk)
    items = list(range(1, 20))  # del 1 al 21
    print(examen)
    return render(request, 'operativchaco/matematica/segundo/examen_detalle_modal.html', {
        'examen': examen,
        'items': items,
    })


@login_required
def cerrar_carga_matematica_segundo_anio(request):  
    user = request.user
    cueanexo = user.username
    fecha_actual = now().strftime('%d/%m/%Y %H:%M')
    region_usuario= EscuelasSecundariasMatematica.objects.filter(cueanexo=request.user.username).values_list('region_loc', flat=True).first()
    total_registros = ExamenMatematicaSegundoAnio.objects.filter(cueanexo=cueanexo).count()
    
    
 
    # ⚠️ Validar si ya se cerró la carga
    if RegistroAsistenciaMatematicaSegundoAnio.objects.filter(cueanexo=cueanexo).exists():
        return HttpResponse("⚠️ La carga ya fue cerrada previamente.")

    # ✅ Obtener los ausentes del formulario
    try:
        ausentes = int(request.POST.get('alumnos_ausentes', 0))
    except (ValueError, TypeError):
        ausentes = 0
            
    # ✅ Guardar el registro del cierre
    RegistroAsistenciaMatematicaSegundoAnio.objects.create(
        cueanexo=cueanexo,
        fecha=fecha_actual,
        region=region_usuario,
        total_registros=total_registros,
        ausentes=ausentes,
    )
    
    # ✅ Actualizar el estado de carga de quinto en EscuelasPrimariasMatematica
    EscuelasSecundariasMatematica.objects.filter(cueanexo=cueanexo).update(segundo="CARGADO")

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
    p.drawString(100, height - 100, "📘 Evaluación Matemática - 2° Año - 2025")

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


from .models import VistaResultadoMatematicaSegundoAnio

logger = logging.getLogger(__name__)


@login_required
def exportar_pdf_segundo_anio(request, n_dni):
    try:
        examen = VistaResultadoMatematicaSegundoAnio.objects.get(dni=n_dni)
    except VistaResultadoMatematicaSegundoAnio.DoesNotExist:
        logger.error(f"No se encontró examen para DNI: {n_dni}")
        return FileResponse(io.BytesIO(b"No se encontro el examen."), content_type='application/pdf')

    # Campos de ítems
    item_fields = [
    "preg1", "preg2", 
    "preg3", "preg4", 
    "preg5", "preg6a", "preg6b", 
    "preg7", "preg8a", "preg8b", 
    "preg9", "preg10"
]


    # Calcular puntaje total
    #total_puntaje = sum(getattr(examen, campo, 0) or 0 for campo in item_fields)

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
    p.drawString(50, y, "Informe de Evaluación Matemática - 2° Año - 2025")
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

    return FileResponse(buffer, as_attachment=True, filename='Evaluacion_matematica_segundo_anio_2025.pdf')
