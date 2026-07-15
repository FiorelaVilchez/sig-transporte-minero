import datetime
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def home(request):
    return render(request, 'core/home.html', {
        'today': datetime.date.today(),
    })

@login_required
def perfil(request):
    return render(request, 'core/perfil.html')


