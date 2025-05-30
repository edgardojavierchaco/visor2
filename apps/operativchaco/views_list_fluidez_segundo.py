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
from .models import EscuelasPrimarias, ExamenFluidezSegundo, RegistroAsistenciaFluidezSegundo 


class ExamenFluidezSegundoListView(LoginRequiredMixin, ListView):
    model = ExamenFluidezSegundo
    template_name = 'operativchaco/fluidez/segundo/examen_segundo_list.html'
    context_object_name = 'examenes'
    #paginate_by = 20

    def get_queryset(self):
        usuario = self.request.user
        cueanexo_usuario = usuario.username 
        return ExamenFluidezSegundo.objects.filter(cueanexo=cueanexo_usuario)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        usuario = self.request.user
        cueanexo_usuario = usuario.username
        region= EscuelasPrimarias.objects.filter(
            cueanexo=cueanexo_usuario).values_list('region_loc', flat=True).first()
        print(f"Usuario: {usuario}, CUEAnexo: {cueanexo_usuario}")
        
        context['fecha_actual'] = now().strftime('%d/%m/%Y %H:%M')
        context['region_usuario'] = region
        print(f"Región del usuario: {context['region_usuario']}")
        return context
        

class ExamenFluidezSegundoDetailView(LoginRequiredMixin, DetailView):
    model = ExamenFluidezSegundo
    template_name = 'operativchaco/fluidez/segundo/examen_segundo_detail.html'
    context_object_name = 'examen'

@login_required
def exportar_excel_examenes_segundo(request):
    usuario = request.user
    cueanexo_usuario = usuario.username

    queryset = ExamenFluidezSegundo.objects.filter(cueanexo=cueanexo_usuario)

    # Agrupar exámenes por división
    exámenes_por_división = defaultdict(list)
    for examen in queryset:
        exámenes_por_división[examen.division].append(examen)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Exámenes Fluidez Lectora 2025 - Segundo Grado"
    ws.sheet_properties.tabColor = "1072BA"

    # Ajustar ancho de columnas
    for col in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        ws.column_dimensions[col].width = 15

    # ENCABEZADO PERSONALIZADO
    fecha_actual = date.today().strftime("%d/%m/%Y")
    ws.append([f'{cueanexo_usuario} - Evaluación Fluidez Lectora'])
    ws.append(['2° Grado - Ciclo 2025 - Fecha: ' + fecha_actual])
    ws.append([])  # Fila vacía para separar

    columnas = [
        'DNI', 'Apellidos', 'Nombres', 'Cueanexo', 'Grado', 'División', 'Región',
        'Velocidad', 'Precisión', 'Prosodia'
    ]

    ws.append(columnas)

    for division, examenes in exámenes_por_división.items():
        ws.append([f'División: {division}'])
        for examen in examenes:
            """ total = sum([
                examen.velocidad, examen.precision, examen.prosodia
            ]) """
            fila = [
                examen.dni, examen.apellidos, examen.nombres, examen.cueanexo, examen.grado,
                examen.division, examen.region, examen.velocidad, examen.precision, examen.prosodia
            ]
            ws.append(fila)

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=examenes_fluidez_segundo.xlsx'
    wb.save(response)
    return response

@login_required
def examen_segundo_detalle_modal(request, pk):
    examen = get_object_or_404(ExamenFluidezSegundo, pk=pk)
    items = list(range(1, 4))  # del 1 al 4
    print(examen)
    return render(request, 'operativchaco/fluidez/segundo/examen_detalle_modal.html', {
        'examen': examen,
        'items': items,
    })


@login_required
def cerrar_carga_fluidez_segundo(request):  
    user = request.user
    cueanexo = user.username
    fecha_actual = now().strftime('%d/%m/%Y %H:%M')
    region_usuario= EscuelasPrimarias.objects.filter(cueanexo=request.user.username).values_list('region_loc', flat=True).first()
    total_registros = ExamenFluidezSegundo.objects.filter(cueanexo=cueanexo).count()
    
    
 
    # ⚠️ Validar si ya se cerró la carga
    if RegistroAsistenciaFluidezSegundo.objects.filter(cueanexo=cueanexo).exists():
        return HttpResponse("⚠️ La carga ya fue cerrada previamente.")

    # ✅ Obtener los ausentes del formulario
    try:
        ausentes = int(request.POST.get('alumnos_ausentes', 0))
    except (ValueError, TypeError):
        ausentes = 0
            
    # ✅ Guardar el registro del cierre
    RegistroAsistenciaFluidezSegundo.objects.create(
        cueanexo=cueanexo,
        fecha=fecha_actual,
        region=region_usuario,
        total_registros=total_registros,
        ausentes=ausentes,
    )
    
    # ✅ Actualizar el estado de carga de lengua en EscuelasSecundarias
    EscuelasPrimarias.objects.filter(cueanexo=cueanexo).update(segundo="CARGADO")

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
    p.drawString(100, height - 100, "📘 Evaluación Fluidez y Comprensión Lectora - 2° Grado - 2025")

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
def exportar_pdf_segundo(request, examen_id):
    examen = ExamenFluidezSegundo.objects.get(id=examen_id)

    # Campos de ítems
    item_fields = [f"p{i}" for i in range(1, 4)]

    # Calcular puntaje total
    total_puntaje = sum(getattr(examen, campo, 0) or 0 for campo in item_fields)

    # Crear texto para el QR
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
    p.drawString(50, y, "Informe de Evaluación Fluidez y Comprensión Lectora - 2° Grado - 2025")
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

    return FileResponse(buffer, as_attachment=True, filename='Evaluacion_fluidez_lectora_segunda_2025.pdf')