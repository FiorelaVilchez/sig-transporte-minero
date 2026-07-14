from django.db import models

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

    TIPO_VEHICULO_CHOICES = [
        ('Camioneta', 'Camioneta'),
        ('Bus', 'Bus'),
        ('Camión', 'Camión'),
        ('Volquete', 'Volquete'),
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
    tipo_vehiculo_requerido = models.CharField(max_length=50, choices=TIPO_VEHICULO_CHOICES, verbose_name="Tipo de Vehículo Requerido")
    estado_solicitud = models.CharField(max_length=20, choices=ESTADO_SOLICITUD_CHOICES, default='Pendiente', verbose_name="Estado de Solicitud")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Fecha de Modificación")

    class Meta:
        verbose_name = "Solicitud de Servicio"
        verbose_name_plural = "Solicitudes de Servicio"
        ordering = ['-fecha_servicio', '-hora_servicio']

    def __str__(self):
        return f"Solicitud #{self.request_id} - {self.cliente} ({self.fecha_servicio})"
