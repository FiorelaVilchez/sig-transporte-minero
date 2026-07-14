from django.db import models
from service_requests.models import SolicitudServicio
from drivers.models import Conductor
from trucks.models import Vehiculo

class Asignacion(models.Model):
    ESTADO_ASIGNACION_CHOICES = [
        ('Aprobada', 'Aprobada'),
        ('Rechazada', 'Rechazada'),
        ('Observada', 'Observada'),
        ('Pendiente', 'Pendiente'),
    ]

    assignment_id = models.BigAutoField(primary_key=True)
    solicitud = models.ForeignKey(SolicitudServicio, on_delete=models.PROTECT, related_name='asignaciones', verbose_name="Solicitud de Servicio")
    conductor = models.ForeignKey(Conductor, on_delete=models.PROTECT, null=True, blank=True, related_name='asignaciones', verbose_name="Conductor")
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.PROTECT, null=True, blank=True, related_name='asignaciones', verbose_name="Vehículo")
    estado_asignacion = models.CharField(max_length=20, choices=ESTADO_ASIGNACION_CHOICES, default='Pendiente', verbose_name="Estado de Asignación")
    observacion = models.TextField(blank=True, verbose_name="Observación / Motivo")
    fecha_asignacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Asignación")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Fecha de Modificación")

    class Meta:
        verbose_name = "Asignación"
        verbose_name_plural = "Asignaciones"
        ordering = ['-fecha_asignacion']

    def __str__(self):
        return f"Asignación #{self.assignment_id} - Solicitud #{self.solicitud.request_id} ({self.estado_asignacion})"
