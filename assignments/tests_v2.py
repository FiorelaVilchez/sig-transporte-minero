"""Pruebas de las mejoras de la versión 2.0 (M0 a M7)."""
import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from alerts.models import Alerta
from assignments.models import Asignacion, ChecklistPreoperacional, Incidencia, Notificacion
from assignments.services import (
    asignar_automaticamente, completar_servicio, iniciar_ruta, registrar_checklist, reportar_incidencia,
)
from assignments.validators import validar_asignacion
from billing.models import Tarifa, Valorizacion
from billing.services import cambiar_estado
from core.models import PerfilUsuario
from documents.models import DocumentoConductor, DocumentoVehiculo, RequisitoDocumental
from drivers.models import Conductor
from service_requests.models import CambioSolicitud, SolicitudServicio
from trucks.models import TipoVehiculo, Vehiculo

HOY = datetime.date.today()


def dias(n):
    return HOY + datetime.timedelta(days=n)


class EscenarioV2(TestCase):
    """Conductor y unidad con todos los documentos de la matriz al día."""

    def setUp(self):
        self.camioneta = TipoVehiculo.objects.get(nombre='Camioneta')
        self.bus = TipoVehiculo.objects.get(nombre='Bus')
        self.conductor = self.crear_conductor('Ana', 'Quispe', '10000001', ['Camioneta', 'Bus'])
        self.vehiculo = self.crear_vehiculo('TST-100', 'Camioneta', 4)
        self.solicitud = self.crear_solicitud(dias(3), datetime.time(6, 0), 'Camioneta', pasajeros=3)

    def crear_conductor(self, nombres, apellidos, dni, tipos, categoria='A-IIIc', anios=10):
        c = Conductor.objects.create(
            nombres=nombres, apellidos=apellidos, dni=dni, licencia=f'Q{dni}', estado='Disponible',
            categoria_licencia=categoria, fecha_obtencion_licencia=dias(-365 * anios - 5),
            fecha_nacimiento=datetime.date(1985, 1, 1), fecha_ingreso=datetime.date(2018, 1, 1),
        )
        c.tipos_habilitados.set(TipoVehiculo.objects.filter(nombre__in=tipos))
        for req in RequisitoDocumental.objects.filter(aplica_a='Conductor', activo=True):
            DocumentoConductor.objects.create(
                conductor=c, tipo_documento=req.tipo_documento, fecha_emision=dias(-100),
                fecha_vencimiento=dias(300), estado_mina='Aprobado' if req.requiere_visto_bueno_mina else 'No requiere',
            )
        return c

    def crear_vehiculo(self, placa, tipo, asientos):
        v = Vehiculo.objects.create(placa=placa, tipo_id=tipo, capacidad=asientos, estado='Disponible')
        for req in RequisitoDocumental.objects.filter(aplica_a='Vehículo', activo=True):
            if req.aplica_al_tipo(v.tipo):
                DocumentoVehiculo.objects.create(
                    vehiculo=v, tipo_documento=req.tipo_documento, fecha_emision=dias(-100),
                    fecha_vencimiento=dias(300) if req.vence else None,
                    estado_mina='Aprobado' if req.requiere_visto_bueno_mina else 'No requiere',
                )
        return v

    def crear_solicitud(self, fecha, hora, tipo, pasajeros=3, duracion=8, cliente='Cliente Demo S.A.C.', estado='Pendiente'):
        return SolicitudServicio.objects.create(
            cliente=cliente, fecha_servicio=fecha, hora_servicio=hora, origen='Juliaca', destino='U.M. Cerro Azul',
            tipo_servicio='Traslado de personal', prioridad='Alta', tipo_vehiculo_requerido_id=tipo,
            pasajeros=pasajeros, duracion_horas=duracion, km_estimados=380, estado_solicitud=estado,
        )

    def validar(self, conductor=None, vehiculo=None, solicitud=None):
        return validar_asignacion(
            conductor or self.conductor, vehiculo or self.vehiculo,
            solicitud=solicitud or self.solicitud, generar_alertas=False,
        )


