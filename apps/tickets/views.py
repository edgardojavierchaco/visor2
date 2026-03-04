from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Ticket,TicketMensaje
from .utils import obtener_region_escuela,obtener_gestor_region


@login_required
def crear_ticket(request):

    if request.method == "POST":

        cue = request.user.username

        region = obtener_region_escuela(cue)

        gestor = obtener_gestor_region(region)

        asunto = request.POST["asunto"]

        mensaje = request.POST["mensaje"]

        ticket = Ticket.objects.create(
            escuela_cueanexo=cue,
            region=region,
            gestor=gestor,
            asunto=asunto
        )

        TicketMensaje.objects.create(
            ticket=ticket,
            autor=request.user,
            mensaje=mensaje
        )

        return redirect("mis_tickets")

    return render(request,"tickets/crear_ticket.html")


@login_required
def mis_tickets(request):

    tickets = Ticket.objects.filter(
        escuela_cueanexo=request.user.username
    ).order_by("-fecha_creacion")

    return render(
        request,
        "tickets/mis_tickets.html",
        {"tickets":tickets}
    )


@login_required
def tickets_gestor(request):

    tickets = Ticket.objects.filter(
        gestor=request.user,
        cerrado=False
    ).order_by("-fecha_creacion")

    return render(
        request,
        "tickets/tickets_gestor.html",
        {"tickets":tickets}
    )


@login_required
def ver_ticket(request,id):

    ticket = get_object_or_404(Ticket,id=id)

    mensajes = ticket.mensajes.all().order_by("fecha")

    if request.method == "POST":

        texto = request.POST["mensaje"]

        TicketMensaje.objects.create(
            ticket=ticket,
            autor=request.user,
            mensaje=texto
        )

        ticket.estado = "respondido"

        ticket.save()

        return redirect("ver_ticket",id=id)

    return render(
        request,
        "tickets/ver_ticket.html",
        {
            "ticket":ticket,
            "mensajes":mensajes
        }
    )


@login_required
def cerrar_ticket(request,id):

    ticket = Ticket.objects.get(id=id)

    ticket.cerrado=True
    ticket.estado="cerrado"
    ticket.save()

    return redirect("mis_tickets")