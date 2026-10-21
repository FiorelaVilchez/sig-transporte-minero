"""Formularios del módulo Usuarios y accesos."""
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password

from drivers.models import Conductor

from .models import PerfilUsuario


class _ConductorChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, c):
        return f"{c.apellidos}, {c.nombres} · DNI {c.dni} · {c.estado}"


class UsuarioForm(forms.Form):
    """Crea o edita una cuenta junto con su perfil (rol, teléfono y conductor vinculado)."""

    username = forms.CharField(label="Nombre de usuario", max_length=150,
                               help_text="Sin espacios. Es el dato con el que la persona inicia sesión.")
    first_name = forms.CharField(label="Nombres", max_length=150)
    last_name = forms.CharField(label="Apellidos", max_length=150)
    email = forms.EmailField(label="Correo electrónico", required=False)
    telefono = forms.CharField(label="Teléfono", max_length=20, required=False)
    rol = forms.ChoiceField(label="Rol", choices=PerfilUsuario.ROL_CHOICES)
    conductor = _ConductorChoiceField(
        label="Conductor vinculado", queryset=Conductor.objects.none(), required=False,
        empty_label="Seleccione el conductor",
        help_text="Obligatorio para el rol Conductor: es el registro cuyos servicios y documentos verá.",
    )
    is_active = forms.BooleanField(label="Cuenta activa", required=False, initial=True)
    password1 = forms.CharField(label="Contraseña", widget=forms.PasswordInput(render_value=False), required=False)
    password2 = forms.CharField(label="Repetir contraseña", widget=forms.PasswordInput(render_value=False), required=False)

    def __init__(self, *args, usuario=None, **kwargs):
        self.usuario = usuario
        super().__init__(*args, **kwargs)
        perfil = getattr(usuario, 'perfilusuario', None) if usuario else None
        # Conductores sin cuenta, más el que ya tiene esta cuenta.
        ocupados = PerfilUsuario.objects.filter(conductor__isnull=False)
        if perfil:
            ocupados = ocupados.exclude(pk=perfil.pk)
        self.fields['conductor'].queryset = (
            Conductor.objects.exclude(estado='De baja')
            .exclude(pk__in=ocupados.values('conductor_id'))
            .order_by('apellidos', 'nombres')
        )
        if usuario:
            # En edición la contraseña se cambia desde su propia pantalla.
            del self.fields['password1']
            del self.fields['password2']
        else:
            self.fields['password1'].required = True
            self.fields['password2'].required = True

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if ' ' in username:
            raise forms.ValidationError("El nombre de usuario no puede tener espacios.")
        existe = User.objects.filter(username__iexact=username)
        if self.usuario:
            existe = existe.exclude(pk=self.usuario.pk)
        if existe.exists():
            raise forms.ValidationError("Ya existe una cuenta con ese nombre de usuario.")
        return username

    def clean(self):
        datos = super().clean()
        if datos.get('rol') == 'Conductor' and not datos.get('conductor'):
            self.add_error('conductor', "Para el rol Conductor debe elegir el registro de conductor.")
        if datos.get('rol') != 'Conductor':
            datos['conductor'] = None
        p1, p2 = datos.get('password1'), datos.get('password2')
        if 'password1' in self.fields and p1:
            if p1 != p2:
                self.add_error('password2', "Las contraseñas no coinciden.")
            else:
                try:
                    validate_password(p1)
                except forms.ValidationError as e:
                    self.add_error('password1', e)
        return datos

    def save(self):
        d = self.cleaned_data
        usuario = self.usuario or User(username=d['username'])
        usuario.username = d['username']
        usuario.first_name = d['first_name']
        usuario.last_name = d['last_name']
        usuario.email = d.get('email') or ''
        usuario.is_active = d.get('is_active', True)
        if not self.usuario:
            usuario.set_password(d['password1'])
        usuario.save()
        perfil, _ = PerfilUsuario.objects.get_or_create(usuario=usuario, defaults={'rol': d['rol']})
        perfil.rol = d['rol']
        perfil.telefono = d.get('telefono') or ''
        perfil.conductor = d.get('conductor')
        perfil.save()
        return usuario


class CambiarPasswordForm(forms.Form):
    password1 = forms.CharField(label="Nueva contraseña", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Repetir contraseña", widget=forms.PasswordInput)

    def clean(self):
        datos = super().clean()
        p1, p2 = datos.get('password1'), datos.get('password2')
        if p1 and p1 != p2:
            self.add_error('password2', "Las contraseñas no coinciden.")
        elif p1:
            try:
                validate_password(p1)
            except forms.ValidationError as e:
                self.add_error('password1', e)
        return datos