class CatalogoYMatrizTests(EscenarioV2):
    def test_catalogo_inicial_y_matriz_cargados_por_migracion(self):
        self.assertTrue(TipoVehiculo.objects.filter(nombre='Van / Sprinter', activo=True).exists())
        self.assertFalse(TipoVehiculo.objects.get(nombre='Volquete').activo)
        self.assertEqual(RequisitoDocumental.objects.filter(aplica_a='Conductor').count(), 6)
        ocupantes = RequisitoDocumental.objects.get(tipo_documento='Seguro de ocupantes')
        self.assertFalse(ocupantes.aplica_al_tipo(self.camioneta))
        self.assertTrue(ocupantes.aplica_al_tipo(self.bus))

    def test_caso_feliz_con_matriz_completa(self):
        resultado = self.validar()
        self.assertEqual(resultado['veredicto'], 'Aprobada', resultado['bloqueos'])

    def test_r1_falta_documento_bloqueante(self):
        DocumentoConductor.objects.filter(conductor=self.conductor, tipo_documento='Seguro Vida Ley').delete()
        resultado = self.validar()
        self.assertIn('R1: Falta Seguro Vida Ley del conductor', resultado['bloqueos'])

    def test_falta_documento_no_bloqueante_solo_observa(self):
        DocumentoConductor.objects.filter(conductor=self.conductor, tipo_documento='Récord de conductor').delete()
        resultado = self.validar()
        self.assertEqual(resultado['veredicto'], 'Observada')

    def test_r2_documento_bloqueante_vencido(self):
        doc = DocumentoVehiculo.objects.get(vehiculo=self.vehiculo, tipo_documento='SOAT')
        doc.fecha_vencimiento = dias(-1)
        doc.save()
        self.assertIn('R2: SOAT del vehículo vencido', self.validar()['bloqueos'])

    def test_documento_renovado_reemplaza_al_vencido(self):
        DocumentoVehiculo.objects.create(
            vehiculo=self.vehiculo, tipo_documento='SOAT', fecha_emision=dias(-400), fecha_vencimiento=dias(-35),
        )
        self.assertEqual(self.validar()['veredicto'], 'Aprobada')

    def test_r8_visto_bueno_de_mina_pendiente(self):
        doc = DocumentoConductor.objects.get(conductor=self.conductor, tipo_documento='Inducción en mina')
        doc.estado_mina = 'Pendiente'
        doc.save()
        self.assertTrue(any(b.startswith('R8') for b in self.validar()['bloqueos']))

    def test_tarjeta_de_propiedad_no_vence(self):
        doc = DocumentoVehiculo.objects.get(vehiculo=self.vehiculo, tipo_documento='Tarjeta de propiedad')
        self.assertIsNone(doc.fecha_vencimiento)
        self.assertEqual(doc.estado_documento, 'Vigente')


