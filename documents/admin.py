from django.contrib import admin
from .models import DocumentoConductor, DocumentoVehiculo

@admin.register(DocumentoConductor)
class DocumentoConductorAdmin(admin.ModelAdmin):
    list_display = ('conductor', 'tipo_documento', 'fecha_emision', 'fecha_vencimiento', 'estado_documento')
    list_filter = ('tipo_documento', 'estado_documento')
    search_fields = ('conductor__apellidos', 'conductor__nombres', 'conductor__dni')
    ordering = ('-fecha_vencimiento',)

@admin.register(DocumentoVehiculo)
class DocumentoVehiculoAdmin(admin.ModelAdmin):
    list_display = ('vehiculo', 'tipo_documento', 'fecha_emision', 'fecha_vencimiento', 'estado_documento')
    list_filter = ('tipo_documento', 'estado_documento')
    search_fields = ('vehiculo__placa',)
    ordering = ('-fecha_vencimiento',)
