from django.contrib import admin
from .models import Asignacion, Notificacion

@admin.register(Asignacion)
class AsignacionAdmin(admin.ModelAdmin):
    list_display = ('assignment_id', 'solicitud', 'conductor', 'vehiculo', 'estado_asignacion', 'fecha_asignacion')
    list_filter = ('estado_asignacion', 'fecha_asignacion')
    search_fields = ('solicitud__cliente', 'conductor__apellidos', 'conductor__nombres', 'vehiculo__placa')
    ordering = ('-fecha_asignacion',)


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ('id', 'conductor', 'mensaje', 'leida', 'fecha')
    list_filter = ('leida', 'fecha')
    search_fields = ('conductor__apellidos', 'conductor__nombres', 'mensaje')
    ordering = ('-fecha',)

