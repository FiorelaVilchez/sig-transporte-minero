import csv
import os
from django.conf import settings
from django.utils import timezone
from documents.models import DocumentoConductor, DocumentoVehiculo
from service_requests.models import SolicitudServicio
from assignments.models import Asignacion
from alerts.models import Alerta

def _formatear_fecha(fecha):
    if not fecha:
        return ""
    return fecha.strftime('%Y-%m-%d')

def _formatear_fecha_hora(fecha_hora):
    if not fecha_hora:
        return ""
    # Convertir a local timezone si es aware
    if timezone.is_aware(fecha_hora):
        fecha_hora = timezone.localtime(fecha_hora)
    return fecha_hora.strftime('%Y-%m-%d %H:%M:%S')

def _obtener_referencia_alerta(alert):
    if alert.documento_conductor:
        tipo = alert.documento_conductor.tipo_documento
        if "Licencia" in tipo:
            tipo_str = "Licencia"
        elif "Examen" in tipo:
            tipo_str = "Examen"
        elif "Homologación" in tipo:
            tipo_str = "Homologación"
        elif "Autorización" in tipo:
            tipo_str = "Autorización"
        else:
            tipo_str = tipo
        return f"{tipo_str} — {alert.documento_conductor.conductor.apellidos}, {alert.documento_conductor.conductor.nombres}"
    elif alert.documento_vehiculo:
        tipo = alert.documento_vehiculo.tipo_documento
        if "Revisión" in tipo:
            tipo_str = "Revisión técnica"
        elif "Seguro" in tipo:
            tipo_str = "Seguro"
        elif "Homologación" in tipo:
            tipo_str = "Homologación"
        elif "Permiso" in tipo:
            tipo_str = "Permiso"
        else:
            tipo_str = tipo
        return f"{tipo_str} — {alert.documento_vehiculo.vehiculo.placa}"
    return "N/A"

def generar_driver_documents_csv(writer):
    writer.writerow([
        "document_id", "driver_id", "conductor_nombre_completo", "dni", 
        "tipo_documento", "fecha_emision", "fecha_vencimiento", "estado_documento"
    ])
    count = 0
    for doc in DocumentoConductor.objects.select_related('conductor').all():
        nombre = f"{doc.conductor.nombres} {doc.conductor.apellidos}"
        writer.writerow([
            doc.document_id,
            doc.conductor.driver_id,
            nombre,
            doc.conductor.dni,
            doc.tipo_documento,
            _formatear_fecha(doc.fecha_emision),
            _formatear_fecha(doc.fecha_vencimiento),
            doc.estado_documento
        ])
        count += 1
    return count

def generar_truck_documents_csv(writer):
    writer.writerow([
        "document_id", "truck_id", "placa", "tipo", 
        "tipo_documento", "fecha_emision", "fecha_vencimiento", "estado_documento"
    ])
    count = 0
    for doc in DocumentoVehiculo.objects.select_related('vehiculo').all():
        writer.writerow([
            doc.document_id,
            doc.vehiculo.truck_id,
            doc.vehiculo.placa,
            doc.vehiculo.tipo,
            doc.tipo_documento,
            _formatear_fecha(doc.fecha_emision),
            _formatear_fecha(doc.fecha_vencimiento),
            doc.estado_documento
        ])
        count += 1
    return count

def generar_service_requests_csv(writer):
    writer.writerow([
        "request_id", "cliente", "fecha_servicio", "hora_servicio", 
        "origen", "destino", "tipo_servicio", "prioridad", 
        "tipo_vehiculo_requerido", "estado_solicitud"
    ])
    count = 0
    for req in SolicitudServicio.objects.all():
        writer.writerow([
            req.request_id,
            req.cliente,
            _formatear_fecha(req.fecha_servicio),
            req.hora_servicio.strftime('%H:%M:%S') if req.hora_servicio else "",
            req.origen,
            req.destino,
            req.tipo_servicio,
            req.prioridad,
            req.tipo_vehiculo_requerido,
            req.estado_solicitud
        ])
        count += 1
    return count

def generar_assignments_csv(writer):
    writer.writerow([
        "assignment_id", "request_id", "driver_id", "conductor_nombre", 
        "truck_id", "placa", "estado_asignacion", "observacion", "fecha_asignacion"
    ])
    count = 0
    for asn in Asignacion.objects.select_related('solicitud', 'conductor', 'vehiculo').all():
        cond_nombre = f"{asn.conductor.nombres} {asn.conductor.apellidos}" if asn.conductor else ""
        driver_id = asn.conductor.driver_id if asn.conductor else ""
        truck_id = asn.vehiculo.truck_id if asn.vehiculo else ""
        placa = asn.vehiculo.placa if asn.vehiculo else ""
        writer.writerow([
            asn.assignment_id,
            asn.solicitud.request_id,
            driver_id,
            cond_nombre,
            truck_id,
            placa,
            asn.estado_asignacion,
            asn.observacion,
            _formatear_fecha_hora(asn.fecha_asignacion)
        ])
        count += 1
    return count

