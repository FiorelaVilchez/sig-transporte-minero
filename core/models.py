from django.db import models
from django.contrib.auth.models import User
from drivers.models import Conductor

class PerfilUsuario(models.Model):
    ROL_CHOICES = [
        ('Administrador de operaciones', 'Administrador de operaciones'),
        ('Supervisor', 'Supervisor'),
        ('Gerencia', 'Gerencia'),
        ('Conductor', 'Conductor'),
    ]

    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfilusuario', verbose_name="Usuario")
    rol = models.CharField(max_length=50, choices=ROL_CHOICES, verbose_name="Rol")
    conductor = models.ForeignKey(Conductor, on_delete=models.SET_NULL, null=True, blank=True, related_name='perfiles', verbose_name="Conductor Vinculado")
    telefono = models.CharField(max_length=20, blank=True, verbose_name="Teléfono")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Fecha de Modificación")

    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuario"

    def __str__(self):
        return f"{self.usuario.username} ({self.rol})"
