from django.shortcuts import redirect, render
from functools import wraps

def role_required(*allowed_roles):
    """
    Decorador para restringir el acceso a vistas basándose en el rol del usuario.
    Si el usuario no está autenticado, redirige al login.
    Si no tiene el rol requerido, renderiza la plantilla core/403.html con código de estado 403.

    Matriz de accesos y permisos futuros:
    ----------------------------------------------------------------------------------------
    - Gestión de Conductores / Vehículos / Solicitudes / Asignación manual:
        -> Solo 'Administrador de operaciones'
    - Control documental / Alertas:
        -> 'Administrador de operaciones' y 'Supervisor'
    - Dashboard / Reportes gerenciales (Power BI):
        -> 'Gerencia' y 'Administrador de operaciones' (Gerencia tendrá permisos de solo lectura)
    - Mis servicios asignados / Mi documentación pendiente:
        -> Solo 'Conductor' (visualiza exclusivamente su información vinculada a PerfilUsuario.conductor)
    ----------------------------------------------------------------------------------------
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('core:login')
            
            try:
                perfil = request.user.perfilusuario
                if perfil.rol in allowed_roles:
                    return view_func(request, *args, **kwargs)
            except AttributeError:
                # El usuario no tiene un perfil asociado
                pass
            
            return render(request, 'core/403.html', {
                'allowed_roles': allowed_roles,
                'user_role': getattr(getattr(request.user, 'perfilusuario', None), 'rol', 'Sin Rol'),
            }, status=403)
        return _wrapped_view
    return decorator
```
,Description:
