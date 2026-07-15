import datetime
from dataclasses import dataclass, field

from alerts.services import generar_alerta


@dataclass
class ResultadoValidacion:
    veredicto: str = "Aprobada"
    bloqueos: list = field(default_factory=list)
    observaciones: list = field(default_factory=list)
    alertas_a_generar: list = field(default_factory=list)
    alertas_generadas: list = field(default_factory=list)

    def como_dict(self):
        return {
            "veredicto": self.veredicto,
            "bloqueos": self.bloqueos,
            "observaciones": self.observaciones,
            "alertas_a_generar": self.alertas_a_generar,
            "alertas_generadas": self.alertas_generadas,
        }


def _dias_hasta_vencimiento(fecha_vencimiento):
    return (fecha_vencimiento - datetime.date.today()).days


def _mensaje_por_vencer(tipo_documento, es_conductor, dias):
    prefijo = "conductor" if es_conductor else "vehículo"
    return f"R3: {tipo_documento} del {prefijo} vence en {dias} días"


def validar_asignacion(conductor, vehiculo, *, generar_alertas=True):
    """
    Evalúa las 5 reglas de validación documental y de disponibilidad (Anexo B).
    """
    resultado = ResultadoValidacion()
    documentos_bloqueados = set()

    # R1 — Licencia de conducir vencida
    r1_detectada = False
    for documento in conductor.documentos.filter(tipo_documento="Licencia de conducir"):
        if documento.estado_documento == "Vencido":
            if not r1_detectada:
                resultado.bloqueos.append("R1: Licencia de conductor vencida")
                r1_detectada = True
            documentos_bloqueados.add(("conductor", documento.document_id))
            resultado.alertas_a_generar.append(
                {
                    "nivel_riesgo": "Alto",
                    "tipo_alerta": "Documento vencido",
                    "documento_conductor": documento.document_id,
                    "documento_vehiculo": None,
                    "mensaje": (
                        f"Licencia de conducir vencida del conductor "
                        f"{conductor.apellidos}, {conductor.nombres}"
                    ),
                }
            )

    # R2 — Revisión técnica vencida
    r2_detectada = False
    for documento in vehiculo.documentos.filter(tipo_documento="Revisión técnica"):
        if documento.estado_documento == "Vencido":
            if not r2_detectada:
                resultado.bloqueos.append("R2: Revisión técnica vencida")
                r2_detectada = True
            documentos_bloqueados.add(("vehiculo", documento.document_id))
            resultado.alertas_a_generar.append(
                {
                    "nivel_riesgo": "Alto",
                    "tipo_alerta": "Documento vencido",
                    "documento_conductor": None,
                    "documento_vehiculo": documento.document_id,
                    "mensaje": (
                        f"Revisión técnica vencida del vehículo {vehiculo.placa}"
                    ),
                }
            )

    # R3 — Documentos por vencer (cualquier tipo, conductor y vehículo)
    for documento in conductor.documentos.filter(estado_documento="Por vencer"):
        dias = _dias_hasta_vencimiento(documento.fecha_vencimiento)
        resultado.observaciones.append(
            _mensaje_por_vencer(documento.tipo_documento, True, dias)
        )
        resultado.alertas_a_generar.append(
            {
                "nivel_riesgo": "Medio",
                "tipo_alerta": "Documento por vencer",
                "documento_conductor": documento.document_id,
                "documento_vehiculo": None,
                "mensaje": (
                    f"{documento.tipo_documento} del conductor "
                    f"{conductor.apellidos} vence en {dias} días"
                ),
            }
        )

    for documento in vehiculo.documentos.filter(estado_documento="Por vencer"):
        dias = _dias_hasta_vencimiento(documento.fecha_vencimiento)
        resultado.observaciones.append(
            _mensaje_por_vencer(documento.tipo_documento, False, dias)
        )
        resultado.alertas_a_generar.append(
            {
                "nivel_riesgo": "Medio",
                "tipo_alerta": "Documento por vencer",
                "documento_conductor": None,
                "documento_vehiculo": documento.document_id,
                "mensaje": (
                    f"{documento.tipo_documento} del vehículo {vehiculo.placa} "
                    f"vence en {dias} días"
                ),
            }
        )

    # Documentos vencidos no bloqueantes (no licencia ni revisión técnica)
    for documento in conductor.documentos.filter(estado_documento="Vencido"):
        clave = ("conductor", documento.document_id)
        if clave in documentos_bloqueados:
            continue
        if documento.tipo_documento == "Licencia de conducir":
            continue
        resultado.observaciones.append(
            f"Documento vencido (no bloqueante): {documento.tipo_documento} del conductor"
        )

    for documento in vehiculo.documentos.filter(estado_documento="Vencido"):
        clave = ("vehiculo", documento.document_id)
        if clave in documentos_bloqueados:
            continue
        if documento.tipo_documento == "Revisión técnica":
            continue
        resultado.observaciones.append(
            f"Documento vencido (no bloqueante): {documento.tipo_documento} del vehículo"
        )

    # R4 — Vehículo en mantenimiento
    if vehiculo.estado == "En mantenimiento":
        resultado.bloqueos.append("R4: Vehículo en mantenimiento")

    # R5 — Conductor ocupado o no apto
    if conductor.estado == "Ocupado":
        resultado.bloqueos.append("R5: Conductor ocupado")
    elif conductor.estado == "No apto":
        resultado.bloqueos.append("R5: Conductor no apto")
    elif conductor.estado == "De baja":
        resultado.bloqueos.append("R5: Conductor de baja")

    # Veredicto final
    if resultado.bloqueos:
        resultado.veredicto = "Rechazada"
    elif resultado.observaciones:
        resultado.veredicto = "Observada"
    else:
        resultado.veredicto = "Aprobada"

    if generar_alertas:
        _persistir_alertas(resultado)

    return resultado.como_dict()


def _persistir_alertas(resultado):
    from documents.models import DocumentoConductor, DocumentoVehiculo

    for alerta_data in resultado.alertas_a_generar:
        doc_conductor = None
        doc_vehiculo = None

        if alerta_data.get("documento_conductor"):
            doc_conductor = DocumentoConductor.objects.filter(
                document_id=alerta_data["documento_conductor"]
            ).first()

        if alerta_data.get("documento_vehiculo"):
            doc_vehiculo = DocumentoVehiculo.objects.filter(
                document_id=alerta_data["documento_vehiculo"]
            ).first()

        alerta = generar_alerta(
            nivel_riesgo=alerta_data["nivel_riesgo"],
            tipo_alerta=alerta_data["tipo_alerta"],
            documento_conductor=doc_conductor,
            documento_vehiculo=doc_vehiculo,
            mensaje=alerta_data["mensaje"],
        )
        resultado.alertas_generadas.append(alerta.alert_id)
