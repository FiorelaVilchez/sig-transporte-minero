from django.db import models
from service_requests.models import SolicitudServicio
from drivers.models import Conductor
from trucks.models import Vehiculo
from assignments.models import Asignacion, Notificacion
from assignments.validators import validar_asignacion

def asignar_automaticamente(solicitud):
    """
    Realiza la asignación automática de conductor y vehículo para una solicitud.
    Sigue el flujo de la Figura 3 del proyecto.
    """
    if solicitud.estado_solicitud != "Pendiente" and solicitud.estado_solicitud != "Reprogramada":
        return {
            "exito": False,
            "asignacion": None,
            "mensaje": f"La solicitud no está en un estado programable (estado actual: {solicitud.estado_solicitud})."
        }

    # a) Buscar candidatos disponibles
    conductores_candidatos = Conductor.objects.filter(estado="Disponible")
    vehiculos_candidatos = Vehiculo.objects.filter(
        estado="Disponible", 
        tipo=solicitud.tipo_vehiculo_requerido
    )

    # b) Si no hay conductores o vehículos compatibles, reprogramar
    if not conductores_candidatos.exists():
        solicitud.estado_solicitud = "Reprogramada"
        solicitud.save()
        return {
            "exito": False,
            "asignacion": None,
            "mensaje": "No hay conductores disponibles. Solicitud reprogramada."
        }

    if not vehiculos_candidatos.exists():
        solicitud.estado_solicitud = "Reprogramada"
        solicitud.save()
        return {
            "exito": False,
            "asignacion": None,
            "mensaje": f"No hay vehículos disponibles del tipo requerido ({solicitud.tipo_vehiculo_requerido}). Solicitud reprogramada."
        }

    # c) Ordenar candidatos
    # Conductores por equidad: menor cantidad de asignaciones históricas totales
    conductores_candidatos = conductores_candidatos.annotate(
        total_assignments=models.Count('asignaciones')
    ).order_by('total_assignments', 'apellidos', 'nombres')

    # Vehículos por placa de forma determinista
    vehiculos_candidatos = vehiculos_candidatos.order_by('placa')

    # Recorrer combinaciones para buscar Aprobada
    mejor_comb = None
    veredicto_mejor = None
    detalles_mejor = None

    # Primero buscamos una "Aprobada"
    for conductor in conductores_candidatos:
        for vehiculo in vehiculos_candidatos:
            resultado = validar_asignacion(conductor, vehiculo, generar_alertas=False)
            if resultado['veredicto'] == "Aprobada":
                mejor_comb = (conductor, vehiculo)
                veredicto_mejor = "Aprobada"
                detalles_mejor = resultado
                break
        if mejor_comb:
            break

    # Si no hay "Aprobada", buscamos una "Observada"
    if not mejor_comb:
        for conductor in conductores_candidatos:
            for vehiculo in vehiculos_candidatos:
                resultado = validar_asignacion(conductor, vehiculo, generar_alertas=False)
                if resultado['veredicto'] == "Observada":
                    mejor_comb = (conductor, vehiculo)
                    veredicto_mejor = "Observada"
                    detalles_mejor = resultado
                    break
            if mejor_comb:
                break

    # Si ninguna combinación es Aprobada u Observada
    if not mejor_comb:
        solicitud.estado_solicitud = "Reprogramada"
        solicitud.save()
        return {
            "exito": False,
            "asignacion": None,
            "mensaje": "Todos los recursos disponibles tienen bloqueos documentales. Solicitud reprogramada."
        }

    # d) Se encontró una combinación válida
    conductor_elegido, vehiculo_elegido = mejor_comb

    # Ejecutar de nuevo con generar_alertas=True para que se guarden en DB las alertas de la asignación seleccionada
    resultado_persistido = validar_asignacion(conductor_elegido, vehiculo_elegido, generar_alertas=True)

    # Crear Asignacion
    obs_texto = ", ".join(resultado_persistido.get('observaciones', []))
    asignacion = Asignacion.objects.create(
        solicitud=solicitud,
        conductor=conductor_elegido,
        vehiculo=vehiculo_elegido,
        estado_asignacion=veredicto_mejor,
        observacion=obs_texto
    )

    # Actualizar estados
    conductor_elegido.estado = "Ocupado"
    conductor_elegido.save()

    vehiculo_elegido.estado = "En servicio"
    vehiculo_elegido.save()

    solicitud.estado_solicitud = "Asignada"
    solicitud.save()

    # Generar notificación para el conductor
    mensaje_notif = f"Nuevo servicio asignado: {solicitud.cliente} el {solicitud.fecha_servicio} a las {solicitud.hora_servicio}. Ruta: {solicitud.origen} -> {solicitud.destino}."
    Notificacion.objects.create(
        conductor=conductor_elegido,
        mensaje=mensaje_notif,
        leida=False
    )

    return {
        "exito": True,
        "asignacion": asignacion,
        "mensaje": f"Asignación automática exitosa ({veredicto_mejor}) con Conductor {conductor_elegido} y Vehículo {vehiculo_elegido}."
    }
