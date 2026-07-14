from django.contrib import admin
from .models import Asignacion

@admin.register(Asignacion)
class AsignacionAdmin(admin.ModelAdmin):
    list_display = ('assignment_id', 'solicitud', 'conductor', 'vehiculo', 'estado_asignacion', 'fecha_asignacion')
    list_filter = ('estado_asignacion', 'fecha_asignacion')
    search_fields = ('solicitud__cliente', 'conductor__apellidos', 'conductor__nombres', 'vehiculo__placa')
    ordering = ('-fecha_asignacion',)
