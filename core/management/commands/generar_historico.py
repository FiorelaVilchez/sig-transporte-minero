"""
Historial de servicios de demostración para el Data Mart (Evidencia 02).

Cada servicio pasa por las mismas funciones que usa el sistema: la asignación
automática con las reglas R1 a R10, el checklist, la salida a ruta, las
incidencias y el cierre con su valorización. Después se ajustan las fechas de
registro para que correspondan al día del servicio.

Uso:  python manage.py seed_data
      python manage.py generar_historico            (mayo a octubre, por defecto)
      python manage.py generar_historico --reiniciar
"""
import datetime
import random
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from alerts.models import Alerta
from assignments.models import (
    Asignacion, ChecklistPreoperacional, GastoServicio, Incidencia, Notificacion,
)
from assignments.services import (
    asignar_automaticamente, completar_servicio, iniciar_ruta, registrar_checklist, reportar_incidencia,
)
from billing.models import Tarifa, Valorizacion
from billing.services import cambiar_estado
from crm.models import Cliente
from drivers.models import Conductor
from service_requests.models import CambioSolicitud, SolicitudServicio
from service_requests.services import registrar_cambio
from trucks.models import TipoVehiculo, Vehiculo

MARCA = 'Solicitud registrada (historial)'

# razón social, peso en la demanda, tipos de unidad que suele pedir
CLIENTES = [
    ('Andes Perforaciones S.A.C.', 30, ['Van / Sprinter', 'Bus', 'Camioneta']),
    ('Montajes Titicaca S.R.L.', 24, ['Bus', 'Minibús']),
    ('Geoservicios del Sur E.I.R.L.', 15, ['Camioneta', 'Van / Sprinter']),
    ('Construcciones Altiplánicas S.A.C.', 11, ['Minibús', 'Van / Sprinter']),
    ('Servicios Mineros Aymara S.A.C.', 12, ['Bus', 'Minibús', 'Van / Sprinter']),
    ('Ingeniería Collao E.I.R.L.', 8, ['Camioneta']),
]

# tarifas de los clientes que no las tienen en seed_data
TARIFAS_NUEVAS = {
    'Servicios Mineros Aymara S.A.C.': [('Camioneta', '700.00', 380, '3.30'), ('Van / Sprinter', '1180.00', 380, '4.60'),
                                        ('Minibús', '1690.00', 380, '5.90'), ('Bus', '2300.00', 380, '7.20')],
    'Ingeniería Collao E.I.R.L.': [('Camioneta', '650.00', 350, '3.00'), ('Van / Sprinter', '1120.00', 350, '4.40'),
                                   ('Minibús', '1600.00', 350, '5.60'), ('Bus', '2200.00', 350, '6.80')],
}

# origen, destino, km estimados, desvío medio en km, probabilidad de incidencia grave
RUTAS = [
    ('Juliaca', 'U.M. Cerro Azul', 380, 12, 0.04),
    ('Puno', 'U.M. Pampa Blanca', 460, 20, 0.11),
    ('Juliaca', 'U.M. Santa Lucía', 320, 8, 0.03),
    ('Puno', 'U.M. Laguna Verde', 410, 15, 0.07),
]

PASAJEROS = {'Camioneta': (2, 4), 'Van / Sprinter': (8, 15), 'Minibús': (18, 30), 'Bus': (32, 45)}
SOLES_POR_KM = {'Camioneta': '0.55', 'Van / Sprinter': '0.80', 'Minibús': '1.10', 'Bus': '1.40'}
HORAS = [(5, 0), (5, 30), (6, 0), (6, 30)]
DEMANDA_MES = {5: 1.4, 6: 1.7, 7: 2.0, 8: 2.2, 9: 1.9, 10: 1.7}

INCIDENCIAS_GRAVES = [
    ('Falla mecánica', 'Pérdida de potencia y recalentamiento del motor en la subida.'),
    ('Vía bloqueada o clima', 'Nevada intensa cerró la vía de acceso a la unidad minera.'),
    ('Accidente', 'Despiste leve sin heridos; la unidad no puede continuar.'),
]
INCIDENCIAS_LEVES = [
    ('Retraso del personal', 'El personal llegó tarde al punto de recojo.'),
    ('Vía bloqueada o clima', 'Tramo con niebla; se redujo la velocidad.'),
    ('Otro', 'Control policial prolongado en la garita.'),
]


