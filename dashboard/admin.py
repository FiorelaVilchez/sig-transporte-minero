from django.contrib import admin

from .models import CapturaReporte, ReporteGerencial


class CapturaReporteInline(admin.TabularInline):
    model = CapturaReporte
    extra = 0
    fields = ('imagen', 'orden')


@admin.register(ReporteGerencial)
class ReporteGerencialAdmin(admin.ModelAdmin):
    list_display = ('descripcion', 'subido_por', 'fecha_subida', 'tiene_pdf', 'tiene_capturas')
    list_filter = ('fecha_subida', 'subido_por')
    search_fields = ('descripcion', 'subido_por__username')
    readonly_fields = ('fecha_subida',)
    inlines = [CapturaReporteInline]
