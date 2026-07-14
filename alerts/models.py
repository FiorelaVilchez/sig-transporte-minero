from django.db import models
from documents.models import DocumentoConductor, DocumentoVehiculo

class Alerta(models.Model):
    TIPO_ALERTA_CHOICES = [
        ('Documento vencido', 'Documento vencido'),
        ('Documento por vencer', 'Documento por vencer'),
        ('Vehículo en mantenimiento', 'Vehículo en mantenimiento'),
        ('Conductor no apto', 'Conductor no apto'),
    ]

    NIVEL_RIESGO_CHOICES = [
        ('Alto', 'Alto'),
        ('Medio', 'Medio'),
        ('Bajo', 'Bajo'),
    ]

    ESTADO_ALERTA_CHOICES = [
        ('Activa', 'Activa'),
        ('Resuelta', 'Resuelta'),
    ]

    alert_id = models.BigAutoField(primary_key=True)
    tipo_alerta = models.CharField(max_length=50, choices=TIPO_ALERTA_CHOICES, verbose_name="Tipo de Alerta")
    nivel_riesgo = models.CharField(max_length=20, choices=NIVEL_RIESGO_CHOICES, verbose_name="Nivel de Riesgo")
    estado_alerta = models.CharField(max_length=20, choices=ESTADO_ALERTA_CHOICES, default='Activa', verbose_name="Estado de Alerta")
    documento_conductor = models.ForeignKey(DocumentoConductor, on_delete=models.CASCADE, null=True, blank=True, related_name='alertas', verbose_name="Documento de Conductor")
    documento_vehiculo = models.ForeignKey(DocumentoVehiculo, on_delete=models.CASCADE, null=True, blank=True, related_name='alertas', verbose_name="Documento de Vehículo")
    mensaje = models.CharField(max_length=255, verbose_name="Mensaje de Alerta")
    fecha_generacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Generación")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Fecha de Modificación")

    class Meta:
        verbose_name = "Alerta"
        verbose_name_plural = "Alertas"
        ordering = ['-fecha_generacion']

    def __str__(self):
        return f"Alerta #{self.alert_id} ({self.tipo_alerta}) - {self.nivel_riesgo} [{self.estado_alerta}]"
