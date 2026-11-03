"""Configuración de catálogos: tipos de vehículo, requisitos, clientes y tarifas."""
from django.contrib import messages
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from billing.models import Tarifa
from crm.models import Cliente
from documents.models import RequisitoDocumental
from trucks.models import TipoVehiculo

from .config_forms import ClienteForm, RequisitoForm, TarifaForm, TipoVehiculoForm
from .decorators import role_required

CATALOGOS = {
    'tipos': {
        'modelo': TipoVehiculo, 'form': TipoVehiculoForm, 'titulo': 'Tipo de vehículo',
        'roles': ('Administrador de operaciones',),
    },
    'requisitos': {
        'modelo': RequisitoDocumental, 'form': RequisitoForm, 'titulo': 'Requisito documental',
        'roles': ('Administrador de operaciones',),
    },
    'clientes': {
        'modelo': Cliente, 'form': ClienteForm, 'titulo': 'Cliente',
        'roles': ('Administrador de operaciones', 'Finanzas'),
    },
    'tarifas': {
        'modelo': Tarifa, 'form': TarifaForm, 'titulo': 'Tarifa',
        'roles': ('Administrador de operaciones', 'Finanzas'),
    },
}


@role_required('Administrador de operaciones', 'Finanzas')
def configuracion(request):
    rol = request.user.perfilusuario.rol
    return render(request, 'core/configuracion.html', {
        'tipos': TipoVehiculo.objects.all(),
        'requisitos': RequisitoDocumental.objects.prefetch_related('tipos_vehiculo'),
        'clientes': Cliente.objects.annotate(n_solicitudes=Count('solicitudes')),
        'tarifas': Tarifa.objects.select_related('cliente', 'tipo_vehiculo'),
        'puede_operaciones': rol == 'Administrador de operaciones',
    })


@role_required('Administrador de operaciones', 'Finanzas')
def catalogo_form(request, catalogo, pk=None):
    conf = CATALOGOS.get(catalogo)
    if conf is None:
        raise Http404
    if request.user.perfilusuario.rol not in conf['roles']:
        return render(request, 'core/403.html', {'allowed_roles': conf['roles']}, status=403)
    instancia = get_object_or_404(conf['modelo'], pk=pk) if pk else None
    form = conf['form'](request.POST or None, instance=instancia)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"{conf['titulo']} guardado correctamente.")
        return redirect(f"{reverse('core:configuracion')}#{catalogo}")
    return render(request, 'core/catalogo_form.html', {
        'form': form,
        'titulo': f"{'Editar' if instancia else 'Nuevo'}: {conf['titulo'].lower()}",
    })
