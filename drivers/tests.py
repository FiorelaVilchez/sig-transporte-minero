import datetime
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from core.models import PerfilUsuario
from drivers.models import Conductor
from service_requests.models import SolicitudServicio
from assignments.models import Asignacion

class ConductorViewsTestCase(TestCase):
    def setUp(self):
        # Create users with different roles
        self.admin_user = User.objects.create_user(username='admin', password='password')
        PerfilUsuario.objects.create(usuario=self.admin_user, rol='Administrador de operaciones')
        
        self.supervisor_user = User.objects.create_user(username='supervisor', password='password')
        PerfilUsuario.objects.create(usuario=self.supervisor_user, rol='Supervisor')
        
        self.gerencia_user = User.objects.create_user(username='gerencia', password='password')
        PerfilUsuario.objects.create(usuario=self.gerencia_user, rol='Gerencia')

        # Create test conductor
        self.conductor = Conductor.objects.create(
            nombres="Juan",
            apellidos="Pérez",
            licencia="Q12345678",
            especialidad="Camión",
            estado="Disponible",
            dni="12345678",
            fecha_nacimiento=datetime.date(1990, 1, 1),
            fecha_ingreso=datetime.date(2020, 1, 1),
        )

    def test_list_view_permissions(self):
        # Admin can view
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('drivers:conductor_list'))
        self.assertEqual(response.status_code, 200)

        # Supervisor can view
        self.client.force_login(self.supervisor_user)
        response = self.client.get(reverse('drivers:conductor_list'))
        self.assertEqual(response.status_code, 200)

        # Gerencia cannot view
        self.client.force_login(self.gerencia_user)
        response = self.client.get(reverse('drivers:conductor_list'))
        self.assertEqual(response.status_code, 403)

    def test_detail_view_permissions(self):
        self.client.force_login(self.supervisor_user)
        response = self.client.get(reverse('drivers:conductor_detail', args=[self.conductor.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pérez")

    def test_create_and_update_permissions(self):
        # Supervisor cannot create (403)
        self.client.force_login(self.supervisor_user)
        response = self.client.get(reverse('drivers:conductor_create'))
        self.assertEqual(response.status_code, 403)

        # Admin can create
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('drivers:conductor_create'))
        self.assertEqual(response.status_code, 200)
        
        # Admin post create
        post_data = {
            'nombres': 'Carlos',
            'apellidos': 'Soto',
            'dni': '87654321',
            'licencia': 'Q87654321',
            'especialidad': 'Bus',
            'estado': 'Disponible',
            'fecha_nacimiento': '1985-05-12',
            'fecha_ingreso': '2021-02-15',
        }
        response = self.client.post(reverse('drivers:conductor_create'), post_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Conductor.objects.filter(dni='87654321').exists())

    def test_dar_baja(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(reverse('drivers:conductor_dar_baja', args=[self.conductor.pk]))
        self.assertEqual(response.status_code, 302)
        self.conductor.refresh_from_db()
        self.assertEqual(self.conductor.estado, 'De baja')

    def test_delete_protection(self):
        # Physical delete works when no assignments
        self.client.force_login(self.admin_user)
        response = self.client.post(reverse('drivers:conductor_delete', args=[self.conductor.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Conductor.objects.filter(pk=self.conductor.pk).exists())

        # Re-create conductor and assign
        cond2 = Conductor.objects.create(
            nombres="Pedro",
            apellidos="Gómez",
            licencia="Q11111111",
            especialidad="Bus",
            estado="Disponible",
            dni="11111111",
            fecha_nacimiento=datetime.date(1990, 1, 1),
            fecha_ingreso=datetime.date(2020, 1, 1),
        )
        solicitud = SolicitudServicio.objects.create(
            cliente="Cliente Test",
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
            conductor=cond2,
            estado_asignacion="Pendiente"
        )

        # Try to delete cond2 -> protected error redirect to detail with error message
        response = self.client.post(reverse('drivers:conductor_delete', args=[cond2.pk]))
        self.assertEqual(response.status_code, 302)
        # Should redirect to detail view
        self.assertRedirects(response, reverse('drivers:conductor_detail', args=[cond2.pk]))
        self.assertTrue(Conductor.objects.filter(pk=cond2.pk).exists())
