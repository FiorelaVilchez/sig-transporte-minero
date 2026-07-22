from django.urls import path
from . import views

app_name = 'assignments'

urlpatterns = [
    path('requests/', views.solicitudes_pendientes_list, name='solicitudes_pendientes'),
    path('auto/<int:solicitud_id>/', views.asignar_automatica_view, name='asignar_automatica'),
    path('manual/<int:solicitud_id>/', views.asignar_manual_view, name='asignar_manual'),
    path('complete/<int:solicitud_id>/', views.completar_servicio_view, name='completar_servicio'),
    path('mis-servicios/', views.mis_servicios_conductor, name='mis_servicios'),
    path('notificacion/leer/<int:notificacion_id>/', views.marcar_notificacion_leida, name='leer_notificacion'),
]
