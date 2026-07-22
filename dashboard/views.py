import json
import os
import datetime
import io
import zipfile

from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.http import HttpResponse, Http404
from django.conf import settings

from alerts.services import escanear_documentos_y_generar_alertas
from core.decorators import role_required
from documents.services import recalcular_estados_documentales

from .services import get_dashboard_kpis
from .exports import exportar_todos_los_csv_a_disco

def _formatear_ultima_actualizacion(valor_iso):
    if not valor_iso:
        return None
    dt = parse_datetime(valor_iso)
    if dt is None:
        return valor_iso
    return timezone.localtime(dt).strftime('%d/%m/%Y %H:%M')

@role_required('Administrador de operaciones', 'Supervisor', 'Gerencia')
def dashboard_operativo(request):
    kpis = get_dashboard_kpis()
    ultima_actualizacion = _formatear_ultima_actualizacion(
        request.session.get('dashboard_ultima_actualizacion')
    )
    puede_actualizar = request.user.perfilusuario.rol in (
        'Administrador de operaciones',
        'Gerencia',
    )

    context = {
        'kpis': kpis,
        'ultima_actualizacion': ultima_actualizacion,
        'puede_actualizar': puede_actualizar,
        'solicitudes_labels': json.dumps(list(kpis['solicitudes_por_estado'].keys())),
        'solicitudes_values': json.dumps(list(kpis['solicitudes_por_estado'].values())),
        'conductores_labels': json.dumps(
            [item['conductor'] for item in kpis['asignaciones_por_conductor']]
        ),
        'conductores_values': json.dumps(
            [item['total'] for item in kpis['asignaciones_por_conductor']]
        ),
        'vehiculos_labels': json.dumps(
            [item['vehiculo'] for item in kpis['asignaciones_por_vehiculo']]
        ),
        'vehiculos_values': json.dumps(
            [item['total'] for item in kpis['asignaciones_por_vehiculo']]
        ),
    }
    return render(request, 'dashboard/dashboard_operativo.html', context)

@role_required('Administrador de operaciones', 'Gerencia')
def dashboard_actualizar(request):
    if request.method == 'POST':
        recalcular_estados_documentales()
        resumen = escanear_documentos_y_generar_alertas()
        ahora = timezone.localtime(timezone.now())
        request.session['dashboard_ultima_actualizacion'] = ahora.isoformat()
        mensaje = (
            f"Indicadores actualizados correctamente. "
            f"Documentos: Vencidos={resumen['documentos_vencidos']}, "
            f"Por vencer={resumen['documentos_por_vencer']}. "
            f"Alertas: Nuevas Altas={resumen['alertas_nuevas_altas']}, "
            f"Nuevas Medias={resumen['alertas_nuevas_medias']}, "
            f"Resueltas={resumen['alertas_resueltas']}."
        )
        messages.success(request, mensaje)
    return redirect('dashboard:operativo')

def _obtener_metadatos_archivo(filename, description):
    filepath = os.path.join(settings.BASE_DIR, 'exports', filename)
    if os.path.exists(filepath):
        mtime = os.path.getmtime(filepath)
        dt = datetime.datetime.fromtimestamp(mtime)
        dt_aware = timezone.make_aware(dt, timezone.get_current_timezone())
        dt_str = timezone.localtime(dt_aware).strftime('%d/%m/%Y %H:%M:%S')
        
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                rows = max(0, sum(1 for _ in f) - 1)
        except Exception:
            rows = 0
        return {
            'filename': filename,
            'description': description,
            'exists': True,
            'rows': rows,
            'fecha_generacion': dt_str
        }
    return {
        'filename': filename,
        'description': description,
        'exists': False,
        'rows': 0,
        'fecha_generacion': 'No generado'
    }

@role_required('Administrador de operaciones', 'Supervisor', 'Gerencia')
def reportes_gerenciales(request):
    filenames = [
        ('driver_documents.csv', 'Documentos de conductores: licencias, homologaciones, exámenes médicos y autorizaciones'),
        ('truck_documents.csv', 'Documentos de vehículos: revisión técnica, seguro, homologación y permisos'),
        ('service_requests.csv', 'Solicitudes de transporte con fecha, origen, destino, prioridad y tipo de vehículo requerido'),
        ('assignments.csv', 'Asignaciones de conductor y vehículo a una solicitud, con estado y observación'),
        ('alerts.csv', 'Alertas generadas por documentos vencidos o próximos a vencer'),
        ('powerbi_asignaciones_completas.csv', 'Archivo consolidado para dashboard de asignaciones'),
        ('powerbi_drivers_con_documentos.csv', 'Archivo consolidado para análisis documental de conductores'),
        ('powerbi_trucks_con_documentos.csv', 'Archivo consolidado para análisis documental de vehículos'),
    ]
    
    archivos_info = [_obtener_metadatos_archivo(fn, desc) for fn, desc in filenames]
    puede_regenerar = request.user.perfilusuario.rol in ('Administrador de operaciones', 'Gerencia')
    
    context = {
        'archivos_info': archivos_info,
        'puede_regenerar': puede_regenerar,
    }
    return render(request, 'dashboard/reportes_gerenciales.html', context)

@role_required('Administrador de operaciones', 'Gerencia')
def reportes_generar_csv(request):
    if request.method == 'POST':
        resumen = exportar_todos_los_csv_a_disco()
        detalles = ", ".join([f"{k}: {v} filas" for k, v in resumen.items()])
        messages.success(request, f"Archivos CSV generados correctamente para Power BI: {detalles}")
    return redirect('dashboard:reportes')

@role_required('Administrador de operaciones', 'Supervisor', 'Gerencia')
def reportes_descargar_csv(request, filename):
    valid_filenames = [
        'driver_documents.csv',
        'truck_documents.csv',
        'service_requests.csv',
        'assignments.csv',
        'alerts.csv',
        'powerbi_asignaciones_completas.csv',
        'powerbi_drivers_con_documentos.csv',
        'powerbi_trucks_con_documentos.csv',
    ]
    if filename not in valid_filenames:
        raise Http404("Archivo no encontrado")
        
    filepath = os.path.join(settings.BASE_DIR, 'exports', filename)
    if not os.path.exists(filepath):
        # Intentar generar
        exportar_todos_los_csv_a_disco()
        if not os.path.exists(filepath):
            messages.error(request, f"El archivo {filename} no existe y no pudo ser generado.")
            return redirect('dashboard:reportes')
            
    with open(filepath, 'rb') as f:
        response = HttpResponse(f.read(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

@role_required('Administrador de operaciones', 'Supervisor', 'Gerencia')
def reportes_descargar_zip(request):
    exportar_todos_los_csv_a_disco()
    
    valid_filenames = [
        'driver_documents.csv',
        'truck_documents.csv',
        'service_requests.csv',
        'assignments.csv',
        'alerts.csv',
        'powerbi_asignaciones_completas.csv',
        'powerbi_drivers_con_documentos.csv',
        'powerbi_trucks_con_documentos.csv',
    ]
    
    exports_dir = os.path.join(settings.BASE_DIR, 'exports')
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for filename in valid_filenames:
            filepath = os.path.join(exports_dir, filename)
            if os.path.exists(filepath):
                zip_file.write(filepath, filename)
                
    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="reportes_powerbi.zip"'
    return response
