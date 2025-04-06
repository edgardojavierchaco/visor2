# Librerías estándar
import io
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
from .models import EscuelasSecundarias, ExamenLenguaAlumno, RegistroAsistenciaLengua


class ExamenLenguaListView(LoginRequiredMixin, ListView):
    model = ExamenLenguaAlumno
    template_name = 'operativchaco/lengua/examen_lengua_list.html'
    context_object_name = 'examenes'
    paginate_by = 20

    def get_queryset(self):
        usuario = self.request.user
        cueanexo_usuario = usuario.username 
        return ExamenLenguaAlumno.objects.filter(cueanexo=cueanexo_usuario)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        usuario = self.request.user
        cueanexo_usuario = usuario.username
        region= EscuelasSecundarias.objects.filter(
            cueanexo=cueanexo_usuario).values_list('region_loc', flat=True).first()
        print(f"Usuario: {usuario}, CUEAnexo: {cueanexo_usuario}")
        
        context['fecha_actual'] = now().strftime('%d/%m/%Y %H:%M')
        context['region_usuario'] = region
        print(f"Región del usuario: {context['region_usuario']}")
        return context
        

class ExamenLenguaDetailView(LoginRequiredMixin, DetailView):
    model = ExamenLenguaAlumno
    template_name = 'operativchaco/lengua/examen_lengua_detail.html'
    context_object_name = 'examen'

@login_required
def exportar_excel_examenes(request):
    usuario = request.user
    cueanexo_usuario = usuario.username

    queryset = ExamenLenguaAlumno.objects.filter(cueanexo=cueanexo_usuario)

    # Agrupar exámenes por división
    exámenes_por_división = defaultdict(list)
    for examen in queryset:
        exámenes_por_división[examen.division].append(examen)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Exámenes Lengua"
    ws.sheet_properties.tabColor = "1072BA"

    # Ajustar ancho de columnas
    for col in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        ws.column_dimensions[col].width = 15

    # ENCABEZADO PERSONALIZADO
    fecha_actual = date.today().strftime("%d/%m/%Y")
    ws.append([f'{cueanexo_usuario} - Diagnóstico Área de Lengua'])
    ws.append(['1° Año - Ciclo 2025 - Fecha: ' + fecha_actual])
    ws.append([])  # Fila vacía para separar

    columnas = [
        'DNI', 'Apellidos', 'Nombres', 'CUEAnexo', 'Año', 'División', 'Región',
        'Item 1', 'Item 2', 'Item 3', 'Item 4', 'Item 5', 'Item 6', 'Item 7', 'Item 8',
        'Item 9', 'Item 10', 'Item 11', 'Item 12', 'Item 13', 'Item 14', 'Item 15', 'Item 16',
        'Total'
    ]

    ws.append(columnas)

    for division, examenes in exámenes_por_división.items():
        ws.append([f'División: {division}'])
        for examen in examenes:
            total = sum([
                examen.p1, examen.p2, examen.p3, examen.p4, examen.p5, examen.p6,
                examen.p7, examen.p8, examen.p9, examen.p10, examen.p11, examen.p12,
                examen.p13, examen.p14, examen.p15, examen.p16
            ])
            fila = [
                examen.dni, examen.apellidos, examen.nombres, examen.cueanexo, examen.anio,
                examen.division, examen.region, examen.p1, examen.p2, examen.p3, examen.p4,
                examen.p5, examen.p6, examen.p7, examen.p8, examen.p9, examen.p10,
                examen.p11, examen.p12, examen.p13, examen.p14, examen.p15, examen.p16,
                total
            ]
            ws.append(fila)

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=examenes_lengua.xlsx'
    wb.save(response)
    return response

@login_required
def examen_lengua_detalle_modal(request, pk):
    examen = get_object_or_404(ExamenLenguaAlumno, pk=pk)
    items = list(range(1, 17))  # del 1 al 16
    return render(request, 'operativchaco/lengua/examen_detalle_modal.html', {
        'examen': examen,
        'items': items,
    })


