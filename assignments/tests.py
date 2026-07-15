import datetime

from django.test import TestCase

from assignments.validators import validar_asignacion
from drivers.models import Conductor
from trucks.models import Vehiculo
from documents.models import DocumentoConductor, DocumentoVehiculo


class ValidarAsignacionTestCase(TestCase):
    """Pruebas del motor de validación — una por cada regla del Anexo B."""

    def setUp(self):
        self.hoy = datetime.date.today()
        self.conductor_base = Conductor.objects.create(
            nombres="Test",
            apellidos="Conductor Base",
            licencia="T00000001",
            especialidad="Camioneta",
            estado="Disponible",
            dni="11111111",
            fecha_nacimiento=datetime.date(1990, 1, 1),
            fecha_ingreso=datetime.date(2020, 1, 1),
        )
        self.vehiculo_base = Vehiculo.objects.create(
            placa="TST-001",
            tipo="Camioneta",
            capacidad=5,
            estado="Disponible",
        )

    def _validar(self, conductor=None, vehiculo=None):
        return validar_asignacion(
            conductor or self.conductor_base,
            vehiculo or self.vehiculo_base,
            generar_alertas=False,
        )

    def test_r1_licencia_vencida_rechaza(self):
        DocumentoConductor.objects.create(
            conductor=self.conductor_base,
            tipo_documento="Licencia de conducir",
            fecha_emision=self.hoy - datetime.timedelta(days=400),
            fecha_vencimiento=self.hoy - datetime.timedelta(days=10),
            estado_documento="Vencido",
        )
        resultado = self._validar()
        self.assertEqual(resultado["veredicto"], "Rechazada")
        self.assertTrue(
            any("R1" in b for b in resultado["bloqueos"]),
            resultado["bloqueos"],
        )
        self.assertEqual(
            resultado["alertas_a_generar"][0]["nivel_riesgo"], "Alto"
        )

    def test_r2_revision_tecnica_vencida_rechaza(self):
        DocumentoVehiculo.objects.create(
            vehiculo=self.vehiculo_base,
            tipo_documento="Revisión técnica",
            fecha_emision=self.hoy - datetime.timedelta(days=400),
            fecha_vencimiento=self.hoy - datetime.timedelta(days=5),
            estado_documento="Vencido",
        )
        DocumentoConductor.objects.create(
            conductor=self.conductor_base,
            tipo_documento="Licencia de conducir",
            fecha_emision=self.hoy - datetime.timedelta(days=100),
            fecha_vencimiento=self.hoy + datetime.timedelta(days=365),
            estado_documento="Vigente",
        )
        resultado = self._validar()
        self.assertEqual(resultado["veredicto"], "Rechazada")
        self.assertTrue(
            any("R2" in b for b in resultado["bloqueos"]),
            resultado["bloqueos"],
        )

    def test_r3_documento_por_vencer_observa_sin_bloqueo(self):
        DocumentoConductor.objects.create(
            conductor=self.conductor_base,
            tipo_documento="Licencia de conducir",
            fecha_emision=self.hoy - datetime.timedelta(days=700),
            fecha_vencimiento=self.hoy + datetime.timedelta(days=20),
            estado_documento="Por vencer",
        )
        DocumentoVehiculo.objects.create(
            vehiculo=self.vehiculo_base,
            tipo_documento="Seguro",
            fecha_emision=self.hoy - datetime.timedelta(days=300),
            fecha_vencimiento=self.hoy + datetime.timedelta(days=200),
            estado_documento="Vigente",
        )
        resultado = self._validar()
        self.assertEqual(resultado["veredicto"], "Observada")
        self.assertEqual(resultado["bloqueos"], [])
        self.assertTrue(
            any("R3" in o for o in resultado["observaciones"]),
            resultado["observaciones"],
        )
        self.assertTrue(
            any(a["nivel_riesgo"] == "Medio" for a in resultado["alertas_a_generar"])
        )

    def test_r4_vehiculo_en_mantenimiento_rechaza(self):
        self.vehiculo_base.estado = "En mantenimiento"
        self.vehiculo_base.save()
        DocumentoConductor.objects.create(
            conductor=self.conductor_base,
            tipo_documento="Licencia de conducir",
            fecha_emision=self.hoy - datetime.timedelta(days=100),
            fecha_vencimiento=self.hoy + datetime.timedelta(days=365),
            estado_documento="Vigente",
        )
        resultado = self._validar()
        self.assertEqual(resultado["veredicto"], "Rechazada")
        self.assertIn("R4: Vehículo en mantenimiento", resultado["bloqueos"])

    def test_r5_conductor_ocupado_rechaza(self):
        self.conductor_base.estado = "Ocupado"
        self.conductor_base.save()
        DocumentoConductor.objects.create(
            conductor=self.conductor_base,
            tipo_documento="Licencia de conducir",
            fecha_emision=self.hoy - datetime.timedelta(days=100),
            fecha_vencimiento=self.hoy + datetime.timedelta(days=365),
            estado_documento="Vigente",
        )
        resultado = self._validar()
        self.assertEqual(resultado["veredicto"], "Rechazada")
        self.assertIn("R5: Conductor ocupado", resultado["bloqueos"])

    def test_r5_conductor_no_apto_rechaza(self):
        self.conductor_base.estado = "No apto"
        self.conductor_base.save()
        DocumentoConductor.objects.create(
            conductor=self.conductor_base,
            tipo_documento="Licencia de conducir",
            fecha_emision=self.hoy - datetime.timedelta(days=100),
            fecha_vencimiento=self.hoy + datetime.timedelta(days=365),
            estado_documento="Vigente",
        )
        resultado = self._validar()
        self.assertEqual(resultado["veredicto"], "Rechazada")
        self.assertIn("R5: Conductor no apto", resultado["bloqueos"])

    def test_caso_feliz_aprobada(self):
        DocumentoConductor.objects.create(
            conductor=self.conductor_base,
            tipo_documento="Licencia de conducir",
            fecha_emision=self.hoy - datetime.timedelta(days=100),
            fecha_vencimiento=self.hoy + datetime.timedelta(days=365),
            estado_documento="Vigente",
        )
        DocumentoVehiculo.objects.create(
            vehiculo=self.vehiculo_base,
            tipo_documento="Revisión técnica",
            fecha_emision=self.hoy - datetime.timedelta(days=100),
            fecha_vencimiento=self.hoy + datetime.timedelta(days=365),
            estado_documento="Vigente",
        )
        DocumentoVehiculo.objects.create(
            vehiculo=self.vehiculo_base,
            tipo_documento="Seguro",
            fecha_emision=self.hoy - datetime.timedelta(days=100),
            fecha_vencimiento=self.hoy + datetime.timedelta(days=365),
            estado_documento="Vigente",
        )
        resultado = self._validar()
        self.assertEqual(resultado["veredicto"], "Aprobada")
        self.assertEqual(resultado["bloqueos"], [])
        self.assertEqual(resultado["observaciones"], [])
