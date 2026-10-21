import datetime
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.utils.dateparse import parse_datetime
from django.utils import timezone


class RoleBasedLoginView(LoginView):
    """Redirige al módulo más relevante según el rol del usuario (RNF-01)."""
    template_name = 'core/login.html'

    def get_success_url(self):
        try:
            rol = self.request.user.perfilusuario.rol
        except AttributeError:
            return reverse_lazy('core:home')

        redirect_map = {
            'Administrador de operaciones': 'dashboard:operativo',
            'Gerencia': 'dashboard:operativo',
            'Supervisor': 'alerts:alerta_list',
            'Conductor': 'assignments:mis_servicios',
            'Finanzas': 'billing:valorizacion_list',
        }
        url_name = redirect_map.get(rol, 'core:home')
        return reverse_lazy(url_name)


@login_required
def home(request):
    roles = [
        ('Administrador de operaciones', 'bi-person-fill-gear',
         'Registra conductores, vehículos y solicitudes, asigna servicios y configura los catálogos.'),
        ('Supervisor', 'bi-eye-fill',
         'Controla la documentación, el visto bueno de mina y las alertas de vencimiento.'),
        ('Gerencia', 'bi-graph-up-arrow',
         'Consulta los indicadores operativos y los reportes estratégicos en Power BI.'),
        ('Finanzas', 'bi-receipt',
         'Gestiona tarifas y el ciclo de cobro de las valorizaciones.'),
        ('Conductor', 'bi-person-vcard',
         'Consulta sus servicios, llena el checklist, reporta incidencias y registra gastos.'),
    ]
    return render(request, 'core/home.html', {
        'today': datetime.date.today(),
        'roles': roles,
    })

@login_required
def perfil(request):
    return render(request, 'core/perfil.html')


