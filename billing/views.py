from decimal import Decimal

from django.contrib import messages
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.decorators import role_required

from .models import Valorizacion
from .services import cambiar_estado, recalcular, revisar_cobros_atrasados


@role_required('Finanzas', 'Administrador de operaciones', 'Gerencia')
def valorizacion_list(request):
    qs = Valorizacion.objects.select_related('solicitud', 'tarifa')
    estado = request.GET.get('estado', '')
    if estado:
        qs = qs.filter(estado=estado)
    resumen = {
        fila['estado']: fila for fila in
        Valorizacion.objects.values('estado').annotate(n=Count('id'), monto=Sum('total'))
    }
    por_cobrar = sum(
        (f['monto'] or Decimal('0')) for e, f in resumen.items() if e in ('Enviada', 'Observada', 'Conforme', 'Facturada')
    )
    atrasadas = [v for v in Valorizacion.objects.filter(estado__in=['Enviada', 'Observada']).select_related('solicitud') if v.cobro_atrasado]
    return render(request, 'billing/valorizacion_list.html', {
        'valorizaciones': qs,
        'estado_filtro': estado,
        'estados': Valorizacion.ESTADO_CHOICES,
        'resumen': [(codigo, nombre, resumen.get(codigo, {}).get('n', 0), resumen.get(codigo, {}).get('monto') or 0)
                    for codigo, nombre in Valorizacion.ESTADO_CHOICES],
        'por_cobrar': por_cobrar,
        'atrasadas': atrasadas,
        'dias_alerta': Valorizacion.DIAS_ALERTA_COBRO,
        'puede_editar': request.user.perfilusuario.rol == 'Finanzas',
    })


@role_required('Finanzas', 'Administrador de operaciones', 'Gerencia')
def valorizacion_detail(request, pk):
    v = get_object_or_404(Valorizacion.objects.select_related('solicitud', 'tarifa'), pk=pk)
    from assignments.models import Asignacion
    asignacion = (
        Asignacion.objects.filter(solicitud=v.solicitud, estado_operativo='Completado')
        .select_related('conductor', 'vehiculo').prefetch_related('gastos').first()
    )
    return render(request, 'billing/valorizacion_detail.html', {
        'v': v,
        'asignacion': asignacion,
        'puede_editar': request.user.perfilusuario.rol == 'Finanzas',
    })


@role_required('Finanzas')
@require_POST
def valorizacion_estado(request, pk):
    v = get_object_or_404(Valorizacion, pk=pk)
    try:
        cambiar_estado(
            v, request.POST.get('estado', ''),
            numero_factura=(request.POST.get('numero_factura') or '').strip(),
            observacion=(request.POST.get('observacion') or '').strip(),
        )
        messages.success(request, f"Valorización actualizada a {v.estado}.")
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('billing:valorizacion_detail', pk=pk)


@role_required('Finanzas')
@require_POST
def valorizacion_recalcular(request, pk):
    v = get_object_or_404(Valorizacion, pk=pk)
    try:
        recalcular(v)
        messages.success(request, f"Valorización recalculada: S/ {v.total}.")
    except ValueError as e:
        messages.error(request, str(e))
    return redirect('billing:valorizacion_detail', pk=pk)


@role_required('Finanzas', 'Administrador de operaciones')
@require_POST
def revisar_cobros(request):
    n = revisar_cobros_atrasados()
    messages.info(request, f"Revisión de cobros: {n} valorización(es) con más de {Valorizacion.DIAS_ALERTA_COBRO} días sin conformidad.")
    return redirect('billing:valorizacion_list')