def generar_alerts_csv(writer):
    writer.writerow([
        "alert_id", "tipo_alerta", "nivel_riesgo", "estado_alerta", 
        "referencia", "mensaje", "fecha_generacion"
    ])
    count = 0
    for alert in Alerta.objects.select_related('documento_conductor__conductor', 'documento_vehiculo__vehiculo').all():
        writer.writerow([
            alert.alert_id,
            alert.tipo_alerta,
            alert.nivel_riesgo,
            alert.estado_alerta,
            _obtener_referencia_alerta(alert),
            alert.mensaje,
            _formatear_fecha_hora(alert.fecha_generacion)
        ])
        count += 1
    return count

def generar_powerbi_asignaciones_completas_csv(writer):
    writer.writerow([
        "assignment_id", "request_id", "cliente", "fecha_servicio", "prioridad", 
        "tipo_servicio", "origen", "destino", "driver_id", "conductor_nombre", 
        "especialidad", "truck_id", "placa", "tipo_vehiculo", "estado_asignacion", 
        "observacion", "fecha_asignacion"
    ])
    count = 0
    for asn in Asignacion.objects.select_related('solicitud', 'conductor', 'vehiculo').all():
        cond_nombre = f"{asn.conductor.nombres} {asn.conductor.apellidos}" if asn.conductor else ""
        driver_id = asn.conductor.driver_id if asn.conductor else ""
        especialidad = asn.conductor.especialidad if asn.conductor else ""
        truck_id = asn.vehiculo.truck_id if asn.vehiculo else ""
        placa = asn.vehiculo.placa if asn.vehiculo else ""
        tipo_vehiculo = asn.vehiculo.tipo if asn.vehiculo else ""
        writer.writerow([
            asn.assignment_id,
            asn.solicitud.request_id,
            asn.solicitud.cliente,
            _formatear_fecha(asn.solicitud.fecha_servicio),
            asn.solicitud.prioridad,
            asn.solicitud.tipo_servicio,
            asn.solicitud.origen,
            asn.solicitud.destino,
            driver_id,
            cond_nombre,
            especialidad,
            truck_id,
            placa,
            tipo_vehiculo,
            asn.estado_asignacion,
            asn.observacion,
            _formatear_fecha_hora(asn.fecha_asignacion)
        ])
        count += 1
    return count

def generar_powerbi_drivers_con_documentos_csv(writer):
    writer.writerow([
        "driver_id", "conductor_nombre", "dni", "licencia", "especialidad", 
        "estado_conductor", "document_id", "tipo_documento", "fecha_vencimiento", "estado_documento"
    ])
    count = 0
    for doc in DocumentoConductor.objects.select_related('conductor').all():
        cond_nombre = f"{doc.conductor.nombres} {doc.conductor.apellidos}"
        writer.writerow([
            doc.conductor.driver_id,
            cond_nombre,
            doc.conductor.dni,
            doc.conductor.licencia,
            doc.conductor.especialidad,
            doc.conductor.estado,
            doc.document_id,
            doc.tipo_documento,
            _formatear_fecha(doc.fecha_vencimiento),
            doc.estado_documento
        ])
        count += 1
    return count

def generar_powerbi_trucks_con_documentos_csv(writer):
    writer.writerow([
        "truck_id", "placa", "tipo", "capacidad", "estado_vehiculo", 
        "document_id", "tipo_documento", "fecha_vencimiento", "estado_documento"
    ])
    count = 0
    for doc in DocumentoVehiculo.objects.select_related('vehiculo').all():
        writer.writerow([
            doc.vehiculo.truck_id,
            doc.vehiculo.placa,
            doc.vehiculo.tipo,
            doc.vehiculo.capacidad,
            doc.vehiculo.estado,
            doc.document_id,
            doc.tipo_documento,
            _formatear_fecha(doc.fecha_vencimiento),
            doc.estado_documento
        ])
        count += 1
    return count

def exportar_todos_los_csv_a_disco():
    exports_dir = os.path.join(settings.BASE_DIR, 'exports')
    os.makedirs(exports_dir, exist_ok=True)
    
    mapping = {
        'driver_documents.csv': generar_driver_documents_csv,
        'truck_documents.csv': generar_truck_documents_csv,
        'service_requests.csv': generar_service_requests_csv,
        'assignments.csv': generar_assignments_csv,
        'alerts.csv': generar_alerts_csv,
        'powerbi_asignaciones_completas.csv': generar_powerbi_asignaciones_completas_csv,
        'powerbi_drivers_con_documentos.csv': generar_powerbi_drivers_con_documentos_csv,
        'powerbi_trucks_con_documentos.csv': generar_powerbi_trucks_con_documentos_csv,
    }
    
    resumen = {}
    for filename, func in mapping.items():
        filepath = os.path.join(exports_dir, filename)
        # Usar utf-8-sig para codificar con BOM (Byte Order Mark)
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            rows_written = func(writer)
            resumen[filename] = rows_written
            
    return resumen
