from django.shortcuts import render
from .models import ArchNoramtiva

def ver_normas(request):
    norma=ArchNoramtiva.objects.all()
    return render(request, 'normativa/ver_normas.html', {'norma':norma})