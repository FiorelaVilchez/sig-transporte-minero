import datetime
from decimal import Decimal
from io import StringIO
from unittest import skipUnless

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import TestCase

from assignments.models import Asignacion
from billing.models import Valorizacion
from drivers.models import Conductor
from service_requests.models import CambioSolicitud, SolicitudServicio
from trucks.models import Vehiculo


class HistoricoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_data', stdout=StringIO())

    def generar(self, *args):
        call_command('generar_historico', '--desde', '2026-06-01', '--hasta', '2026-06-14', *args, stdout=StringIO())

    def test_cada_servicio_completado_tiene_su_valorizacion(self):
        estados_conductor = dict(Conductor.objects.values_list('pk', 'estado'))
        estados_vehiculo = dict(Vehiculo.objects.values_list('pk', 'estado'))
        self.generar()
        historicas = SolicitudServicio.objects.filter(fecha_servicio__range=('2026-06-01', '2026-06-14'))
        self.assertGreater(historicas.count(), 10)
        completadas = historicas.filter(estado_solicitud='Completada')
        self.assertEqual(Valorizacion.objects.filter(solicitud__in=completadas).count(), completadas.count())
        self.assertFalse(historicas.filter(estado_solicitud__in=['Pendiente', 'Asignada', 'Reprogramada']).exists())
        cerradas = Asignacion.objects.filter(solicitud__in=historicas, estado_operativo='Completado')
        self.assertFalse(cerradas.filter(fin_real__date__gt=datetime.date(2026, 6, 15)).exists())
        self.assertEqual(dict(Conductor.objects.values_list('pk', 'estado')), estados_conductor)
        self.assertEqual(dict(Vehiculo.objects.values_list('pk', 'estado')), estados_vehiculo)

    def test_no_duplica_el_historial_y_se_puede_reiniciar(self):
        self.generar()
        total = SolicitudServicio.objects.count()
        with self.assertRaises(CommandError):
            self.generar()
        self.generar('--reiniciar')
        self.assertEqual(SolicitudServicio.objects.count(), total)
        self.assertTrue(CambioSolicitud.objects.filter(motivo__contains='historial').exists())


@skipUnless(connection.vendor == 'postgresql', 'El Data Mart solo se carga en PostgreSQL')
class DataMartTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_data', stdout=StringIO())
        call_command('generar_historico', '--desde', '2026-07-01', '--hasta', '2026-07-21', stdout=StringIO())
        call_command('cargar_datamart', stdout=StringIO())

    def uno(self, sql):
        with connection.cursor() as cursor:
            cursor.execute(sql)
            return cursor.fetchone()

    def test_una_fila_por_servicio_cerrado(self):
        cerrados = Asignacion.objects.filter(estado_operativo__in=['Completado', 'Con incidencia']).count()
        self.assertEqual(self.uno('SELECT count(*) FROM datamart.fact_servicio')[0], cerrados)

    def test_el_ingreso_cuadra_con_las_valorizaciones(self):
        total = sum(v.total for v in Valorizacion.objects.all())
        self.assertEqual(self.uno('SELECT sum(monto_total) FROM datamart.fact_servicio')[0], total)

    def test_cumplimiento_y_dimensiones(self):
        cumplidos, cerrados = self.uno('SELECT sum(servicio_cumplido), count(*) FROM datamart.fact_servicio')
        completados = Asignacion.objects.filter(estado_operativo='Completado').count()
        self.assertEqual(cumplidos, completados)
        self.assertLessEqual(cumplidos, cerrados)
        dias = self.uno('SELECT count(*) FROM datamart.dim_tiempo WHERE sk_tiempo = 20260715')[0]
        self.assertEqual(dias, 1)
        sin_ruta = self.uno('SELECT count(*) FROM datamart.fact_servicio f '
                            'LEFT JOIN datamart.dim_ruta r USING (sk_ruta) WHERE r.sk_ruta IS NULL')[0]
        self.assertEqual(sin_ruta, 0)

    def test_se_puede_volver_a_cargar(self):
        antes = self.uno('SELECT count(*) FROM datamart.fact_servicio')[0]
        call_command('cargar_datamart', stdout=StringIO())
        self.assertEqual(self.uno('SELECT count(*) FROM datamart.fact_servicio')[0], antes)
        self.assertGreater(self.uno('SELECT sum(km_recorridos) FROM datamart.fact_servicio')[0], 0)
        self.assertGreaterEqual(self.uno('SELECT min(monto_total) FROM datamart.fact_servicio')[0], Decimal('0'))
