from django.db import models, transaction
from django.utils import timezone

from alerts.services import generar_alerta
from assignments.models import Asignacion, Notificacion
from assignments.validators import horas_programadas_semana, validar_asignacion
from drivers.models import Conductor
from service_requests.services import registrar_cambio
from trucks.models import Vehiculo


def _notificar(conductor, mensaje):
    return Notificacion.objects.create(conductor=conductor, mensaje=mensaje[:255], leida=False)


def confirmar_asignacion(solicitud, conductor, vehiculo, resultado, *, observacion_extra='', usuario=None, manual=False):
    """
    Registra la asignación aprobada u observada y notifica al conductor.
    Desde la versión 2.0 la disponibilidad se controla por horario (R9), por lo
    que el conductor y el vehículo no pasan a Ocupado / En servicio hasta que
    el servicio sale a ruta.
    """
    observaciones = list(resultado.get('observaciones', []))
    if observacion_extra:
        observaciones.append(observacion_extra)
    with transaction.atomic():
        asignacion = Asignacion.objects.create(
            solicitud=solicitud,
            conductor=conductor,
            vehiculo=vehiculo,
            estado_asignacion=resultado['veredicto'],
            estado_operativo='Programado',
            observacion=", ".join(observaciones),
        )
        anterior = solicitud.estado_solicitud
        solicitud.estado_solicitud = "Asignada"
        solicitud.save()
        registrar_cambio(
            solicitud, usuario, 'Estado de Solicitud', anterior, 'Asignada',
            f"{'Asignación manual' if manual else 'Asignación automática'}: "
            f"{conductor.apellidos}, {conductor.nombres} / {vehiculo.placa}",
        )
    prefijo = "Manual: " if manual else ""
    _notificar(
        conductor,
        f"{prefijo}Nuevo servicio asignado: {solicitud.cliente} el {solicitud.fecha_servicio:%d/%m/%Y} "
        f"a las {solicitud.hora_servicio:%H:%M}. Ruta: {solicitud.origen} -> {solicitud.destino}. "
        f"Unidad {vehiculo.placa}.",
    )
    return asignacion


def candidatos_para(solicitud):
    """Conductores y vehículos que pueden evaluarse para la solicitud, ya ordenados."""
    conductores = list(
        Conductor.objects.filter(estado__in=["Disponible", "Ocupado"])
        .annotate(total_assignments=models.Count('asignaciones'))
        .order_by('total_assignments', 'apellidos', 'nombres')
    )
    # Equidad (M5): primero quien tiene menos horas programadas en la semana.
    for c in conductores:
        c.horas_semana = horas_programadas_semana(c, solicitud.fecha_servicio, excluir_solicitud=solicitud)
    conductores.sort(key=lambda c: (c.horas_semana, c.total_assignments, c.apellidos, c.nombres))

    # Vehículos del tipo requerido; primero la unidad más chica que alcanza.
    vehiculos = (
        Vehiculo.objects.filter(tipo=solicitud.tipo_vehiculo_requerido)
        .exclude(estado__in=["En mantenimiento", "De baja"])
        .order_by('capacidad', 'placa')
    )
    return conductores, list(vehiculos)


