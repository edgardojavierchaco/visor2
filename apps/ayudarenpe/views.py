from django.shortcuts import render
from .models import FAQ, Concepto

def index(request):
    return render(request, "ayudarenpe/index.html")

def faq_list(request):
    faqs = FAQ.objects.all()
    return render(request, "ayudarenpe/faq_list.html", {"faqs": faqs})

def glosario_list(request):
    conceptos = Concepto.objects.all()
    return render(request, "ayudarenpe/glosario_list.html", {"conceptos": conceptos})
