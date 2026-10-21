"""Usuarios y accesos: el Administrador de operaciones crea y mantiene las cuentas del sistema."""
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from drivers.models import Conductor

from .decorators import role_required
from .models import PerfilUsuario
from .usuarios_forms import CambiarPasswordForm, UsuarioForm

ADMIN = 'Administrador de operaciones'


@role_required(ADMIN)
def usuario_list(request):
    usuarios = User.objects.select_related('perfilusuario', 'perfilusuario__conductor').order_by('-is_active', 'username')
    q = request.GET.get('q', '').strip()
    rol = request.GET.get('rol', '')
    if q:
        usuarios = usuarios.filter(
            Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q)
        )
    if rol == 'sin-perfil':
        usuarios = usuarios.filter(perfilusuario__isnull=True)
    elif rol:
        usuarios = usuarios.filter(perfilusuario__rol=rol)
    conductores_sin_cuenta = Conductor.objects.exclude(estado='De baja').exclude(
        pk__in=PerfilUsuario.objects.filter(conductor__isnull=False).values('conductor_id')
    ).order_by('apellidos')
    return render(request, 'core/usuarios/usuario_list.html', {
        'usuarios': usuarios,
        'q': q,
        'rol_filtro': rol,
        'roles': PerfilUsuario.ROL_CHOICES,
        'sin_vinculo': PerfilUsuario.objects.filter(rol='Conductor', conductor__isnull=True).select_related('usuario'),
        'conductores_sin_cuenta': conductores_sin_cuenta,
        'total_activos': User.objects.filter(is_active=True).count(),
    })


@role_required(ADMIN)
def usuario_create(request):
    inicial = {'is_active': True}
    conductor_id = request.GET.get('conductor')
    if conductor_id:
        conductor = Conductor.objects.filter(pk=conductor_id).first()
        if conductor:
            base = (conductor.nombres.split()[0][0] + conductor.apellidos.split()[0]).lower()
            inicial.update({
                'rol': 'Conductor', 'conductor': conductor.pk, 'first_name': conductor.nombres,
                'last_name': conductor.apellidos, 'telefono': conductor.telefono,
                'username': ''.join(ch for ch in base if ch.isalnum()),
            })
    form = UsuarioForm(request.POST or None, initial=inicial)
    if request.method == 'POST' and form.is_valid():
        usuario = form.save()
        messages.success(request, f"Cuenta '{usuario.username}' creada. Comparta la contraseña inicial con la persona de forma segura.")
        return redirect('core:usuario_list')
    return render(request, 'core/usuarios/usuario_form.html', {'form': form, 'titulo': 'Nueva cuenta'})


@role_required(ADMIN)
def usuario_update(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    perfil = getattr(usuario, 'perfilusuario', None)
    inicial = {
        'username': usuario.username, 'first_name': usuario.first_name, 'last_name': usuario.last_name,
        'email': usuario.email, 'is_active': usuario.is_active,
        'rol': perfil.rol if perfil else '', 'telefono': perfil.telefono if perfil else '',
        'conductor': perfil.conductor_id if perfil else None,
    }
    form = UsuarioForm(request.POST or None, initial=inicial, usuario=usuario)
    if request.method == 'POST' and form.is_valid():
        if usuario == request.user and (not form.cleaned_data.get('is_active') or form.cleaned_data['rol'] != ADMIN):
            messages.error(request, "No puede desactivar su propia cuenta ni quitarse el rol de administrador.")
        else:
            form.save()
            messages.success(request, f"Cuenta '{usuario.username}' actualizada.")
            return redirect('core:usuario_list')
    return render(request, 'core/usuarios/usuario_form.html', {
        'form': form, 'titulo': f"Editar cuenta: {usuario.username}", 'usuario_obj': usuario,
    })


@role_required(ADMIN)
def usuario_password(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    form = CambiarPasswordForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        usuario.set_password(form.cleaned_data['password1'])
        usuario.save(update_fields=['password'])
        messages.success(request, f"Contraseña de '{usuario.username}' restablecida.")
        return redirect('core:usuario_list')
    return render(request, 'core/usuarios/usuario_password.html', {'form': form, 'usuario_obj': usuario})


@role_required(ADMIN)
@require_POST
def usuario_toggle(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    if usuario == request.user:
        messages.error(request, "No puede desactivar su propia cuenta.")
    else:
        usuario.is_active = not usuario.is_active
        usuario.save(update_fields=['is_active'])
        messages.success(request, f"Cuenta '{usuario.username}' {'activada' if usuario.is_active else 'desactivada'}.")
    return redirect('core:usuario_list')
