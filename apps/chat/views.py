from django.http import HttpResponseForbidden
from django.shortcuts import render
from .models import Room, Manager
from django.contrib.auth.decorators import login_required

def homeChat(request):
    rooms=Room.objects.all()
    return render(request,'chat/home.html', {'rooms':rooms})

@login_required
def roomChat(request, room_id):
    try:
        room=request.user.rooms_joined.get(id=room_id)
        available_managers = Manager.objects.filter(is_available=True)
        manager_assigned = room.manager_assigned
        print('available-manager:',available_managers)
    except Room.DoesNotExist:
        error_message='No tiene permisos de acceso a este Chat'
        return render(request, 'chat/home.html', {'error_message': error_message, 'rooms': Room.objects.all()})
    
    return render(request, 'chat/room.html', {'room': room, 'manager_assigned': manager_assigned,'available_managers': available_managers})

@login_required
def private_chat(request, room_id):
    room = Room.objects.get(id=room_id)
    manager = room.manager_assigned  # Obtener el gestor asignado a la sala
    return render(request, 'chat/private_chat.html', {'room': room, 'manager': manager})