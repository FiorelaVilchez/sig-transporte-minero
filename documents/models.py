from django.db import models
from drivers.models import Conductor
from trucks.models import TipoVehiculo, Vehiculo


ESTADO_MINA_CHOICES = [
    ('No requiere', 'No requiere'),
    ('Pendiente', 'Pendiente'),
    ('Aprobado', 'Aprobado'),
    ('Observado', 'Observado'),
]


class DocumentoConductor(models.Model):
    TIPO_DOCUMENTO_CHOICES = [
        ('Licencia de conducir', 'Licencia de conducir'),
        ('Homologación', 'Homologación'),
        ('Examen médico', 'Examen médico ocupacional'),
        ('Autorización', 'Autorización'),
        ('Manejo defensivo', 'Certificado de manejo defensivo'),
        ('Inducción en mina', 'Inducción en mina'),
        ('Seguro Vida Ley', 'Seguro Vida Ley'),
        ('Récord de conductor', 'Récord de conductor'),
    ]

    ESTADO_DOCUMENTO_CHOICES = [
        ('Vigente', 'Vigente'),
        ('Por vencer', 'Por vencer'),
        ('Vencido', 'Vencido'),
    ]

    document_id = models.BigAutoField(primary_key=True)
    conductor = models.ForeignKey(Conductor, on_delete=models.CASCADE, related_name='documentos', verbose_name="Conductor")
    tipo_documento = models.CharField(max_length=50, choices=TIPO_DOCUMENTO_CHOICES, verbose_name="Tipo de Documento")
    fecha_emision = models.DateField(verbose_name="Fecha de Emisión")
    fecha_vencimiento = models.DateField(null=True, blank=True, verbose_name="Fecha de Vencimiento")
    estado_documento = models.CharField(max_length=20, choices=ESTADO_DOCUMENTO_CHOICES, default='Vigente', verbose_name="Estado de Documento")
    estado_mina = models.CharField(max_length=20, choices=ESTADO_MINA_CHOICES, default='No requiere', verbose_name="Visto bueno de mina")
    archivo = models.FileField(upload_to='documentos_conductores/', null=True, blank=True, verbose_name="Archivo Adjunto")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Fecha de Modificación")

    class Meta:
        verbose_name = "Documento de Conductor"
        verbose_name_plural = "Documentos de Conductor"
        ordering = ['-fecha_vencimiento']

    def __str__(self):
        return f"{self.conductor.apellidos} - {self.tipo_documento} (Vence: {self.fecha_vencimiento or 'no vence'})"

    def save(self, *args, **kwargs):
        from documents.services import calcular_estado_documento
        self.estado_documento = calcular_estado_documento(self.fecha_vencimiento)
        super().save(*args, **kwargs)


class DocumentoVehiculo(models.Model):
    TIPO_DOCUMENTO_CHOICES = [
        ('Revisión técnica', 'Revisión técnica'),
        ('Seguro', 'Seguro (versión 1.0)'),
        ('Homologación', 'Homologación'),
        ('Permiso de operación', 'Permiso de operación'),
        ('SOAT', 'SOAT'),
        ('Póliza todo riesgo', 'Póliza todo riesgo'),
        ('Seguro de ocupantes', 'Seguro de ocupantes'),
        ('Tarjeta de propiedad', 'Tarjeta de propiedad'),
        ('Certificado GPS', 'Certificado de GPS'),
    ]

    ESTADO_DOCUMENTO_CHOICES = [
        ('Vigente', 'Vigente'),
        ('Por vencer', 'Por vencer'),
        ('Vencido', 'Vencido'),
    ]

    document_id = models.BigAutoField(primary_key=True)
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, related_name='documentos', verbose_name="Vehículo")
    tipo_documento = models.CharField(max_length=50, choices=TIPO_DOCUMENTO_CHOICES, verbose_name="Tipo de Documento")
    fecha_emision = models.DateField(verbose_name="Fecha de Emisión")
    fecha_vencimiento = models.DateField(null=True, blank=True, verbose_name="Fecha de Vencimiento")
    estado_documento = models.CharField(max_length=20, choices=ESTADO_DOCUMENTO_CHOICES, default='Vigente', verbose_name="Estado de Documento")
    estado_mina = models.CharField(max_length=20, choices=ESTADO_MINA_CHOICES, default='No requiere', verbose_name="Visto bueno de mina")
    archivo = models.FileField(upload_to='documentos_vehiculos/', null=True, blank=True, verbose_name="Archivo Adjunto")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Fecha de Modificación")

    class Meta:
        verbose_name = "Documento de Vehículo"
        verbose_name_plural = "Documentos de Vehículo"
        ordering = ['-fecha_vencimiento']

    def __str__(self):
        return f"{self.vehiculo.placa} - {self.tipo_documento} (Vence: {self.fecha_vencimiento or 'no vence'})"

    def save(self, *args, **kwargs):
        from documents.services import calcular_estado_documento
        self.estado_documento = calcular_estado_documento(self.fecha_vencimiento)
        super().save(*args, **kwargs)


class RequisitoDocumental(models.Model):
    """
    Matriz de requisitos documentales (M1). Indica qué documento debe tener
    cada conductor o cada vehículo, si su falta o vencimiento bloquea la
    asignación, si vence y si la mina debe darle visto bueno.
    """

    APLICA_A_CHOICES = [
        ('Conductor', 'Conductor'),
        ('Vehículo', 'Vehículo'),
    ]

    aplica_a = models.CharField(max_length=10, choices=APLICA_A_CHOICES, verbose_name="Aplica a")
    tipo_documento = models.CharField(max_length=50, verbose_name="Tipo de documento")
    bloqueante = models.BooleanField(default=True, verbose_name="Bloquea la asignación si falta o vence")
    vence = models.BooleanField(default=True, verbose_name="Tiene fecha de vencimiento")
    requiere_visto_bueno_mina = models.BooleanField(default=False, verbose_name="Requiere visto bueno de mina")
    tipos_vehiculo = models.ManyToManyField(
        TipoVehiculo, blank=True, related_name='requisitos',
        verbose_name="Solo para estos tipos de vehículo (vacío = todos)",
    )
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Requisito documental"
        verbose_name_plural = "Requisitos documentales"
        ordering = ['aplica_a', '-bloqueante', 'tipo_documento']
        constraints = [
            models.UniqueConstraint(fields=['aplica_a', 'tipo_documento'], name='requisito_unico_por_tipo'),
        ]

    def __str__(self):
        return f"{self.aplica_a}: {self.tipo_documento}"

    def aplica_al_tipo(self, tipo):
        """True si el requisito aplica al tipo de vehículo dado."""
        if not self.pk:
            return True
        ids = list(self.tipos_vehiculo.values_list('id', flat=True))
        return not ids or (tipo is not None and tipo.id in ids)

    @classmethod
    def tipos_que_no_vencen(cls, aplica_a):
        return set(
            cls.objects.filter(aplica_a=aplica_a, activo=True, vence=False)
            .values_list('tipo_documento', flat=True)
        )

    @classmethod
    def tipos_con_visto_bueno(cls, aplica_a):
        return set(
            cls.objects.filter(aplica_a=aplica_a, activo=True, requiere_visto_bueno_mina=True)
            .values_list('tipo_documento', flat=True)
        )
