from django.shortcuts import render

def publico(request):
    return render(request,'publico/base.html')
