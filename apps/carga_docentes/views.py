from django.shortcuts import render
from django.http import JsonResponse
from .models import Personal
from apps.consultasge.models import CapaUnicaOfertas
from .models import DocenteFrenteGrado
from .forms import DocenteFrenteGradoForm


#######################
# CREAR DOCENTE
#######################
def crear_docente(request):

    form = DocenteFrenteGradoForm()

    return render(request, 'carga_docentes/form.html', {
        'form': form
    })


########################
# API CUEANEXO
########################
def api_cueanexo(request):

    cue = request.GET.get('cueanexo')

    try:
        obj = CapaUnicaOfertas.objects.get(cueanexo=cue)

        return JsonResponse({
            'found': True,
            'nom_est': obj.nom_est,
            'oferta': obj.oferta
        })

    except:
        return JsonResponse({'found': False})


########################
# API PERSONAL
########################
def api_personal(request):

    cuil = request.GET.get('cuil')

    obj, created = Personal.objects.get_or_create(
        cuil=cuil,
        defaults={
            'apellido': '',
            'nombres': ''
        }
    )

    return JsonResponse({
        'found': True,
        'apellido': obj.apellido,
        'nombres': obj.nombres,
        'created': created
    })
    
    
###########################
#