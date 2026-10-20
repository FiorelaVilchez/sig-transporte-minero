"""
Motor de validación de asignaciones.

Versión 1.0 (Anexo B): R1 a R5.
Versión 2.0: matriz de requisitos documentales y reglas R6 a R10.

  R1  Falta un documento obligatorio (o la licencia de conducir está vencida)
  R2  Documento obligatorio vencido (incluye la revisión técnica)
  R3  Documento por vencer en 30 días o menos (observa, no bloquea)
  R4  Vehículo en mantenimiento o de baja
  R5  Conductor no apto, de baja u ocupado en ruta el mismo día
  R6  Conductor no habilitado para el tipo de vehículo, experiencia o categoría insuficiente
  R7  Asientos del vehículo menores que los pasajeros de la solicitud
  R8  Documento pendiente u observado en el visto bueno de la mina
  R9  Cruce de horario con otro servicio (con 8 h de descanso para el conductor)
  R10 Superaría el límite de horas de manejo de la semana
"""
import datetime
from dataclasses import dataclass, field

from alerts.services import generar_alerta

HORAS_DESCANSO = 8
LIMITE_HORAS_SEMANA = 60

# Documentos que bloquean al vencer aunque no estén en la matriz (comportamiento 1.0).
BLOQUEANTES_BASE = {
    'Conductor': {'Licencia de conducir'},
    'Vehículo': {'Revisión técnica'},
}


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


def _documento_vigente_por_tipo(documentos):
    """
    Devuelve {tipo_documento: documento más reciente}. Un documento sin fecha de
    vencimiento cuenta como el más reciente, porque no vence.
    """
    elegido = {}
    for doc in documentos:
        actual = elegido.get(doc.tipo_documento)
        if actual is None:
            elegido[doc.tipo_documento] = doc
            continue
        if actual.fecha_vencimiento is None:
            continue
        if doc.fecha_vencimiento is None or doc.fecha_vencimiento > actual.fecha_vencimiento:
            elegido[doc.tipo_documento] = doc
    return elegido


def _requisitos(aplica_a, tipo_vehiculo):
    from documents.models import RequisitoDocumental

    return [
        r for r in RequisitoDocumental.objects.filter(aplica_a=aplica_a, activo=True).prefetch_related('tipos_vehiculo')
        if r.aplica_al_tipo(tipo_vehiculo)
    ]


def _evaluar_documentos(resultado, titular, es_conductor, tipo_vehiculo):
    aplica_a = 'Conductor' if es_conductor else 'Vehículo'
    sujeto = 'conductor' if es_conductor else 'vehículo'
    requisitos = _requisitos(aplica_a, tipo_vehiculo)
    bloqueantes = {r.tipo_documento for r in requisitos if r.bloqueante} | BLOQUEANTES_BASE[aplica_a]
    con_visto_bueno = {r.tipo_documento for r in requisitos if r.requiere_visto_bueno_mina}
    vigentes = _documento_vigente_por_tipo(titular.documentos.all())
    nombre = (
        f"{titular.apellidos}, {titular.nombres}" if es_conductor else titular.placa
    )

    # R1 — documentos obligatorios que faltan
    for req in requisitos:
        if req.tipo_documento in vigentes:
            continue
        if req.bloqueante:
            resultado.bloqueos.append(f"R1: Falta {req.tipo_documento} del {sujeto}")
        else:
            resultado.observaciones.append(f"Falta {req.tipo_documento} del {sujeto} (no bloqueante)")

    for tipo_doc, doc in vigentes.items():
        campo_doc = "documento_conductor" if es_conductor else "documento_vehiculo"
        if doc.estado_documento == "Vencido":
            if tipo_doc in bloqueantes:
                if es_conductor and tipo_doc == "Licencia de conducir":
                    resultado.bloqueos.append("R1: Licencia de conductor vencida")
                    mensaje = f"Licencia de conducir vencida del conductor {nombre}"
                elif not es_conductor and tipo_doc == "Revisión técnica":
                    resultado.bloqueos.append("R2: Revisión técnica vencida")
                    mensaje = f"Revisión técnica vencida del vehículo {nombre}"
                else:
                    resultado.bloqueos.append(f"R2: {tipo_doc} del {sujeto} vencido")
                    mensaje = f"{tipo_doc} vencido del {sujeto} {nombre}"
                resultado.alertas_a_generar.append({
                    "nivel_riesgo": "Alto",
                    "tipo_alerta": "Documento vencido",
                    "documento_conductor": doc.document_id if es_conductor else None,
                    "documento_vehiculo": None if es_conductor else doc.document_id,
                    "mensaje": mensaje,
                })
            else:
                resultado.observaciones.append(
                    f"Documento vencido (no bloqueante): {tipo_doc} del {sujeto}"
                )
        elif doc.estado_documento == "Por vencer" and doc.fecha_vencimiento:
            dias = _dias_hasta_vencimiento(doc.fecha_vencimiento)
            resultado.observaciones.append(_mensaje_por_vencer(tipo_doc, es_conductor, dias))
            resultado.alertas_a_generar.append({
                "nivel_riesgo": "Medio",
                "tipo_alerta": "Documento por vencer",
                "documento_conductor": doc.document_id if es_conductor else None,
                "documento_vehiculo": None if es_conductor else doc.document_id,
                "mensaje": (
                    f"{tipo_doc} del {sujeto} "
                    f"{titular.apellidos if es_conductor else titular.placa} vence en {dias} días"
                ),
            })

        # R8 — visto bueno de la mina
        if tipo_doc in con_visto_bueno and doc.estado_mina in ("Pendiente", "Observado"):
            estado = "pendiente de" if doc.estado_mina == "Pendiente" else "observado en el"
            resultado.bloqueos.append(f"R8: {tipo_doc} del {sujeto} {estado} visto bueno de mina")