class ReglasR6aR10Tests(EscenarioV2):
    def test_r6_conductor_no_habilitado_para_el_tipo(self):
        solo_bus = self.crear_conductor('Beto', 'Mamani', '10000002', ['Bus'])
        self.assertTrue(any(b.startswith('R6') for b in self.validar(conductor=solo_bus)['bloqueos']))

    def test_r6_experiencia_insuficiente(self):
        novato = self.crear_conductor('Ciro', 'Apaza', '10000003', ['Camioneta'], anios=1)
        bloqueos = self.validar(conductor=novato)['bloqueos']
        self.assertTrue(any('Experiencia de 1 años' in b for b in bloqueos), bloqueos)

    def test_r6_categoria_de_licencia_insuficiente(self):
        bus = self.crear_vehiculo('TST-200', 'Bus', 45)
        conductor = self.crear_conductor('Dina', 'Flores', '10000004', ['Bus'], categoria='A-IIa')
        sol = self.crear_solicitud(dias(3), datetime.time(6, 0), 'Bus', pasajeros=40)
        bloqueos = self.validar(conductor=conductor, vehiculo=bus, solicitud=sol)['bloqueos']
        self.assertTrue(any('Licencia A-IIa' in b for b in bloqueos), bloqueos)

    def test_r7_asientos_insuficientes(self):
        self.solicitud.pasajeros = 6
        self.solicitud.save()
        self.assertTrue(any(b.startswith('R7') for b in self.validar()['bloqueos']))

    def test_r9_cruce_de_horario_con_descanso(self):
        asignar_automaticamente(self.solicitud)
        # Mismo día, 10 h después del inicio: termina a las 14:00 y faltan 8 h de descanso.
        otra = self.crear_solicitud(dias(3), datetime.time(16, 0), 'Camioneta')
        otro_vehiculo = self.crear_vehiculo('TST-101', 'Camioneta', 4)
        bloqueos = self.validar(vehiculo=otro_vehiculo, solicitud=otra)['bloqueos']
        self.assertTrue(any(b.startswith('R9: El conductor') for b in bloqueos), bloqueos)

    def test_servicios_sin_cruce_permiten_dos_asignaciones_al_mismo_conductor(self):
        asignar_automaticamente(self.solicitud)
        siguiente = self.crear_solicitud(dias(4), datetime.time(6, 0), 'Camioneta')
        self.assertEqual(self.validar(solicitud=siguiente)['veredicto'], 'Aprobada')

    def test_r9_vehiculo_ocupado_en_el_horario(self):
        asignar_automaticamente(self.solicitud)
        otro_conductor = self.crear_conductor('Eva', 'Ticona', '10000005', ['Camioneta'])
        otra = self.crear_solicitud(dias(3), datetime.time(9, 0), 'Camioneta')
        bloqueos = self.validar(conductor=otro_conductor, solicitud=otra)['bloqueos']
        self.assertTrue(any(b.startswith('R9: El vehículo') for b in bloqueos), bloqueos)

    def test_r10_limite_de_horas_semanales(self):
        lunes = HOY - datetime.timedelta(days=HOY.weekday()) + datetime.timedelta(days=7)
        for i in range(5):
            s = self.crear_solicitud(lunes + datetime.timedelta(days=i), datetime.time(6, 0), 'Camioneta', duracion=12, estado='Asignada')
            Asignacion.objects.create(solicitud=s, conductor=self.conductor, vehiculo=self.vehiculo, estado_asignacion='Aprobada')
        sexto = self.crear_solicitud(lunes + datetime.timedelta(days=5), datetime.time(20, 0), 'Camioneta', duracion=2)
        otro_vehiculo = self.crear_vehiculo('TST-102', 'Camioneta', 4)
        bloqueos = self.validar(vehiculo=otro_vehiculo, solicitud=sexto)['bloqueos']
        self.assertTrue(any(b.startswith('R10') for b in bloqueos), bloqueos)

    def test_auto_asignacion_prefiere_al_conductor_con_menos_horas(self):
        segundo = self.crear_conductor('Fany', 'Zela', '10000006', ['Camioneta'])
        previo = self.crear_solicitud(self.solicitud.fecha_servicio, datetime.time(23, 0), 'Camioneta', duracion=1, estado='Completada')
        Asignacion.objects.create(solicitud=previo, conductor=self.conductor, vehiculo=self.vehiculo,
                                  estado_asignacion='Aprobada', estado_operativo='Completado')
        resultado = asignar_automaticamente(self.solicitud)
        self.assertTrue(resultado['exito'])
        self.assertEqual(resultado['asignacion'].conductor, segundo)


