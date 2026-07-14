from django.contrib import admin
from .models import SolicitudServicio

@admin.register(SolicitudServicio)
class SolicitudServicioAdmin(admin.ModelAdmin):
    list_display = ('request_id', 'cliente', 'fecha_servicio', 'hora_servicio', 'origen', 'destino', 'tipo_servicio', 'prioridad', 'tipo_vehiculo_requerido', 'estado_solicitud')
    list_filter = ('tipo_servicio', 'prioridad', 'tipo_vehiculo_requerido', 'estado_solicitud')
    search_fields = ('cliente', 'origen', 'destino')
    ordering = ('-fecha_servicio', '-hora_servicio')
