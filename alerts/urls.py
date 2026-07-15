from django.urls import path
from . import views

app_name = 'alerts'

urlpatterns = [
    path('', views.alerta_list, name='alerta_list'),
    path('<int:pk>/resolve/', views.alerta_resolver, name='alerta_resolver'),
    path('run-scan/', views.alerta_run_scan, name='alerta_run_scan'),
]
