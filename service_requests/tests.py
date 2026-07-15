import datetime
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from core.models import PerfilUsuario
from .models import SolicitudServicio

class SolicitudServicioViewsTestCase(TestCase):
    def setUp(self):
        # Create users
        self.admin_user = User.objects.create_user(username='admin', password='password')
        PerfilUsuario.objects.create(usuario=self.admin_user, rol='Administrador de operaciones')
        
        self.supervisor_user = User.objects.create_user(username='supervisor', password='password')
        PerfilUsuario.objects.create(usuario=self.supervisor_user, rol='Supervisor')
        
        self.gerencia_user = User.objects.create_user(username='gerencia', password='password')
        PerfilUsuario.objects.create(usuario=self.gerencia_user, rol='Gerencia')

        # Create test requests
        self.req1 = SolicitudServicio.objects.create(
            cliente="Cliente A",
            fecha_servicio=datetime.date.today() + datetime.timedelta(days=2),
            hora_servicio=datetime.time(14, 0),
            origen="Punto A",
            destino="Punto B",
            tipo_servicio="Traslado de personal",
            prioridad="Alta",
            tipo_vehiculo_requerido="Bus",
            estado_solicitud="Pendiente"
        )
        self.req2 = SolicitudServicio.objects.create(
            cliente="Cliente B",
            fecha_servicio=datetime.date.today() + datetime.timedelta(days=1),
            hora_servicio=datetime.time(8, 0),
            origen="Punto C",
            destino="Punto D",
            tipo_servicio="Traslado de carga",
            prioridad="Media",
            tipo_vehiculo_requerido="Camión",
            estado_solicitud="Pendiente"
        )

    def test_list_view_permissions(self):
        # Admin can view
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('service_requests:solicitud_list'))
        self.assertEqual(response.status_code, 200)

        # Supervisor can view
        self.client.force_login(self.supervisor_user)
        response = self.client.get(reverse('service_requests:solicitud_list'))
        self.assertEqual(response.status_code, 200)

        # Gerencia can view
        self.client.force_login(self.gerencia_user)
        response = self.client.get(reverse('service_requests:solicitud_list'))
        self.assertEqual(response.status_code, 200)

    def test_list_view_ordering(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('service_requests:solicitud_list'))
        self.assertEqual(response.status_code, 200)
        
        # Verify that req2 (which is scheduled 1 day from now) appears before req1 (which is scheduled 2 days from now)
        items = list(response.context['page_obj'])
        self.assertEqual(items[0].pk, self.req2.pk)
        self.assertEqual(items[1].pk, self.req1.pk)

    def test_create_and_edit_permissions(self):
        # Supervisor cannot create (403)
        self.client.force_login(self.supervisor_user)
        response = self.client.get(reverse('service_requests:solicitud_create'))
        self.assertEqual(response.status_code, 403)

        # Admin can create
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('service_requests:solicitud_create'))
        self.assertEqual(response.status_code, 200)
        
        # Post data
        post_data = {
            'cliente': 'Cliente C',
            'fecha_servicio': '2026-08-15',
            'hora_servicio': '10:30',
            'origen': 'Origen C',
            'destino': 'Destino C',
            'tipo_servicio': 'Traslado mixto',
            'prioridad': 'Baja',
            'tipo_vehiculo_requerido': 'Camioneta',
            'estado_solicitud': 'Pendiente',
        }
        response = self.client.post(reverse('service_requests:solicitud_create'), post_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(SolicitudServicio.objects.filter(cliente='Cliente C').exists())
