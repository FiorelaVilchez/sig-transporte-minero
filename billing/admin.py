from django.contrib import admin

from .models import Tarifa, Valorizacion


@admin.register(Tarifa)
class TarifaAdmin(admin.ModelAdmin):
    list_display = ('cliente', 'tipo_vehiculo', 'tarifa_base', 'km_incluidos', 'precio_km_adicional', 'activo')
    list_filter = ('activo', 'tipo_vehiculo')


@admin.register(Valorizacion)
class ValorizacionAdmin(admin.ModelAdmin):
    list_display = ('solicitud', 'total', 'estado', 'fecha_envio', 'numero_factura')
    list_filter = ('estado',)