def asignar_automaticamente(solicitud, usuario=None):
    """
    Asignación automática: busca la primera combinación Aprobada (y si no hay,
    la primera Observada) evaluando R1 a R10 contra el horario de la solicitud.
    """
    if solicitud.estado_solicitud not in ("Pendiente", "Reprogramada"):
        return {
            "exito": False,
            "asignacion": None,
            "mensaje": f"La solicitud no está en un estado programable (estado actual: {solicitud.estado_solicitud}).",
        }

    conductores, vehiculos = candidatos_para(solicitud)

    def reprogramar(motivo):
        anterior = solicitud.estado_solicitud
        solicitud.estado_solicitud = "Reprogramada"
        solicitud.save()
        if anterior != "Reprogramada":
            registrar_cambio(solicitud, usuario, 'Estado de Solicitud', anterior, 'Reprogramada', motivo)
        return {"exito": False, "asignacion": None, "mensaje": motivo}

    if not conductores:
        return reprogramar("No hay conductores disponibles. Solicitud reprogramada.")
    if not vehiculos:
        return reprogramar(
            f"No hay vehículos disponibles del tipo requerido ({solicitud.tipo_vehiculo_requerido}). Solicitud reprogramada."
        )

    mejor = None
    observada = None
    motivos = {}
    for conductor in conductores:
        for vehiculo in vehiculos:
            resultado = validar_asignacion(conductor, vehiculo, solicitud=solicitud, generar_alertas=False)
            if resultado['veredicto'] == "Aprobada":
                mejor = (conductor, vehiculo)
                break
            if resultado['veredicto'] == "Observada" and observada is None:
                observada = (conductor, vehiculo)
            for b in resultado['bloqueos']:
                regla = b.split(':')[0]
                motivos[regla] = motivos.get(regla, 0) + 1
        if mejor:
            break

    elegido = mejor or observada
    if not elegido:
        resumen = ", ".join(f"{r} ({n})" for r, n in sorted(motivos.items()))
        return reprogramar(
            "Ninguna combinación de conductor y vehículo cumple las reglas. Solicitud reprogramada."
            + (f" Bloqueos encontrados: {resumen}." if resumen else "")
        )

    conductor, vehiculo = elegido
    resultado = validar_asignacion(conductor, vehiculo, solicitud=solicitud, generar_alertas=True)
    asignacion = confirmar_asignacion(solicitud, conductor, vehiculo, resultado, usuario=usuario)
    return {
        "exito": True,
        "asignacion": asignacion,
        "mensaje": f"Asignación automática exitosa ({resultado['veredicto']}) con Conductor {conductor} y Vehículo {vehiculo}.",
    }


def asignacion_vigente(solicitud):
    return (
        Asignacion.objects.filter(solicitud=solicitud, estado_asignacion__in=['Aprobada', 'Observada'])
        .exclude(estado_operativo='Cancelado')
        .select_related('conductor', 'vehiculo')
        .order_by('-fecha_asignacion')
        .first()
    )


def _liberar_recursos(asignacion, vehiculo_a_mantenimiento=False):
    if asignacion.conductor and asignacion.conductor.estado == "Ocupado":
        asignacion.conductor.estado = "Disponible"
        asignacion.conductor.save()
    if asignacion.vehiculo:
        if vehiculo_a_mantenimiento:
            asignacion.vehiculo.estado = "En mantenimiento"
            asignacion.vehiculo.save()
        elif asignacion.vehiculo.estado == "En servicio":
            asignacion.vehiculo.estado = "Disponible"
            asignacion.vehiculo.save()


def registrar_checklist(asignacion, checklist):
    """Guarda el checklist (M3). Si aprueba, el servicio queda Listo para salir."""
    checklist.asignacion = asignacion
    checklist.evaluar()
    checklist.save()
    if checklist.aprobado:
        asignacion.estado_operativo = 'Listo para salir'
        asignacion.km_inicial = checklist.km_inicial
        asignacion.save()
    else:
        generar_alerta(
            nivel_riesgo="Alto",
            tipo_alerta="Checklist no aprobado",
            mensaje=(
                f"Checklist no aprobado: solicitud #{asignacion.solicitud_id}, unidad "
                f"{asignacion.vehiculo.placa}. {checklist.motivo_rechazo}"
            )[:255],
        )
    return checklist


def iniciar_ruta(asignacion, usuario=None):
    asignacion.estado_operativo = 'En ruta'
    asignacion.inicio_real = timezone.now()
    asignacion.save()
    asignacion.conductor.estado = "Ocupado"
    asignacion.conductor.save()
    asignacion.vehiculo.estado = "En servicio"
    asignacion.vehiculo.save()
    registrar_cambio(asignacion.solicitud, usuario, 'Estado del servicio', 'Listo para salir', 'En ruta', 'Salida registrada por el conductor')


