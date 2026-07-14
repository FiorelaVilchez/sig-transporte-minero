from django.db import models

class Vehiculo(models.Model):
    TIPO_CHOICES = [
        ('Camioneta', 'Camioneta'),
        ('Bus', 'Bus'),
        ('Camión', 'Camión'),
        ('Volquete', 'Volquete'),
    ]

    ESTADO_CHOICES = [
        ('Disponible', 'Disponible'),
        ('En servicio', 'En servicio'),
        ('En mantenimiento', 'En mantenimiento'),
        ('De baja', 'De baja'),
    ]

    truck_id = models.BigAutoField(primary_key=True)
    placa = models.CharField(max_length=15, unique=True, verbose_name="Placa")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name="Tipo de Vehículo")
    capacidad = models.IntegerField(verbose_name="Capacidad (pasajeros/toneladas)")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='Disponible', verbose_name="Estado")
    revision_tecnica_vigente = models.BooleanField(default=True, verbose_name="Revisión Técnica Vigente")
    seguro_vigente = models.BooleanField(default=True, verbose_name="Seguro Vigente")
    homologacion = models.CharField(max_length=100, blank=True, verbose_name="Código de Homologación")
    mantenimiento_programado = models.DateField(null=True, blank=True, verbose_name="Mantenimiento Programado")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Fecha de Modificación")

    class Meta:
        verbose_name = "Vehículo"
        verbose_name_plural = "Vehículos"
        ordering = ['placa']

    def __str__(self):
        return f"{self.tipo} - Placa: {self.placa} ({self.estado})"
