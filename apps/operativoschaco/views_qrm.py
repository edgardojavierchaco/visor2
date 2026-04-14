import io
import qrcode
from django.http import FileResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from django.utils.timezone import now
from reportlab.lib.utils import ImageReader
from .models import ExamenAlumnoCueanexoM, CierreCargaM

def cerrar_carga_matem(request):
    user = request.user  # Objeto User
    registros = ExamenAlumnoCueanexoM.objects.filter(alumno__cueanexo=user.username).count()
    fecha_cierre = now()

    # Guardar el cierre en la base de datos
    cierre = CierreCargaM.objects.create(usuario=user, total_registros=registros)

    # Crear QR
    qr_data = f'Usuario: {user.username}\nFecha: {fecha_cierre.date()}\nRegistros: {registros}'
    qr_img = qrcode.make(qr_data)
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)

    qr_image = ImageReader(qr_buffer)  # 🔸 Esta línea es nueva

    # Crear PDF
    pdf_buffer = io.BytesIO()
    p = canvas.Canvas(pdf_buffer, pagesize=A4)
    p.setFont("Helvetica", 12)
    p.drawString(100, 800, f"Cierre de carga - Usuario: {user.username}")
    p.drawString(100, 780, f"Fecha de cierre: {fecha_cierre.strftime('%d/%m/%Y %H:%M')}")
    p.drawString(100, 760, f"Total de registros cargados: {registros}")
    p.drawImage(qr_image, 100, 600, width=150, height=150)  # 🔸 Usá `drawImage` con ImageReader

    p.showPage()
    p.save()
    pdf_buffer.seek(0)

    return FileResponse(pdf_buffer, as_attachment=True, filename='cierre_carga_matematica.pdf')
