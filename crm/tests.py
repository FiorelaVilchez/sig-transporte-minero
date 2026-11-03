from decimal import Decimal
from unittest import mock

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from assignments.models import Asignacion
from assignments.services import asignar_automaticamente, completar_servicio, iniciar_ruta
from assignments.tests_v2 import EscenarioV2
from billing.models import Tarifa, Valorizacion
from core.config_forms import ClienteForm
from core.models import PerfilUsuario
from trucks.models import TipoVehiculo

from .models import Cliente


class ClienteTests(TestCase):
    def test_obtener_no_duplica_por_mayusculas_ni_espacios(self):
        a = Cliente.obtener('Minera  Andina S.A.C.')
        b = Cliente.obtener('minera andina s.a.c.')
        self.assertEqual(a, b)
        self.assertEqual(Cliente.objects.count(), 1)

    def test_ruc_valido_y_vacio_se_guarda_como_nulo(self):
        c = Cliente(razon_social='Minera Sur', ruc='2012345678')
        with self.assertRaises(ValidationError):
            c.full_clean()
        Cliente.objects.create(razon_social='Minera Uno', ruc='')
        Cliente.objects.create(razon_social='Minera Dos', ruc='')
        self.assertEqual(Cliente.objects.filter(ruc__isnull=True).count(), 2)

    def test_formulario_rechaza_razon_social_repetida(self):
        Cliente.objects.create(razon_social='Minera Sur S.A.')
        form = ClienteForm(data={'razon_social': 'minera sur s.a.', 'activo': True})
        self.assertFalse(form.is_valid())
        self.assertIn('razon_social', form.errors)

    def test_tarifa_se_busca_por_cliente_y_no_por_texto(self):
        cliente = Cliente.objects.create(razon_social='Minera X S.A.')
        camioneta = TipoVehiculo.objects.get(nombre='Camioneta')
        tarifa = Tarifa.objects.create(cliente=cliente, tipo_vehiculo=camioneta, tarifa_base=Decimal('500'),
                                       km_incluidos=300, precio_km_adicional=Decimal('2.50'))
        self.assertEqual(Tarifa.buscar(cliente, camioneta), tarifa)
        self.assertIsNone(Tarifa.buscar(Cliente.objects.create(razon_social='Minera X SA'), camioneta))

    def test_finanzas_registra_cliente_desde_configuracion(self):
        user = User.objects.create_user('finanzas', password='clave12345')
        PerfilUsuario.objects.create(usuario=user, rol='Finanzas')
        self.client.login(username='finanzas', password='clave12345')
        r = self.client.post(reverse('core:catalogo_nuevo', args=['clientes']),
                             {'razon_social': 'Minera Nueva S.A.C.', 'ruc': '20123456789', 'activo': 'on'})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Cliente.objects.filter(ruc='20123456789').exists())
        self.assertContains(self.client.get(reverse('core:configuracion')), 'Minera Nueva S.A.C.')


class CierreAtomicoTests(EscenarioV2):
    def setUp(self):
        super().setUp()
        asignar_automaticamente(self.solicitud)
        self.asignacion = Asignacion.objects.get(solicitud=self.solicitud)
        Asignacion.objects.filter(pk=self.asignacion.pk).update(estado_operativo='Listo para salir', km_inicial=1000)
        self.asignacion.refresh_from_db()
        iniciar_ruta(self.asignacion)

    def test_si_falla_la_valorizacion_no_se_cierra_el_servicio(self):
        with mock.patch('billing.services.generar_valorizacion', side_effect=RuntimeError('falla')):
            with self.assertRaises(RuntimeError):
                completar_servicio(self.asignacion, km_final=1400)
        self.asignacion.refresh_from_db()
        self.solicitud.refresh_from_db()
        self.conductor.refresh_from_db()
        self.assertEqual(self.asignacion.estado_operativo, 'En ruta')
        self.assertEqual(self.solicitud.estado_solicitud, 'Asignada')
        self.assertEqual(self.conductor.estado, 'Ocupado')
        self.assertFalse(Valorizacion.objects.exists())
