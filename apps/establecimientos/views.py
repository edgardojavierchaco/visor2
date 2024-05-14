from django.shortcuts import render
from .models import PadronOfertas

def establecimientos(request):
    # Filtrar los establecimientos según los criterios requeridos
    establecimientos = PadronOfertas.objects.filter(cueanexo__endswith='00', est_oferta='Activo')

    # Renderizar la vista con los establecimientos filtrados
    return render(request, 'establecimientos/establecimientos.html', {'establecimientos': establecimientos})
