from django.contrib import admin
from .models import Vehiculo

@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display = ('placa', 'tipo', 'capacidad', 'estado', 'revision_tecnica_vigente', 'seguro_vigente', 'homologacion', 'mantenimiento_programado')
    list_filter = ('tipo', 'estado', 'revision_tecnica_vigente', 'seguro_vigente')
    search_fields = ('placa', 'homologacion')
    ordering = ('placa',)
