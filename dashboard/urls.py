from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_operativo, name='operativo'),
    path('actualizar/', views.dashboard_actualizar, name='actualizar'),
    path('reportes/', views.reportes_gerenciales, name='reportes'),
    path('reportes/generar/', views.reportes_generar_csv, name='generar_csv'),
    path('reportes/descargar/zip/', views.reportes_descargar_zip, name='descargar_zip'),
    path('reportes/descargar/<str:filename>/', views.reportes_descargar_csv, name='descargar_csv'),
]
