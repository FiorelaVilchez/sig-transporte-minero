import datetime


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
