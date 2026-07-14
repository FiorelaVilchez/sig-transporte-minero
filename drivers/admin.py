from django.contrib import admin
from .models import Conductor

@admin.register(Conductor)
class ConductorAdmin(admin.ModelAdmin):
    list_display = ('apellidos', 'nombres', 'licencia', 'dni', 'especialidad', 'estado', 'fecha_ingreso')
    list_filter = ('estado', 'especialidad')
    search_fields = ('apellidos', 'nombres', 'dni', 'licencia')
    ordering = ('apellidos', 'nombres')