@login_required
def cerrar_carga_lengua(request):  
    user = request.user
    cueanexo = user.username
    fecha_actual = now().strftime('%d/%m/%Y %H:%M')
    region_usuario= EscuelasSecundarias.objects.filter(cueanexo=request.user.username).values_list('region', flat=True).first()
    total_registros = ExamenLenguaAlumno.objects.filter(cueanexo=cueanexo).count()
    
    
 
    # ⚠️ Validar si ya se cerró la carga
    if RegistroAsistenciaLengua.objects.filter(cueanexo=cueanexo).exists():
        return HttpResponse("⚠️ La carga ya fue cerrada previamente.")

    # ✅ Obtener los ausentes del formulario
    try:
        ausentes = int(request.POST.get('alumnos_ausentes', 0))
    except (ValueError, TypeError):
        ausentes = 0
            
    # ✅ Guardar el registro del cierre
    RegistroAsistenciaLengua.objects.create(
        cueanexo=cueanexo,
        fecha=fecha_actual,
        region=region_usuario,
        total_registros=total_registros,
        ausentes=ausentes,
    )
    
    # ✅ Actualizar el estado de carga de lengua en EscuelasSecundarias
    EscuelasSecundarias.objects.filter(cueanexo=cueanexo).update(lengua="CARGADO")

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
    p.drawString(100, height - 100, "📘 Diagnóstico Área Lengua 2025")

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

@login_required
def exportar_pdf(request, examen_id):
    examen = ExamenLenguaAlumno.objects.get(id=examen_id)

    # Campos de ítems
    item_fields = [f"p{i}" for i in range(1, 17)]

    # Calcular puntaje total
    total_puntaje = sum(getattr(examen, campo, 0) or 0 for campo in item_fields)

    # Crear texto para el QR
    qr_data = f"""DNI: {examen.dni}
Apellidos: {examen.apellidos}
Nombres: {examen.nombres}
CUE: {examen.cueanexo}
Región: {examen.region}
Año: {examen.anio}
División: {examen.division}
Puntaje total: {total_puntaje}
Fecha de generación: {datetime.now().strftime('%d/%m/%Y %H:%M')}
Puntajes por ítem:"""

    for i, campo in enumerate(item_fields, start=1):
        valor = getattr(examen, campo, 0) or 0
        simbolo = "✔️" if valor else "❌"
        qr_data += f"\nÍtem {i}: {simbolo} ({valor})"

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
    p.drawString(50, y, "Informe de Diagnóstico de Lengua 2025")
    y -= 30

    p.setFont("Helvetica", 12)
    datos = [
        f"DNI: {examen.dni}",
        f"Apellidos: {examen.apellidos}",
        f"Nombres: {examen.nombres}",
        f"CUE: {examen.cueanexo}",
        f"Región: {examen.region}",
        f"Año: {examen.anio}",
        f"División: {examen.division}",
        f"Puntaje total: {total_puntaje}",
        f"Fecha de generación: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "Puntajes por ítem:"
    ]

    for linea in datos:
        p.drawString(50, y, linea)
        y -= 20

    for i, campo in enumerate(item_fields, start=1):
        valor = getattr(examen, campo, 0) or 0
        simbolo = "✔️" if valor else "❌"
        texto_item = f"Ítem {i}: {simbolo} ({valor})"
        p.drawString(60, y, texto_item)
        y -= 18
        if y < 100:
            p.showPage()
            y = height - 50
            p.setFont("Helvetica", 12)

    # Insertar QR
    p.drawInlineImage(qr_pil, width - 200, 50, width=150, height=150)
    p.showPage()
    p.save()
    buffer.seek(0)

    return FileResponse(buffer, as_attachment=True, filename='Diagnostico_Lengua_2025.pdf')