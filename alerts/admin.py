from django.contrib import admin
from .models import Alerta

@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ('alert_id', 'tipo_alerta', 'nivel_riesgo', 'estado_alerta', 'mensaje', 'fecha_generacion')
    list_filter = ('tipo_alerta', 'nivel_riesgo', 'estado_alerta')
    search_fields = ('mensaje',)
    ordering = ('-fecha_generacion',)
