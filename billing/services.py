import datetime

from alerts.services import generar_alerta

from .models import Tarifa, Valorizacion


def generar_valorizacion(solicitud):
    """
    Crea la valorización en Borrador al completar un servicio (M6). Si el
    cliente no tiene tarifa para el tipo de vehículo, se crea con monto cero y
    una observación para que Finanzas la complete.
    """
    existente = Valorizacion.objects.filter(solicitud=solicitud).first()
    if existente:
        return existente
    from assignments.models import Asignacion

    asignacion = (
        Asignacion.objects.filter(solicitud=solicitud, estado_operativo='Completado')
        .order_by('-fecha_asignacion').first()
    )
    km = (asignacion.km_recorridos if asignacion else None) or solicitud.km_estimados or 0
    tarifa = Tarifa.buscar(solicitud.cliente, solicitud.tipo_vehiculo_requerido)
    valorizacion = Valorizacion(solicitud=solicitud, tarifa=tarifa, km_recorridos=km)
    if not tarifa:
        valorizacion.observacion = (
            f"No hay tarifa activa para {solicitud.cliente} y {solicitud.tipo_vehiculo_requerido}. "
            "Registre la tarifa en Configuración y recalcule."
        )
    valorizacion.calcular()
    valorizacion.save()
    return valorizacion


def cambiar_estado(valorizacion, nuevo_estado, *, numero_factura='', observacion=''):
    """Aplica una transición válida del ciclo de cobro y registra la fecha correspondiente."""
    if nuevo_estado not in valorizacion.siguientes_estados:
        raise ValueError(f"No se puede pasar de {valorizacion.estado} a {nuevo_estado}.")
    hoy = datetime.date.today()
    if nuevo_estado == 'Enviada':
        valorizacion.fecha_envio = hoy
    elif nuevo_estado == 'Conforme':
        valorizacion.fecha_conformidad = hoy
    elif nuevo_estado == 'Facturada':
        if not numero_factura:
            raise ValueError("Ingrese el número de factura.")
        valorizacion.numero_factura = numero_factura
        valorizacion.fecha_factura = hoy
    elif nuevo_estado == 'Pagada':
        valorizacion.fecha_pago = hoy
    if observacion:
        valorizacion.observacion = observacion
    valorizacion.estado = nuevo_estado
    valorizacion.save()
    return valorizacion


def recalcular(valorizacion):
    if valorizacion.estado not in ('Borrador', 'Observada'):
        raise ValueError("Solo se recalculan valorizaciones en Borrador u Observada.")
    valorizacion.tarifa = Tarifa.buscar(valorizacion.solicitud.cliente, valorizacion.solicitud.tipo_vehiculo_requerido)
    if valorizacion.tarifa:
        valorizacion.observacion = ''
    valorizacion.calcular()
    valorizacion.save()
    return valorizacion


def revisar_cobros_atrasados():
    """Genera una alerta por cada valorización enviada sin conformidad tras 15 días."""
    nuevas = 0
    for v in Valorizacion.objects.filter(estado__in=['Enviada', 'Observada']).select_related('solicitud'):
        if v.cobro_atrasado:
            generar_alerta(
                nivel_riesgo='Medio',
                tipo_alerta='Cobro pendiente',
                mensaje=(
                    f"Valorización de la solicitud #{v.solicitud_id} ({v.solicitud.cliente}) "
                    f"lleva {v.dias_sin_conformidad} días sin conformidad. Total S/ {v.total}"
                ),
            )
            nuevas += 1
    return nuevas
