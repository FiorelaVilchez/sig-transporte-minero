from django.db import models
from drivers.models import Conductor
from trucks.models import Vehiculo

class DocumentoConductor(models.Model):
    TIPO_DOCUMENTO_CHOICES = [
        ('Licencia de conducir', 'Licencia de conducir'),
        ('Homologación', 'Homologación'),
        ('Examen médico', 'Examen médico'),
        ('Autorización', 'Autorización'),
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
    fecha_vencimiento = models.DateField(verbose_name="Fecha de Vencimiento")
    estado_documento = models.CharField(max_length=20, choices=ESTADO_DOCUMENTO_CHOICES, default='Vigente', verbose_name="Estado de Documento")
    archivo = models.FileField(upload_to='documentos_conductores/', null=True, blank=True, verbose_name="Archivo Adjunto")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Fecha de Modificación")

    class Meta:
        verbose_name = "Documento de Conductor"
        verbose_name_plural = "Documentos de Conductor"
        ordering = ['-fecha_vencimiento']

    def __str__(self):
        return f"{self.conductor.apellidos} - {self.tipo_documento} (Vence: {self.fecha_vencimiento})"

    def save(self, *args, **kwargs):
        from documents.services import calcular_estado_documento
        self.estado_documento = calcular_estado_documento(self.fecha_vencimiento)
        super().save(*args, **kwargs)



class DocumentoVehiculo(models.Model):
    TIPO_DOCUMENTO_CHOICES = [
        ('Revisión técnica', 'Revisión técnica'),
        ('Seguro', 'Seguro'),
        ('Homologación', 'Homologación'),
        ('Permiso de operación', 'Permiso de operación'),
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
    fecha_vencimiento = models.DateField(verbose_name="Fecha de Vencimiento")
    estado_documento = models.CharField(max_length=20, choices=ESTADO_DOCUMENTO_CHOICES, default='Vigente', verbose_name="Estado de Documento")
    archivo = models.FileField(upload_to='documentos_vehiculos/', null=True, blank=True, verbose_name="Archivo Adjunto")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Fecha de Modificación")

    class Meta:
        verbose_name = "Documento de Vehículo"
        verbose_name_plural = "Documentos de Vehículo"
        ordering = ['-fecha_vencimiento']

    def __str__(self):
        return f"{self.vehiculo.placa} - {self.tipo_documento} (Vence: {self.fecha_vencimiento})"

    def save(self, *args, **kwargs):
        from documents.services import calcular_estado_documento
        self.estado_documento = calcular_estado_documento(self.fecha_vencimiento)
        super().save(*args, **kwargs)

