from django.shortcuts import render

def publico(request):
    return render(request,'dashboard/portada.html')