class Command(BaseCommand):
    help = 'Genera un historial de servicios cerrados y valorizados para el Data Mart.'

    def add_arguments(self, parser):
        parser.add_argument('--desde', default='2026-05-01', help='Primer día del historial (AAAA-MM-DD).')
        parser.add_argument('--hasta', default=None, help='Último día del historial; por defecto, 30 días antes de hoy.')
        parser.add_argument('--semilla', type=int, default=2026)
        parser.add_argument('--reiniciar', action='store_true', help='Borra el historial generado antes y lo vuelve a crear.')

    def handle(self, *args, **opts):
        hoy = datetime.date.today()
        desde = datetime.date.fromisoformat(opts['desde'])
        hasta = datetime.date.fromisoformat(opts['hasta']) if opts['hasta'] else hoy - datetime.timedelta(days=30)
        if desde > hasta:
            raise CommandError('La fecha inicial es posterior a la final.')
        if not Conductor.objects.exists() or not Vehiculo.objects.exists():
            raise CommandError('Primero ejecute python manage.py seed_data.')

        if opts['reiniciar']:
            self.stdout.write(f'Historial anterior eliminado: {borrar_historial()} solicitudes.')
        elif CambioSolicitud.objects.filter(motivo=MARCA).exists():
            raise CommandError('Ya existe un historial generado. Use --reiniciar para crearlo de nuevo.')

        self.azar = random.Random(opts['semilla'])
        self.hoy = hoy
        self.inicio_ejecucion = timezone.now()
        self.clientes = self._clientes()
        self.odometro = {}
        estados_conductor = dict(Conductor.objects.values_list('pk', 'estado'))
        estados_vehiculo = dict(Vehiculo.objects.values_list('pk', 'estado'))
        # Los servicios en ruta de hoy no deben bloquear a sus recursos en fechas pasadas.
        Conductor.objects.filter(estado='Ocupado').update(estado='Disponible')
        Vehiculo.objects.filter(estado='En servicio').update(estado='Disponible')
        self.en_taller = {}
        self.en_descanso = {}

        totales = {'solicitudes': 0, 'completados': 0, 'con_incidencia': 0, 'canceladas': 0}
        fecha = desde
        while fecha <= hasta:
            with transaction.atomic():
                self._devolver_de_taller(fecha)
                for clave, n in self._dia(fecha).items():
                    totales[clave] += n
            if fecha.day == 1 or fecha == hasta:
                self.stdout.write(f'  {fecha:%Y-%m}: {totales["solicitudes"]} solicitudes acumuladas')
            fecha += datetime.timedelta(days=1)

        for pk, estado in estados_conductor.items():
            Conductor.objects.filter(pk=pk).update(estado=estado)
        for pk, estado in estados_vehiculo.items():
            Vehiculo.objects.filter(pk=pk).update(estado=estado)

        self.stdout.write(self.style.SUCCESS(
            f"Historial generado del {desde:%d/%m/%Y} al {hasta:%d/%m/%Y}: {totales['solicitudes']} solicitudes, "
            f"{totales['completados']} servicios completados, {totales['con_incidencia']} con incidencia grave "
            f"y {totales['canceladas']} canceladas."
        ))

    def _clientes(self):
        clientes = []
        for nombre, peso, tipos in CLIENTES:
            cliente = Cliente.obtener(nombre)
            for tipo, base, km, pkm in TARIFAS_NUEVAS.get(nombre, []):
                Tarifa.objects.get_or_create(
                    cliente=cliente, tipo_vehiculo=TipoVehiculo.objects.get(nombre=tipo),
                    defaults={'tarifa_base': Decimal(base), 'km_incluidos': km, 'precio_km_adicional': Decimal(pkm)},
                )
            clientes.append((cliente, peso, tipos))
        return clientes

    def _devolver_de_taller(self, fecha):
        for pk, regreso in list(self.en_taller.items()):
            if fecha >= regreso:
                Vehiculo.objects.filter(pk=pk, estado='En mantenimiento').update(estado='Disponible')
                del self.en_taller[pk]
        for pk, regreso in list(self.en_descanso.items()):
            if fecha >= regreso:
                Conductor.objects.filter(pk=pk, estado='No apto').update(estado='Disponible')
                del self.en_descanso[pk]

    def _dia(self, fecha):
        az = self.azar
        conteo = {'solicitudes': 0, 'completados': 0, 'con_incidencia': 0, 'canceladas': 0}
        media = DEMANDA_MES.get(fecha.month, 1.6) * (0.6 if fecha.weekday() == 6 else 1)
        cantidad = max(0, round(az.gauss(media, 0.8)))

        programados = []
        for _ in range(cantidad):
            cliente, _, tipos = az.choices(self.clientes, weights=[c[1] for c in self.clientes])[0]
            tipo = az.choice(tipos)
            origen, destino, km, _, _ = ruta = az.choice(RUTAS)
            s = SolicitudServicio.objects.create(
                cliente=cliente, fecha_servicio=fecha, hora_servicio=datetime.time(*az.choice(HORAS)),
                origen=origen, destino=destino, tipo_servicio='Traslado de personal',
                prioridad=az.choice(['Alta', 'Media', 'Media', 'Baja']), tipo_vehiculo_requerido_id=tipo,
                pasajeros=az.randint(*PASAJEROS[tipo]), duracion_horas=az.choice([8, 10]), km_estimados=km,
            )
            CambioSolicitud.objects.create(solicitud=s, campo='registro', valor_nuevo='Pendiente', motivo=MARCA)
            conteo['solicitudes'] += 1

            if az.random() < 0.04:
                self._cancelar(s, 'El cliente postergó la movilización de su personal.')
                conteo['canceladas'] += 1
                continue
            resultado = asignar_automaticamente(s)
            if resultado['exito']:
                programados.append((s, resultado['asignacion'], ruta))
            else:
                self._cancelar(s, 'No se contó con conductor o unidad disponible para la fecha.')
                conteo['canceladas'] += 1

        for s, asignacion, ruta in programados:
            for clave, n in self._ejecutar(s, asignacion, ruta).items():
                conteo[clave] += n
            self._fechar(s)
        return conteo

    def _cancelar(self, s, motivo):
        anterior = s.estado_solicitud
        s.estado_solicitud = 'Cancelada'
        s.save()
        registrar_cambio(s, None, 'Estado de Solicitud', anterior, 'Cancelada', motivo)
        self._fechar(s)

    def _ejecutar(self, s, asignacion, ruta):
        az = self.azar
        conteo = {'completados': 0, 'con_incidencia': 0, 'canceladas': 0}
        _, _, km, desvio, p_grave = ruta

        if az.random() < p_grave:
            self._salir(asignacion)
            tipo, descripcion = az.choice(INCIDENCIAS_GRAVES)
            reportar_incidencia(asignacion, Incidencia(tipo=tipo, gravedad='Alta', descripcion=descripcion, resuelta=True))
            asignacion.refresh_from_db()
            asignacion.km_final = asignacion.km_inicial + az.randint(40, km // 2)
            asignacion.save(update_fields=['km_final'])
            self.odometro[asignacion.vehiculo_id] = asignacion.km_final
            conteo['con_incidencia'] += 1
            s.refresh_from_db()
            if tipo == 'Vía bloqueada o clima':
                self._cancelar(s, 'Vía cerrada por nevada; el cliente reprogramó la movilización.')
                conteo['canceladas'] += 1
                return conteo
            regreso = s.fecha_servicio + datetime.timedelta(days=az.randint(2, 5))
            self.en_taller[asignacion.vehiculo_id] = regreso
            Vehiculo.objects.filter(pk=asignacion.vehiculo_id).update(estado='En mantenimiento')
            if tipo == 'Accidente':
                self.en_descanso[asignacion.conductor_id] = regreso
                Conductor.objects.filter(pk=asignacion.conductor_id).update(estado='No apto')
            reemplazo = asignar_automaticamente(s)
            if not reemplazo['exito']:
                self._cancelar(s, 'No se consiguió una unidad de reemplazo.')
                conteo['canceladas'] += 1
                return conteo
            asignacion = reemplazo['asignacion']

        self._salir(asignacion)
        if az.random() < 0.10:
            tipo, descripcion = az.choice(INCIDENCIAS_LEVES)
            reportar_incidencia(asignacion, Incidencia(tipo=tipo, gravedad='Baja', descripcion=descripcion, resuelta=True))
        recorrido = max(km - 15, round(az.gauss(km + desvio, 12)))
        km_final = asignacion.km_inicial + recorrido
        self._gastos(asignacion, recorrido)
        valorizacion = completar_servicio(asignacion, km_final=km_final)
        self.odometro[asignacion.vehiculo_id] = km_final
        self._cobrar(valorizacion, s.fecha_servicio)
        conteo['completados'] += 1
        return conteo

    def _salir(self, asignacion):
        vehiculo = asignacion.vehiculo
        km = self.odometro.get(vehiculo.pk)
        if km is None:
            km = 30000 + (vehiculo.pk % 10) * 6500
        km += self.azar.randint(5, 40)
        registrar_checklist(asignacion, ChecklistPreoperacional(
            frenos=True, llantas=True, luces=True, cinturones=True, botiquin=True, extintor=True, radio_gps=True,
            horas_sueno=Decimal(self.azar.choice(['7.0', '7.5', '8.0', '8.5'])), km_inicial=km,
        ))
        asignacion.refresh_from_db()
        iniciar_ruta(asignacion)
        asignacion.refresh_from_db()

    def _gastos(self, asignacion, recorrido):
        tipo = asignacion.vehiculo.tipo_id
        combustible = (Decimal(recorrido) * Decimal(SOLES_POR_KM[tipo]) * Decimal(str(self.azar.uniform(0.92, 1.08))))
        GastoServicio.objects.create(asignacion=asignacion, concepto='Combustible',
                                     monto=combustible.quantize(Decimal('0.01')), detalle='Grifo en ruta')
        GastoServicio.objects.create(asignacion=asignacion, concepto='Peaje', monto=Decimal('18.50'))
        if self.azar.random() < 0.35:
            GastoServicio.objects.create(asignacion=asignacion, concepto='Viático', monto=Decimal('35.00'),
                                         detalle='Alimentación del conductor')

    def _cobrar(self, valorizacion, fecha_servicio):
        """Avanza la valorización por su ciclo de cobro hasta donde lo permita la fecha de hoy."""
        az = self.azar
        envio = fecha_servicio + datetime.timedelta(days=az.randint(1, 3))
        pasos = [('Enviada', envio)]
        if az.random() < 0.08:
            observada = envio + datetime.timedelta(days=az.randint(3, 6))
            pasos += [('Observada', observada), ('Enviada', observada + datetime.timedelta(days=az.randint(2, 4)))]
        conformidad = pasos[-1][1] + datetime.timedelta(days=max(2, round(az.gauss(9, 5))))
        factura = conformidad + datetime.timedelta(days=az.randint(1, 3))
        pago = factura + datetime.timedelta(days=az.randint(12, 35))
        pasos += [('Conforme', conformidad), ('Facturada', factura), ('Pagada', pago)]

        fechas = {}
        for estado, dia in pasos:
            if dia >= self.hoy:
                break
            cambiar_estado(valorizacion, estado, numero_factura=f'F001-{valorizacion.solicitud_id:06d}',
                           observacion='Corregir kilometraje del parte diario.' if estado == 'Observada' else '')
            campo = {'Enviada': 'fecha_envio', 'Conforme': 'fecha_conformidad',
                     'Facturada': 'fecha_factura', 'Pagada': 'fecha_pago'}.get(estado)
            if campo:
                fechas[campo] = dia
        if fechas:
            Valorizacion.objects.filter(pk=valorizacion.pk).update(**fechas)

    def _fechar(self, s):
        """Lleva las fechas de registro al día del servicio en lugar de la fecha de hoy."""
        inicio = timezone.make_aware(s.inicio)
        registro = inicio - datetime.timedelta(days=3, hours=-4)
        SolicitudServicio.objects.filter(pk=s.pk).update(created_at=registro, updated_at=inicio)
        cambios = list(s.cambios.order_by('id'))
        for i, cambio in enumerate(cambios):
            momento = registro if i == 0 else inicio + datetime.timedelta(minutes=10 * i)
            if cambio.campo == 'Estado de Solicitud' and cambio.valor_nuevo == 'Asignada':
                momento = registro + datetime.timedelta(hours=2)
            CambioSolicitud.objects.filter(pk=cambio.pk).update(fecha=momento)

        for a in Asignacion.objects.filter(solicitud=s).select_related('conductor'):
            asignado = registro + datetime.timedelta(hours=2)
            salida = inicio + datetime.timedelta(minutes=self.azar.randint(-10, 15))
            llegada = salida + datetime.timedelta(hours=s.duracion_horas, minutes=self.azar.randint(-40, 50))
            if a.estado_operativo == 'Con incidencia':
                llegada = salida + datetime.timedelta(hours=self.azar.randint(2, 5))
            Asignacion.objects.filter(pk=a.pk).update(
                fecha_asignacion=asignado, created_at=asignado, updated_at=llegada,
                inicio_real=salida if a.inicio_real else None,
                fin_real=llegada if a.estado_operativo == 'Completado' else None,
            )
            ChecklistPreoperacional.objects.filter(asignacion=a).update(fecha=salida - datetime.timedelta(minutes=40))
            Incidencia.objects.filter(asignacion=a).update(fecha=salida + datetime.timedelta(hours=3))
            GastoServicio.objects.filter(asignacion=a).update(fecha=salida + datetime.timedelta(hours=2))
            Valorizacion.objects.filter(solicitud=s).update(created_at=llegada)
            Notificacion.objects.filter(conductor=a.conductor, fecha__gte=self.inicio_ejecucion).update(leida=True, fecha=asignado)
        Alerta.objects.filter(estado_alerta='Activa', tipo_alerta__in=['Incidencia operativa', 'Checklist no aprobado'],
                              mensaje__contains=f'#{s.request_id} ').update(
            estado_alerta='Resuelta', fecha_generacion=inicio, created_at=inicio)


def borrar_historial():
    ids = list(CambioSolicitud.objects.filter(motivo=MARCA).values_list('solicitud_id', flat=True))
    with transaction.atomic():
        Valorizacion.objects.filter(solicitud_id__in=ids).delete()
        Asignacion.objects.filter(solicitud_id__in=ids).delete()
        CambioSolicitud.objects.filter(solicitud_id__in=ids).delete()
        SolicitudServicio.objects.filter(request_id__in=ids).delete()
    return len(ids)
