import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.db import models

from core.decorators import role_required
from service_requests.models import SolicitudServicio
from drivers.models import Conductor
from trucks.models import Vehiculo
from assignments.models import Asignacion, Notificacion
from assignments.services import asignar_automaticamente
from assignments.validators import validar_asignacion

@login_required
@role_required('Administrador de operaciones', 'Supervisor', 'Gerencia')
def solicitudes_pendientes_list(request):
    """
    Lista las solicitudes pendientes y reprogramadas, y el historial de asignaciones.
    """
    rol_usuario = request.user.perfilusuario.rol
    es_admin = (rol_usuario == 'Administrador de operaciones')

    # Ordenar por prioridad (Alta primero, Media, Baja) y luego fecha de servicio ascendente
    orden_prioridad = models.Case(
        models.When(prioridad='Alta', then=0),
        models.When(prioridad='Media', then=1),
        models.When(prioridad='Baja', then=2),
        default=3
    )
    
    pendientes = SolicitudServicio.objects.filter(
        estado_solicitud='Pendiente'
    ).order_by(orden_prioridad, 'fecha_servicio', 'hora_servicio')

    reprogramadas = SolicitudServicio.objects.filter(
        estado_solicitud='Reprogramada'
    ).order_by(orden_prioridad, 'fecha_servicio', 'hora_servicio')

    # Historial de asignaciones filtrable
    filtro_estado = request.GET.get('estado_asignacion', '')
    historial = Asignacion.objects.all()
    if filtro_estado:
        historial = historial.filter(estado_asignacion=filtro_estado)
    historial = historial.select_related('solicitud', 'conductor', 'vehiculo')

    # Agregar información del estado actual de reprogramación (razones)
    # Para simplificar en este prototipo, si la solicitud está reprogramada
    # mostramos el mensaje de la última asignación rechazada o un mensaje por defecto.
    for rep in reprogramadas:
        ultima_asig = Asignacion.objects.filter(solicitud=rep).order_by('-created_at').first()
        if ultima_asig and ultima_asig.observacion:
            rep.motivo_reprogramacion = ultima_asig.observacion
        else:
            rep.motivo_reprogramacion = "Recursos no disponibles (conductores/vehículos ocupados o incompatibles)."

    context = {
        'pendientes': pendientes,
        'reprogramadas': reprogramadas,
        'historial': historial,
        'filtro_estado': filtro_estado,
        'es_admin': es_admin,
        'today': datetime.date.today(),
    }
    return render(request, 'assignments/solicitudes_pendientes.html', context)


@login_required
@role_required('Administrador de operaciones')
def asignar_automatica_view(request, solicitud_id):
    """
    Vista que ejecuta el motor de asignación automática.
    """
    solicitud = get_object_or_404(SolicitudServicio, request_id=solicitud_id)
    resultado = asignar_automaticamente(solicitud)
    
    if resultado['exito']:
        messages.success(request, resultado['mensaje'])
    else:
        messages.warning(request, resultado['mensaje'])
        
    return redirect('assignments:solicitudes_pendientes')


