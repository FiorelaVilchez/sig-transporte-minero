from django.db import models
from service_requests.models import SolicitudServicio
from drivers.models import Conductor
from trucks.models import Vehiculo

ESTADO_OPERATIVO_CHOICES = [
    ('Programado', 'Programado'),
    ('Listo para salir', 'Listo para salir'),
    ('En ruta', 'En ruta'),
    ('Completado', 'Completado'),
    ('Con incidencia', 'Con incidencia'),
    ('Cancelado', 'Cancelado'),
]

# Estados en que una asignación ocupa al conductor y al vehículo en su horario.
ESTADOS_OPERATIVOS_ACTIVOS = ['Programado', 'Listo para salir', 'En ruta']


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
    estado_operativo = models.CharField(
        max_length=20, choices=ESTADO_OPERATIVO_CHOICES, default='Programado', verbose_name="Estado del servicio",
    )
    km_inicial = models.PositiveIntegerField(null=True, blank=True, verbose_name="Kilometraje inicial")
    km_final = models.PositiveIntegerField(null=True, blank=True, verbose_name="Kilometraje final")
    inicio_real = models.DateTimeField(null=True, blank=True, verbose_name="Salida real")
    fin_real = models.DateTimeField(null=True, blank=True, verbose_name="Llegada real")
    fecha_asignacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Asignación")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Fecha de Modificación")

    class Meta:
        verbose_name = "Asignación"
        verbose_name_plural = "Asignaciones"
        ordering = ['-fecha_asignacion']

    def __str__(self):
        return f"Asignación #{self.assignment_id} - Solicitud #{self.solicitud.request_id} ({self.estado_asignacion})"

    @property
    def km_recorridos(self):
        if self.km_inicial is not None and self.km_final is not None and self.km_final >= self.km_inicial:
            return self.km_final - self.km_inicial
        return None

    @property
    def total_gastos(self):
        return sum((g.monto for g in self.gastos.all()), 0)


class Notificacion(models.Model):
    conductor = models.ForeignKey(Conductor, on_delete=models.CASCADE, related_name='notificaciones', verbose_name="Conductor")
    mensaje = models.CharField(max_length=255, verbose_name="Mensaje")
    leida = models.BooleanField(default=False, verbose_name="Leída")
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha")

    class Meta:
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"
        ordering = ['-fecha']

    def __str__(self):
        return f"Notificación para {self.conductor.apellidos} - {self.mensaje[:30]}..."



class ChecklistPreoperacional(models.Model):
    """Inspección antes de salir (M3). Si falla un punto crítico, la unidad no sale."""

    PUNTOS_CRITICOS = ['frenos', 'llantas', 'luces', 'cinturones']
    HORAS_SUENO_MINIMAS = 6

    asignacion = models.OneToOneField(Asignacion, on_delete=models.CASCADE, related_name='checklist', verbose_name="Asignación")
    frenos = models.BooleanField(default=False, verbose_name="Frenos en buen estado")
    llantas = models.BooleanField(default=False, verbose_name="Llantas y repuesto en buen estado")
    luces = models.BooleanField(default=False, verbose_name="Luces y circulina operativas")
    cinturones = models.BooleanField(default=False, verbose_name="Cinturones de seguridad completos")
    botiquin = models.BooleanField(default=False, verbose_name="Botiquín")
    extintor = models.BooleanField(default=False, verbose_name="Extintor vigente")
    radio_gps = models.BooleanField(default=False, verbose_name="Radio y GPS operativos")
    horas_sueno = models.DecimalField(max_digits=4, decimal_places=1, verbose_name="Horas de sueño previas")
    km_inicial = models.PositiveIntegerField(verbose_name="Kilometraje inicial")
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")
    aprobado = models.BooleanField(default=False, verbose_name="Aprobado")
    motivo_rechazo = models.CharField(max_length=255, blank=True, verbose_name="Motivo de rechazo")
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha")

    class Meta:
        verbose_name = "Checklist preoperacional"
        verbose_name_plural = "Checklists preoperacionales"
        ordering = ['-fecha']

    def evaluar(self):
        """Calcula aprobado y motivo_rechazo según los puntos críticos y el descanso."""
        fallas = [self._meta.get_field(p).verbose_name for p in self.PUNTOS_CRITICOS if not getattr(self, p)]
        if self.horas_sueno is not None and float(self.horas_sueno) < self.HORAS_SUENO_MINIMAS:
            fallas.append(f"Descanso insuficiente ({self.horas_sueno} h; mínimo {self.HORAS_SUENO_MINIMAS} h)")
        self.aprobado = not fallas
        self.motivo_rechazo = "; ".join(fallas)[:255]
        return self.aprobado

    def __str__(self):
        return f"Checklist asignación #{self.asignacion_id} ({'Aprobado' if self.aprobado else 'No aprobado'})"


class Incidencia(models.Model):
    """Evento en ruta reportado por el conductor (M4)."""

    TIPO_CHOICES = [
        ('Falla mecánica', 'Falla mecánica'),
        ('Accidente', 'Accidente'),
        ('Vía bloqueada o clima', 'Vía bloqueada o clima'),
        ('Salud del conductor', 'Salud del conductor'),
        ('Retraso del personal', 'Retraso del personal'),
        ('Otro', 'Otro'),
    ]
    GRAVEDAD_CHOICES = [
        ('Baja', 'Baja: el servicio continúa'),
        ('Alta', 'Alta: se requiere reemplazo'),
    ]

    asignacion = models.ForeignKey(Asignacion, on_delete=models.CASCADE, related_name='incidencias', verbose_name="Asignación")
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES, verbose_name="Tipo de incidencia")
    gravedad = models.CharField(max_length=10, choices=GRAVEDAD_CHOICES, default='Baja', verbose_name="Gravedad")
    descripcion = models.TextField(verbose_name="Descripción")
    resuelta = models.BooleanField(default=False, verbose_name="Resuelta")
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha")

    class Meta:
        verbose_name = "Incidencia"
        verbose_name_plural = "Incidencias"
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.tipo} ({self.gravedad}) - asignación #{self.asignacion_id}"


class GastoServicio(models.Model):
    """Gasto del servicio registrado por el conductor (M4), insumo de la valorización."""

    CONCEPTO_CHOICES = [
        ('Combustible', 'Combustible'),
        ('Peaje', 'Peaje'),
        ('Viático', 'Viático'),
        ('Otro', 'Otro'),
    ]

    asignacion = models.ForeignKey(Asignacion, on_delete=models.CASCADE, related_name='gastos', verbose_name="Asignación")
    concepto = models.CharField(max_length=20, choices=CONCEPTO_CHOICES, verbose_name="Concepto")
    monto = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto (S/)")
    detalle = models.CharField(max_length=150, blank=True, verbose_name="Detalle")
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha")

    class Meta:
        verbose_name = "Gasto del servicio"
        verbose_name_plural = "Gastos del servicio"
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.concepto} S/ {self.monto} - asignación #{self.asignacion_id}"
