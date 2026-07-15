from django.utils import timezone

from alerts.models import Alerta


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
