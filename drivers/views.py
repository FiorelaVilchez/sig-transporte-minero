from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q, ProtectedError
from django.contrib import messages
from django.core.paginator import Paginator
from core.decorators import role_required
from .models import Conductor
from .forms import ConductorForm

@role_required('Administrador de operaciones', 'Supervisor')
def conductor_list(request):
    conductores_list = Conductor.objects.all()
    
    # Buscador
    query = request.GET.get('q', '')
    if query:
        conductores_list = conductores_list.filter(
            Q(nombres__icontains=query) |
            Q(apellidos__icontains=query) |
            Q(dni__icontains=query)
        )
        
    # Filtro por estado
    estado_filtro = request.GET.get('estado', '')
    if estado_filtro:
        conductores_list = conductores_list.filter(estado=estado_filtro)
        
    # Paginación
    paginator = Paginator(conductores_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Roles y permisos en template
    user_rol = request.user.perfilusuario.rol
    is_admin = user_rol == 'Administrador de operaciones'
    
    return render(request, 'drivers/conductor_list.html', {
        'page_obj': page_obj,
        'query': query,
        'estado_filtro': estado_filtro,
        'estado_choices': Conductor.ESTADO_CHOICES,
        'is_admin': is_admin,
    })

@role_required('Administrador de operaciones', 'Supervisor')
def conductor_detail(request, pk):
    conductor = get_object_or_404(Conductor, pk=pk)
    documentos = conductor.documentos.all()
    user_rol = request.user.perfilusuario.rol
    is_admin = user_rol == 'Administrador de operaciones'
    
    return render(request, 'drivers/conductor_detail.html', {
        'conductor': conductor,
        'documentos': documentos,
        'is_admin': is_admin,
    })

@role_required('Administrador de operaciones')
def conductor_create(request):
    if request.method == 'POST':
        form = ConductorForm(request.POST)
        if form.is_valid():
            conductor = form.save()
            messages.success(request, f"Conductor {conductor.nombres} {conductor.apellidos} registrado correctamente.")
            return redirect('drivers:conductor_list')
    else:
        form = ConductorForm()
        
    return render(request, 'drivers/conductor_form.html', {
        'form': form,
        'titulo': 'Registrar Conductor',
    })

@role_required('Administrador de operaciones')
def conductor_update(request, pk):
    conductor = get_object_or_404(Conductor, pk=pk)
    if request.method == 'POST':
        form = ConductorForm(request.POST, instance=conductor)
        if form.is_valid():
            form.save()
            messages.success(request, f"Conductor {conductor.nombres} {conductor.apellidos} actualizado correctamente.")
            return redirect('drivers:conductor_list')
    else:
        form = ConductorForm(instance=conductor)
        
    return render(request, 'drivers/conductor_form.html', {
        'form': form,
        'titulo': f"Editar Conductor: {conductor.nombres} {conductor.apellidos}",
    })

@role_required('Administrador de operaciones')
def conductor_dar_baja(request, pk):
    if request.method == 'POST':
        conductor = get_object_or_404(Conductor, pk=pk)
        conductor.estado = 'De baja'
        conductor.save(update_fields=['estado', 'updated_at'])
        messages.success(request, f"El conductor {conductor.nombres} {conductor.apellidos} ha sido dado de baja correctamente.")
    return redirect('drivers:conductor_list')

@role_required('Administrador de operaciones')
def conductor_delete(request, pk):
    if request.method == 'POST':
        conductor = get_object_or_404(Conductor, pk=pk)
        nombre_completo = f"{conductor.nombres} {conductor.apellidos}"
        try:
            conductor.delete()
            messages.success(request, f"Conductor {nombre_completo} eliminado físicamente de la base de datos.")
        except ProtectedError:
            messages.error(request, "Este conductor tiene historial de asignaciones, no se puede eliminar. Puedes darlo de baja.")
            return redirect('drivers:conductor_detail', pk=pk)
    return redirect('drivers:conductor_list')
