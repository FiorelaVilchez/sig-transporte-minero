from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from core.decorators import role_required
from .models import SolicitudServicio
from .forms import SolicitudServicioForm
from .services import CAMPOS_DE_PROGRAMACION, registrar_cambio

@role_required('Administrador de operaciones', 'Supervisor', 'Gerencia')
def solicitud_list(request):
    solicitudes_list = SolicitudServicio.objects.all().order_by('fecha_servicio', 'hora_servicio')
    
    # Filtros
    estado_filtro = request.GET.get('estado', '')
    prioridad_filtro = request.GET.get('prioridad', '')
    
    if estado_filtro:
        solicitudes_list = solicitudes_list.filter(estado_solicitud=estado_filtro)
    if prioridad_filtro:
        solicitudes_list = solicitudes_list.filter(prioridad=prioridad_filtro)
        
    # Paginación
    paginator = Paginator(solicitudes_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    user_rol = request.user.perfilusuario.rol
    is_admin = user_rol == 'Administrador de operaciones'
    
    return render(request, 'service_requests/solicitud_list.html', {
        'page_obj': page_obj,
        'estado_filtro': estado_filtro,
        'prioridad_filtro': prioridad_filtro,
        'estado_choices': SolicitudServicio.ESTADO_SOLICITUD_CHOICES,
        'prioridad_choices': SolicitudServicio.PRIORIDAD_CHOICES,
        'is_admin': is_admin,
    })

@role_required('Administrador de operaciones')
def solicitud_create(request):
    if request.method == 'POST':
        form = SolicitudServicioForm(request.POST)
        if form.is_valid():
            solicitud = form.save()
            registrar_cambio(solicitud, request.user, 'registro', '', solicitud.estado_solicitud, 'Solicitud registrada')
            messages.success(request, f"Solicitud #{solicitud.request_id} registrada correctamente en estado 'Pendiente'.")
            return redirect('service_requests:solicitud_list')
    else:
        form = SolicitudServicioForm(initial={'estado_solicitud': 'Pendiente'})
        
    return render(request, 'service_requests/solicitud_form.html', {
        'form': form,
        'titulo': 'Registrar Solicitud de Servicio',
    })

@role_required('Administrador de operaciones')
def solicitud_update(request, pk):
    solicitud = get_object_or_404(SolicitudServicio, pk=pk)
    if request.method == 'POST':
        antes = {campo: getattr(SolicitudServicio.objects.get(pk=pk), campo) for campo in SolicitudServicioForm.Meta.fields}
        form = SolicitudServicioForm(request.POST, instance=solicitud)
        if form.is_valid():
            solicitud = form.save()
            motivo = form.cleaned_data.get('motivo_cambio', '')
            for campo in form.changed_data:
                if campo in antes:
                    registrar_cambio(
                        solicitud, request.user, SolicitudServicio._meta.get_field(campo).verbose_name,
                        antes[campo], getattr(solicitud, campo), motivo,
                    )
            messages.success(request, f"Solicitud #{solicitud.request_id} actualizada correctamente.")
            if solicitud.estado_solicitud == 'Asignada' and any(c in CAMPOS_DE_PROGRAMACION for c in form.changed_data):
                from assignments.services import revalidar_por_cambio
                revision = revalidar_por_cambio(solicitud, request.user, motivo)
                if revision and revision['cancelada']:
                    messages.warning(
                        request,
                        "La asignación ya no cumple las reglas con los nuevos datos y fue cancelada; "
                        "la solicitud quedó Reprogramada y se avisó al conductor. Motivo: "
                        + "; ".join(revision['bloqueos']),
                    )
                elif revision:
                    messages.info(request, "La asignación sigue siendo válida. Se notificó el cambio al conductor.")
            return redirect('service_requests:solicitud_detail', pk=solicitud.pk)
    else:
        form = SolicitudServicioForm(instance=solicitud)
        
    return render(request, 'service_requests/solicitud_form.html', {
        'form': form,
        'titulo': f"Editar Solicitud #{solicitud.request_id}",
    })


@role_required('Administrador de operaciones', 'Supervisor', 'Gerencia', 'Finanzas')
def solicitud_detail(request, pk):
    """Ficha de la solicitud con su asignación, checklist, incidencias, gastos y bitácora (M2)."""
    from assignments.models import Asignacion

    solicitud = get_object_or_404(SolicitudServicio, pk=pk)
    asignaciones = (
        Asignacion.objects.filter(solicitud=solicitud)
        .select_related('conductor', 'vehiculo')
        .prefetch_related('incidencias', 'gastos')
        .order_by('-fecha_asignacion')
    )
    return render(request, 'service_requests/solicitud_detail.html', {
        'solicitud': solicitud,
        'asignaciones': asignaciones,
        'cambios': solicitud.cambios.select_related('usuario'),
        'valorizacion': getattr(solicitud, 'valorizacion', None),
        'is_admin': request.user.perfilusuario.rol == 'Administrador de operaciones',
    })


@role_required('Administrador de operaciones')
def solicitud_cancelar(request, pk):
    """Cancela la solicitud registrando el motivo y libera la asignación vigente."""
    from assignments.services import asignacion_vigente

    solicitud = get_object_or_404(SolicitudServicio, pk=pk)
    if request.method == 'POST':
        motivo = (request.POST.get('motivo') or '').strip()
        if not motivo:
            messages.error(request, "Indique el motivo de la cancelación.")
        elif solicitud.estado_solicitud in ('Completada', 'Cancelada'):
            messages.error(request, "La solicitud ya está cerrada.")
        else:
            asignacion = asignacion_vigente(solicitud)
            if asignacion and asignacion.estado_operativo == 'En ruta':
                messages.error(request, "El servicio está en ruta; registre una incidencia en lugar de cancelarlo.")
                return redirect('service_requests:solicitud_detail', pk=pk)
            if asignacion:
                asignacion.estado_operativo = 'Cancelado'
                asignacion.save()
                from assignments.models import Notificacion
                Notificacion.objects.create(
                    conductor=asignacion.conductor,
                    mensaje=f"Se canceló el servicio #{solicitud.request_id} ({solicitud.cliente}). Motivo: {motivo}"[:255],
                )
            anterior = solicitud.estado_solicitud
            solicitud.estado_solicitud = 'Cancelada'
            solicitud.save()
            registrar_cambio(solicitud, request.user, 'Estado de Solicitud', anterior, 'Cancelada', motivo)
            messages.success(request, f"Solicitud #{solicitud.request_id} cancelada.")
    return redirect('service_requests:solicitud_detail', pk=pk)
