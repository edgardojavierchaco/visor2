from django.shortcuts import render, redirect
from datetime import datetime
from django.utils.timezone import make_aware, is_naive
from apps.cuenta_regresiva.models import FechaEvento
import pytz

def cuenta_regresiva_matematica(request):
    # Define la zona horaria
    zona_horaria = pytz.timezone('UTC')  

    # Ejemplo usando un modelo, ajusta según lo necesites
    fecha_evento = FechaEvento.objects.filter(nombre='Apertura Matematica').first()
    fecha_futura = fecha_evento.fecha_evento
    print(fecha_futura)
    # Verifica si la fecha es naive y la convierte a aware si es necesario
    if is_naive(fecha_futura):
        fecha_futura = make_aware(fecha_futura, timezone=zona_horaria)

    # Obtiene la fecha actual con la misma zona horaria
    fecha_actual = datetime.now(zona_horaria)

    # Compara sólo las fechas sin la hora para mayor precisión
    if fecha_futura.date() <= fecha_actual.date():
        # Renderiza a otro template si las fechas son iguales
        return redirect('operativ:examen_matematica_listado')
    else:
        # Calcula el tiempo restante
        tiempo_restante = fecha_futura - fecha_actual

        dias, segundos = tiempo_restante.days, tiempo_restante.seconds
        horas = segundos // 3600
        minutos = (segundos % 3600) // 60
        segundos = segundos % 60

        contexto = {
            'dias': dias,
            'horas': horas,
            'minutos': minutos,
            'segundos': segundos,
        }

        return render(request, 'operativchaco/cuentas_regresivas/cuenta_exmatem.html', contexto)

def cuenta_regresiva_lengua_graficos(request):
    # Define la zona horaria
    zona_horaria = pytz.timezone('UTC') 

    # Ejemplo usando un modelo
    fecha_evento = FechaEvento.objects.filter(nombre='Grafico Lengua').first()
    fecha_futura = fecha_evento.fecha_evento
    print(fecha_futura)
    # Verifica si la fecha es naive y la convierte a aware si es necesario
    if is_naive(fecha_futura):
        fecha_futura = make_aware(fecha_futura, timezone=zona_horaria)

    # Obtiene la fecha actual con la misma zona horaria
    fecha_actual = datetime.now(zona_horaria)

    # Compara solo las fechas sin la hora para mayor precisión
    if fecha_futura.date() <= fecha_actual.date():
        # Renderiza a otro template si las fechas son iguales
        return redirect('operativ:graficos_lengua')
    else:
        # Calcula el tiempo restante
        tiempo_restante = fecha_futura - fecha_actual

        dias, segundos = tiempo_restante.days, tiempo_restante.seconds
        horas = segundos // 3600
        minutos = (segundos % 3600) // 60
        segundos = segundos % 60

        contexto = {
            'dias': dias,
            'horas': horas,
            'minutos': minutos,
            'segundos': segundos,
        }

        return render(request, 'operativchaco/cuentas_regresivas/lengua_grafico.html', contexto)


def cuenta_regresiva_matematica_graficos(request):
    # Define la zona horaria
    zona_horaria = pytz.timezone('UTC') 

    # Ejemplo usando un modelo
    fecha_evento = FechaEvento.objects.filter(nombre='Grafico Matematica').first()
    fecha_futura = fecha_evento.fecha_evento
    print(fecha_futura)
    # Verifica si la fecha es naive y la convierte a aware si es necesario
    if is_naive(fecha_futura):
        fecha_futura = make_aware(fecha_futura, timezone=zona_horaria)

    # Obtiene la fecha actual con la misma zona horaria
    fecha_actual = datetime.now(zona_horaria)

    # Compara solo las fechas sin la hora para mayor precisión
    if fecha_futura.date() <= fecha_actual.date():
        # Renderiza a otro template si las fechas son iguales
        return redirect('operativ:graficos_matematica')
    else:
        # Calcula el tiempo restante
        tiempo_restante = fecha_futura - fecha_actual

        dias, segundos = tiempo_restante.days, tiempo_restante.seconds
        horas = segundos // 3600
        minutos = (segundos % 3600) // 60
        segundos = segundos % 60

        contexto = {
            'dias': dias,
            'horas': horas,
            'minutos': minutos,
            'segundos': segundos,
        }

        return render(request, 'operativchaco/cuentas_regresivas/matematica_grafico.html', contexto)
