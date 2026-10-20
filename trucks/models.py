from django.db import models


class TipoVehiculo(models.Model):
    """Catálogo de tipos de unidad (M0). Se administra desde Configuración."""

    CATEGORIA_LICENCIA_CHOICES = [
        ('A-I', 'A-I'),
        ('A-IIa', 'A-IIa'),
        ('A-IIb', 'A-IIb'),
        ('A-IIIa', 'A-IIIa'),
        ('A-IIIb', 'A-IIIb'),
        ('A-IIIc', 'A-IIIc'),
    ]

    nombre = models.CharField(max_length=50, unique=True, verbose_name="Nombre del tipo")
    asientos_referencia = models.PositiveIntegerField(default=4, verbose_name="Asientos de referencia")
    experiencia_minima_anios = models.PositiveIntegerField(
        default=0, verbose_name="Experiencia mínima (años de licencia)"
    )
    categoria_licencia_minima = models.CharField(
        max_length=10, choices=CATEGORIA_LICENCIA_CHOICES, default='A-I',
        verbose_name="Categoría mínima de licencia",
    )
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Tipo de vehículo"
        verbose_name_plural = "Tipos de vehículo"
        ordering = ['asientos_referencia', 'nombre']

    def __str__(self):
        return self.nombre

    @classmethod
    def orden_categoria(cls, categoria):
        codigos = [c[0] for c in cls.CATEGORIA_LICENCIA_CHOICES]
        return codigos.index(categoria) if categoria in codigos else -1


class Vehiculo(models.Model):
    ESTADO_CHOICES = [
        ('Disponible', 'Disponible'),
        ('En servicio', 'En servicio'),
        ('En mantenimiento', 'En mantenimiento'),
        ('De baja', 'De baja'),
    ]

    truck_id = models.BigAutoField(primary_key=True)
    placa = models.CharField(max_length=15, unique=True, verbose_name="Placa")
    tipo = models.ForeignKey(
        TipoVehiculo, to_field='nombre', db_column='tipo', on_delete=models.PROTECT,
        related_name='vehiculos', verbose_name="Tipo de Vehículo",
    )
    capacidad = models.IntegerField(verbose_name="Capacidad (asientos)")
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
        return f"{self.tipo_id} - Placa: {self.placa} ({self.estado})"
