from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from core.decorators import role_required
from .models import SolicitudServicio
from .forms import SolicitudServicioForm

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
        form = SolicitudServicioForm(request.POST, instance=solicitud)
        if form.is_valid():
            form.save()
            messages.success(request, f"Solicitud #{solicitud.request_id} actualizada correctamente.")
            return redirect('service_requests:solicitud_list')
    else:
        form = SolicitudServicioForm(instance=solicitud)
        
    return render(request, 'service_requests/solicitud_form.html', {
        'form': form,
        'titulo': f"Editar Solicitud #{solicitud.request_id}",
    })
