import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.db import models

from core.decorators import role_required
from django.views.decorators.http import require_POST
from assignments.forms import ChecklistForm, FinalizarForm, GastoForm, IncidenciaForm
from service_requests.models import SolicitudServicio
from drivers.models import Conductor
from trucks.models import Vehiculo
from assignments.models import Asignacion, ChecklistPreoperacional, GastoServicio, Incidencia, Notificacion
from assignments.services import (
    asignar_automaticamente, asignacion_vigente, completar_servicio, confirmar_asignacion,
    iniciar_ruta, registrar_checklist, reportar_incidencia,
)
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
        ultimo_cambio = rep.cambios.filter(valor_nuevo='Reprogramada').order_by('-fecha').first()
        ultima_asig = Asignacion.objects.filter(solicitud=rep).order_by('-created_at').first()
        if ultimo_cambio and ultimo_cambio.motivo:
            rep.motivo_reprogramacion = ultimo_cambio.motivo
        elif ultima_asig and ultima_asig.observacion:
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
    resultado = asignar_automaticamente(solicitud, usuario=request.user)
    
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
    # Desde la versión 2.0 la disponibilidad se valida por horario (R9), no por estado global.
    conductores = Conductor.objects.filter(estado__in=["Disponible", "Ocupado"]).order_by('apellidos', 'nombres')
    vehiculos = Vehiculo.objects.exclude(estado__in=["En mantenimiento", "De baja"]).order_by('tipo__asientos_referencia', 'placa')

    if request.method == "POST":
        conductor_id = request.POST.get('conductor')
        vehiculo_id = request.POST.get('vehiculo')
        confirmado = request.POST.get('confirmado') == 'true'

        conductor = get_object_or_404(Conductor, driver_id=conductor_id)
        vehiculo = get_object_or_404(Vehiculo, truck_id=vehiculo_id)

        # Advertencia de discrepancia de tipo de vehículo
        tipo_discrepancia = (vehiculo.tipo_id != solicitud.tipo_vehiculo_requerido_id)

        # Validar la asignación (sin persistir alertas todavía si no está confirmado)
        resultado = validar_asignacion(conductor, vehiculo, solicitud=solicitud, generar_alertas=confirmado)

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
            obs_extra = ""
            if tipo_discrepancia:
                obs_extra = f"Vehículo asignado ({vehiculo.tipo}) difiere del requerido ({solicitud.tipo_vehiculo_requerido})"
            confirmar_asignacion(
                solicitud, conductor, vehiculo, resultado,
                observacion_extra=obs_extra, usuario=request.user, manual=True,
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

    asignacion = asignacion_vigente(solicitud)
    if asignacion:
        km_final = request.POST.get('km_final') if request.method == 'POST' else None
        completar_servicio(asignacion, km_final=int(km_final) if km_final and km_final.isdigit() else None, usuario=request.user)
    else:
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

    from assignments.models import ESTADOS_OPERATIVOS_ACTIVOS
    from assignments.validators import LIMITE_HORAS_SEMANA, horas_programadas_semana

    activas = asignaciones.filter(
        estado_asignacion__in=['Aprobada', 'Observada'],
        estado_operativo__in=ESTADOS_OPERATIVOS_ACTIVOS,
    ).prefetch_related('gastos', 'incidencias').order_by('solicitud__fecha_servicio', 'solicitud__hora_servicio')
    historial = asignaciones.exclude(pk__in=activas.values('pk'))

    context = {
        'conductor': conductor,
        'asignaciones': historial,
        'activas': activas,
        'notificaciones': notificaciones,
        'documentos': documentos,
        'today': datetime.date.today(),
        'tipos_incidencia': Incidencia.TIPO_CHOICES,
        'gravedades': Incidencia.GRAVEDAD_CHOICES,
        'conceptos_gasto': GastoServicio.CONCEPTO_CHOICES,
        'horas_semana': horas_programadas_semana(conductor, datetime.date.today()),
        'limite_semana': LIMITE_HORAS_SEMANA,
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


# ---------------------------------------------------------------------------
# Versión 2.0: ejecución del servicio desde el portal del conductor (M3 y M4)
# ---------------------------------------------------------------------------


def _asignacion_del_conductor(request, asignacion_id):
    return get_object_or_404(
        Asignacion.objects.select_related('solicitud', 'vehiculo', 'conductor'),
        assignment_id=asignacion_id,
        conductor=request.user.perfilusuario.conductor,
    )


@login_required
@role_required('Conductor')
def checklist_view(request, asignacion_id):
    asignacion = _asignacion_del_conductor(request, asignacion_id)
    if asignacion.estado_operativo != 'Programado':
        messages.error(request, "El checklist solo se registra cuando el servicio está Programado.")
        return redirect('assignments:mis_servicios')
    existente = ChecklistPreoperacional.objects.filter(asignacion=asignacion).first()
    if request.method == 'POST':
        form = ChecklistForm(request.POST, instance=existente)
        if form.is_valid():
            checklist = registrar_checklist(asignacion, form.save(commit=False))
            if checklist.aprobado:
                messages.success(request, "Checklist aprobado. El servicio está listo para salir.")
            else:
                messages.error(
                    request,
                    f"Checklist no aprobado: {checklist.motivo_rechazo}. La unidad no puede salir; "
                    "se avisó a operaciones. Corrija y vuelva a registrar el checklist.",
                )
            return redirect('assignments:mis_servicios')
    else:
        form = ChecklistForm(instance=existente, initial={'km_inicial': asignacion.km_inicial})
    return render(request, 'assignments/checklist.html', {
        'asignacion': asignacion,
        'form': form,
        'criticos': ChecklistPreoperacional.PUNTOS_CRITICOS,
        'horas_minimas': ChecklistPreoperacional.HORAS_SUENO_MINIMAS,
    })


@login_required
@role_required('Conductor')
@require_POST
def iniciar_ruta_view(request, asignacion_id):
    asignacion = _asignacion_del_conductor(request, asignacion_id)
    if asignacion.estado_operativo != 'Listo para salir':
        messages.error(request, "Primero registre y apruebe el checklist preoperacional.")
    else:
        iniciar_ruta(asignacion, request.user)
        messages.success(request, "Salida registrada. Servicio en ruta.")
    return redirect('assignments:mis_servicios')


@login_required
@role_required('Conductor')
@require_POST
def incidencia_view(request, asignacion_id):
    asignacion = _asignacion_del_conductor(request, asignacion_id)
    form = IncidenciaForm(request.POST)
    if asignacion.estado_operativo not in ('Listo para salir', 'En ruta'):
        messages.error(request, "Solo se reportan incidencias de servicios listos o en ruta.")
    elif form.is_valid():
        incidencia = reportar_incidencia(asignacion, form.save(commit=False), request.user)
        if incidencia.gravedad == 'Alta':
            messages.warning(request, "Incidencia grave registrada. Operaciones reasignará el servicio.")
        else:
            messages.success(request, "Incidencia registrada. Operaciones fue notificado.")
    else:
        messages.error(request, "Complete el tipo y la descripción de la incidencia.")
    return redirect('assignments:mis_servicios')


@login_required
@role_required('Conductor')
@require_POST
def gasto_view(request, asignacion_id):
    asignacion = _asignacion_del_conductor(request, asignacion_id)
    form = GastoForm(request.POST)
    if asignacion.estado_operativo not in ('Listo para salir', 'En ruta', 'Completado'):
        messages.error(request, "No se pueden registrar gastos en este servicio.")
    elif form.is_valid():
        gasto = form.save(commit=False)
        gasto.asignacion = asignacion
        gasto.save()
        messages.success(request, f"Gasto registrado: {gasto.concepto} S/ {gasto.monto}.")
    else:
        messages.error(request, "Revise el concepto y el monto del gasto.")
    return redirect('assignments:mis_servicios')


@login_required
@role_required('Conductor')
@require_POST
def finalizar_view(request, asignacion_id):
    asignacion = _asignacion_del_conductor(request, asignacion_id)
    form = FinalizarForm(request.POST, km_inicial=asignacion.km_inicial)
    if asignacion.estado_operativo != 'En ruta':
        messages.error(request, "Solo se finalizan servicios en ruta.")
    elif form.is_valid():
        completar_servicio(asignacion, km_final=form.cleaned_data['km_final'], usuario=request.user)
        messages.success(request, "Servicio finalizado. Gracias.")
    else:
        messages.error(request, " ".join(e for errs in form.errors.values() for e in errs))
    return redirect('assignments:mis_servicios')


def _asignaciones_en_rango(inicio, fin):
    return (
        Asignacion.objects.filter(
            solicitud__fecha_servicio__range=(inicio, fin),
            estado_asignacion__in=['Aprobada', 'Observada'],
        )
        .exclude(estado_operativo='Cancelado')
        .select_related('solicitud', 'conductor', 'vehiculo')
        .order_by('solicitud__fecha_servicio', 'solicitud__hora_servicio')
    )


@login_required
@role_required('Administrador de operaciones', 'Supervisor', 'Gerencia')
def programacion_semanal(request):
    """Programación de servicios (M5) en vista semanal o mensual."""
    if request.GET.get('vista') == 'mes':
        return _programacion_mensual(request)

    from assignments.validators import LIMITE_HORAS_SEMANA, horas_programadas_semana

    try:
        base = datetime.date.fromisoformat(request.GET.get('semana', ''))
    except ValueError:
        base = datetime.date.today()
    lunes = base - datetime.timedelta(days=base.weekday())
    dias = [lunes + datetime.timedelta(days=i) for i in range(7)]
    por_dia = {d: [] for d in dias}
    for a in _asignaciones_en_rango(dias[0], dias[-1]):
        por_dia[a.solicitud.fecha_servicio].append(a)
    sin_asignar = SolicitudServicio.objects.filter(
        fecha_servicio__range=(dias[0], dias[-1]), estado_solicitud__in=['Pendiente', 'Reprogramada'],
    ).order_by('fecha_servicio', 'hora_servicio')
    carga = []
    for c in Conductor.objects.exclude(estado='De baja').order_by('apellidos'):
        horas = horas_programadas_semana(c, lunes)
        carga.append({'conductor': c, 'horas': horas, 'porcentaje': min(100, round(horas * 100 / LIMITE_HORAS_SEMANA))})
    carga.sort(key=lambda x: -x['horas'])
    return render(request, 'assignments/programacion.html', {
        'vista': 'semana',
        'dias': [(d, por_dia[d]) for d in dias],
        'lunes': lunes,
        'domingo': dias[-1],
        'anterior': (lunes - datetime.timedelta(days=7)).isoformat(),
        'siguiente': (lunes + datetime.timedelta(days=7)).isoformat(),
        'mes_actual': lunes.strftime('%Y-%m'),
        'sin_asignar': sin_asignar,
        'carga': carga,
        'limite': LIMITE_HORAS_SEMANA,
        'today': datetime.date.today(),
    })


def _programacion_mensual(request):
    """Calendario del mes completo: servicios por día, solicitudes sin asignar y horas por conductor."""
    import calendar

    hoy = datetime.date.today()
    try:
        anio, mes = (int(x) for x in request.GET.get('mes', '').split('-'))
        primero = datetime.date(anio, mes, 1)
    except (ValueError, TypeError):
        primero = hoy.replace(day=1)
    ultimo = primero.replace(day=calendar.monthrange(primero.year, primero.month)[1])
    inicio = primero - datetime.timedelta(days=primero.weekday())
    fin = ultimo + datetime.timedelta(days=6 - ultimo.weekday())

    por_dia = {}
    for a in _asignaciones_en_rango(inicio, fin):
        por_dia.setdefault(a.solicitud.fecha_servicio, []).append(a)
    pendientes_por_dia = {}
    sin_asignar = SolicitudServicio.objects.filter(
        fecha_servicio__range=(primero, ultimo), estado_solicitud__in=['Pendiente', 'Reprogramada'],
    ).order_by('fecha_servicio', 'hora_servicio')
    for s in sin_asignar:
        pendientes_por_dia[s.fecha_servicio] = pendientes_por_dia.get(s.fecha_servicio, 0) + 1

    MAX_VISIBLES = 3
    semanas, fecha = [], inicio
    while fecha <= fin:
        semana = []
        for _ in range(7):
            servicios = por_dia.get(fecha, [])
            semana.append({
                'fecha': fecha,
                'en_mes': fecha.month == primero.month,
                'servicios': servicios[:MAX_VISIBLES],
                'total': len(servicios),
                'ocultos': max(0, len(servicios) - MAX_VISIBLES),
                'pendientes': pendientes_por_dia.get(fecha, 0),
                'lunes': (fecha - datetime.timedelta(days=fecha.weekday())).isoformat(),
            })
            fecha += datetime.timedelta(days=1)
        semanas.append(semana)

    del_mes = [a for f, lista in por_dia.items() if primero <= f <= ultimo for a in lista]
    horas_conductor = {}
    for a in del_mes:
        clave = a.conductor_id
        if clave not in horas_conductor:
            horas_conductor[clave] = {'conductor': a.conductor, 'horas': 0, 'servicios': 0}
        horas_conductor[clave]['horas'] += a.solicitud.duracion_horas or 0
        horas_conductor[clave]['servicios'] += 1
    carga = sorted(horas_conductor.values(), key=lambda x: -x['horas'])
    maximo = max((c['horas'] for c in carga), default=0) or 1
    for c in carga:
        c['porcentaje'] = round(c['horas'] * 100 / maximo)

    dias_activos = [d for d in por_dia if primero <= d <= ultimo]
    dia_pico = max(dias_activos, key=lambda d: len(por_dia[d]), default=None)
    mes_anterior = (primero - datetime.timedelta(days=1)).replace(day=1)
    mes_siguiente = ultimo + datetime.timedelta(days=1)
    return render(request, 'assignments/programacion.html', {
        'vista': 'mes',
        'primero': primero,
        'semanas': semanas,
        'anterior': mes_anterior.strftime('%Y-%m'),
        'siguiente': mes_siguiente.strftime('%Y-%m'),
        'semana_ref': (primero if not (primero <= hoy <= ultimo) else hoy).isoformat(),
        'resumen': {
            'servicios': len(del_mes),
            'completados': sum(1 for a in del_mes if a.estado_operativo == 'Completado'),
            'por_asignar': sin_asignar.count(),
            'horas': sum(a.solicitud.duracion_horas or 0 for a in del_mes),
            'dia_pico': dia_pico,
            'dia_pico_total': len(por_dia[dia_pico]) if dia_pico else 0,
        },
        'sin_asignar': sin_asignar,
        'carga': carga,
        'today': hoy,
    })
