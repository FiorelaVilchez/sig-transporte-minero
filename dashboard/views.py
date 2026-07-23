import json

from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from alerts.services import escanear_documentos_y_generar_alertas
from core.decorators import role_required
from documents.services import recalcular_estados_documentales

from .services import get_dashboard_kpis


def _formatear_ultima_actualizacion(valor_iso):
    if not valor_iso:
        return None
    dt = parse_datetime(valor_iso)
    if dt is None:
        return valor_iso
    return timezone.localtime(dt).strftime('%d/%m/%Y %H:%M')


@role_required('Administrador de operaciones', 'Supervisor', 'Gerencia')
def dashboard_operativo(request):
    kpis = get_dashboard_kpis()
    ultima_actualizacion = _formatear_ultima_actualizacion(
        request.session.get('dashboard_ultima_actualizacion')
    )
    puede_actualizar = request.user.perfilusuario.rol in (
        'Administrador de operaciones',
        'Gerencia',
    )

    context = {
        'kpis': kpis,
        'ultima_actualizacion': ultima_actualizacion,
        'puede_actualizar': puede_actualizar,
        'solicitudes_labels': json.dumps(list(kpis['solicitudes_por_estado'].keys())),
        'solicitudes_values': json.dumps(list(kpis['solicitudes_por_estado'].values())),
        'conductores_labels': json.dumps(
            [item['conductor'] for item in kpis['asignaciones_por_conductor']]
        ),
        'conductores_values': json.dumps(
            [item['total'] for item in kpis['asignaciones_por_conductor']]
        ),
        'vehiculos_labels': json.dumps(
            [item['vehiculo'] for item in kpis['asignaciones_por_vehiculo']]
        ),
        'vehiculos_values': json.dumps(
            [item['total'] for item in kpis['asignaciones_por_vehiculo']]
        ),
    }
    return render(request, 'dashboard/dashboard_operativo.html', context)


@role_required('Administrador de operaciones', 'Gerencia')
def dashboard_actualizar(request):
    if request.method == 'POST':
        recalcular_estados_documentales()
        resumen = escanear_documentos_y_generar_alertas()
        ahora = timezone.localtime(timezone.now())
        request.session['dashboard_ultima_actualizacion'] = ahora.isoformat()
        mensaje = (
            f"Indicadores actualizados correctamente. "
            f"Documentos: Vencidos={resumen['documentos_vencidos']}, "
            f"Por vencer={resumen['documentos_por_vencer']}. "
            f"Alertas: Nuevas Altas={resumen['alertas_nuevas_altas']}, "
            f"Nuevas Medias={resumen['alertas_nuevas_medias']}, "
            f"Resueltas={resumen['alertas_resueltas']}."
        )
        messages.success(request, mensaje)
    return redirect('dashboard:operativo')


@role_required('Administrador de operaciones', 'Gerencia')
def reportes_gerenciales(request):
    return render(request, 'dashboard/reportes_gerenciales.html')