class EjecucionDelServicioTests(EscenarioV2):
    def setUp(self):
        super().setUp()
        asignar_automaticamente(self.solicitud)
        self.asignacion = Asignacion.objects.get(solicitud=self.solicitud)

    def checklist(self, **cambios):
        datos = dict(frenos=True, llantas=True, luces=True, cinturones=True, botiquin=True, extintor=True,
                     radio_gps=True, horas_sueno=Decimal('7'), km_inicial=1000)
        datos.update(cambios)
        return registrar_checklist(self.asignacion, ChecklistPreoperacional(**datos))

    def test_checklist_con_falla_critica_no_aprueba_y_alerta(self):
        c = self.checklist(frenos=False)
        self.assertFalse(c.aprobado)
        self.asignacion.refresh_from_db()
        self.assertEqual(self.asignacion.estado_operativo, 'Programado')
        self.assertTrue(Alerta.objects.filter(tipo_alerta='Checklist no aprobado').exists())

    def test_checklist_con_poco_descanso_no_aprueba(self):
        self.assertFalse(self.checklist(horas_sueno=Decimal('5')).aprobado)

    def test_flujo_completo_hasta_la_valorizacion(self):
        Tarifa.objects.create(cliente='cliente demo s.a.c.', tipo_vehiculo=self.camioneta,
                              tarifa_base=Decimal('680'), km_incluidos=380, precio_km_adicional=Decimal('3.20'))
        self.checklist()
        self.asignacion.refresh_from_db()
        self.assertEqual(self.asignacion.estado_operativo, 'Listo para salir')
        iniciar_ruta(self.asignacion)
        self.conductor.refresh_from_db()
        self.assertEqual(self.conductor.estado, 'Ocupado')
        v = completar_servicio(self.asignacion, km_final=1400)
        self.conductor.refresh_from_db()
        self.vehiculo.refresh_from_db()
        self.assertEqual(self.conductor.estado, 'Disponible')
        self.assertEqual(self.vehiculo.estado, 'Disponible')
        # 400 km recorridos: 20 km adicionales x 3.20 = 64
        self.assertEqual(v.km_adicionales, 20)
        self.assertEqual(v.total, Decimal('744.00'))
        self.assertEqual(v.estado, 'Borrador')

    def test_incidencia_grave_reprograma_y_manda_unidad_a_mantenimiento(self):
        self.checklist()
        iniciar_ruta(self.asignacion)
        reportar_incidencia(self.asignacion, Incidencia(tipo='Falla mecánica', gravedad='Alta', descripcion='Motor'))
        self.solicitud.refresh_from_db()
        self.vehiculo.refresh_from_db()
        self.conductor.refresh_from_db()
        self.assertEqual(self.solicitud.estado_solicitud, 'Reprogramada')
        self.assertEqual(self.vehiculo.estado, 'En mantenimiento')
        self.assertEqual(self.conductor.estado, 'Disponible')
        self.assertTrue(Alerta.objects.filter(tipo_alerta='Incidencia operativa', nivel_riesgo='Alto').exists())

    def test_ciclo_de_cobro_y_transiciones_invalidas(self):
        self.checklist()
        iniciar_ruta(self.asignacion)
        v = completar_servicio(self.asignacion, km_final=1300)
        self.assertIsNone(v.tarifa)
        with self.assertRaises(ValueError):
            cambiar_estado(v, 'Pagada')
        cambiar_estado(v, 'Enviada')
        cambiar_estado(v, 'Conforme')
        with self.assertRaises(ValueError):
            cambiar_estado(v, 'Facturada')  # falta el número de factura
        cambiar_estado(v, 'Facturada', numero_factura='F001-000001')
        cambiar_estado(v, 'Pagada')
        self.assertEqual(Valorizacion.objects.get().estado, 'Pagada')

    def test_cobro_atrasado_despues_de_15_dias(self):
        self.checklist()
        iniciar_ruta(self.asignacion)
        v = completar_servicio(self.asignacion, km_final=1300)
        cambiar_estado(v, 'Enviada')
        v.fecha_envio = dias(-16)
        self.assertTrue(v.cobro_atrasado)