def completar_servicio(asignacion, *, km_final=None, usuario=None):
    """Cierra el servicio, libera recursos y genera la valorización en borrador (M6)."""
    solicitud = asignacion.solicitud
    with transaction.atomic():
        if km_final is not None:
            asignacion.km_final = km_final
        asignacion.estado_operativo = 'Completado'
        asignacion.fin_real = timezone.now()
        asignacion.save()
        _liberar_recursos(asignacion)
        anterior = solicitud.estado_solicitud
        solicitud.estado_solicitud = "Completada"
        solicitud.save()
        registrar_cambio(solicitud, usuario, 'Estado de Solicitud', anterior, 'Completada', 'Servicio finalizado')
    from billing.services import generar_valorizacion
    return generar_valorizacion(solicitud)


def reportar_incidencia(asignacion, incidencia, usuario=None):
    """
    Registra la incidencia (M4). Si es grave, el servicio pasa a Con incidencia,
    se liberan los recursos y la solicitud vuelve a Reprogramada para reasignar.
    """
    incidencia.asignacion = asignacion
    incidencia.save()
    solicitud = asignacion.solicitud
    generar_alerta(
        nivel_riesgo="Alto" if incidencia.gravedad == "Alta" else "Medio",
        tipo_alerta="Incidencia operativa",
        mensaje=(
            f"{incidencia.tipo} en el servicio #{solicitud.request_id} "
            f"({asignacion.vehiculo.placa}): {incidencia.descripcion}"
        )[:255],
    )
    if incidencia.gravedad == "Alta":
        with transaction.atomic():
            asignacion.estado_operativo = 'Con incidencia'
            asignacion.save()
            _liberar_recursos(asignacion, vehiculo_a_mantenimiento=incidencia.tipo == 'Falla mecánica')
            anterior = solicitud.estado_solicitud
            solicitud.estado_solicitud = "Reprogramada"
            solicitud.save()
            registrar_cambio(
                solicitud, usuario, 'Estado de Solicitud', anterior, 'Reprogramada',
                f"Incidencia grave: {incidencia.tipo}. Requiere reemplazo.",
            )
    return incidencia


def revalidar_por_cambio(solicitud, usuario=None, motivo=''):
    """
    Tras cambiar fecha, hora, duración, pasajeros o tipo de una solicitud ya
    asignada (M2), vuelve a validar la asignación. Si ya no cumple, la cancela,
    deja la solicitud Reprogramada y avisa al conductor.
    """
    asignacion = asignacion_vigente(solicitud)
    if not asignacion or asignacion.estado_operativo not in ('Programado', 'Listo para salir'):
        return None
    resultado = validar_asignacion(asignacion.conductor, asignacion.vehiculo, solicitud=solicitud, generar_alertas=False)
    tipo_distinto = asignacion.vehiculo.tipo_id != solicitud.tipo_vehiculo_requerido_id
    if resultado['veredicto'] == 'Rechazada' or tipo_distinto:
        asignacion.estado_operativo = 'Cancelado'
        asignacion.observacion = (asignacion.observacion + ', ' if asignacion.observacion else '') + \
            'Cancelada por cambio en la solicitud: ' + '; '.join(resultado['bloqueos'] or ['tipo de vehículo distinto'])
        asignacion.save()
        solicitud.estado_solicitud = 'Reprogramada'
        solicitud.save()
        registrar_cambio(solicitud, usuario, 'Estado de Solicitud', 'Asignada', 'Reprogramada',
                         'La asignación ya no cumple las reglas tras el cambio')
        _notificar(asignacion.conductor,
                   f"Se canceló su servicio #{solicitud.request_id} ({solicitud.cliente}) por un cambio en la solicitud.")
        return {'cancelada': True, 'bloqueos': resultado['bloqueos']}
    _notificar(asignacion.conductor,
               f"Cambio en su servicio #{solicitud.request_id}: {solicitud.fecha_servicio:%d/%m/%Y} "
               f"{solicitud.hora_servicio:%H:%M}, {solicitud.origen} -> {solicitud.destino}. {motivo}")
    return {'cancelada': False, 'bloqueos': []}
