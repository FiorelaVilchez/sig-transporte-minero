import datetime

from django.contrib.auth.models import User
from django.test import TestCase

from alerts.models import Alerta
from assignments.models import Asignacion
from core.models import PerfilUsuario
from dashboard.services import (
    get_dashboard_kpis,
    kpi_alertas_riesgo_alto,
    kpi_asignaciones_aprobadas,
    kpi_asignaciones_por_conductor,
    kpi_asignaciones_por_vehiculo,
    kpi_asignaciones_rechazadas,
    kpi_documentos_por_vencer,
    kpi_documentos_vencidos,
    kpi_solicitudes_por_estado,
    kpi_total_asignaciones,
)
from documents.models import DocumentoConductor, DocumentoVehiculo
from drivers.models import Conductor
from service_requests.models import SolicitudServicio
from trucks.models import Vehiculo


class DashboardKPIsTestCase(TestCase):
    """Escenario controlado para verificar los 8 indicadores KPI."""

    def setUp(self):
        self.hoy = datetime.date.today()

        self.conductor_a = Conductor.objects.create(
            nombres="Juan",
            apellidos="Pérez",
            licencia="LIC001",
            especialidad="Camioneta",
            estado="Disponible",
            dni="11111111",
            fecha_nacimiento=datetime.date(1990, 1, 1),
            fecha_ingreso=datetime.date(2020, 1, 1),
        )
        self.conductor_b = Conductor.objects.create(
            nombres="María",
            apellidos="López",
            licencia="LIC002",
            especialidad="Bus",
            estado="Disponible",
            dni="22222222",
            fecha_nacimiento=datetime.date(1988, 5, 10),
            fecha_ingreso=datetime.date(2019, 3, 1),
        )
        self.conductor_c = Conductor.objects.create(
            nombres="Carlos",
            apellidos="Quispe",
            licencia="LIC003",
            especialidad="Volquete",
            estado="Disponible",
            dni="33333333",
            fecha_nacimiento=datetime.date(1985, 8, 20),
            fecha_ingreso=datetime.date(2018, 6, 15),
        )

        self.vehiculo_a = Vehiculo.objects.create(
            placa="ABC-123",
            tipo="Camioneta",
            capacidad=5,
            estado="Disponible",
        )
        self.vehiculo_b = Vehiculo.objects.create(
            placa="XYZ-789",
            tipo="Bus",
            capacidad=40,
            estado="Disponible",
        )

        self.solicitud_pendiente = self._crear_solicitud("Cliente A", "Pendiente")
        self.solicitud_asignada = self._crear_solicitud("Cliente B", "Asignada")
        self.solicitud_reprogramada = self._crear_solicitud("Cliente C", "Reprogramada")
        self.solicitud_completada = self._crear_solicitud("Cliente D", "Completada")
        self.solicitud_cancelada = self._crear_solicitud("Cliente E", "Cancelada")

        Asignacion.objects.create(
            solicitud=self.solicitud_asignada,
            conductor=self.conductor_a,
            vehiculo=self.vehiculo_a,
            estado_asignacion="Aprobada",
        )
        Asignacion.objects.create(
            solicitud=self.solicitud_completada,
            conductor=self.conductor_a,
            vehiculo=self.vehiculo_a,
            estado_asignacion="Aprobada",
        )
        Asignacion.objects.create(
            solicitud=self.solicitud_reprogramada,
            conductor=self.conductor_b,
            vehiculo=self.vehiculo_b,
            estado_asignacion="Rechazada",
        )
        Asignacion.objects.create(
            solicitud=self.solicitud_pendiente,
            conductor=self.conductor_c,
            vehiculo=self.vehiculo_b,
            estado_asignacion="Observada",
        )

        DocumentoConductor.objects.create(
            conductor=self.conductor_a,
            tipo_documento="Licencia",
            fecha_emision=self.hoy - datetime.timedelta(days=400),
            fecha_vencimiento=self.hoy - datetime.timedelta(days=10),
            estado_documento="Vencido",
        )
        DocumentoConductor.objects.create(
            conductor=self.conductor_b,
            tipo_documento="Examen médico",
            fecha_emision=self.hoy - datetime.timedelta(days=300),
            fecha_vencimiento=self.hoy + datetime.timedelta(days=15),
            estado_documento="Por vencer",
        )
        DocumentoVehiculo.objects.create(
            vehiculo=self.vehiculo_a,
            tipo_documento="SOAT",
            fecha_emision=self.hoy - datetime.timedelta(days=200),
            fecha_vencimiento=self.hoy - datetime.timedelta(days=3),
            estado_documento="Vencido",
        )
        DocumentoVehiculo.objects.create(
            vehiculo=self.vehiculo_b,
            tipo_documento="Revisión técnica",
            fecha_emision=self.hoy - datetime.timedelta(days=350),
            fecha_vencimiento=self.hoy + datetime.timedelta(days=20),
            estado_documento="Por vencer",
        )

        Alerta.objects.create(
            tipo_alerta="Documento vencido",
            nivel_riesgo="Alto",
            estado_alerta="Activa",
            mensaje="Alerta alta 1",
        )
        Alerta.objects.create(
            tipo_alerta="Documento vencido",
            nivel_riesgo="Alto",
            estado_alerta="Activa",
            mensaje="Alerta alta 2",
        )
        Alerta.objects.create(
            tipo_alerta="Documento por vencer",
            nivel_riesgo="Medio",
            estado_alerta="Activa",
            mensaje="Alerta media",
        )
        Alerta.objects.create(
            tipo_alerta="Documento vencido",
            nivel_riesgo="Alto",
            estado_alerta="Resuelta",
            mensaje="Alerta resuelta",
        )

    def _crear_solicitud(self, cliente, estado):
        return SolicitudServicio.objects.create(
            cliente=cliente,
            fecha_servicio=self.hoy + datetime.timedelta(days=1),
            hora_servicio=datetime.time(8, 0),
            origen="Planta",
            destino="Mina",
            tipo_servicio="Traslado de personal",
            prioridad="Media",
            tipo_vehiculo_requerido="Camioneta",
            estado_solicitud=estado,
        )

    def test_kpi_total_asignaciones(self):
        self.assertEqual(kpi_total_asignaciones(), 4)

    def test_kpi_asignaciones_aprobadas(self):
        self.assertEqual(kpi_asignaciones_aprobadas(), 2)

    def test_kpi_asignaciones_rechazadas(self):
        self.assertEqual(kpi_asignaciones_rechazadas(), 1)

    def test_kpi_documentos_vencidos(self):
        self.assertEqual(kpi_documentos_vencidos(), 2)

    def test_kpi_documentos_por_vencer(self):
        self.assertEqual(kpi_documentos_por_vencer(), 2)

    def test_kpi_alertas_riesgo_alto(self):
        self.assertEqual(kpi_alertas_riesgo_alto(), 2)

    def test_kpi_solicitudes_por_estado(self):
        self.assertEqual(
            kpi_solicitudes_por_estado(),
            {
                "Pendiente": 1,
                "Asignada": 1,
                "Reprogramada": 1,
                "Completada": 1,
                "Cancelada": 1,
            },
        )

    def test_kpi_asignaciones_por_conductor(self):
        resultado = kpi_asignaciones_por_conductor()
        self.assertEqual(len(resultado), 3)
        self.assertEqual(resultado[0], {"conductor": "Pérez, Juan", "total": 2})
        self.assertEqual(resultado[1]["total"], 1)
        self.assertEqual(resultado[2]["total"], 1)

    def test_kpi_asignaciones_por_vehiculo(self):
        resultado = kpi_asignaciones_por_vehiculo()
        self.assertEqual(len(resultado), 2)
        self.assertEqual(resultado[0], {"vehiculo": "ABC-123", "total": 2})
        self.assertEqual(resultado[1], {"vehiculo": "XYZ-789", "total": 2})

    def test_get_dashboard_kpis_agrega_todos_los_indicadores(self):
        kpis = get_dashboard_kpis()
        self.assertEqual(kpis["total_asignaciones"], 4)
        self.assertEqual(kpis["asignaciones_aprobadas"], 2)
        self.assertEqual(kpis["asignaciones_rechazadas"], 1)
        self.assertEqual(kpis["documentos_vencidos"], 2)
        self.assertEqual(kpis["documentos_por_vencer"], 2)
        self.assertEqual(kpis["alertas_riesgo_alto"], 2)
        self.assertEqual(kpis["solicitudes_por_estado"]["Pendiente"], 1)
        self.assertEqual(len(kpis["asignaciones_por_conductor"]), 3)
        self.assertEqual(len(kpis["asignaciones_por_vehiculo"]), 2)


