from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from core.decorators import role_required
from .models import Alerta
from .services import get_alertas_activas, escanear_documentos_y_generar_alertas

@role_required('Administrador de operaciones', 'Supervisor')
def alerta_list(request):
    alertas_qs = get_alertas_activas()
    
    # Filtros
    nivel_filtro = request.GET.get('nivel_riesgo', '')
    tipo_filtro = request.GET.get('tipo_alerta', '')
    
    if nivel_filtro:
        alertas_qs = alertas_qs.filter(nivel_riesgo=nivel_filtro)
    if tipo_filtro:
        alertas_qs = alertas_qs.filter(tipo_alerta=tipo_filtro)
        
    # Paginación
    paginator = Paginator(alertas_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'alerts/alerta_list.html', {
        'page_obj': page_obj,
        'nivel_filtro': nivel_filtro,
        'tipo_filtro': tipo_filtro,
        'nivel_choices': Alerta.NIVEL_RIESGO_CHOICES,
        'tipo_choices': Alerta.TIPO_ALERTA_CHOICES,
    })

@role_required('Administrador de operaciones', 'Supervisor')
def alerta_resolver(request, pk):
    if request.method == 'POST':
        alerta = get_object_or_404(Alerta, pk=pk)
        alerta.estado_alerta = 'Resuelta'
        alerta.save(update_fields=['estado_alerta', 'updated_at'])
        messages.success(request, f"La alerta #{alerta.alert_id} ({alerta.tipo_alerta}) ha sido marcada como RESUELTA.")
    return redirect('alerts:alerta_list')

@role_required('Administrador de operaciones', 'Supervisor')
def alerta_run_scan(request):
    if request.method == 'POST':
        resumen = escanear_documentos_y_generar_alertas()
        mensaje = (
            f"Escaneo finalizado. Documentos procesados: "
            f"Vencidos={resumen['documentos_vencidos']}, "
            f"Por vencer={resumen['documentos_por_vencer']}. "
            f"Alertas de esta corrida: Nuevas Altas={resumen['alertas_nuevas_altas']}, "
            f"Nuevas Medias={resumen['alertas_nuevas_medias']}, Resueltas={resumen['alertas_resueltas']}."
        )
        messages.success(request, mensaje)
    return redirect('alerts:alerta_list')
