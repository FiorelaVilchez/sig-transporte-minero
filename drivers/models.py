from django.db import models

class Conductor(models.Model):
    ESTADO_CHOICES = [
        ('Disponible', 'Disponible'),
        ('Ocupado', 'Ocupado'),
        ('No apto', 'No apto'),
        ('De baja', 'De baja'),
    ]

    driver_id = models.BigAutoField(primary_key=True)
    nombres = models.CharField(max_length=100, verbose_name="Nombres")
    apellidos = models.CharField(max_length=100, verbose_name="Apellidos")
    licencia = models.CharField(max_length=20, unique=True, verbose_name="Número de Licencia")
    especialidad = models.CharField(max_length=100, verbose_name="Especialidad")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='Disponible', verbose_name="Estado")
    dni = models.CharField(max_length=8, unique=True, verbose_name="DNI")
    telefono = models.CharField(max_length=20, blank=True, verbose_name="Teléfono")
    fecha_nacimiento = models.DateField(verbose_name="Fecha de Nacimiento")
    fecha_ingreso = models.DateField(verbose_name="Fecha de Ingreso")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Fecha de Modificación")

    class Meta:
        verbose_name = "Conductor"
        verbose_name_plural = "Conductores"
        ordering = ['apellidos', 'nombres']

    def __str__(self):
        return f"{self.apellidos}, {self.nombres} - Lic. {self.licencia}"
