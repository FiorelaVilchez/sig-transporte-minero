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
    """Portada: resumen del día según el rol, accesos rápidos y listas de trabajo."""
    from alerts.models import Alerta
    from assignments.models import Asignacion
    from billing.models import Valorizacion
    from documents.models import DocumentoConductor, DocumentoVehiculo
    from service_requests.models import SolicitudServicio

    hoy = datetime.date.today()
    manana = hoy + datetime.timedelta(days=1)
    rol = getattr(getattr(request.user, 'perfilusuario', None), 'rol', '')
    from django.utils import dateformat, timezone
    hora = timezone.localtime().hour
    saludo = 'Buenos días' if hora < 12 else ('Buenas tardes' if hora < 19 else 'Buenas noches')
    ctx = {
        'today': hoy, 'rol': rol, 'saludo': saludo,
        'fecha_larga': dateformat.format(hoy, r'l, j \d\e F \d\e Y'),
    }

    if rol in ('Administrador de operaciones', 'Supervisor', 'Gerencia'):
        agenda = (
            Asignacion.objects.filter(
                estado_asignacion__in=['Aprobada', 'Observada'],
                solicitud__fecha_servicio__in=[hoy, manana],
            ).exclude(estado_operativo='Cancelado')
            .select_related('solicitud', 'conductor', 'vehiculo')
            .order_by('solicitud__fecha_servicio', 'solicitud__hora_servicio')
        )
        alertas = Alerta.objects.filter(estado_alerta='Activa')
        ctx.update({
            'servicios_hoy': agenda.filter(solicitud__fecha_servicio=hoy).count(),
            'en_ruta': Asignacion.objects.filter(estado_operativo='En ruta').count(),
            'por_asignar': SolicitudServicio.objects.filter(estado_solicitud__in=['Pendiente', 'Reprogramada']).count(),
            'reprogramadas': SolicitudServicio.objects.filter(estado_solicitud='Reprogramada').count(),
            'alertas_activas': alertas.count(),
            'alertas_altas': alertas.filter(nivel_riesgo='Alto').count(),
            'docs_por_vencer': (DocumentoConductor.objects.filter(estado_documento='Por vencer').count()
                                + DocumentoVehiculo.objects.filter(estado_documento='Por vencer').count()),
            'docs_vencidos': (DocumentoConductor.objects.filter(estado_documento='Vencido').count()
                              + DocumentoVehiculo.objects.filter(estado_documento='Vencido').count()),
            'agenda': agenda[:8],
            'alertas_recientes': alertas.order_by('-fecha_generacion')[:5],
        })
    elif rol == 'Finanzas':
        abiertas = Valorizacion.objects.exclude(estado='Pagada')
        ctx.update({
            'borradores': Valorizacion.objects.filter(estado='Borrador').count(),
            'por_cobrar': sum((v.total for v in abiertas.exclude(estado='Borrador')), 0),
            'atrasadas': sum(1 for v in abiertas.filter(estado__in=['Enviada', 'Observada']) if v.cobro_atrasado),
            'cobrado_mes': sum((v.total for v in Valorizacion.objects.filter(estado='Pagada', fecha_pago__gte=hoy.replace(day=1))), 0),
            'valorizaciones': abiertas.select_related('solicitud').order_by('-created_at')[:8],
        })
    elif rol == 'Conductor' and request.user.perfilusuario.conductor:
        conductor = request.user.perfilusuario.conductor
        ctx.update({
            'mis_proximos': Asignacion.objects.filter(
                conductor=conductor, estado_operativo__in=['Programado', 'Listo para salir', 'En ruta'],
                estado_asignacion__in=['Aprobada', 'Observada'],
            ).select_related('solicitud', 'vehiculo').order_by('solicitud__fecha_servicio', 'solicitud__hora_servicio')[:5],
            'mis_docs_alerta': conductor.documentos.exclude(estado_documento='Vigente').order_by('fecha_vencimiento'),
        })
    return render(request, 'core/home.html', ctx)

@login_required
def perfil(request):
    return render(request, 'core/perfil.html')


