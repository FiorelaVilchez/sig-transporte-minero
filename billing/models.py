import datetime
from decimal import Decimal

from django.db import models

from service_requests.models import SolicitudServicio
from trucks.models import TipoVehiculo


class Tarifa(models.Model):
    """Tarifa pactada con un cliente para un tipo de unidad (M6)."""

    cliente = models.CharField(max_length=150, verbose_name="Cliente")
    tipo_vehiculo = models.ForeignKey(TipoVehiculo, on_delete=models.PROTECT, related_name='tarifas', verbose_name="Tipo de vehículo")
    tarifa_base = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Tarifa base por servicio (S/)")
    km_incluidos = models.PositiveIntegerField(default=0, verbose_name="Kilómetros incluidos")
    precio_km_adicional = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="Precio por km adicional (S/)")
    activo = models.BooleanField(default=True, verbose_name="Activa")

    class Meta:
        verbose_name = "Tarifa"
        verbose_name_plural = "Tarifas"
        ordering = ['cliente', 'tipo_vehiculo__asientos_referencia']
        constraints = [
            models.UniqueConstraint(fields=['cliente', 'tipo_vehiculo'], name='tarifa_unica_cliente_tipo'),
        ]

    def __str__(self):
        return f"{self.cliente} - {self.tipo_vehiculo}: S/ {self.tarifa_base}"

    @classmethod
    def buscar(cls, cliente, tipo_vehiculo):
        return cls.objects.filter(
            cliente__iexact=(cliente or '').strip(), tipo_vehiculo=tipo_vehiculo, activo=True
        ).first()


class Valorizacion(models.Model):
    """Valorización de un servicio completado y su ciclo de cobro (M6)."""

    ESTADO_CHOICES = [
        ('Borrador', 'Borrador'),
        ('Enviada', 'Enviada al cliente'),
        ('Observada', 'Observada por el cliente'),
        ('Conforme', 'Conforme'),
        ('Facturada', 'Facturada'),
        ('Pagada', 'Pagada'),
    ]
    # Transiciones permitidas: estado actual -> estados siguientes.
    TRANSICIONES = {
        'Borrador': ['Enviada'],
        'Enviada': ['Observada', 'Conforme'],
        'Observada': ['Enviada'],
        'Conforme': ['Facturada'],
        'Facturada': ['Pagada'],
        'Pagada': [],
    }
    DIAS_ALERTA_COBRO = 15

    solicitud = models.OneToOneField(SolicitudServicio, on_delete=models.PROTECT, related_name='valorizacion', verbose_name="Solicitud")
    tarifa = models.ForeignKey(Tarifa, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Tarifa aplicada")
    monto_base = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Monto base (S/)")
    km_recorridos = models.PositiveIntegerField(default=0, verbose_name="Kilómetros recorridos")
    km_adicionales = models.PositiveIntegerField(default=0, verbose_name="Kilómetros adicionales")
    monto_adicional = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Monto por km adicional (S/)")
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Total (S/)")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='Borrador', verbose_name="Estado")
    numero_factura = models.CharField(max_length=30, blank=True, verbose_name="N.º de factura")
    observacion = models.TextField(blank=True, verbose_name="Observación")
    fecha_envio = models.DateField(null=True, blank=True, verbose_name="Fecha de envío")
    fecha_conformidad = models.DateField(null=True, blank=True, verbose_name="Fecha de conformidad")
    fecha_factura = models.DateField(null=True, blank=True, verbose_name="Fecha de factura")
    fecha_pago = models.DateField(null=True, blank=True, verbose_name="Fecha de pago")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Fecha de modificación")

    class Meta:
        verbose_name = "Valorización"
        verbose_name_plural = "Valorizaciones"
        ordering = ['-created_at']

    def __str__(self):
        return f"Valorización solicitud #{self.solicitud_id} - S/ {self.total} ({self.estado})"

    def calcular(self):
        """total = tarifa base + max(0, km recorridos - km incluidos) x precio por km."""
        if self.tarifa:
            self.monto_base = self.tarifa.tarifa_base
            self.km_adicionales = max(0, (self.km_recorridos or 0) - self.tarifa.km_incluidos)
            self.monto_adicional = Decimal(self.km_adicionales) * self.tarifa.precio_km_adicional
        else:
            self.km_adicionales = 0
            self.monto_adicional = Decimal('0')
        self.total = (self.monto_base or Decimal('0')) + self.monto_adicional
        return self.total

    @property
    def siguientes_estados(self):
        return self.TRANSICIONES.get(self.estado, [])

    @property
    def dias_sin_conformidad(self):
        if self.estado in ('Enviada', 'Observada') and self.fecha_envio:
            return (datetime.date.today() - self.fecha_envio).days
        return 0

    @property
    def cobro_atrasado(self):
        return self.dias_sin_conformidad > self.DIAS_ALERTA_COBRO
