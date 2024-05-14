from django.contrib import admin
from .models import Room, Message, Manager

#Personalizamos el Admin de Message
class MessageAdmin(admin.ModelAdmin):
    list_display = ('user','room','message','timestamp')
    
    #Filtros para filtrar la información
    list_filter = ('room','user')
    
admin.site.register(Room)
admin.site.register(Message, MessageAdmin)
admin.site.register(Manager)
