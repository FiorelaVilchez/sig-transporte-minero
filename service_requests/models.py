import datetime

from django.conf import settings
from django.db import models

from trucks.models import TipoVehiculo

class SolicitudServicio(models.Model):
    TIPO_SERVICIO_CHOICES = [
        ('Traslado de personal', 'Traslado de personal'),
        ('Traslado de carga', 'Traslado de carga'),
        ('Traslado mixto', 'Traslado mixto'),
    ]

    PRIORIDAD_CHOICES = [
        ('Alta', 'Alta'),
        ('Media', 'Media'),
        ('Baja', 'Baja'),
    ]

    ESTADO_SOLICITUD_CHOICES = [
        ('Pendiente', 'Pendiente'),
        ('Asignada', 'Asignada'),
        ('Reprogramada', 'Reprogramada'),
        ('Completada', 'Completada'),
        ('Cancelada', 'Cancelada'),
    ]

    request_id = models.BigAutoField(primary_key=True)
    cliente = models.CharField(max_length=150, verbose_name="Cliente")
    fecha_servicio = models.DateField(verbose_name="Fecha de Servicio")
    hora_servicio = models.TimeField(verbose_name="Hora de Servicio")
    origen = models.CharField(max_length=200, verbose_name="Origen")
    destino = models.CharField(max_length=200, verbose_name="Destino")
    tipo_servicio = models.CharField(max_length=50, choices=TIPO_SERVICIO_CHOICES, verbose_name="Tipo de Servicio")
    prioridad = models.CharField(max_length=20, choices=PRIORIDAD_CHOICES, verbose_name="Prioridad")
    tipo_vehiculo_requerido = models.ForeignKey(
        TipoVehiculo, to_field='nombre', db_column='tipo_vehiculo_requerido',
        on_delete=models.PROTECT, related_name='solicitudes',
        verbose_name="Tipo de Vehículo Requerido",
    )
    pasajeros = models.PositiveIntegerField(default=1, verbose_name="Número de pasajeros")
    duracion_horas = models.PositiveIntegerField(default=8, verbose_name="Duración estimada (horas)")
    km_estimados = models.PositiveIntegerField(default=0, verbose_name="Kilómetros estimados")
    estado_solicitud = models.CharField(max_length=20, choices=ESTADO_SOLICITUD_CHOICES, default='Pendiente', verbose_name="Estado de Solicitud")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Fecha de Modificación")

    class Meta:
        verbose_name = "Solicitud de Servicio"
        verbose_name_plural = "Solicitudes de Servicio"
        ordering = ['-fecha_servicio', '-hora_servicio']

    def __str__(self):
        return f"Solicitud #{self.request_id} - {self.cliente} ({self.fecha_servicio})"

    @property
    def inicio(self):
        return datetime.datetime.combine(self.fecha_servicio, self.hora_servicio)

    @property
    def fin(self):
        return self.inicio + datetime.timedelta(hours=self.duracion_horas or 0)


class CambioSolicitud(models.Model):
    """Bitácora de cambios de una solicitud (M2): quién, cuándo, qué y por qué."""

    solicitud = models.ForeignKey(SolicitudServicio, on_delete=models.CASCADE, related_name='cambios', verbose_name="Solicitud")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Usuario")
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha del cambio")
    campo = models.CharField(max_length=60, verbose_name="Campo")
    valor_anterior = models.CharField(max_length=255, blank=True, verbose_name="Valor anterior")
    valor_nuevo = models.CharField(max_length=255, blank=True, verbose_name="Valor nuevo")
    motivo = models.CharField(max_length=255, blank=True, verbose_name="Motivo")

    class Meta:
        verbose_name = "Cambio de solicitud"
        verbose_name_plural = "Bitácora de cambios"
        ordering = ['-fecha', '-id']

    def __str__(self):
        return f"#{self.solicitud_id} {self.campo}: {self.valor_anterior} -> {self.valor_nuevo}"
