from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from .services.permission_service import get_responsable
from apps.supervisa2.models import SituacionRevista, NivelModalidad

from django.views.decorators.csrf import ensure_csrf_cookie

@ensure_csrf_cookie
@login_required
def dashboard(request):

    responsable = get_responsable(request.user)

    return render(request, "supervisores/dashboard.html", {
        "responsable": responsable,
        "regiones": responsable.regiones.all() if responsable else [],
        "situaciones": SituacionRevista.objects.all(),
        "niveles": NivelModalidad.objects.all(),
    })