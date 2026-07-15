import datetime
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from core.models import PerfilUsuario
from trucks.models import Vehiculo
from service_requests.models import SolicitudServicio
from assignments.models import Asignacion

class VehiculoViewsTestCase(TestCase):
    def setUp(self):
        # Create users
        self.admin_user = User.objects.create_user(username='admin', password='password')
        PerfilUsuario.objects.create(usuario=self.admin_user, rol='Administrador de operaciones')
        
        self.supervisor_user = User.objects.create_user(username='supervisor', password='password')
        PerfilUsuario.objects.create(usuario=self.supervisor_user, rol='Supervisor')
        
        self.gerencia_user = User.objects.create_user(username='gerencia', password='password')
        PerfilUsuario.objects.create(usuario=self.gerencia_user, rol='Gerencia')

        # Create test vehicle
        self.vehiculo = Vehiculo.objects.create(
            placa="ABC-123",
            tipo="Camioneta",
            capacidad=5,
            estado="Disponible",
            revision_tecnica_vigente=True,
            seguro_vigente=True,
            homologacion="HOM-123",
            mantenimiento_programado=datetime.date.today() + datetime.timedelta(days=10),
        )

    def test_list_view_permissions(self):
        # Admin can view
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('trucks:vehiculo_list'))
        self.assertEqual(response.status_code, 200)

        # Supervisor can view
        self.client.force_login(self.supervisor_user)
        response = self.client.get(reverse('trucks:vehiculo_list'))
        self.assertEqual(response.status_code, 200)

        # Gerencia cannot view
        self.client.force_login(self.gerencia_user)
        response = self.client.get(reverse('trucks:vehiculo_list'))
        self.assertEqual(response.status_code, 403)

    def test_detail_view_permissions(self):
        self.client.force_login(self.supervisor_user)
        response = self.client.get(reverse('trucks:vehiculo_detail', args=[self.vehiculo.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ABC-123")

    def test_create_and_update_permissions(self):
        # Supervisor cannot create (403)
        self.client.force_login(self.supervisor_user)
        response = self.client.get(reverse('trucks:vehiculo_create'))
        self.assertEqual(response.status_code, 403)

        # Admin can create
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('trucks:vehiculo_create'))
        self.assertEqual(response.status_code, 200)
        
        # Admin post create
        post_data = {
            'placa': 'XYZ-789',
            'tipo': 'Bus',
            'capacidad': 40,
            'estado': 'Disponible',
            'revision_tecnica_vigente': True,
            'seguro_vigente': True,
            'homologacion': 'HOM-456',
            'mantenimiento_programado': '2026-08-01',
        }
        response = self.client.post(reverse('trucks:vehiculo_create'), post_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Vehiculo.objects.filter(placa='XYZ-789').exists())

    def test_dar_baja(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(reverse('trucks:vehiculo_dar_baja', args=[self.vehiculo.pk]))
        self.assertEqual(response.status_code, 302)
        self.vehiculo.refresh_from_db()
        self.assertEqual(self.vehiculo.estado, 'De baja')

    def test_delete_protection(self):
        # Physical delete works when no assignments
        self.client.force_login(self.admin_user)
        response = self.client.post(reverse('trucks:vehiculo_delete', args=[self.vehiculo.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Vehiculo.objects.filter(pk=self.vehiculo.pk).exists())

        # Re-create vehicle and assign
        v2 = Vehiculo.objects.create(
            placa="FFF-444",
            tipo="Bus",
            capacidad=40,
            estado="Disponible",
            revision_tecnica_vigente=True,
            seguro_vigente=True,
        )
        solicitud = SolicitudServicio.objects.create(
            cliente="Cliente Test 2",
            fecha_servicio=datetime.date.today(),
            hora_servicio=datetime.time(10, 0),
            origen="Lima",
            destino="Arequipa",
            tipo_servicio="Traslado de personal",
            prioridad="Alta",
            tipo_vehiculo_requerido="Bus",
            estado_solicitud="Pendiente"
        )
        Asignacion.objects.create(
            solicitud=solicitud,
            vehiculo=v2,
            estado_asignacion="Pendiente"
        )

        # Try to delete v2 -> protected error redirect to detail with error message
        response = self.client.post(reverse('trucks:vehiculo_delete', args=[v2.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('trucks:vehiculo_detail', args=[v2.pk]))
        self.assertTrue(Vehiculo.objects.filter(pk=v2.pk).exists())
