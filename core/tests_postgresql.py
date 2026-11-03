"""Pruebas de los objetos que la migración core 0003 crea solo en PostgreSQL."""
from decimal import Decimal
from unittest import skipUnless

from django.db import DataError, IntegrityError, InternalError, connection, transaction

from assignments.models import Asignacion
from assignments.services import asignar_automaticamente, iniciar_ruta
from assignments.tests_v2 import EscenarioV2
from billing.models import Tarifa, Valorizacion
from crm.models import Cliente
from trucks.models import Vehiculo

ERRORES_BD = (DataError, IntegrityError, InternalError)


@skipUnless(connection.vendor == 'postgresql', 'Solo aplica a PostgreSQL')
class BaseActivaTests(EscenarioV2):
    def setUp(self):
        super().setUp()
        asignar_automaticamente(self.solicitud)
        self.asignacion = Asignacion.objects.get(solicitud=self.solicitud)

    def sql(self, consulta, params=()):
        with connection.cursor() as cursor:
            cursor.execute(consulta, params)
            return cursor.fetchall() if cursor.description else None

    def en_ruta(self):
        Asignacion.objects.filter(pk=self.asignacion.pk).update(estado_operativo='Listo para salir', km_inicial=1000)
        self.asignacion.refresh_from_db()
        iniciar_ruta(self.asignacion)

    def test_dominio_rechaza_dni_invalido(self):
        with self.assertRaises(ERRORES_BD), transaction.atomic():
            self.sql("UPDATE drivers_conductor SET dni = '12AB' WHERE driver_id = %s", [self.conductor.pk])

    def test_enum_rechaza_estado_que_no_existe(self):
        with self.assertRaises(ERRORES_BD), transaction.atomic():
            self.sql("UPDATE service_requests_solicitudservicio SET estado_solicitud = 'Inventado' WHERE request_id = %s",
                     [self.solicitud.pk])

    def test_trigger_impide_asignar_unidad_en_mantenimiento(self):
        otra = self.crear_vehiculo('TST-200', 'Camioneta', 4)
        Vehiculo.objects.filter(pk=otra.pk).update(estado='En mantenimiento')
        with self.assertRaises(ERRORES_BD), transaction.atomic():
            Asignacion.objects.filter(pk=self.asignacion.pk).update(vehiculo=otra)

    def test_trigger_no_bloquea_guardar_sin_cambiar_vehiculo(self):
        Vehiculo.objects.filter(pk=self.vehiculo.pk).update(estado='En mantenimiento')
        self.asignacion.observacion = 'Unidad enviada a revisión'
        self.asignacion.save()

    def test_procedimiento_cierra_servicio_y_crea_valorizacion(self):
        Tarifa.objects.create(cliente=Cliente.obtener('Cliente Demo S.A.C.'), tipo_vehiculo=self.camioneta,
                              tarifa_base=Decimal('680'), km_incluidos=380, precio_km_adicional=Decimal('3.20'))
        self.en_ruta()
        self.sql('CALL sp_completar_servicio(%s, %s)', [self.asignacion.pk, 1400])
        self.asignacion.refresh_from_db()
        self.solicitud.refresh_from_db()
        self.conductor.refresh_from_db()
        self.assertEqual(self.asignacion.estado_operativo, 'Completado')
        self.assertEqual(self.solicitud.estado_solicitud, 'Completada')
        self.assertEqual(self.conductor.estado, 'Disponible')
        v = Valorizacion.objects.get(solicitud=self.solicitud)
        self.assertEqual(v.km_adicionales, 20)
        self.assertEqual(v.total, Decimal('744.00'))
        self.assertEqual(self.sql('SELECT a.km_recorridos FROM assignments_asignacion a WHERE a.assignment_id = %s',
                                  [self.asignacion.pk])[0][0], 400)
        self.assertEqual(self.sql('SELECT (fn_calcular_valorizacion(%s)).total', [v.pk])[0][0], Decimal('744.00'))

    def test_procedimiento_rechaza_servicio_que_no_esta_en_ruta(self):
        with self.assertRaises(ERRORES_BD), transaction.atomic():
            self.sql('CALL sp_completar_servicio(%s, %s)', [self.asignacion.pk, 1400])
        self.assertFalse(Valorizacion.objects.exists())