class KpiAsignacionesPorConductorLimiteTestCase(TestCase):
    """Verifica orden descendente y límite de 10 conductores."""

    def setUp(self):
        self.hoy = datetime.date.today()
        self.solicitud = SolicitudServicio.objects.create(
            cliente="Cliente Test",
            fecha_servicio=self.hoy,
            hora_servicio=datetime.time(9, 0),
            origen="A",
            destino="B",
            tipo_servicio="Traslado de carga",
            prioridad="Baja",
            tipo_vehiculo_requerido="Camión",
            estado_solicitud="Pendiente",
        )

        for indice in range(11):
            conductor = Conductor.objects.create(
                nombres=f"Nombre{indice}",
                apellidos=f"Apellido{indice:02d}",
                licencia=f"LIM{indice:03d}",
                especialidad="Camión",
                estado="Disponible",
                dni=f"{indice:08d}",
                fecha_nacimiento=datetime.date(1990, 1, 1),
                fecha_ingreso=datetime.date(2020, 1, 1),
            )
            cantidad = 11 - indice
            for _ in range(cantidad):
                Asignacion.objects.create(
                    solicitud=self.solicitud,
                    conductor=conductor,
                    estado_asignacion="Aprobada",
                )

    def test_top_10_ordenado_de_mayor_a_menor(self):
        resultado = kpi_asignaciones_por_conductor()
        self.assertEqual(len(resultado), 10)
        totales = [item["total"] for item in resultado]
        self.assertEqual(totales, sorted(totales, reverse=True))
        self.assertEqual(resultado[0]["conductor"], "Apellido00, Nombre0")
        self.assertEqual(resultado[0]["total"], 11)
        self.assertEqual(resultado[-1]["total"], 2)


class DashboardVistasTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin_ops', password='pass')
        PerfilUsuario.objects.create(
            usuario=self.admin,
            rol='Administrador de operaciones',
        )
        self.supervisor = User.objects.create_user(username='super', password='pass')
        PerfilUsuario.objects.create(
            usuario=self.supervisor,
            rol='Supervisor',
        )
        self.gerencia = User.objects.create_user(username='gerencia', password='pass')
        PerfilUsuario.objects.create(
            usuario=self.gerencia,
            rol='Gerencia',
        )
        self.conductor_user = User.objects.create_user(username='cond', password='pass')
        PerfilUsuario.objects.create(
            usuario=self.conductor_user,
            rol='Conductor',
        )

    def test_gerencia_redirige_al_dashboard_tras_login(self):
        response = self.client.post(
            '/login/',
            {'username': 'gerencia', 'password': 'pass'},
        )
        self.assertRedirects(response, '/dashboard/', fetch_redirect_response=False)

    def test_conductor_sin_acceso_al_dashboard(self):
        self.client.force_login(self.conductor_user)
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 403)

    def test_supervisor_acceso_solo_lectura_sin_boton_actualizar(self):
        self.client.force_login(self.supervisor)
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['puede_actualizar'])

    def test_admin_puede_actualizar_indicadores(self):
        self.client.force_login(self.admin)
        response = self.client.post('/dashboard/actualizar/')
        self.assertRedirects(response, '/dashboard/')
        self.assertIn('dashboard_ultima_actualizacion', self.client.session)

    def test_reportes_gerenciales_placeholder_accesible(self):
        self.client.force_login(self.gerencia)
        response = self.client.get('/dashboard/reportes/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Disponible próximamente')
