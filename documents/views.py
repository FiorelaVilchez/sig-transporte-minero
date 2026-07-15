from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from core.decorators import role_required
from .models import DocumentoConductor, DocumentoVehiculo
from .forms import DocumentoConductorForm, DocumentoVehiculoForm
from drivers.models import Conductor
from trucks.models import Vehiculo

@role_required('Administrador de operaciones', 'Supervisor')
def document_list(request):
    doc_cond_list = DocumentoConductor.objects.all().select_related('conductor')
    doc_veh_list = DocumentoVehiculo.objects.all().select_related('vehiculo')
    
    # Filtros
    estado_filtro = request.GET.get('estado', '')
    tipo_filtro = request.GET.get('tipo', '')
    search_query = request.GET.get('q', '')
    
    if estado_filtro:
        doc_cond_list = doc_cond_list.filter(estado_documento=estado_filtro)
        doc_veh_list = doc_veh_list.filter(estado_documento=estado_filtro)
        
    if tipo_filtro:
        doc_cond_list = doc_cond_list.filter(tipo_documento=tipo_filtro)
        doc_veh_list = doc_veh_list.filter(tipo_documento=tipo_filtro)
        
    if search_query:
        doc_cond_list = doc_cond_list.filter(
            conductor__nombres__icontains=search_query) | doc_cond_list.filter(
            conductor__apellidos__icontains=search_query) | doc_cond_list.filter(
            conductor__dni__icontains=search_query
        )
        doc_veh_list = doc_veh_list.filter(vehiculo__placa__icontains=search_query)
        
    # Paginación para conductores
    paginator_cond = Paginator(doc_cond_list, 10)
    page_cond = request.GET.get('page_cond')
    page_obj_cond = paginator_cond.get_page(page_cond)
    
    # Paginación para vehículos
    paginator_veh = Paginator(doc_veh_list, 10)
    page_veh = request.GET.get('page_veh')
    page_obj_veh = paginator_veh.get_page(page_veh)
    
    # Choices de tipo para filtros (unificados o separados)
    tipo_cond_choices = DocumentoConductor.TIPO_DOCUMENTO_CHOICES
    tipo_veh_choices = DocumentoVehiculo.TIPO_DOCUMENTO_CHOICES
    
    # Para determinar qué tab se activa por defecto si se paginó
    active_tab = 'conductores'
    if page_veh:
        active_tab = 'vehiculos'
        
    return render(request, 'documents/document_list.html', {
        'page_obj_cond': page_obj_cond,
        'page_obj_veh': page_obj_veh,
        'estado_filtro': estado_filtro,
        'tipo_filtro': tipo_filtro,
        'search_query': search_query,
        'tipo_cond_choices': tipo_cond_choices,
        'tipo_veh_choices': tipo_veh_choices,
        'active_tab': active_tab,
    })

@role_required('Administrador de operaciones', 'Supervisor')
def documento_conductor_create(request):
    conductor_id = request.GET.get('conductor')
    conductor_obj = None
    if conductor_id:
        conductor_obj = get_object_or_404(Conductor, pk=conductor_id)
        
    if request.method == 'POST':
        form = DocumentoConductorForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save()
            messages.success(request, f"Documento '{doc.tipo_documento}' cargado con éxito para el conductor {doc.conductor.nombres} {doc.conductor.apellidos}.")
            if conductor_id:
                return redirect('drivers:conductor_detail', pk=conductor_id)
            return redirect('documents:document_list')
    else:
        initial = {}
        if conductor_obj:
            initial['conductor'] = conductor_obj
        form = DocumentoConductorForm(initial=initial)
        
    return render(request, 'documents/documento_form.html', {
        'form': form,
        'titulo': 'Agregar Documento de Conductor',
        'conductor_obj': conductor_obj,
    })

@role_required('Administrador de operaciones', 'Supervisor')
def documento_conductor_update(request, pk):
    doc = get_object_or_404(DocumentoConductor, pk=pk)
    if request.method == 'POST':
        form = DocumentoConductorForm(request.POST, request.FILES, instance=doc)
        if form.is_valid():
            form.save()
            messages.success(request, f"Documento '{doc.tipo_documento}' del conductor {doc.conductor.nombres} {doc.conductor.apellidos} renovado/actualizado correctamente.")
            return redirect('drivers:conductor_detail', pk=doc.conductor.pk)
    else:
        form = DocumentoConductorForm(instance=doc)
        
    return render(request, 'documents/documento_form.html', {
        'form': form,
        'titulo': f"Renovar/Editar: {doc.tipo_documento} de {doc.conductor.nombres} {doc.conductor.apellidos}",
    })

@role_required('Administrador de operaciones', 'Supervisor')
def documento_vehiculo_create(request):
    vehiculo_id = request.GET.get('vehiculo')
    vehiculo_obj = None
    if vehiculo_id:
        vehiculo_obj = get_object_or_404(Vehiculo, pk=vehiculo_id)
        
    if request.method == 'POST':
        form = DocumentoVehiculoForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save()
            messages.success(request, f"Documento '{doc.tipo_documento}' cargado con éxito para el vehículo {doc.vehiculo.placa}.")
            if vehiculo_id:
                return redirect('trucks:vehiculo_detail', pk=vehiculo_id)
            return redirect('documents:document_list')
    else:
        initial = {}
        if vehiculo_obj:
            initial['vehiculo'] = vehiculo_obj
        form = DocumentoVehiculoForm(initial=initial)
        
    return render(request, 'documents/documento_form.html', {
        'form': form,
        'titulo': 'Agregar Documento de Vehículo',
        'vehiculo_obj': vehiculo_obj,
    })

@role_required('Administrador de operaciones', 'Supervisor')
def documento_vehiculo_update(request, pk):
    doc = get_object_or_404(DocumentoVehiculo, pk=pk)
    if request.method == 'POST':
        form = DocumentoVehiculoForm(request.POST, request.FILES, instance=doc)
        if form.is_valid():
            form.save()
            messages.success(request, f"Documento '{doc.tipo_documento}' del vehículo {doc.vehiculo.placa} renovado/actualizado correctamente.")
            return redirect('trucks:vehiculo_detail', pk=doc.vehiculo.pk)
    else:
        form = DocumentoVehiculoForm(instance=doc)
        
    return render(request, 'documents/documento_form.html', {
        'form': form,
        'titulo': f"Renovar/Editar: {doc.tipo_documento} de {doc.vehiculo.placa}",
    })
