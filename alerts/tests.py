import datetime

from django.test import TestCase

from alerts.models import Alerta
from alerts.services import escanear_documentos_y_generar_alertas
from documents.models import DocumentoConductor
from drivers.models import Conductor


class EscanearDocumentosAlertasTestCase(TestCase):
    def setUp(self):
        self.hoy = datetime.date.today()
        self.conductor = Conductor.objects.create(
            nombres="Juan",
            apellidos="Pérez Quispe",
            licencia="Q99999999",
            especialidad="Camioneta",
            estado="Disponible",
            dni="99999999",
            fecha_nacimiento=datetime.date(1990, 1, 1),
            fecha_ingreso=datetime.date(2020, 1, 1),
        )

    def test_documento_vencido_genera_una_alerta_alta(self):
        DocumentoConductor.objects.create(
            conductor=self.conductor,
            tipo_documento="Licencia de conducir",
            fecha_emision=self.hoy - datetime.timedelta(days=400),
            fecha_vencimiento=self.hoy - datetime.timedelta(days=5),
            estado_documento="Vencido",
        )
        resumen = escanear_documentos_y_generar_alertas()
        self.assertEqual(resumen["alertas_nuevas_altas"], 1)
        self.assertEqual(Alerta.objects.filter(estado_alerta="Activa").count(), 1)
        alerta = Alerta.objects.get()
        self.assertEqual(alerta.nivel_riesgo, "Alto")
        self.assertEqual(alerta.tipo_alerta, "Documento vencido")

    def test_escaneo_doble_no_duplica_alertas(self):
        DocumentoConductor.objects.create(
            conductor=self.conductor,
            tipo_documento="Licencia de conducir",
            fecha_emision=self.hoy - datetime.timedelta(days=400),
            fecha_vencimiento=self.hoy - datetime.timedelta(days=5),
            estado_documento="Vencido",
        )
        escanear_documentos_y_generar_alertas()
        resumen = escanear_documentos_y_generar_alertas()
        self.assertEqual(resumen["alertas_nuevas_altas"], 0)
        self.assertEqual(Alerta.objects.filter(estado_alerta="Activa").count(), 1)

    def test_documento_por_vencer_genera_alerta_media(self):
        DocumentoConductor.objects.create(
            conductor=self.conductor,
            tipo_documento="Examen médico",
            fecha_emision=self.hoy - datetime.timedelta(days=300),
            fecha_vencimiento=self.hoy + datetime.timedelta(days=15),
            estado_documento="Por vencer",
        )
        resumen = escanear_documentos_y_generar_alertas()
        self.assertEqual(resumen["alertas_nuevas_medias"], 1)
        alerta = Alerta.objects.get()
        self.assertEqual(alerta.nivel_riesgo, "Medio")
        self.assertEqual(alerta.tipo_alerta, "Documento por vencer")

    def test_documento_renovado_resuelve_alerta_anterior(self):
        documento = DocumentoConductor.objects.create(
            conductor=self.conductor,
            tipo_documento="Licencia de conducir",
            fecha_emision=self.hoy - datetime.timedelta(days=400),
            fecha_vencimiento=self.hoy - datetime.timedelta(days=5),
            estado_documento="Vencido",
        )
        escanear_documentos_y_generar_alertas()
        alerta = Alerta.objects.get(estado_alerta="Activa")
        documento.fecha_vencimiento = self.hoy + datetime.timedelta(days=365)
        documento.estado_documento = "Vigente"
        documento.save()
        resumen = escanear_documentos_y_generar_alertas()
        alerta.refresh_from_db()
        self.assertEqual(alerta.estado_alerta, "Resuelta")
        self.assertEqual(resumen["alertas_resueltas"], 1)
        self.assertEqual(Alerta.objects.filter(estado_alerta="Activa").count(), 0)

    def test_documento_vigente_no_genera_alerta(self):
        DocumentoConductor.objects.create(
            conductor=self.conductor,
            tipo_documento="Licencia de conducir",
            fecha_emision=self.hoy - datetime.timedelta(days=100),
            fecha_vencimiento=self.hoy + datetime.timedelta(days=200),
            estado_documento="Vigente",
        )
        resumen = escanear_documentos_y_generar_alertas()
        self.assertEqual(resumen["alertas_nuevas_altas"], 0)
        self.assertEqual(resumen["alertas_nuevas_medias"], 0)
        self.assertEqual(Alerta.objects.count(), 0)