def _asignaciones_activas(excluir_solicitud=None):
    from assignments.models import ESTADOS_OPERATIVOS_ACTIVOS, Asignacion

    qs = Asignacion.objects.filter(
        estado_asignacion__in=["Aprobada", "Observada"],
        estado_operativo__in=ESTADOS_OPERATIVOS_ACTIVOS,
    ).select_related("solicitud")
    if excluir_solicitud is not None and excluir_solicitud.pk:
        qs = qs.exclude(solicitud=excluir_solicitud)
    return qs


def horas_programadas_semana(conductor, fecha, excluir_solicitud=None):
    """Horas de servicio del conductor en la semana (lunes a domingo) de la fecha dada."""
    from assignments.models import Asignacion

    lunes = fecha - datetime.timedelta(days=fecha.weekday())
    domingo = lunes + datetime.timedelta(days=6)
    qs = Asignacion.objects.filter(
        conductor=conductor,
        estado_asignacion__in=["Aprobada", "Observada"],
        solicitud__fecha_servicio__range=(lunes, domingo),
    ).exclude(estado_operativo="Cancelado").select_related("solicitud")
    if excluir_solicitud is not None and excluir_solicitud.pk:
        qs = qs.exclude(solicitud=excluir_solicitud)
    return sum(a.solicitud.duracion_horas or 0 for a in qs)


def _evaluar_horario(resultado, conductor, vehiculo, solicitud):
    inicio, fin = solicitud.inicio, solicitud.fin
    descanso = datetime.timedelta(hours=HORAS_DESCANSO)
    activas = _asignaciones_activas(excluir_solicitud=solicitud)

    for otra in activas.filter(conductor=conductor):
        o_ini, o_fin = otra.solicitud.inicio, otra.solicitud.fin
        if inicio < o_fin + descanso and o_ini < fin + descanso:
            resultado.bloqueos.append(
                f"R9: El conductor tiene el servicio #{otra.solicitud.request_id} "
                f"({otra.solicitud.fecha_servicio:%d/%m} {otra.solicitud.hora_servicio:%H:%M}) "
                f"que se cruza, contando {HORAS_DESCANSO} h de descanso"
            )
            break

    for otra in activas.filter(vehiculo=vehiculo):
        o_ini, o_fin = otra.solicitud.inicio, otra.solicitud.fin
        if inicio < o_fin and o_ini < fin:
            resultado.bloqueos.append(
                f"R9: El vehículo tiene el servicio #{otra.solicitud.request_id} "
                f"({otra.solicitud.fecha_servicio:%d/%m} {otra.solicitud.hora_servicio:%H:%M}) que se cruza"
            )
            break

    horas = horas_programadas_semana(conductor, solicitud.fecha_servicio, excluir_solicitud=solicitud)
    if horas + (solicitud.duracion_horas or 0) > LIMITE_HORAS_SEMANA:
        resultado.bloqueos.append(
            f"R10: Superaría el límite semanal: {horas + solicitud.duracion_horas} de {LIMITE_HORAS_SEMANA} h"
        )


def validar_asignacion(conductor, vehiculo, *, solicitud=None, generar_alertas=True):
    """
    Evalúa las reglas R1 a R10. Sin solicitud se omiten las reglas que dependen
    del servicio (R7, R9 y R10), como en la versión 1.0.
    """
    from trucks.models import TipoVehiculo

    resultado = ResultadoValidacion()
    tipo = vehiculo.tipo

    _evaluar_documentos(resultado, conductor, True, tipo)
    _evaluar_documentos(resultado, vehiculo, False, tipo)

    # R4 — Vehículo en mantenimiento o de baja
    if vehiculo.estado == "En mantenimiento":
        resultado.bloqueos.append("R4: Vehículo en mantenimiento")
    elif vehiculo.estado == "De baja":
        resultado.bloqueos.append("R4: Vehículo de baja")

    # R5 — Conductor no apto, de baja u ocupado
    if conductor.estado == "No apto":
        resultado.bloqueos.append("R5: Conductor no apto")
    elif conductor.estado == "De baja":
        resultado.bloqueos.append("R5: Conductor de baja")
    elif conductor.estado == "Ocupado" and (
        solicitud is None or solicitud.fecha_servicio <= datetime.date.today()
    ):
        resultado.bloqueos.append("R5: Conductor ocupado")

    # R6 — Habilitación para el tipo de vehículo
    if not conductor.puede_manejar(tipo):
        resultado.bloqueos.append(f"R6: El conductor no está habilitado para manejar {tipo}")
    else:
        anios = conductor.anios_licencia()
        if anios is not None and anios < tipo.experiencia_minima_anios:
            resultado.bloqueos.append(
                f"R6: Experiencia de {anios} años; {tipo} exige {tipo.experiencia_minima_anios}"
            )
        if conductor.categoria_licencia and (
            TipoVehiculo.orden_categoria(conductor.categoria_licencia)
            < TipoVehiculo.orden_categoria(tipo.categoria_licencia_minima)
        ):
            resultado.bloqueos.append(
                f"R6: Licencia {conductor.categoria_licencia}; {tipo} exige {tipo.categoria_licencia_minima}"
            )

    if solicitud is not None:
        # R7 — Asientos suficientes
        if vehiculo.capacidad < (solicitud.pasajeros or 0):
            resultado.bloqueos.append(
                f"R7: La unidad tiene {vehiculo.capacidad} asientos y la solicitud requiere {solicitud.pasajeros}"
            )
        # R9 y R10 — Horario y horas de la semana
        _evaluar_horario(resultado, conductor, vehiculo, solicitud)

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
