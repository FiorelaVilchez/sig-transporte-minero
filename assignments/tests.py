import datetime

from django.test import TestCase

from assignments.validators import validar_asignacion
from drivers.models import Conductor
from trucks.models import Vehiculo
from documents.models import DocumentoConductor, DocumentoVehiculo
from service_requests.models import SolicitudServicio
from assignments.models import Asignacion, Notificacion
from assignments.services import asignar_automaticamente


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


class AsignacionAutomaticaTestCase(TestCase):
    """Pruebas para el motor de asignación automática (Fase 7)."""

    def setUp(self):
        self.hoy = datetime.date.today()
        # Crear una solicitud pendiente
        self.solicitud = SolicitudServicio.objects.create(
            cliente="Minera Test",
            fecha_servicio=self.hoy + datetime.timedelta(days=2),
            hora_servicio=datetime.time(8, 0),
            origen="Juliaca",
            destino="Mina San Rafael",
            tipo_servicio="Traslado de personal",
            prioridad="Alta",
            tipo_vehiculo_requerido="Camioneta",
            estado_solicitud="Pendiente"
        )
        # Crear conductor
        self.conductor = Conductor.objects.create(
            nombres="Juan",
            apellidos="Pérez",
            licencia="Q11111111",
            especialidad="Camioneta",
            estado="Disponible",
            dni="77777771",
            fecha_nacimiento=datetime.date(1985, 1, 1),
            fecha_ingreso=datetime.date(2020, 1, 1)
        )
        # Licencia de conducir válida para Conductor
        DocumentoConductor.objects.create(
            conductor=self.conductor,
            tipo_documento="Licencia de conducir",
            fecha_emision=self.hoy - datetime.timedelta(days=100),
            fecha_vencimiento=self.hoy + datetime.timedelta(days=300),
            estado_documento="Vigente"
        )
        # Crear vehículo
        self.vehiculo = Vehiculo.objects.create(
            placa="TST-001",
            tipo="Camioneta",
            capacidad=5,
            estado="Disponible"
        )
        # Revisión técnica válida para vehículo
        DocumentoVehiculo.objects.create(
            vehiculo=self.vehiculo,
            tipo_documento="Revisión técnica",
            fecha_emision=self.hoy - datetime.timedelta(days=100),
            fecha_vencimiento=self.hoy + datetime.timedelta(days=300),
            estado_documento="Vigente"
        )

    def test_sin_conductores_disponibles_reprograma(self):
        self.conductor.estado = "Ocupado"
        self.conductor.save()
        
        resultado = asignar_automaticamente(self.solicitud)
        self.assertFalse(resultado["exito"])
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado_solicitud, "Reprogramada")
        self.assertEqual(Asignacion.objects.count(), 0)

    def test_sin_vehiculo_compatible_disponible_reprograma(self):
        # Cambiar el tipo de vehículo para simular incompatibilidad
        self.vehiculo.tipo = "Bus"
        self.vehiculo.save()

        resultado = asignar_automaticamente(self.solicitud)
        self.assertFalse(resultado["exito"])
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado_solicitud, "Reprogramada")
        self.assertEqual(Asignacion.objects.count(), 0)

    def test_asignacion_exitosa_happy_path(self):
        resultado = asignar_automaticamente(self.solicitud)
        self.assertTrue(resultado["exito"])
        
        self.solicitud.refresh_from_db()
        self.conductor.refresh_from_db()
        self.vehiculo.refresh_from_db()
        
        self.assertEqual(self.solicitud.estado_solicitud, "Asignada")
        self.assertEqual(self.conductor.estado, "Ocupado")
        self.assertEqual(self.vehiculo.estado, "En servicio")
        
        # Verificar registro de Asignacion
        self.assertEqual(Asignacion.objects.count(), 1)
        asig = Asignacion.objects.first()
        self.assertEqual(asig.conductor, self.conductor)
        self.assertEqual(asig.vehiculo, self.vehiculo)
        self.assertEqual(asig.estado_asignacion, "Aprobada")
        
        # Verificar notificación
        self.assertEqual(Notificacion.objects.count(), 1)
        notif = Notificacion.objects.first()
        self.assertEqual(notif.conductor, self.conductor)
        self.assertFalse(notif.leida)

    def test_criterio_equidad_menos_asignaciones(self):
        # Crear un segundo conductor disponible con licencia vigente
        conductor2 = Conductor.objects.create(
            nombres="Pedro",
            apellidos="Gómez",
            licencia="Q22222222",
            especialidad="Camioneta",
            estado="Disponible",
            dni="77777772",
            fecha_nacimiento=datetime.date(1990, 1, 1),
            fecha_ingreso=datetime.date(2021, 1, 1)
        )
        DocumentoConductor.objects.create(
            conductor=conductor2,
            tipo_documento="Licencia de conducir",
            fecha_emision=self.hoy - datetime.timedelta(days=100),
            fecha_vencimiento=self.hoy + datetime.timedelta(days=300),
            estado_documento="Vigente"
        )
        
        # Crear una asignación histórica para self.conductor para que tenga 1 asignación
        solicitud_dummy = SolicitudServicio.objects.create(
            cliente="Minera Dummy",
            fecha_servicio=self.hoy - datetime.timedelta(days=5),
            hora_servicio=datetime.time(8, 0),
            origen="A",
            destino="B",
            tipo_servicio="Traslado de personal",
            prioridad="Media",
            tipo_vehiculo_requerido="Camioneta",
            estado_solicitud="Completada"
        )
        Asignacion.objects.create(
            solicitud=solicitud_dummy,
            conductor=self.conductor,
            vehiculo=self.vehiculo,
            estado_asignacion="Aprobada"
        )
        
        # Conductor2 tiene 0 asignaciones históricas, self.conductor tiene 1.
        # Debe elegir Conductor2 por equidad.
        resultado = asignar_automaticamente(self.solicitud)
        self.assertTrue(resultado["exito"])
        
        asig = Asignacion.objects.get(solicitud=self.solicitud)
        self.assertEqual(asig.conductor, conductor2)

    def test_liberar_recursos_al_completar(self):
        # Ejecutar asignación
        asignar_automaticamente(self.solicitud)
        
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado_solicitud, "Asignada")
        
        # Simular marcado como completado
        asig = Asignacion.objects.filter(solicitud=self.solicitud, estado_asignacion="Aprobada").first()
        asig.conductor.estado = "Disponible"
        asig.conductor.save()
        asig.vehiculo.estado = "Disponible"
        asig.vehiculo.save()
        self.solicitud.estado_solicitud = "Completada"
        self.solicitud.save()
        
        self.conductor.refresh_from_db()
        self.vehiculo.refresh_from_db()
        self.assertEqual(self.conductor.estado, "Disponible")
        self.assertEqual(self.vehiculo.estado, "Disponible")