@login_required
@role_required('Administrador de operaciones')
def asignar_manual_view(request, solicitud_id):
    """
    Formulario y confirmación de asignación manual.
    """
    solicitud = get_object_or_404(SolicitudServicio, request_id=solicitud_id)
    conductores = Conductor.objects.filter(estado="Disponible").order_by('apellidos', 'nombres')
    vehiculos = Vehiculo.objects.filter(estado="Disponible").order_by('placa')

    if request.method == "POST":
        conductor_id = request.POST.get('conductor')
        vehiculo_id = request.POST.get('vehiculo')
        confirmado = request.POST.get('confirmado') == 'true'

        conductor = get_object_or_404(Conductor, driver_id=conductor_id)
        vehiculo = get_object_or_404(Vehiculo, truck_id=vehiculo_id)

        # Advertencia de discrepancia de tipo de vehículo
        tipo_discrepancia = (vehiculo.tipo != solicitud.tipo_vehiculo_requerido)

        # Validar la asignación (sin persistir alertas todavía si no está confirmado)
        resultado = validar_asignacion(conductor, vehiculo, generar_alertas=confirmado)

        if resultado['veredicto'] == "Rechazada":
            # Si es rechazada, no se permite confirmar, se vuelve al formulario
            for bloqueo in resultado['bloqueos']:
                messages.error(request, f"Bloqueo: {bloqueo}")
            return render(request, 'assignments/asignacion_manual.html', {
                'solicitud': solicitud,
                'conductores': conductores,
                'vehiculos': vehiculos,
                'conductor_seleccionado': conductor,
                'vehiculo_seleccionado': vehiculo,
                'error_validacion': True,
                'resultado': resultado,
            })

        if confirmado:
            # Si ya se confirmó y es Aprobada u Observada
            obs_texto = ", ".join(resultado.get('observaciones', []))
            if tipo_discrepancia:
                if obs_texto:
                    obs_texto += ", "
                obs_texto += f"Vehículo asignado ({vehiculo.tipo}) difiere del requerido ({solicitud.tipo_vehiculo_requerido})"

            asignacion = Asignacion.objects.create(
                solicitud=solicitud,
                conductor=conductor,
                vehiculo=vehiculo,
                estado_asignacion=resultado['veredicto'],
                observacion=obs_texto
            )

            # Cambiar estados
            conductor.estado = "Ocupado"
            conductor.save()

            vehiculo.estado = "En servicio"
            vehiculo.save()

            solicitud.estado_solicitud = "Asignada"
            solicitud.save()

            # Notificar conductor
            mensaje_notif = f"Manual: Nuevo servicio asignado: {solicitud.cliente} el {solicitud.fecha_servicio} a las {solicitud.hora_servicio}. Ruta: {solicitud.origen} -> {solicitud.destino}."
            Notificacion.objects.create(
                conductor=conductor,
                mensaje=mensaje_notif,
                leida=False
            )

            messages.success(request, f"Asignación manual confirmada con éxito. Veredicto: {resultado['veredicto']}.")
            return redirect('assignments:solicitudes_pendientes')
        
        else:
            # Mostrar la pantalla de confirmación intermedia
            return render(request, 'assignments/asignacion_manual.html', {
                'solicitud': solicitud,
                'conductor_seleccionado': conductor,
                'vehiculo_seleccionado': vehiculo,
                'confirmar_paso': True,
                'tipo_discrepancia': tipo_discrepancia,
                'resultado': resultado,
            })

    return render(request, 'assignments/asignacion_manual.html', {
        'solicitud': solicitud,
        'conductores': conductores,
        'vehiculos': vehiculos,
    })


@login_required
@role_required('Administrador de operaciones')
def completar_servicio_view(request, solicitud_id):
    """
    Marca un servicio como completado, liberando al conductor y vehículo.
    """
    solicitud = get_object_or_404(SolicitudServicio, request_id=solicitud_id)
    if solicitud.estado_solicitud != "Asignada":
        messages.error(request, "Solo se pueden completar servicios en estado 'Asignada'.")
        return redirect('assignments:solicitudes_pendientes')

    # Buscar la asignación activa aprobada/observada
    asignacion = Asignacion.objects.filter(
        solicitud=solicitud, 
        estado_asignacion__in=['Aprobada', 'Observada']
    ).first()

    if asignacion:
        if asignacion.conductor:
            asignacion.conductor.estado = "Disponible"
            asignacion.conductor.save()
        if asignacion.vehiculo:
            asignacion.vehiculo.estado = "Disponible"
            asignacion.vehiculo.save()

    solicitud.estado_solicitud = "Completada"
    solicitud.save()

    messages.success(request, f"Servicio completado. Conductor y vehículo liberados con éxito.")
    return redirect('assignments:solicitudes_pendientes')


@login_required
@role_required('Conductor')
def mis_servicios_conductor(request):
    """
    Portal del Conductor: Muestra sus servicios asignados, notificaciones y estado documental.
    """
    perfil = request.user.perfilusuario
    conductor = perfil.conductor

    if not conductor:
        return render(request, 'assignments/mis_servicios.html', {
            'error_vinculo': True
        })

    # Asignaciones del conductor
    asignaciones = Asignacion.objects.filter(
        conductor=conductor
    ).select_related('solicitud', 'vehiculo').order_by('-fecha_asignacion')

    # Notificaciones del conductor
    notificaciones = Notificacion.objects.filter(conductor=conductor)

    # Documentos del conductor
    documentos = conductor.documentos.all().order_by('-fecha_vencimiento')

    context = {
        'conductor': conductor,
        'asignaciones': asignaciones,
        'notificaciones': notificaciones,
        'documentos': documentos,
        'today': datetime.date.today(),
    }
    return render(request, 'assignments/mis_servicios.html', context)


@login_required
@role_required('Conductor')
def marcar_notificacion_leida(request, notificacion_id):
    """
    Marca una notificación específica como leída.
    """
    perfil = request.user.perfilusuario
    notificacion = get_object_or_404(Notificacion, id=notificacion_id, conductor=perfil.conductor)
    notificacion.leida = True
    notificacion.save()
    return redirect('assignments:mis_servicios')
