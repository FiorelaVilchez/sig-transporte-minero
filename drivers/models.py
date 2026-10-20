import datetime

from django.db import models

from trucks.models import TipoVehiculo

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
    especialidad = models.CharField(max_length=100, blank=True, verbose_name="Especialidad (texto, versión 1.0)")
    categoria_licencia = models.CharField(
        max_length=10, choices=TipoVehiculo.CATEGORIA_LICENCIA_CHOICES, blank=True,
        verbose_name="Categoría de licencia",
    )
    fecha_obtencion_licencia = models.DateField(
        null=True, blank=True, verbose_name="Fecha de obtención de la licencia"
    )
    tipos_habilitados = models.ManyToManyField(
        TipoVehiculo, blank=True, related_name='conductores_habilitados',
        verbose_name="Tipos de vehículo que puede manejar",
    )
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

    @property
    def nombre_completo(self):
        return f"{self.apellidos}, {self.nombres}"

    def anios_licencia(self, referencia=None):
        """Años completos desde la obtención de la licencia; None si no se registró."""
        if not self.fecha_obtencion_licencia:
            return None
        ref = referencia or datetime.date.today()
        f = self.fecha_obtencion_licencia
        return ref.year - f.year - ((ref.month, ref.day) < (f.month, f.day))

    def puede_manejar(self, tipo):
        """
        Indica si el conductor está habilitado para el tipo de vehículo.
        Si aún no tiene tipos marcados (registros de la versión 1.0), se usa
        el texto de la especialidad como respaldo.
        """
        nombre = tipo.nombre if hasattr(tipo, 'nombre') else str(tipo)
        if self.pk and self.tipos_habilitados.exists():
            return self.tipos_habilitados.filter(nombre=nombre).exists()
        return bool(self.especialidad) and nombre.lower() in self.especialidad.lower()
