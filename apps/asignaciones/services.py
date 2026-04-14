from .models import EscuelaCapaOfertas


def escuelas_permitidas(supervisor):

    regiones = supervisor.regiones.values_list("nombre", flat=True)
    ofertas = supervisor.niveles_modalidad.values_list("nombre", flat=True)

    return EscuelaCapaOfertas.objects.filter(
        region_loc__in=regiones,
        oferta__in=ofertas,
    )