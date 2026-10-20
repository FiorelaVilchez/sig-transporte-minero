from django.db.models import Count

from alerts.services import get_resumen_alertas_por_nivel
from assignments.models import Asignacion
from documents.models import DocumentoConductor, DocumentoVehiculo
from service_requests.models import SolicitudServicio

ESTADOS_SOLICITUD = [
    "Pendiente",
    "Asignada",
    "Reprogramada",
    "Completada",
    "Cancelada",
]


def kpi_total_asignaciones():
    """Indicador 1: conteo total de assignment_id."""
    return Asignacion.objects.count()


def kpi_asignaciones_aprobadas():
    """Indicador 2: conteo con estado_asignacion = Aprobada."""
    return Asignacion.objects.filter(estado_asignacion="Aprobada").count()


def kpi_asignaciones_rechazadas():
    """Indicador 3: conteo con estado_asignacion = Rechazada."""
    return Asignacion.objects.filter(estado_asignacion="Rechazada").count()


def kpi_documentos_vencidos():
    """Indicador 4: documentos con estado_documento = Vencido."""
    conductores = DocumentoConductor.objects.filter(estado_documento="Vencido").count()
    vehiculos = DocumentoVehiculo.objects.filter(estado_documento="Vencido").count()
    return conductores + vehiculos


def kpi_documentos_por_vencer():
    """Indicador 5: documentos con estado_documento = Por vencer."""
    conductores = DocumentoConductor.objects.filter(estado_documento="Por vencer").count()
    vehiculos = DocumentoVehiculo.objects.filter(estado_documento="Por vencer").count()
    return conductores + vehiculos


def kpi_alertas_riesgo_alto():
    """Indicador 6: alertas activas con nivel_riesgo = Alto."""
    return get_resumen_alertas_por_nivel()["Alto"]


def kpi_solicitudes_por_estado():
    """Indicador 7: conteo de request_id por estado_solicitud."""
    conteos = {estado: 0 for estado in ESTADOS_SOLICITUD}
    agregados = (
        SolicitudServicio.objects.values("estado_solicitud")
        .annotate(total=Count("request_id"))
    )
    for item in agregados:
        conteos[item["estado_solicitud"]] = item["total"]
    return conteos


def kpi_asignaciones_por_conductor():
    """Indicador 8a: top 10 conductores por cantidad de asignaciones."""
    agregados = (
        Asignacion.objects.filter(conductor__isnull=False)
        .values("conductor__apellidos", "conductor__nombres")
        .annotate(total=Count("assignment_id"))
        .order_by("-total")[:10]
    )
    return [
        {
            "conductor": f"{item['conductor__apellidos']}, {item['conductor__nombres']}",
            "total": item["total"],
        }
        for item in agregados
    ]


def kpi_asignaciones_por_vehiculo():
    """Indicador 8b: top 10 vehículos por cantidad de asignaciones."""
    agregados = (
        Asignacion.objects.filter(vehiculo__isnull=False)
        .values("vehiculo__placa")
        .annotate(total=Count("assignment_id"))
        .order_by("-total")[:10]
    )
    return [
        {"vehiculo": item["vehiculo__placa"], "total": item["total"]}
        for item in agregados
    ]


def get_dashboard_kpis():
    """Agrega los 8 indicadores en una estructura lista para el template."""
    return {
        "total_asignaciones": kpi_total_asignaciones(),
        "asignaciones_aprobadas": kpi_asignaciones_aprobadas(),
        "asignaciones_rechazadas": kpi_asignaciones_rechazadas(),
        "documentos_vencidos": kpi_documentos_vencidos(),
        "documentos_por_vencer": kpi_documentos_por_vencer(),
        "alertas_riesgo_alto": kpi_alertas_riesgo_alto(),
        "solicitudes_por_estado": kpi_solicitudes_por_estado(),
        "asignaciones_por_conductor": kpi_asignaciones_por_conductor(),
        "asignaciones_por_vehiculo": kpi_asignaciones_por_vehiculo(),
    }


def get_kpis_ejecucion():
    """
    Indicadores de ejecución, cumplimiento y cobranza (M7): se calculan con los
    datos que generan el checklist, las incidencias y las valorizaciones.
    """
    import datetime
    from decimal import Decimal

    from django.db.models import Q, Sum

    from assignments.models import Asignacion, ChecklistPreoperacional, Incidencia
    from assignments.validators import LIMITE_HORAS_SEMANA, horas_programadas_semana
    from billing.models import Valorizacion
    from documents.models import DocumentoConductor, DocumentoVehiculo
    from drivers.models import Conductor

    hoy = datetime.date.today()
    inicio_mes = hoy.replace(day=1)

    del_mes = Asignacion.objects.filter(solicitud__fecha_servicio__range=(inicio_mes, hoy))
    completados = del_mes.filter(estado_operativo='Completado').count()
    con_incidencia = del_mes.filter(estado_operativo='Con incidencia').count()
    cerrados = completados + con_incidencia
    cumplimiento = round(completados * 100 / cerrados) if cerrados else None

    checklists = ChecklistPreoperacional.objects.filter(fecha__date__gte=inicio_mes)
    total_check = checklists.count()
    check_ok = checklists.filter(aprobado=True).count()

    por_cobrar = Valorizacion.objects.filter(
        estado__in=['Enviada', 'Observada', 'Conforme', 'Facturada']
    ).aggregate(t=Sum('total'))['t'] or Decimal('0')
    cobrado_mes = Valorizacion.objects.filter(
        estado='Pagada', fecha_pago__gte=inicio_mes
    ).aggregate(t=Sum('total'))['t'] or Decimal('0')
    atrasadas = sum(1 for v in Valorizacion.objects.filter(estado__in=['Enviada', 'Observada']) if v.cobro_atrasado)

    cerca_limite = 0
    for c in Conductor.objects.exclude(estado__in=['De baja', 'No apto']):
        if horas_programadas_semana(c, hoy) >= LIMITE_HORAS_SEMANA * 0.8:
            cerca_limite += 1

    pendientes_mina = (
        DocumentoConductor.objects.filter(estado_mina__in=['Pendiente', 'Observado']).count()
        + DocumentoVehiculo.objects.filter(estado_mina__in=['Pendiente', 'Observado']).count()
    )

    return {
        'servicios_completados_mes': completados,
        'cumplimiento_servicio': cumplimiento,
        'incidencias_mes': Incidencia.objects.filter(fecha__date__gte=inicio_mes).count(),
        'incidencias_graves_abiertas': Incidencia.objects.filter(gravedad='Alta', resuelta=False).count(),
        'checklists_mes': total_check,
        'checklists_aprobados_pct': round(check_ok * 100 / total_check) if total_check else None,
        'por_cobrar': por_cobrar,
        'cobrado_mes': cobrado_mes,
        'cobros_atrasados': atrasadas,
        'conductores_cerca_limite': cerca_limite,
        'documentos_pendientes_mina': pendientes_mina,
        'en_ruta': Asignacion.objects.filter(estado_operativo='En ruta').count(),
    }
