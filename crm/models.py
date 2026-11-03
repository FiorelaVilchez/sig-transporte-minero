from django.core.validators import RegexValidator
from django.db import models


class Cliente(models.Model):
    """Empresa contratista que solicita los servicios de transporte."""

    razon_social = models.CharField(max_length=150, unique=True, verbose_name="Razón social")
    ruc = models.CharField(
        max_length=11, unique=True, null=True, blank=True, verbose_name="RUC",
        validators=[RegexValidator(r'^(10|15|17|20)\d{9}$', "El RUC debe tener 11 dígitos y empezar en 10, 15, 17 o 20.")],
    )
    contacto = models.CharField(max_length=100, blank=True, verbose_name="Persona de contacto")
    telefono = models.CharField(max_length=20, blank=True, verbose_name="Teléfono")
    correo = models.EmailField(blank=True, verbose_name="Correo")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Fecha de modificación")

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ['razon_social']

    def __str__(self):
        return self.razon_social

    def save(self, *args, **kwargs):
        self.razon_social = ' '.join((self.razon_social or '').split())
        if not self.ruc:
            self.ruc = None
        super().save(*args, **kwargs)

    @classmethod
    def obtener(cls, nombre):
        """Devuelve el cliente con ese nombre (sin distinguir mayúsculas) o lo crea."""
        nombre = ' '.join((nombre or '').split())
        cliente = cls.objects.filter(razon_social__iexact=nombre).first()
        return cliente or cls.objects.create(razon_social=nombre)
