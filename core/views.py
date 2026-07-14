import datetime
from django.shortcuts import render

def home(request):
    return render(request, 'core/home.html', {
        'today': datetime.date.today(),
    })

