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
    path('servicio/<int:asignacion_id>/checklist/', views.checklist_view, name='checklist'),
    path('servicio/<int:asignacion_id>/iniciar/', views.iniciar_ruta_view, name='iniciar_ruta'),
    path('servicio/<int:asignacion_id>/incidencia/', views.incidencia_view, name='incidencia'),
    path('servicio/<int:asignacion_id>/gasto/', views.gasto_view, name='gasto'),
    path('servicio/<int:asignacion_id>/finalizar/', views.finalizar_view, name='finalizar'),
    path('programacion/', views.programacion_semanal, name='programacion'),
]
