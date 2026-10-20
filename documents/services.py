import datetime

from documents.models import DocumentoConductor, DocumentoVehiculo


def calcular_estado_documento(fecha_vencimiento):
    """
    Calcula el estado documental comparando la fecha de vencimiento contra hoy.

    Retorna uno de: "Vencido", "Por vencer", "Vigente".
    """
    if fecha_vencimiento is None:
        # Documentos que no vencen (por ejemplo, la tarjeta de propiedad).
        return "Vigente"
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


# Alias usado por el dashboard operativo (Fase 8) y la fase documental (Fase 4).
recalcular_estados_documentales = recalcular_estados_todos_documentos


def cumplimiento_documental(titular, es_conductor):
    """
    Compara los documentos del titular con la matriz de requisitos (M1).
    Devuelve una fila por requisito con el documento más reciente y su situación.
    """
    from assignments.validators import _documento_vigente_por_tipo
    from documents.models import RequisitoDocumental

    aplica_a = 'Conductor' if es_conductor else 'Vehículo'
    tipo = None if es_conductor else titular.tipo
    vigentes = _documento_vigente_por_tipo(titular.documentos.all())
    filas = []
    for req in RequisitoDocumental.objects.filter(aplica_a=aplica_a, activo=True).prefetch_related('tipos_vehiculo'):
        if not es_conductor and not req.aplica_al_tipo(tipo):
            continue
        doc = vigentes.get(req.tipo_documento)
        if doc is None:
            situacion = 'Falta'
        elif req.requiere_visto_bueno_mina and doc.estado_mina in ('Pendiente', 'Observado'):
            situacion = f"Mina: {doc.estado_mina}"
        else:
            situacion = doc.estado_documento
        filas.append({'requisito': req, 'documento': doc, 'situacion': situacion})
    return filas
