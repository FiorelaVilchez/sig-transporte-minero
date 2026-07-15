import datetime
from dataclasses import dataclass

from django.db.models import Case, Count, IntegerField, When

from alerts.models import Alerta
from documents.models import DocumentoConductor, DocumentoVehiculo
from documents.services import recalcular_estados_todos_documentos


@dataclass
class ResumenEscaneoAlertas:
    alertas_nuevas_altas: int = 0
    alertas_nuevas_medias: int = 0
    alertas_resueltas: int = 0
    documentos_vencidos: int = 0
    documentos_por_vencer: int = 0

    def como_dict(self):
        return {
            "alertas_nuevas_altas": self.alertas_nuevas_altas,
            "alertas_nuevas_medias": self.alertas_nuevas_medias,
            "alertas_resueltas": self.alertas_resueltas,
            "documentos_vencidos": self.documentos_vencidos,
            "documentos_por_vencer": self.documentos_por_vencer,
        }


def generar_alerta(
    nivel_riesgo,
    tipo_alerta,
    documento_conductor=None,
    documento_vehiculo=None,
    mensaje="",
):
    """
    Crea y persiste una Alerta activa. Evita duplicados del mismo documento,
    nivel y tipo en el mismo día.
    """
    from django.utils import timezone

    hoy = timezone.now().date()
    filtro = {
        "estado_alerta": "Activa",
        "nivel_riesgo": nivel_riesgo,
        "tipo_alerta": tipo_alerta,
        "documento_conductor": documento_conductor,
        "documento_vehiculo": documento_vehiculo,
        "fecha_generacion__date": hoy,
    }
    alerta_existente = Alerta.objects.filter(**filtro).first()
    if alerta_existente:
        return alerta_existente

    return Alerta.objects.create(
        nivel_riesgo=nivel_riesgo,
        tipo_alerta=tipo_alerta,
        documento_conductor=documento_conductor,
        documento_vehiculo=documento_vehiculo,
        mensaje=mensaje,
        estado_alerta="Activa",
    )


def _tiene_alerta_activa(tipo_alerta, documento_conductor=None, documento_vehiculo=None):
    return Alerta.objects.filter(
        estado_alerta="Activa",
        tipo_alerta=tipo_alerta,
        documento_conductor=documento_conductor,
        documento_vehiculo=documento_vehiculo,
    ).exists()


def _mensaje_documento_vencido(documento, es_conductor):
    dias = (datetime.date.today() - documento.fecha_vencimiento).days
    if es_conductor:
        titular = f"{documento.conductor.apellidos}, {documento.conductor.nombres}"
        return f"{documento.tipo_documento} de {titular} venció hace {dias} días"
    return (
        f"{documento.tipo_documento} del vehículo {documento.vehiculo.placa} "
        f"venció hace {dias} días"
    )


def _mensaje_documento_por_vencer(documento, es_conductor):
    dias = (documento.fecha_vencimiento - datetime.date.today()).days
    if es_conductor:
        titular = f"{documento.conductor.apellidos}, {documento.conductor.nombres}"
        return f"{documento.tipo_documento} de {titular} vence en {dias} días"
    return (
        f"{documento.tipo_documento} del vehículo {documento.vehiculo.placa} "
        f"vence en {dias} días"
    )


def _resolver_alertas_obsoletas(resumen):
    alertas_activas = Alerta.objects.filter(
        estado_alerta="Activa",
        tipo_alerta__in=["Documento vencido", "Documento por vencer"],
    ).select_related("documento_conductor", "documento_vehiculo")

    for alerta in alertas_activas:
        documento = alerta.documento_conductor or alerta.documento_vehiculo
        if documento is None:
            continue
        if documento.estado_documento == "Vigente":
            alerta.estado_alerta = "Resuelta"
            alerta.save(update_fields=["estado_alerta", "updated_at"])
            resumen.alertas_resueltas += 1


def escanear_documentos_y_generar_alertas():
    """
    Escanea toda la base documental, recalcula estados y genera/actualiza alertas.
    """
    resumen = ResumenEscaneoAlertas()
    recalculo = recalcular_estados_todos_documentos()
    resumen.documentos_vencidos = recalculo["contadores"]["Vencido"]
    resumen.documentos_por_vencer = recalculo["contadores"]["Por vencer"]

    for documento in DocumentoConductor.objects.select_related("conductor").all():
        if documento.estado_documento == "Vencido":
            if not _tiene_alerta_activa(
                "Documento vencido", documento_conductor=documento
            ):
                generar_alerta(
                    nivel_riesgo="Alto",
                    tipo_alerta="Documento vencido",
                    documento_conductor=documento,
                    mensaje=_mensaje_documento_vencido(documento, True),
                )
                resumen.alertas_nuevas_altas += 1
        elif documento.estado_documento == "Por vencer":
            if not _tiene_alerta_activa(
                "Documento por vencer", documento_conductor=documento
            ):
                generar_alerta(
                    nivel_riesgo="Medio",
                    tipo_alerta="Documento por vencer",
                    documento_conductor=documento,
                    mensaje=_mensaje_documento_por_vencer(documento, True),
                )
                resumen.alertas_nuevas_medias += 1

    for documento in DocumentoVehiculo.objects.select_related("vehiculo").all():
        if documento.estado_documento == "Vencido":
            if not _tiene_alerta_activa(
                "Documento vencido", documento_vehiculo=documento
            ):
                generar_alerta(
                    nivel_riesgo="Alto",
                    tipo_alerta="Documento vencido",
                    documento_vehiculo=documento,
                    mensaje=_mensaje_documento_vencido(documento, False),
                )
                resumen.alertas_nuevas_altas += 1
        elif documento.estado_documento == "Por vencer":
            if not _tiene_alerta_activa(
                "Documento por vencer", documento_vehiculo=documento
            ):
                generar_alerta(
                    nivel_riesgo="Medio",
                    tipo_alerta="Documento por vencer",
                    documento_vehiculo=documento,
                    mensaje=_mensaje_documento_por_vencer(documento, False),
                )
                resumen.alertas_nuevas_medias += 1

    _resolver_alertas_obsoletas(resumen)
    return resumen.como_dict()


def get_alertas_activas():
    """Alertas activas ordenadas por nivel (Alto primero) y fecha descendente."""
    return (
        Alerta.objects.filter(estado_alerta="Activa")
        .annotate(
            orden_nivel=Case(
                When(nivel_riesgo="Alto", then=0),
                When(nivel_riesgo="Medio", then=1),
                When(nivel_riesgo="Bajo", then=2),
                default=3,
                output_field=IntegerField(),
            )
        )
        .order_by("orden_nivel", "-fecha_generacion")
    )


def get_resumen_alertas_por_nivel():
    """Conteo de alertas activas agrupadas por nivel de riesgo."""
    conteos = {"Alto": 0, "Medio": 0, "Bajo": 0}
    agregados = (
        Alerta.objects.filter(estado_alerta="Activa")
        .values("nivel_riesgo")
        .annotate(total=Count("alert_id"))
    )
    for item in agregados:
        conteos[item["nivel_riesgo"]] = item["total"]
    return conteos
