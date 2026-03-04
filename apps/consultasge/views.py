# views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .decorators import rol_requerido
from .models import Consulta, Adjunto
from .services import crear_consulta
from .forms import ConsultaForm


@login_required
def dashboard(request):

    abiertas = Consulta.objects.filter(estado="abierta").count()
    respondidas = Consulta.objects.filter(estado="respondida").count()
    total = Consulta.objects.count()

    return render(request,"consultasge/dashboard.html",{
        "abiertas":abiertas,
        "respondidas":respondidas,
        "total":total
    })


@login_required
def nueva_consulta(request):

    form = ConsultaForm(request.POST or None)

    if form.is_valid():

        consulta = crear_consulta(
            request.user,
            form.cleaned_data["asunto"],
            form.cleaned_data["mensaje"],
            form.cleaned_data["categoria"]
        )

        # 🔹 Guardar adjuntos
        archivos = request.FILES.getlist("archivos")

        for archivo in archivos:
            Adjunto.objects.create(
                consulta=consulta,
                archivo=archivo
            )

        return redirect("consultasge:consultas_lista")

    return render(request,"consultasge/nueva.html",{"form":form})


@login_required
@rol_requerido("Director/a")
def consultas_lista(request):

    consultas = Consulta.objects.filter(
        usuario=request.user
    ).order_by("-fecha_creacion")

    return render(request,"consultasge/lista.html",{
        "consultas":consultas
    })


@login_required
def consulta_detalle(request,id):

    # 🔐 Sólo puede ver SUS consultas
    consulta = get_object_or_404(
        Consulta,
        id=id,
        usuario=request.user
    )

    return render(request,"consultasge/detalle.html",{
        "consulta":consulta
    })