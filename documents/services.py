import datetime

from documents.models import DocumentoConductor, DocumentoVehiculo


def calcular_estado_documento(fecha_vencimiento):
    """
    Calcula el estado documental comparando la fecha de vencimiento contra hoy.

    Retorna uno de: "Vencido", "Por vencer", "Vigente".
    """
    hoy = datetime.date.today()
    if fecha_vencimiento < hoy:
        return "Vencido"
    if fecha_vencimiento <= hoy + datetime.timedelta(days=30):
        return "Por vencer"
    return "Vigente"


def recalcular_estados_todos_documentos():
    """
    Recalcula estado_documento de todos los documentos según fecha de vencimiento.
    """
    contadores = {"Vigente": 0, "Por vencer": 0, "Vencido": 0}
    actualizados = 0

    for documento in DocumentoConductor.objects.all():
        nuevo_estado = calcular_estado_documento(documento.fecha_vencimiento)
        if documento.estado_documento != nuevo_estado:
            documento.estado_documento = nuevo_estado
            documento.save(update_fields=["estado_documento", "updated_at"])
            actualizados += 1
        contadores[nuevo_estado] += 1

    for documento in DocumentoVehiculo.objects.all():
        nuevo_estado = calcular_estado_documento(documento.fecha_vencimiento)
        if documento.estado_documento != nuevo_estado:
            documento.estado_documento = nuevo_estado
            documento.save(update_fields=["estado_documento", "updated_at"])
            actualizados += 1
        contadores[nuevo_estado] += 1

    return {
        "contadores": contadores,
        "actualizados": actualizados,
        "total": sum(contadores.values()),
    }
