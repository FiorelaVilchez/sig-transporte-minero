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
