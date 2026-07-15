from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q, ProtectedError
from django.contrib import messages
from django.core.paginator import Paginator
from core.decorators import role_required
from .models import Vehiculo
from .forms import VehiculoForm

@role_required('Administrador de operaciones', 'Supervisor')
def  vehiculo_list(request):
    vehiculos_list = Vehiculo.objects.all()
    
    # Buscador
    query = request.GET.get('q', '')
    if query:
        vehiculos_list = vehiculos_list.filter(
            Q(placa__icontains=query) |
            Q(tipo__icontains=query)
        )
        
    # Filtro por estado
    estado_filtro = request.GET.get('estado', '')
    if estado_filtro:
        vehiculos_list = vehiculos_list.filter(estado=estado_filtro)
        
    # Paginación
    paginator = Paginator(vehiculos_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Permisos
    user_rol = request.user.perfilusuario.rol
    is_admin = user_rol == 'Administrador de operaciones'
    
    return render(request, 'trucks/vehiculo_list.html', {
        'page_obj': page_obj,
        'query': query,
        'estado_filtro': estado_filtro,
        'estado_choices': Vehiculo.ESTADO_CHOICES,
        'is_admin': is_admin,
    })

@role_required('Administrador de operaciones', 'Supervisor')
def vehiculo_detail(request, pk):
    vehiculo = get_object_or_404(Vehiculo, pk=pk)
    documentos = vehiculo.documentos.all()
    user_rol = request.user.perfilusuario.rol
    is_admin = user_rol == 'Administrador de operaciones'
    
    return render(request, 'trucks/vehiculo_detail.html', {
        'vehiculo': vehiculo,
        'documentos': documentos,
        'is_admin': is_admin,
    })

@role_required('Administrador de operaciones')
def vehiculo_create(request):
    if request.method == 'POST':
        form = VehiculoForm(request.POST)
        if form.is_valid():
            vehiculo = form.save()
            messages.success(request, f"Vehículo con placa {vehiculo.placa} registrado correctamente.")
            return redirect('trucks:vehiculo_list')
    else:
        form = VehiculoForm()
        
    return render(request, 'trucks/vehiculo_form.html', {
        'form': form,
        'titulo': 'Registrar Vehículo',
    })

@role_required('Administrador de operaciones')
def vehiculo_update(request, pk):
    vehiculo = get_object_or_404(Vehiculo, pk=pk)
    if request.method == 'POST':
        form = VehiculoForm(request.POST, instance=vehiculo)
        if form.is_valid():
            form.save()
            messages.success(request, f"Vehículo con placa {vehiculo.placa} actualizado correctamente.")
            return redirect('trucks:vehiculo_list')
    else:
        form = VehiculoForm(instance=vehiculo)
        
    return render(request, 'trucks/vehiculo_form.html', {
        'form': form,
        'titulo': f"Editar Vehículo Placa: {vehiculo.placa}",
    })

@role_required('Administrador de operaciones')
def vehiculo_dar_baja(request, pk):
    if request.method == 'POST':
        vehiculo = get_object_or_404(Vehiculo, pk=pk)
        vehiculo.estado = 'De baja'
        vehiculo.save(update_fields=['estado', 'updated_at'])
        messages.success(request, f"El vehículo con placa {vehiculo.placa} ha sido dado de baja correctamente.")
    return redirect('trucks:vehiculo_list')

@role_required('Administrador de operaciones')
def vehiculo_delete(request, pk):
    if request.method == 'POST':
        vehiculo = get_object_or_404(Vehiculo, pk=pk)
        placa = vehiculo.placa
        try:
            vehiculo.delete()
            messages.success(request, f"Vehículo placa {placa} eliminado físicamente de la base de datos.")
        except ProtectedError:
            messages.error(request, "Este vehículo tiene historial de asignaciones, no se puede eliminar. Puedes darlo de baja.")
            return redirect('trucks:vehiculo_detail', pk=pk)
    return redirect('trucks:vehiculo_list')
