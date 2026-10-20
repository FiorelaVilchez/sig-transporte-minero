from .models import CambioSolicitud

# Campos cuyo cambio afecta la programación y obliga a revalidar la asignación.
CAMPOS_DE_PROGRAMACION = [
    'fecha_servicio', 'hora_servicio', 'duracion_horas', 'pasajeros', 'tipo_vehiculo_requerido',
]


def _texto(valor):
    if valor is None:
        return ''
    tiene_fecha, tiene_hora = hasattr(valor, 'year'), hasattr(valor, 'hour')
    if tiene_fecha and tiene_hora:
        return valor.strftime('%d/%m/%Y %H:%M')
    if tiene_fecha:
        return valor.strftime('%d/%m/%Y')
    if tiene_hora:
        return valor.strftime('%H:%M')
    return str(valor)[:255]


def registrar_cambio(solicitud, usuario, campo, anterior, nuevo, motivo=''):
    """Agrega una línea a la bitácora de la solicitud (M2)."""
    return CambioSolicitud.objects.create(
        solicitud=solicitud,
        usuario=usuario if getattr(usuario, 'is_authenticated', False) else None,
        campo=campo,
        valor_anterior=_texto(anterior),
        valor_nuevo=_texto(nuevo),
        motivo=(motivo or '')[:255],
    )
