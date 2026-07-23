from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_operativo, name='operativo'),
    path('actualizar/', views.dashboard_actualizar, name='actualizar'),
    path('reportes/', views.reportes_gerenciales, name='reportes'),
]
