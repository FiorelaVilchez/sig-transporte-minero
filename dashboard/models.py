from django.conf import settings
from django.db import models


class ReporteGerencial(models.Model):
    descripcion = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Descripción",
        help_text='Ej.: "Dashboard gerencial - Sprint 5"',
    )
    archivo_pdf = models.FileField(
        upload_to='reportes_gerenciales/',
        null=True,
        blank=True,
        verbose_name="Reporte PDF",
    )
    subido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='reportes_gerenciales',
        verbose_name="Subido por",
    )
    fecha_subida = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de subida")

    class Meta:
        verbose_name = "Reporte gerencial"
        verbose_name_plural = "Reportes gerenciales"
        ordering = ['-fecha_subida']

    def __str__(self):
        etiqueta = self.descripcion or f"Reporte #{self.pk}"
        return f"{etiqueta} ({self.fecha_subida:%d/%m/%Y %H:%M})"

    @property
    def tiene_pdf(self):
        return bool(self.archivo_pdf)

    @property
    def tiene_capturas(self):
        return self.capturas.exists()


class CapturaReporte(models.Model):
    reporte = models.ForeignKey(
        ReporteGerencial,
        on_delete=models.CASCADE,
        related_name='capturas',
        verbose_name="Reporte",
    )
    imagen = models.ImageField(
        upload_to='reportes_gerenciales/capturas/',
        verbose_name="Captura de pantalla",
    )
    orden = models.PositiveSmallIntegerField(default=0, verbose_name="Orden")

    class Meta:
        verbose_name = "Captura de reporte"
        verbose_name_plural = "Capturas de reporte"
        ordering = ['orden', 'id']

    def __str__(self):
        return f"Captura {self.orden + 1} — {self.reporte}"
