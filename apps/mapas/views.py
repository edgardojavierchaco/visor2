from django.shortcuts import render
from .services import OfertaEducativaService

def filtrado(request):    
    return render(request, 'mapa/filter.html')

def filter_data(request):
    params = request.POST if request.method == 'POST' else {}
    context = OfertaEducativaService.filtrar_ofertas_mapa(params)
    context['title'] = 'Mapa'
    return render(request, 'mapa/ofertasmark.html', context)

def filter_listado_map(request):
    params = request.POST if request.method == 'POST' else {}
    context = OfertaEducativaService.filtrar_ofertas_mapa(params)
    return render(request, 'publico/listadomap.html', context)

def filtrar_tablas_view(request):
    cueanexo = request.GET.get('cueanexo')
    oferta_rec = request.GET.get('oferta')

    if not cueanexo:
        return render(request, 'error.html', {'mensaje': 'No se proporcionó cueanexo'})

    try:
        inst, planes, anexos, ofertas_lista, matricula = OfertaEducativaService.obtener_detalle_completo(cueanexo, oferta_rec)
        
        context = {
            'resultados': inst,
            'resultados1': planes,
            'resultados2': anexos,
            'resultados3': ofertas_lista,
            'resultados_detalle': [matricula] if matricula else []
        }
        return render(request, 'mapa/otro_template.html', context)
    except Exception as e:
        import traceback
        print(traceback.format_exc()) # Esto imprimirá el error real en tu consola negra (terminal)
        return render(request, 'error.html', {'mensaje': f'Error técnico: {str(e)}'})