class VistasV2Tests(EscenarioV2):
    def usuario(self, nombre, rol, conductor=None):
        u = User.objects.create_user(username=nombre, password='x')
        PerfilUsuario.objects.create(usuario=u, rol=rol, conductor=conductor)
        return u

    def test_editar_solicitud_asignada_registra_bitacora_y_revalida(self):
        asignar_automaticamente(self.solicitud)
        self.client.force_login(self.usuario('admin', 'Administrador de operaciones'))
        datos = {
            'cliente': self.solicitud.cliente, 'fecha_servicio': self.solicitud.fecha_servicio.isoformat(),
            'hora_servicio': '06:00', 'origen': 'Juliaca', 'destino': 'U.M. Cerro Azul',
            'tipo_servicio': 'Traslado de personal', 'prioridad': 'Alta', 'tipo_vehiculo_requerido': 'Camioneta',
            'pasajeros': 6, 'duracion_horas': 8, 'km_estimados': 380, 'estado_solicitud': 'Asignada',
        }
        r = self.client.post(reverse('service_requests:solicitud_update', args=[self.solicitud.pk]), datos)
        self.assertEqual(r.status_code, 200)  # sin motivo no se acepta
        datos['motivo_cambio'] = 'El cliente agregó tres trabajadores'
        r = self.client.post(reverse('service_requests:solicitud_update', args=[self.solicitud.pk]), datos)
        self.assertEqual(r.status_code, 302)
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.estado_solicitud, 'Reprogramada')  # 6 pasajeros no caben (R7)
        self.assertTrue(CambioSolicitud.objects.filter(solicitud=self.solicitud, motivo__icontains='tres trabajadores').exists())
        self.assertTrue(Notificacion.objects.filter(mensaje__icontains='Se canceló').exists())

    def test_portal_conductor_checklist_y_salida(self):
        asignar_automaticamente(self.solicitud)
        asignacion = Asignacion.objects.get()
        self.client.force_login(self.usuario('chofer', 'Conductor', self.conductor))
        url = reverse('assignments:checklist', args=[asignacion.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.post(url, {
            'frenos': 'on', 'llantas': 'on', 'luces': 'on', 'cinturones': 'on',
            'horas_sueno': '7', 'km_inicial': '500',
        })
        asignacion.refresh_from_db()
        self.assertEqual(asignacion.estado_operativo, 'Listo para salir')
        self.client.post(reverse('assignments:iniciar_ruta', args=[asignacion.pk]))
        self.client.post(reverse('assignments:gasto', args=[asignacion.pk]), {'concepto': 'Peaje', 'monto': '18.50'})
        self.client.post(reverse('assignments:finalizar', args=[asignacion.pk]), {'km_final': '880'})
        asignacion.refresh_from_db()
        self.assertEqual(asignacion.estado_operativo, 'Completado')
        self.assertEqual(asignacion.km_recorridos, 380)
        self.assertEqual(asignacion.gastos.count(), 1)

    def test_paginas_nuevas_por_rol(self):
        self.client.force_login(self.usuario('admin', 'Administrador de operaciones'))
        for nombre in ['assignments:programacion', 'core:configuracion', 'billing:valorizacion_list', 'dashboard:operativo']:
            self.assertEqual(self.client.get(reverse(nombre)).status_code, 200, nombre)
        self.assertEqual(self.client.get(reverse('service_requests:solicitud_detail', args=[self.solicitud.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse('core:catalogo_nuevo', args=['requisitos'])).status_code, 200)

        self.client.force_login(self.usuario('fin', 'Finanzas'))
        self.assertEqual(self.client.get(reverse('billing:valorizacion_list')).status_code, 200)
        self.assertEqual(self.client.get(reverse('core:catalogo_nuevo', args=['tarifas'])).status_code, 200)
        self.assertEqual(self.client.get(reverse('core:catalogo_nuevo', args=['tipos'])).status_code, 403)
        self.assertEqual(self.client.get(reverse('drivers:conductor_list')).status_code, 403)

    def test_documento_con_visto_bueno_queda_pendiente_al_registrarse(self):
        self.client.force_login(self.usuario('admin', 'Administrador de operaciones'))
        r = self.client.post(reverse('documents:documento_conductor_create'), {
            'conductor': self.conductor.pk, 'tipo_documento': 'Examen médico',
            'fecha_emision': HOY.isoformat(), 'fecha_vencimiento': dias(365).isoformat(),
        })
        self.assertEqual(r.status_code, 302)
        doc = DocumentoConductor.objects.filter(conductor=self.conductor, tipo_documento='Examen médico').latest('created_at')
        self.assertEqual(doc.estado_mina, 'Pendiente')

    def test_documento_que_vence_exige_fecha(self):
        self.client.force_login(self.usuario('admin', 'Administrador de operaciones'))
        r = self.client.post(reverse('documents:documento_vehiculo_create'), {
            'vehiculo': self.vehiculo.pk, 'tipo_documento': 'SOAT', 'fecha_emision': HOY.isoformat(),
        })
        self.assertEqual(r.status_code, 200)
        r = self.client.post(reverse('documents:documento_vehiculo_create'), {
            'vehiculo': self.vehiculo.pk, 'tipo_documento': 'Tarjeta de propiedad', 'fecha_emision': HOY.isoformat(),
        })
        self.assertEqual(r.status_code, 302)


class FichaSolicitudTests(EscenarioV2):
    def test_ficha_muestra_cambios_registrados_por_el_sistema(self):
        """Un cambio sin usuario (por ejemplo, la asignación automática) no debe romper la ficha."""
        CambioSolicitud.objects.create(solicitud=self.solicitud, campo='registro', valor_nuevo='Pendiente')
        u = User.objects.create_user(username='adm', password='x')
        PerfilUsuario.objects.create(usuario=u, rol='Administrador de operaciones')
        self.client.force_login(u)
        r = self.client.get(reverse('service_requests:solicitud_detail', args=[self.solicitud.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Sistema')

    def test_portada_muestra_los_cinco_roles(self):
        u = User.objects.create_user(username='fin2', password='x', first_name='Rocío')
        PerfilUsuario.objects.create(usuario=u, rol='Finanzas')
        self.client.force_login(u)
        r = self.client.get(reverse('core:home'))
        self.assertContains(r, ', Rocío')
        self.assertContains(r, 'Finanzas')
        self.assertContains(r, 'Base de datos')


class ProgramacionMensualTests(EscenarioV2):
    def setUp(self):
        super().setUp()
        u = User.objects.create_user(username='sup', password='x')
        PerfilUsuario.objects.create(usuario=u, rol='Supervisor')
        self.client.force_login(u)

    def test_vista_mensual_muestra_el_mes_y_los_servicios(self):
        asignar_automaticamente(self.solicitud)
        mes = self.solicitud.fecha_servicio.strftime('%Y-%m')
        r = self.client.get(reverse('assignments:programacion'), {'vista': 'mes', 'mes': mes})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['vista'], 'mes')
        self.assertEqual(r.context['resumen']['servicios'], 1)
        dias = [d for semana in r.context['semanas'] for d in semana]
        self.assertEqual(len(dias) % 7, 0)
        self.assertEqual(dias[0]['fecha'].weekday(), 0)
        dia = next(d for d in dias if d['fecha'] == self.solicitud.fecha_servicio)
        self.assertEqual(dia['total'], 1)
        self.assertContains(r, 'TST-100')

    def test_mes_invalido_usa_el_mes_actual(self):
        r = self.client.get(reverse('assignments:programacion'), {'vista': 'mes', 'mes': 'xx'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['primero'], HOY.replace(day=1))

    def test_vista_semanal_sigue_disponible(self):
        r = self.client.get(reverse('assignments:programacion'))
        self.assertEqual(r.context['vista'], 'semana')
        self.assertEqual(len(r.context['dias']), 7)
