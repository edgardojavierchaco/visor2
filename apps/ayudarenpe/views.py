from django.shortcuts import render
from .models import FAQ, Concepto
from django.http import JsonResponse
from .models import FAQ
import es_core_news_sm

def index(request):
    return render(request, "ayudarenpe/index.html")

def faq_list(request):
    faqs = FAQ.objects.all()
    return render(request, "ayudarenpe/faq_list.html", {"faqs": faqs})

def glosario_list(request):
    conceptos = Concepto.objects.all()
    return render(request, "ayudarenpe/glosario_list.html", {"conceptos": conceptos})



# cargamos el modelo de spaCy
nlp = es_core_news_sm.load()

# API para el chatbot
def chatbot_api(request):
    pregunta_usuario = request.GET.get("q", "")
    if not pregunta_usuario:
        return JsonResponse({"respuesta": "Por favor, escribí una pregunta."})

    # Procesamos la pregunta con spaCy
    doc_usuario = nlp(pregunta_usuario)

    mejor_puntaje = 0
    mejor_respuesta = None
    sugerencias = []

    # Recorremos todas las FAQs
    for faq in FAQ.objects.all():
        doc_faq = nlp(faq.pregunta)
        similitud = doc_usuario.similarity(doc_faq)

        # Guardamos las mejores coincidencias
        sugerencias.append((faq.pregunta, faq.respuesta, similitud))

        if similitud > mejor_puntaje:
            mejor_puntaje = similitud
            mejor_respuesta = faq.respuesta

    # Ordenamos sugerencias por similitud
    sugerencias = sorted(sugerencias, key=lambda x: x[2], reverse=True)

    # Caso 1: hay una coincidencia fuerte
    if mejor_puntaje >= 0.70:
        return JsonResponse({"respuesta": mejor_respuesta})

    # Caso 2: no es seguro → devolvemos top 3 sugerencias
    else:
        top_sugerencias = [
            {"pregunta": s[0], "respuesta": s[1], "similitud": round(s[2], 2)}
            for s in sugerencias[:3]
        ]
        return JsonResponse({
            "respuesta": "🤖 No estoy seguro, pero quizás quisiste preguntar alguna de estas:",
            "sugerencias": top_sugerencias
        })

# Vista para renderizar el template
def chatbot_view(request):
    return render(request, "ayudarenpe/chatbot.html")
